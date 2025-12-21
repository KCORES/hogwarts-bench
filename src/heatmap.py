"""
Heatmap CLI - Generate heatmaps for question coverage and model accuracy.

Usage:
    python -m src.heatmap --mode coverage --questions data/questions.jsonl --output coverage.html
    python -m src.heatmap --mode accuracy --results data/results.jsonl --output accuracy.html
    python -m src.heatmap --mode combined --questions data/questions.jsonl --results data/results.jsonl --output combined.html
    python -m src.heatmap --mode depth --results data/depth_results.jsonl --output depth.html
    python -m src.heatmap --mode combined_depth --questions data/questions.jsonl --results data/depth_results.jsonl --output combined_depth.html
"""

import argparse
import sys
import logging
from pathlib import Path

from src.reporter.heatmap import (
    load_question_data,
    load_result_data,
    load_depth_result_data,
    calculate_coverage_bins,
    calculate_accuracy_bins,
    calculate_depth_bins,
    create_coverage_heatmap,
    create_accuracy_heatmap,
    create_combined_heatmap,
    create_depth_heatmap,
    create_combined_depth_heatmap
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate heatmaps for question coverage and model accuracy.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        required=True,
        choices=['coverage', 'accuracy', 'combined', 'depth', 'combined_depth'],
        help='Heatmap mode: coverage, accuracy, combined, depth, or combined_depth'
    )
    
    parser.add_argument(
        '--questions',
        type=str,
        help='Path to questions JSONL file (required for coverage and combined modes)'
    )
    
    parser.add_argument(
        '--results',
        type=str,
        help='Path to results JSONL file (required for accuracy and combined modes)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output HTML file path'
    )
    
    parser.add_argument(
        '--bins',
        type=int,
        default=50,
        help='Number of bins to divide context into (default: 50)'
    )
    
    parser.add_argument(
        '--context-length',
        type=int,
        default=None,
        help='Total context length in tokens. If not specified, will be read from metadata (total_tokens field)'
    )
    
    return parser.parse_args()



def validate_args(args) -> bool:
    """
    Validate command line arguments based on mode.
    
    Returns:
        True if valid, False otherwise (with error message printed)
    """
    if args.mode == 'coverage':
        if not args.questions:
            logger.error("--questions is required for coverage mode")
            return False
    elif args.mode == 'accuracy':
        if not args.results:
            logger.error("--results is required for accuracy mode")
            return False
    elif args.mode == 'combined':
        if not args.questions:
            logger.error("--questions is required for combined mode")
            return False
        if not args.results:
            logger.error("--results is required for combined mode")
            return False
    elif args.mode == 'depth':
        if not args.results:
            logger.error("--results is required for depth mode")
            return False
    elif args.mode == 'combined_depth':
        if not args.questions:
            logger.error("--questions is required for combined_depth mode")
            return False
        if not args.results:
            logger.error("--results is required for combined_depth mode")
            return False
    
    if args.bins <= 0:
        logger.error("--bins must be a positive integer")
        return False
    
    if args.context_length is not None and args.context_length <= 0:
        logger.error("--context-length must be a positive integer")
        return False
    
    return True


def get_context_length(args, metadata) -> int:
    """
    Determine context length from args or metadata.
    
    Args:
        args: Command line arguments
        metadata: DatasetMetadata object
        
    Returns:
        Context length in tokens
        
    Raises:
        ValueError: If context length cannot be determined
    """
    # Priority: CLI argument > metadata.total_tokens > metadata.context_length > error
    if args.context_length is not None:
        return args.context_length
    
    if metadata.total_tokens is not None:
        logger.info(f"Using total_tokens from metadata: {metadata.total_tokens}")
        return metadata.total_tokens
    
    if metadata.context_length is not None:
        logger.info(f"Using context_length from metadata: {metadata.context_length}")
        return metadata.context_length
    
    raise ValueError(
        "Context length not specified. Either provide --context-length argument "
        "or ensure the input file contains total_tokens in metadata."
    )


