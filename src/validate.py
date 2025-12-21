#!/usr/bin/env python3
"""
Question Validation CLI for hogwarts-bench.

This script validates generated questions by:
1. Having a verification LLM independently answer each question
2. Comparing answers with labeled answers
3. Verifying evidence exists in source context
4. Checking answerability and confidence levels
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from .core.config import Config
from .core.llm_client import LLMClient
from .core.tokenizer import Tokenizer
from .core.file_io import FileIO
from .core.prompt_template import PromptTemplateManager
from .validator.question_validator import QuestionValidator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Validate generated questions for quality and accuracy.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate questions and save all results
  python -m src.validate --novel data/novel.txt --questions data/questions.jsonl \\
      --output data/questions_validated.jsonl
  
  # Validate and output only valid questions
  python -m src.validate --novel data/novel.txt --questions data/questions.jsonl \\
      --output data/questions_clean.jsonl --valid-only
  
  # Validate with custom confidence threshold
  python -m src.validate --novel data/novel.txt --questions data/questions.jsonl \\
      --output data/questions_validated.jsonl --confidence-threshold high
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
        '--questions',
        type=str,
        required=True,
        help='Path to the questions JSONL file to validate'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output path for validated questions (JSONL format)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--concurrency',
        type=int,
        default=5,
        help='Number of concurrent validation requests (default: 5)'
    )
    
    parser.add_argument(
        '--confidence-threshold',
        type=str,
        default='medium',
        choices=['low', 'medium', 'high'],
        help='Minimum confidence level required (default: medium)'
    )
    
    parser.add_argument(
        '--similarity-threshold',
        type=float,
        default=0.8,
        help='Minimum similarity for evidence matching (default: 0.8)'
    )
    
    parser.add_argument(
        '--valid-only',
        action='store_true',
        help='Only output questions that pass validation'
    )
    
    parser.add_argument(
        '--env',
        type=str,
        default=None,
        help='Path to .env file (default: .env in current directory)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def validate_args(args):
    """Validate command-line arguments."""
    # Validate novel file exists
    if not Path(args.novel).exists():
        raise ValueError(f"Novel file not found: {args.novel}")
    
    # Validate questions file exists
    if not Path(args.questions).exists():
        raise ValueError(f"Questions file not found: {args.questions}")
    
    # Validate numeric arguments
    if args.concurrency <= 0:
        raise ValueError("concurrency must be positive")
    
    if not 0.0 <= args.similarity_threshold <= 1.0:
        raise ValueError("similarity-threshold must be between 0.0 and 1.0")
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)


def save_results(
    results: List[Any],
    output_path: str,
    novel_path: str,
    questions_path: str,
    stats: Dict[str, Any],
    valid_only: bool,
    original_metadata: Dict[str, Any],
    llm_config: Dict[str, Any],
    validation_config: Dict[str, Any]
):
    """Save validation results to JSONL file.
    
    Args:
        results: List of validation results
        output_path: Output file path
        novel_path: Path to novel file
        questions_path: Path to questions file
        stats: Validation statistics
        valid_only: Whether to output only valid questions
        original_metadata: Original metadata from questions file
        llm_config: LLM configuration used for validation
        validation_config: Validation parameters
    """
    # Build metadata - preserve original and add validation info
    metadata = {}
    
    # Preserve all original metadata
    if original_metadata:
        metadata.update(original_metadata)
    
    # Add validation metadata
    metadata["validated_at"] = datetime.now().isoformat()
    metadata["validation"] = {
        "novel_path": novel_path,
        "questions_path": questions_path,
        "total_questions": stats["total"],
        "passed": stats["passed"],
        "failed": stats["failed"],
        "pass_rate": stats["pass_rate"],
        "valid_only": valid_only,
        "model_name": llm_config.get("model_name"),
        "config": {
            "confidence_threshold": validation_config.get("confidence_threshold"),
            "similarity_threshold": validation_config.get("similarity_threshold"),
            "temperature": llm_config.get("temperature"),
            "max_tokens": llm_config.get("max_tokens"),
            "timeout": llm_config.get("timeout"),
        },
        "failure_breakdown": {
            "answer_mismatch": stats["answer_mismatch"],
            "evidence_not_found": stats["evidence_not_found"],
            "not_answerable": stats["not_answerable"],
            "low_confidence": stats["low_confidence"],
        }
    }
    
    # Convert results to dictionaries
    if valid_only:
        output_data = [
            r.to_question_with_validation()
            for r in results
            if r.is_valid
        ]
    else:
        output_data = [
            r.to_question_with_validation()
            for r in results
        ]
    
    # Save to JSONL
    FileIO.write_jsonl(output_path, output_data, metadata)
    logger.info(f"Results saved to: {output_path}")


async def main():
    """Main entry point for validation."""
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
        prompt_manager = PromptTemplateManager()
        tokenizer = Tokenizer()
        
        # Create validator
        validator = QuestionValidator(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            similarity_threshold=args.similarity_threshold,
            confidence_threshold=args.confidence_threshold
        )
        
        # Load novel and tokenize
        logger.info("Loading and tokenizing novel...")
        novel_text = FileIO.read_novel(args.novel)
        novel_tokens = tokenizer.encode(novel_text)
        logger.info(f"Novel loaded: {len(novel_tokens)} tokens")
        
        # Load questions
        logger.info("Loading questions...")
        file_io = FileIO()
        metadata, questions = file_io.read_jsonl(args.questions)
        logger.info(f"Loaded {len(questions)} questions")
        
        if not questions:
            logger.error("No questions found in input file")
            return 1
        
        # Display validation parameters
        logger.info("=" * 60)
        logger.info("Validation Parameters:")
        logger.info(f"  Novel: {args.novel}")
        logger.info(f"  Questions: {args.questions}")
        logger.info(f"  Total questions: {len(questions)}")
        logger.info(f"  Concurrency: {args.concurrency}")
        logger.info(f"  Confidence threshold: {args.confidence_threshold}")
        logger.info(f"  Similarity threshold: {args.similarity_threshold}")
        logger.info(f"  Valid only output: {args.valid_only}")
        logger.info(f"  Output: {args.output}")
        logger.info("=" * 60)
        
        # Run validation
        logger.info("Starting validation...")
        results, stats = await validator.validate_batch(
            questions=questions,
            novel_tokens=novel_tokens,
            concurrency=args.concurrency
        )
        
        # Save results
        save_results(
            results=results,
            output_path=args.output,
            novel_path=args.novel,
            questions_path=args.questions,
            stats=stats,
            valid_only=args.valid_only,
            original_metadata=metadata,
            llm_config=llm_config,
            validation_config={
                "confidence_threshold": args.confidence_threshold,
                "similarity_threshold": args.similarity_threshold,
            }
        )
        
        # Display summary
        logger.info("=" * 60)
        logger.info("Validation Summary:")
        logger.info(f"  Total questions: {stats['total']}")
        logger.info(f"  Passed: {stats['passed']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Pass rate: {stats['pass_rate']:.1%}")
        logger.info("")
        logger.info("Failure breakdown:")
        logger.info(f"  Answer mismatch: {stats['answer_mismatch']}")
        logger.info(f"  Evidence not found: {stats['evidence_not_found']}")
        logger.info(f"  Not answerable: {stats['not_answerable']}")
        logger.info(f"  Low confidence: {stats['low_confidence']}")
        
        if args.valid_only:
            logger.info(f"\nOutput contains only {stats['passed']} valid questions")
        else:
            logger.info(f"\nOutput contains all {stats['total']} questions with validation metadata")
        
        logger.info(f"  Results saved to: {args.output}")
        logger.info("=" * 60)
        
        logger.info("Validation completed successfully!")
        return 0
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}", exc_info=True)
        return 1


def cli_main():
    """CLI entry point wrapper for console script."""
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == '__main__':
    cli_main()
