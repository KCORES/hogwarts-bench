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
  # Test with 50k token context
  python -m src.test --novel data/novel.txt --data_set data/questions.jsonl \\
      --context_length 50000 --output data/results.jsonl
  
  # Test with custom padding and concurrency
  python -m src.test --novel data/novel.txt --data_set data/questions.jsonl \\
      --context_length 100000 --padding_size 1000 \\
      --concurrency 10 --output data/results.jsonl
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--novel',
        type=str,
        required=True,
        help='Path to the novel text file'
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
        required=True,
        help='Number of tokens to use as context for testing'
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
        default=5,
        help='Number of concurrent test requests (default: 5)'
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
    
    return parser.parse_args()


def validate_args(args):
    """Validate command-line arguments.
    
    Args:
        args: Parsed arguments from argparse.
        
    Raises:
        ValueError: If arguments are invalid.
    """
    # Validate novel file exists
    if not Path(args.novel).exists():
        raise ValueError(f"Novel file not found: {args.novel}")
    
    # Validate question set file exists
    if not Path(args.data_set).exists():
        raise ValueError(f"Question set file not found: {args.data_set}")
    
    # Validate numeric arguments
    if args.context_length <= 0:
        raise ValueError("context_length must be positive")
    
    if args.padding_size < 0:
        raise ValueError("padding_size must be non-negative")
    
    if args.concurrency <= 0:
        raise ValueError("concurrency must be positive")
    
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
        logger.info(f"  Novel: {args.novel}")
        logger.info(f"  Question set: {args.data_set}")
        logger.info(f"  Context length: {args.context_length} tokens")
        logger.info(f"  Padding size: {args.padding_size} tokens")
        logger.info(f"  Concurrency: {args.concurrency}")
        logger.info(f"  Skip validation: {args.skip_validation}")
        logger.info(f"  Ignore invalid: {args.ignore_invalid}")
        logger.info(f"  Output: {args.output}")
        logger.info("=" * 60)
        
        # Run tests
        logger.info("Starting test execution...")
        results = await testing_tool.run_tests(
            novel_path=args.novel,
            question_set_path=args.data_set,
            context_length=args.context_length,
            padding_size=args.padding_size,
            concurrency=args.concurrency,
            output_path=args.output,
            skip_validation=args.skip_validation,
            ignore_invalid=args.ignore_invalid
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
