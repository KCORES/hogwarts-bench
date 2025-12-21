#!/usr/bin/env python3
"""
Question Generator CLI for hogwarts-bench.

This script generates test questions from novel text using LLM.
It supports different sampling strategies, configurable context windows,
and concurrent generation with retry logic.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .core.config import Config
from .core.llm_client import LLMClient
from .core.tokenizer import Tokenizer
from .core.prompt_template import PromptTemplateManager
from .core.validator import QuestionValidator
from .generator.question_generator import QuestionGenerator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate test questions from novel text using LLM.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 100 questions using stratified sampling
  python -m src.generate --novel data/novel.txt --question_nums 100 --output data/questions.jsonl
  
  # Generate 50 questions using random sampling with custom settings
  python -m src.generate --novel data/novel.txt --question_nums 50 \\
      --sampling_strategy random --context_window_size 1000 \\
      --concurrency 10 --retry_times 5 --output data/questions.jsonl
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
        '--question_nums',
        type=int,
        required=True,
        help='Number of questions to generate'
    )
    
    # Optional arguments
    parser.add_argument(
        '--sampling_strategy',
        type=str,
        default='stratified',
        choices=['stratified', 'random'],
        help='Sampling strategy for selecting text positions (default: stratified)'
    )
    
    parser.add_argument(
        '--context_window_size',
        type=int,
        default=500,
        help='Size of context window in tokens (default: 500)'
    )
    
    parser.add_argument(
        '--concurrency',
        type=int,
        default=5,
        help='Number of concurrent generation tasks (default: 5)'
    )
    
    parser.add_argument(
        '--retry_times',
        type=int,
        default=3,
        help='Maximum retry attempts for failed generations (default: 3)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output path for generated questions (JSONL format)'
    )
    
    parser.add_argument(
        '--env',
        type=str,
        default=None,
        help='Path to .env file (default: .env in current directory)'
    )
    
    parser.add_argument(
        '--prompt_dir',
        type=str,
        default='prompts/',
        help='Directory containing prompt templates (default: prompts/)'
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
    
    # Validate numeric arguments
    if args.question_nums <= 0:
        raise ValueError("question_nums must be positive")
    
    if args.context_window_size <= 0:
        raise ValueError("context_window_size must be positive")
    
    if args.concurrency <= 0:
        raise ValueError("concurrency must be positive")
    
    if args.retry_times < 0:
        raise ValueError("retry_times must be non-negative")
    
    # Validate output path is writable
    output_path = Path(args.output)
    if output_path.exists() and not output_path.is_file():
        raise ValueError(f"Output path exists but is not a file: {args.output}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)


async def main():
    """Main entry point for question generation."""
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
        tokenizer = Tokenizer()
        prompt_manager = PromptTemplateManager(args.prompt_dir)
        validator = QuestionValidator()
        
        # Log template info
        template_info = prompt_manager.get_template_info()
        logger.info(
            f"Question generation template: "
            f"{'default' if template_info['question_generation_template']['is_default'] else 'custom'}"
        )
        
        # Create question generator
        generator = QuestionGenerator(
            llm_client=llm_client,
            tokenizer=tokenizer,
            prompt_manager=prompt_manager,
            validator=validator
        )
        
        # Display generation parameters
        logger.info("=" * 60)
        logger.info("Question Generation Parameters:")
        logger.info(f"  Novel: {args.novel}")
        logger.info(f"  Target questions: {args.question_nums}")
        logger.info(f"  Sampling strategy: {args.sampling_strategy}")
        logger.info(f"  Context window size: {args.context_window_size} tokens")
        logger.info(f"  Concurrency: {args.concurrency}")
        logger.info(f"  Max retry attempts: {args.retry_times}")
        logger.info(f"  Output: {args.output}")
        logger.info("=" * 60)
        
        # Generate questions
        logger.info("Starting question generation...")
        questions = await generator.generate_questions(
            novel_path=args.novel,
            num_questions=args.question_nums,
            sampling_strategy=args.sampling_strategy,
            context_window_size=args.context_window_size,
            concurrency=args.concurrency,
            retry_times=args.retry_times,
            output_path=args.output
        )
        
        # Display summary statistics
        logger.info("=" * 60)
        logger.info("Generation Summary:")
        logger.info(f"  Total questions generated: {len(questions)}")
        logger.info(f"  Success rate: {len(questions)}/{args.question_nums} "
                   f"({len(questions)/args.question_nums*100:.1f}%)")
        
        # Count question types
        single_choice = sum(1 for q in questions if q.get('question_type') == 'single_choice')
        multiple_choice = sum(1 for q in questions if q.get('question_type') == 'multiple_choice')
        
        logger.info(f"  Single choice questions: {single_choice}")
        logger.info(f"  Multiple choice questions: {multiple_choice}")
        logger.info(f"  Output saved to: {args.output}")
        logger.info("=" * 60)
        
        if len(questions) < args.question_nums:
            logger.warning(
                f"Generated {len(questions)} questions, "
                f"which is less than the target of {args.question_nums}. "
                f"Some generations may have failed. Check logs for details."
            )
            return 1
        
        logger.info("Question generation completed successfully!")
        return 0
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error during generation: {e}", exc_info=True)
        return 1


def cli_main():
    """CLI entry point wrapper for console script."""
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == '__main__':
    cli_main()
