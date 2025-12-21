#!/usr/bin/env python3
"""
Report Generator CLI for hogwarts-bench.

This script generates comprehensive HTML reports from test results.
It analyzes test results, calculates metrics, creates visualizations,
and produces standalone interactive HTML reports.
"""

import argparse
import logging
import sys
from pathlib import Path

from .reporter.report_generator import ReportGenerator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate comprehensive HTML reports from test results.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate report with default settings
  python -m src.report --results data/results.jsonl --output reports/report.html
  
  # Generate report with custom number of error examples
  python -m src.report --results data/results.jsonl \\
      --output reports/report.html --error_examples 20
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--results',
        type=str,
        required=True,
        help='Path to test results JSONL file'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output path for HTML report'
    )
    
    # Optional arguments
    parser.add_argument(
        '--error_examples',
        type=int,
        default=10,
        help='Number of error examples to include in report (default: 10)'
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
    # Validate results file exists
    if not Path(args.results).exists():
        raise ValueError(f"Results file not found: {args.results}")
    
    # Validate results file is a file
    if not Path(args.results).is_file():
        raise ValueError(f"Results path is not a file: {args.results}")
    
    # Validate error_examples is non-negative
    if args.error_examples < 0:
        raise ValueError("error_examples must be non-negative")
    
    # Validate output path
    output_path = Path(args.output)
    if output_path.exists() and not output_path.is_file():
        raise ValueError(f"Output path exists but is not a file: {args.output}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)


def main():
    """Main entry point for report generation."""
    # Parse arguments
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Validate arguments
        logger.info("Validating arguments...")
        validate_args(args)
        
        # Display report generation parameters
        logger.info("=" * 60)
        logger.info("Report Generation Parameters:")
        logger.info(f"  Results file: {args.results}")
        logger.info(f"  Output file: {args.output}")
        logger.info(f"  Error examples: {args.error_examples}")
        logger.info("=" * 60)
        
        # Load results and initialize report generator
        logger.info("Loading test results...")
        try:
            report_generator = ReportGenerator(args.results)
        except FileNotFoundError as e:
            logger.error(f"Results file not found: {e}")
            return 1
        except ValueError as e:
            logger.error(f"Invalid results file: {e}")
            return 1
        except Exception as e:
            logger.error(f"Failed to load results: {e}")
            return 1
        
        logger.info(f"Loaded {len(report_generator.results)} test results")
        
        # Generate report
        logger.info("Generating HTML report...")
        try:
            report_generator.generate_report(
                output_path=args.output,
                error_examples=args.error_examples
            )
        except IOError as e:
            logger.error(f"Failed to write report file: {e}")
            return 1
        except Exception as e:
            logger.error(f"Failed to generate report: {e}", exc_info=True)
            return 1
        
        # Display success message
        logger.info("=" * 60)
        logger.info("Report generation completed successfully!")
        logger.info(f"Report saved to: {args.output}")
        logger.info("=" * 60)
        
        return 0
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error during report generation: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
