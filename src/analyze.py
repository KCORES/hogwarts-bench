#!/usr/bin/env python3
"""
Novel Analysis CLI for hogwarts-bench.

This script analyzes a novel file and provides:
1. Token count statistics
2. Recommended question counts for different context lengths
3. Coverage analysis for benchmark testing
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

from .core.tokenizer import Tokenizer
from .core.file_io import FileIO


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Predefined context lengths (in tokens)
CONTEXT_LENGTHS = [
    (2_000, "2K"),
    (4_000, "4K"),
    (8_000, "8K"),
    (16_000, "16K"),
    (32_000, "32K"),
    (64_000, "64K"),
    (128_000, "128K"),
    (192_000, "192K"),
    (256_000, "256K"),
    (512_000, "512K"),
    (1_000_000, "1M"),
    (2_000_000, "2M"),
]


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Analyze novel and recommend question counts for benchmarking.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a novel file
  python -m src.analyze --novel data/harry_potter_1.txt
  
  # Customize questions per 10K tokens
  python -m src.analyze --novel data/novel.txt --questions-per-10k 10
        """
    )
    
    parser.add_argument(
        '--novel',
        type=str,
        required=True,
        help='Path to the novel text file'
    )
    
    parser.add_argument(
        '--questions-per-10k',
        type=int,
        default=5,
        help='Questions per 10K tokens for each context level (default: 5)'
    )
    
    return parser.parse_args()


def format_tokens(tokens: int) -> str:
    """Format token count with K/M suffix."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.2f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def calculate_questions_for_context(
    context_length: int,
    questions_per_10k: int = 5
) -> int:
    """
    Calculate recommended question count for a specific context length.
    
    Uses a simple formula: ~5 questions per 10K tokens of context,
    with a minimum of 5 questions.
    
    Args:
        context_length: Target context length in tokens
        questions_per_10k: Questions per 10K tokens (default: 5)
        
    Returns:
        Recommended question count for this context length
    """
    # Calculate based on context size
    questions = max(5, (context_length // 10_000) * questions_per_10k)
    return questions


def calculate_questions_for_level(
    novel_tokens: int,
    context_length: int,
    prev_context_length: int = 0,
    questions_per_segment: int = 5
) -> Tuple[int, str]:
    """
    Calculate questions needed for a specific context level.
    
    For each context level, we need questions that have their evidence
    located in the range (prev_context_length, context_length].
    
    Args:
        novel_tokens: Total tokens in the novel
        context_length: Target context length
        prev_context_length: Previous context length (for incremental calculation)
        questions_per_segment: Questions per 10K token segment
        
    Returns:
        Tuple of (question_count, status_note)
    """
    if context_length > novel_tokens:
        return 0, "超出小说长度"
    
    # Calculate the new range that needs coverage
    range_start = prev_context_length
    range_end = min(context_length, novel_tokens)
    range_size = range_end - range_start
    
    if range_size <= 0:
        return 0, "无新增范围"
    
    # Questions needed: ~5 per 10K tokens in the new range
    questions = max(5, (range_size // 10_000) * questions_per_segment)
    
    return questions, "可测试"


def analyze_novel(novel_path: str, questions_per_10k: int = 5):
    """Analyze novel and print cumulative question recommendations."""
    
    # Load and tokenize novel
    logger.info(f"Loading novel: {novel_path}")
    novel_text = FileIO.read_novel(novel_path)
    
    tokenizer = Tokenizer()
    novel_tokens = tokenizer.encode(novel_text)
    total_tokens = len(novel_tokens)
    
    # Print basic stats
    print("\n" + "=" * 70)
    print("小说分析报告 / NOVEL ANALYSIS REPORT")
    print("=" * 70)
    print(f"\n文件 / File: {novel_path}")
    print(f"总Token数 / Total tokens: {total_tokens:,} ({format_tokens(total_tokens)})")
    print(f"总字符数 / Total characters: {len(novel_text):,}")
    
    # Print cumulative recommendations table
    print("\n" + "-" * 70)
    print("累计问题数量建议 / CUMULATIVE QUESTION RECOMMENDATIONS")
    print("-" * 70)
    print("如果要测试到某个上下文长度，需要生成多少问题：")
    print("(How many questions to generate for testing up to each context length)")
    print("-" * 70)
    print(f"{'测试上限':<12} {'本级问题数':<12} {'累计问题数':<12} {'状态':<15}")
    print(f"{'Context':<12} {'This Level':<12} {'Cumulative':<12} {'Status':<15}")
    print("-" * 70)
    
    cumulative_questions = 0
    prev_context = 0
    applicable_levels = []
    
    for tokens, label in CONTEXT_LENGTHS:
        if tokens > total_tokens:
            # Show this level as not applicable
            print(f"{label:<12} {'-':<12} {'-':<12} {'✗ 超出小说长度':<15}")
            continue
        
        # Calculate questions for this level
        level_questions, status = calculate_questions_for_level(
            total_tokens, tokens, prev_context, questions_per_10k
        )
        
        cumulative_questions += level_questions
        applicable_levels.append((tokens, label, level_questions, cumulative_questions))
        
        print(f"{label:<12} {level_questions:<12} {cumulative_questions:<12} {'✓ ' + status:<15}")
        
        prev_context = tokens
    
    print("-" * 70)
    
    # Print summary
    print("\n" + "=" * 70)
    print("使用建议 / RECOMMENDATIONS")
    print("=" * 70)
    
    if applicable_levels:
        max_level = applicable_levels[-1]
        print(f"\n1. 最大可测试上下文: {max_level[1]} ({max_level[0]:,} tokens)")
        print(f"   Maximum testable context: {max_level[1]}")
        
        print(f"\n2. 完整测试所需问题数: {max_level[3]} 个")
        print(f"   Total questions for full coverage: {max_level[3]}")
        
        print(f"\n3. 生成命令示例 / Example command:")
        print(f"   python -m src.generate --novel {novel_path} \\")
        print(f"       --output data/questions.jsonl \\")
        print(f"       --question_nums {max_level[3]}")
        
        # Show quick reference
        print(f"\n4. 快速参考 / Quick Reference:")
        for tokens, label, level_q, cumul_q in applicable_levels:
            print(f"   测试到 {label}: 生成 {cumul_q} 个问题")
    else:
        print("\n警告: 小说太短，无法进行任何预设上下文长度的测试。")
        print(f"Warning: Novel too short. Only {total_tokens:,} tokens.")
    
    print("\n" + "=" * 70)
    
    return total_tokens, applicable_levels


def main():
    """Main entry point."""
    args = parse_args()
    
    # Validate arguments
    if not Path(args.novel).exists():
        logger.error(f"Novel file not found: {args.novel}")
        return 1
    
    if args.questions_per_10k <= 0:
        logger.error("questions-per-10k must be positive")
        return 1
    
    try:
        analyze_novel(
            args.novel,
            args.questions_per_10k
        )
        return 0
    
    except Exception as e:
        logger.error(f"Error analyzing novel: {e}", exc_info=True)
        return 1


def cli_main():
    """CLI entry point wrapper."""
    sys.exit(main())


if __name__ == '__main__':
    cli_main()