def main():
    """Main entry point for heatmap CLI."""
    args = parse_args()
    
    if not validate_args(args):
        sys.exit(1)
    
    try:
        html_content = ""
        
        if args.mode == 'coverage':
            logger.info(f"Loading questions from {args.questions}")
            questions, skipped, metadata = load_question_data(args.questions)
            logger.info(f"Loaded {len(questions)} questions, skipped {skipped}")
            
            if not questions:
                logger.error("No valid questions found")
                sys.exit(1)
            
            context_length = get_context_length(args, metadata)
            logger.info(f"Calculating coverage bins (bins={args.bins}, context_length={context_length})")
            bins = calculate_coverage_bins(questions, context_length, args.bins)
            
            logger.info("Generating coverage heatmap")
            html_content = create_coverage_heatmap(bins, context_length, metadata)
            
        elif args.mode == 'accuracy':
            logger.info(f"Loading results from {args.results}")
            results, skipped, metadata = load_result_data(args.results)
            logger.info(f"Loaded {len(results)} results, skipped {skipped}")
            
            if not results:
                logger.error("No valid results found")
                sys.exit(1)
            
            context_length = get_context_length(args, metadata)
            logger.info(f"Calculating accuracy bins (bins={args.bins}, context_length={context_length})")
            bins = calculate_accuracy_bins(results, context_length, args.bins)
            
            logger.info("Generating accuracy heatmap")
            html_content = create_accuracy_heatmap(bins, context_length, metadata)
            
        elif args.mode == 'combined':
            logger.info(f"Loading questions from {args.questions}")
            questions, q_skipped, q_metadata = load_question_data(args.questions)
            logger.info(f"Loaded {len(questions)} questions, skipped {q_skipped}")
            
            logger.info(f"Loading results from {args.results}")
            results, r_skipped, r_metadata = load_result_data(args.results)
            logger.info(f"Loaded {len(results)} results, skipped {r_skipped}")
            
            if not questions and not results:
                logger.error("No valid data found")
                sys.exit(1)
            
            # Prefer question metadata for context length, fall back to result metadata
            metadata = q_metadata if q_metadata.total_tokens else r_metadata
            context_length = get_context_length(args, metadata)
            
            logger.info(f"Calculating bins (bins={args.bins}, context_length={context_length})")
            coverage_bins = calculate_coverage_bins(questions, context_length, args.bins)
            accuracy_bins = calculate_accuracy_bins(results, context_length, args.bins)
            
            logger.info("Generating combined heatmap")
            html_content = create_combined_heatmap(
                coverage_bins, accuracy_bins, context_length,
                question_metadata=q_metadata, result_metadata=r_metadata
            )
        
        elif args.mode == 'depth':
            logger.info(f"Loading depth-aware results from {args.results}")
            results, metadata = load_depth_result_data(args.results)
            logger.info(f"Loaded {len(results)} depth-aware results")
            
            if not results:
                logger.error("No valid depth-aware results found")
                sys.exit(1)
            
            logger.info("Calculating depth bins")
            bins = calculate_depth_bins(results)
            
            logger.info("Generating depth heatmap")
            html_content = create_depth_heatmap(bins, metadata)
        
        elif args.mode == 'combined_depth':
            logger.info(f"Loading questions from {args.questions}")
            questions, q_skipped, q_metadata = load_question_data(args.questions)
            logger.info(f"Loaded {len(questions)} questions, skipped {q_skipped}")
            
            logger.info(f"Loading depth-aware results from {args.results}")
            depth_results, r_metadata = load_depth_result_data(args.results)
            logger.info(f"Loaded {len(depth_results)} depth-aware results")
            
            if not questions and not depth_results:
                logger.error("No valid data found")
                sys.exit(1)
            
            # Get context length for coverage calculation
            metadata = q_metadata if q_metadata.total_tokens else r_metadata
            context_length = get_context_length(args, metadata)
            
            logger.info(f"Calculating coverage bins (bins={args.bins}, context_length={context_length})")
            coverage_bins = calculate_coverage_bins(questions, context_length, args.bins)
            
            logger.info("Calculating depth bins")
            depth_bins = calculate_depth_bins(depth_results)
            
            logger.info("Generating combined depth heatmap")
            html_content = create_combined_depth_heatmap(
                coverage_bins, depth_bins, context_length,
                question_metadata=q_metadata, result_metadata=r_metadata
            )
        
        # Write output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding='utf-8')
        logger.info(f"Heatmap saved to {args.output}")
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error generating heatmap: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
