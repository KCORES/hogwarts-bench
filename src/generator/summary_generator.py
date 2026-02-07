"""
Summary generator for hogwarts-bench.

This module provides the SummaryGenerator class that generates novel summaries
for no-reference testing mode. It reads the first N lines of a novel and uses
LLM to generate a brief description without revealing plot details.
"""

import logging
from pathlib import Path
from typing import Optional

from ..core.llm_client import LLMClient
from ..core.prompt_template import PromptTemplateManager
from ..core.file_io import FileIO


# Configure logging
logger = logging.getLogger(__name__)


class SummaryGenerator:
    """
    Generates novel summaries for no-reference testing.
    
    Reads the first N lines of a novel and uses LLM to generate
    a brief description without revealing plot details.
    """
    
    DEFAULT_LINES_TO_READ = 100
    
    def __init__(
        self,
        llm_client: LLMClient,
        prompt_manager: Optional[PromptTemplateManager] = None,
        lines_to_read: int = DEFAULT_LINES_TO_READ
    ):
        """
        Initialize the summary generator.
        
        Args:
            llm_client: LLM client for API calls
            prompt_manager: Prompt template manager. If None, creates default.
            lines_to_read: Number of lines to read from novel (default: 100)
        """
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager or PromptTemplateManager()
        self.lines_to_read = lines_to_read
        
        logger.info(
            f"SummaryGenerator initialized with lines_to_read={lines_to_read}"
        )
    
    def _read_novel_excerpt(self, novel_path: str) -> str:
        """
        Read the first N lines of the novel.
        
        Args:
            novel_path: Path to the novel text file
            
        Returns:
            Excerpt text (first N lines)
            
        Raises:
            FileNotFoundError: If the novel file does not exist
        """
        path = Path(novel_path)
        if not path.exists():
            raise FileNotFoundError(f"Novel file not found: {novel_path}")
        
        lines = []
        with open(path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= self.lines_to_read:
                    break
                lines.append(line)
        
        actual_lines = len(lines)
        if actual_lines < self.lines_to_read:
            logger.warning(
                f"Novel has only {actual_lines} lines, "
                f"requested {self.lines_to_read}"
            )
        
        excerpt = ''.join(lines)
        logger.info(
            f"Read {actual_lines} lines from novel "
            f"({len(excerpt)} characters)"
        )
        
        return excerpt
    
    async def generate_summary(self, novel_path: str) -> str:
        """
        Generate a summary for the given novel.
        
        Args:
            novel_path: Path to the novel text file
            
        Returns:
            Generated summary string
            
        Raises:
            FileNotFoundError: If the novel file does not exist
            RuntimeError: If LLM fails to generate summary
        """
        logger.info(f"Generating summary for: {novel_path}")
        
        # Read novel excerpt
        excerpt = self._read_novel_excerpt(novel_path)
        
        # Get prompt from template manager
        system_prompt, user_prompt = self.prompt_manager.get_summary_generation_prompt(
            excerpt=excerpt
        )
        
        # Call LLM to generate summary
        logger.info("Calling LLM to generate summary...")
        response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt
        )
        
        if response is None:
            raise RuntimeError(
                "LLM failed to generate summary after all retries"
            )
        
        # Clean up response
        summary = response.strip()
        
        logger.info(f"Generated summary: {summary[:100]}...")
        
        return summary
    
    async def update_question_set_summary(
        self,
        novel_path: str,
        question_set_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate summary and update question set metadata.
        
        Args:
            novel_path: Path to the novel text file
            question_set_path: Path to the question set JSONL file
            output_path: Output path. If None, overwrites input file.
            
        Returns:
            Generated summary string
            
        Raises:
            FileNotFoundError: If files do not exist
            RuntimeError: If LLM fails to generate summary
        """
        # Generate summary
        summary = await self.generate_summary(novel_path)
        
        # Load existing question set
        logger.info(f"Loading question set: {question_set_path}")
        metadata, questions = FileIO.read_jsonl(question_set_path)
        
        # Update metadata with summary
        metadata["novel_summary"] = summary
        logger.info("Updated metadata with novel_summary")
        
        # Determine output path
        if output_path is None:
            output_path = question_set_path
        
        # Save updated question set
        FileIO.write_jsonl(output_path, questions, metadata)
        logger.info(f"Saved updated question set to: {output_path}")
        
        return summary
