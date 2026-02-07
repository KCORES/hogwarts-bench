#!/usr/bin/env python3
"""
Summary generation CLI for hogwarts-bench.

This script generates or updates novel summaries in question sets.
It reads the first N lines of a novel and uses LLM to generate a brief
description for no-reference testing mode.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .core.config import Config
from .core.llm_client import LLMClient
from .generator.summary_generator import SummaryGenerator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate novel summary for question sets.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate summary and update question set
  python -m src.summary --novel data/novel.txt --data_set data/questions.jsonl
  
  # Generate summary and save to new file
  python -m src.summary --novel data/novel.txt --data_set data/questions.jsonl \\
      --output data/questions_with_summary.jsonl
  
  # Use custom number of lines for excerpt
  python -m src.summary --novel data/novel.txt --data_set data/questions.jsonl \\
      --lines 200
        """
    )
    
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
        '--output',
        type=str,
        default=None,
        help='Output path (default: overwrite input file)'
    )
    
    parser.add_argument(
        '--lines',
        type=int,
        default=100,
        help='Number of lines to read from novel for summary (default: 100)'
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
    
    # Validate lines is positive
    if args.lines <= 0:
        raise ValueError("--lines must be positive")
    
    # Validate output path is writable if specified
    if args.output:
        output_path = Path(args.output)
        if output_path.exists() and not output_path.is_file():
            raise ValueError(f"Output path exists but is not a file: {args.output}")
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)


async def main():
    """Main entry point for summary generation."""
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
        
        summary_generator = SummaryGenerator(
            llm_client=llm_client,
            lines_to_read=args.lines
        )
        
        # Display parameters
        logger.info("=" * 60)
        logger.info("Summary Generation Parameters:")
        logger.info(f"  Novel: {args.novel}")
        logger.info(f"  Question set: {args.data_set}")
        logger.info(f"  Lines to read: {args.lines}")
        logger.info(f"  Output: {args.output or args.data_set} (overwrite)")
        logger.info("=" * 60)
        
        # Generate summary and update question set
        logger.info("Generating summary...")
        summary = await summary_generator.update_question_set_summary(
            novel_path=args.novel,
            question_set_path=args.data_set,
            output_path=args.output
        )
        
        # Display result
        logger.info("=" * 60)
        logger.info("Summary Generation Complete!")
        logger.info(f"Generated summary:")
        logger.info(f"  {summary}")
        logger.info("=" * 60)
        
        output_file = args.output or args.data_set
        logger.info(f"Question set updated: {output_file}")
        
        return 0
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


def cli_main():
    """CLI entry point wrapper for console script."""
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == '__main__':
    cli_main()
