#!/usr/bin/env python3
"""
Testing Tool CLI for hogwarts-bench.

This script executes tests on target LLM using generated questions.
It loads questions, prepares context from the novel, filters questions
based on context length, and executes tests concurrently with answer parsing.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .core.config import Config
from .core.llm_client import LLMClient
from .tester.testing_tool import TestingTool
from .tester.question_checker import QuestionCheckError
from .tester.depth_scheduler import DepthMode


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Execute tests on target LLM using generated questions.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 50k token context (legacy mode)
  python -m src.test --novel data/novel.txt --data_set data/questions.jsonl \\
      --context_length 50000 --output data/results.jsonl
  
  # Depth-aware testing with uniform distribution
  python -m src.test --novel data/novel.txt --data_set data/questions.jsonl \\
      --depth-mode uniform --context-lengths 64000,128000,200000 \\
      --output data/results_depth.jsonl
  
  # Depth-aware testing with fixed depth (50%)
  python -m src.test --novel data/novel.txt --data_set data/questions.jsonl \\
      --depth-mode fixed --depth 0.5 --context-lengths 128000 \\
      --output data/results_fixed.jsonl
  
  # No-reference testing (test model's inherent knowledge)
  python -m src.test --no-reference --data_set data/questions.jsonl \\
      --output data/results_no_ref.jsonl
        """
    )
    
    # Required arguments (novel is optional for no-reference mode)
    parser.add_argument(
        '--novel',
        type=str,
        default=None,
        help='Path to the novel text file (not required for --no-reference mode)'
    )
    
    parser.add_argument(
        '--data_set',
        type=str,
        required=True,
        help='Path to the question set JSONL file'
    )
    
    parser.add_argument(
        '--context_length',
        type=int,
        default=None,
        help='Number of tokens to use as context (required for legacy mode)'
    )
    
    # No-reference testing mode
    parser.add_argument(
        '--no-reference',
        action='store_true',
        help='Run tests without novel context (test model inherent knowledge)'
    )
    
    # Depth-aware testing arguments
    parser.add_argument(
        '--depth-mode',
        type=str,
        choices=['legacy', 'uniform', 'fixed'],
        default='legacy',
        help='Depth testing mode: legacy (default), uniform, or fixed'
    )
    
    parser.add_argument(
        '--depth',
        type=float,
        default=None,
        help='Fixed depth value (0.0-1.0) for fixed mode'
    )
    
    parser.add_argument(
        '--context-lengths',
        type=str,
        default=None,
        help='Comma-separated context lengths for depth-aware testing (e.g., 64000,128000,200000)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--padding_size',
        type=int,
        default=500,
        help='Buffer tokens to ensure answer region not truncated (default: 500)'
    )
    
    parser.add_argument(
        '--concurrency',
        type=int,
        default=None,
        help='Number of concurrent test requests (default: from DEFAULT_CONCURRENCY in .env, or 5)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output path for test results (JSONL format)'
    )
    
    parser.add_argument(
        '--env',
        type=str,
        default=None,
        help='Path to .env file (default: .env in current directory)'
    )
    
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip validation field check, allow testing unvalidated questions'
    )
    
    parser.add_argument(
        '--ignore-invalid',
        action='store_true',
        help='Skip questions with is_valid=false instead of erroring'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Question limit argument
    parser.add_argument(
        '--max-questions',
        type=int,
        default=None,
        help='Maximum number of questions to test. Questions will be sampled uniformly across depth bins to ensure balanced coverage.'
    )
    
    # Recovery mode arguments
    parser.add_argument(
        '--recovery',
        type=str,
        default=None,
        help='Path to previous results file for recovery mode. Will re-run failed/error/missing tests only.'
    )
    
    return parser.parse_args()


def validate_args(args):
    """Validate command-line arguments.
    
    Args:
        args: Parsed arguments from argparse.
        
    Raises:
        ValueError: If arguments are invalid.
    """
    # Recovery mode validation
    if args.recovery:
        if not Path(args.recovery).exists():
            raise ValueError(f"Recovery file not found: {args.recovery}")
        # In recovery mode, we still need the original parameters to re-run failed tests
    
    # Validate question set file exists
    if not Path(args.data_set).exists():
        raise ValueError(f"Question set file not found: {args.data_set}")
    
    # No-reference mode validation
    if args.no_reference:
        # Check for mutually exclusive arguments
        if args.depth_mode != 'legacy':
            raise ValueError(
                "--no-reference cannot be used with --depth-mode. "
                "No-reference mode tests without any context."
            )
        if args.context_length is not None:
            raise ValueError(
                "--no-reference cannot be used with --context_length. "
                "No-reference mode tests without any context."
            )
        if args.context_lengths is not None:
            raise ValueError(
                "--no-reference cannot be used with --context-lengths. "
                "No-reference mode tests without any context."
            )
        # Warn if novel is provided
        if args.novel:
            logger.warning(
                "--novel is ignored in no-reference mode. "
                "Tests will use novel_summary from question set metadata."
            )
    else:
        # Standard mode requires novel
        if not args.novel:
            raise ValueError(
                "--novel is required (unless using --no-reference mode)"
            )
        
        # Validate novel file exists
        if not Path(args.novel).exists():
            raise ValueError(f"Novel file not found: {args.novel}")
        
        # Validate depth mode and related arguments
        depth_mode = args.depth_mode
        
        if depth_mode == 'legacy':
            # Legacy mode requires context_length
            if args.context_length is None:
                raise ValueError("--context_length is required for legacy mode")
            if args.context_length <= 0:
                raise ValueError("context_length must be positive")
        else:
            # Depth-aware modes require context-lengths
            if args.context_lengths is None:
                raise ValueError(f"--context-lengths is required for {depth_mode} mode")
            
            # Parse and validate context lengths
            try:
                context_lengths = [int(x.strip()) for x in args.context_lengths.split(',')]
                if not context_lengths:
                    raise ValueError("--context-lengths cannot be empty")
                for length in context_lengths:
                    if length <= 0:
                        raise ValueError(f"Invalid context length: {length}")
            except ValueError as e:
                raise ValueError(f"Invalid --context-lengths format: {e}")
            
            # Fixed mode requires depth
            if depth_mode == 'fixed':
                if args.depth is None:
                    raise ValueError("--depth is required for fixed mode")
                if not 0.0 <= args.depth <= 1.0:
                    raise ValueError("--depth must be between 0.0 and 1.0")
        
        if args.padding_size < 0:
            raise ValueError("padding_size must be non-negative")
    
    if args.concurrency is not None and args.concurrency <= 0:
        raise ValueError("concurrency must be positive")
    
    if args.max_questions is not None and args.max_questions <= 0:
        raise ValueError("max-questions must be positive")
    
    # Validate output path is writable
    output_path = Path(args.output)
    if output_path.exists() and not output_path.is_file():
        raise ValueError(f"Output path exists but is not a file: {args.output}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)


async def main():
    """Main entry point for testing."""
    # Parse arguments
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Validate arguments
        logger.info("Validating arguments...")
        validate_args(args)
        
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.load_from_env(args.env)
        Config.validate_config(config)
        llm_config = Config.get_llm_config(config)
        
        # Set default concurrency from config if not specified via CLI
        if args.concurrency is None:
            args.concurrency = config.get("default_concurrency", 5)
            logger.info(f"Using default concurrency from config: {args.concurrency}")
        
        logger.info(f"Using model: {llm_config['model_name']}")
        logger.info(f"API endpoint: {llm_config['base_url']}")
        
        # Initialize components
        logger.info("Initializing components...")
        llm_client = LLMClient(llm_config)
        
        # Create testing tool
        testing_tool = TestingTool(
            config=llm_config,
            llm_client=llm_client
        )
        
        # Display testing parameters
        logger.info("=" * 60)
        logger.info("Testing Parameters:")
        if args.no_reference:
            logger.info(f"  Mode: NO-REFERENCE (testing model's inherent knowledge)")
            logger.info(f"  Question set: {args.data_set}")
        else:
            logger.info(f"  Novel: {args.novel}")
            logger.info(f"  Question set: {args.data_set}")
            logger.info(f"  Depth mode: {args.depth_mode}")
            if args.depth_mode == 'legacy':
                logger.info(f"  Context length: {args.context_length} tokens")
            else:
                context_lengths = [int(x.strip()) for x in args.context_lengths.split(',')]
                logger.info(f"  Context lengths: {context_lengths}")
                if args.depth_mode == 'fixed':
                    logger.info(f"  Fixed depth: {args.depth}")
            logger.info(f"  Padding size: {args.padding_size} tokens")
        logger.info(f"  Concurrency: {args.concurrency}")
        logger.info(f"  Max questions: {args.max_questions if args.max_questions else 'all'}")
        logger.info(f"  Skip validation: {args.skip_validation}")
        logger.info(f"  Ignore invalid: {args.ignore_invalid}")
        logger.info(f"  Output: {args.output}")
        logger.info("=" * 60)
        
        # Run tests based on mode
        logger.info("Starting test execution...")
        
        # Check for recovery mode
        if args.recovery:
            logger.info(f"Recovery mode enabled, loading previous results from: {args.recovery}")
            if args.no_reference:
                results = await testing_tool.run_no_reference_recovery(
                    recovery_path=args.recovery,
                    question_set_path=args.data_set,
                    concurrency=args.concurrency,
                    output_path=args.output,
                    skip_validation=args.skip_validation,
                    ignore_invalid=args.ignore_invalid
                )
            elif args.depth_mode == 'legacy':
                results = await testing_tool.run_recovery(
                    recovery_path=args.recovery,
                    novel_path=args.novel,
                    question_set_path=args.data_set,
                    context_length=args.context_length,
                    padding_size=args.padding_size,
                    concurrency=args.concurrency,
                    output_path=args.output,
                    skip_validation=args.skip_validation,
                    ignore_invalid=args.ignore_invalid
                )
            else:
                context_lengths = [int(x.strip()) for x in args.context_lengths.split(',')]
                results = await testing_tool.run_depth_aware_recovery(
                    recovery_path=args.recovery,
                    novel_path=args.novel,
                    question_set_path=args.data_set,
                    depth_mode=args.depth_mode,
                    context_lengths=context_lengths,
                    fixed_depth=args.depth,
                    padding_size=args.padding_size,
                    concurrency=args.concurrency,
                    output_path=args.output,
                    skip_validation=args.skip_validation,
                    ignore_invalid=args.ignore_invalid
                )
        elif args.no_reference:
            # No-reference mode - test model's inherent knowledge
            results = await testing_tool.run_no_reference_tests(
                question_set_path=args.data_set,
                concurrency=args.concurrency,
                output_path=args.output,
                skip_validation=args.skip_validation,
                ignore_invalid=args.ignore_invalid,
                max_questions=args.max_questions
            )
        elif args.depth_mode == 'legacy':
            # Legacy mode - use original run_tests
            results = await testing_tool.run_tests(
                novel_path=args.novel,
                question_set_path=args.data_set,
                context_length=args.context_length,
                padding_size=args.padding_size,
                concurrency=args.concurrency,
                output_path=args.output,
                skip_validation=args.skip_validation,
                ignore_invalid=args.ignore_invalid,
                max_questions=args.max_questions
            )
        else:
            # Depth-aware mode
            context_lengths = [int(x.strip()) for x in args.context_lengths.split(',')]
            results = await testing_tool.run_depth_aware_tests(
                novel_path=args.novel,
                question_set_path=args.data_set,
                depth_mode=args.depth_mode,
                context_lengths=context_lengths,
                fixed_depth=args.depth,
                padding_size=args.padding_size,
                concurrency=args.concurrency,
                output_path=args.output,
                skip_validation=args.skip_validation,
                ignore_invalid=args.ignore_invalid,
                max_questions=args.max_questions
            )
        
        # Display summary statistics
        logger.info("=" * 60)
        logger.info("Testing Summary:")
        logger.info(f"  Total questions tested: {len(results)}")
        
        # Count by parsing status
        success = sum(1 for r in results if r["parsing_status"] == "success")
        regex_extracted = sum(1 for r in results if r["parsing_status"] == "regex_extracted")
        parsing_error = sum(1 for r in results if r["parsing_status"] == "parsing_error")
        timeout = sum(1 for r in results if r["parsing_status"] == "timeout")
        error = sum(1 for r in results if r["parsing_status"] == "error")
        
        logger.info(f"  Parsing status:")
        logger.info(f"    Success: {success}")
        logger.info(f"    Regex extracted: {regex_extracted}")
        logger.info(f"    Parsing error: {parsing_error}")
        logger.info(f"    Timeout: {timeout}")
        logger.info(f"    Error: {error}")
        
        # Calculate average score
        if results:
            avg_score = sum(r["score"] for r in results) / len(results)
            logger.info(f"  Average score: {avg_score:.4f}")
            
            # Count by question type
            single_choice = sum(1 for r in results if r["question_type"] == "single_choice")
            multiple_choice = sum(1 for r in results if r["question_type"] == "multiple_choice")
            
            logger.info(f"  Question types:")
            logger.info(f"    Single choice: {single_choice}")
            logger.info(f"    Multiple choice: {multiple_choice}")
            
            # Calculate accuracy for single choice
            if single_choice > 0:
                single_correct = sum(
                    1 for r in results 
                    if r["question_type"] == "single_choice" and r["score"] == 1.0
                )
                single_accuracy = single_correct / single_choice
                logger.info(f"  Single choice accuracy: {single_accuracy:.4f} ({single_correct}/{single_choice})")
            
            # Calculate average F1 for multiple choice
            if multiple_choice > 0:
                multi_f1_scores = [
                    r["score"] for r in results 
                    if r["question_type"] == "multiple_choice"
                ]
                avg_multi_f1 = sum(multi_f1_scores) / len(multi_f1_scores)
                logger.info(f"  Multiple choice avg F1: {avg_multi_f1:.4f}")
        
        logger.info(f"  Results saved to: {args.output}")
        logger.info("=" * 60)
        
        if not results:
            logger.warning("No test results generated. Check if questions passed filtering.")
            return 1
        
        logger.info("Testing completed successfully!")
        return 0
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    
    except QuestionCheckError as e:
        # Error already logged by QuestionChecker
        return 1
    
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error during testing: {e}", exc_info=True)
        return 1


def cli_main():
    """CLI entry point wrapper for console script."""
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == '__main__':
    cli_main()
