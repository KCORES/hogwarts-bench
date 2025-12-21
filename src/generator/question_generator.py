"""
Question generator core logic for hogwarts-bench.

This module provides the QuestionGenerator class that orchestrates the
question generation pipeline including sampling, context extraction,
LLM generation, validation, and saving results.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from ..core.llm_client import LLMClient
from ..core.tokenizer import Tokenizer
from ..core.validator import QuestionValidator
from ..core.prompt_template import PromptTemplateManager
from ..core.file_io import FileIO
from .sampling import get_sampling_strategy


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionGenerator:
    """
    Main class for generating test questions from novel text.
    
    Orchestrates the complete pipeline: sampling positions, extracting context,
    generating questions via LLM, validating, and saving results.
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        tokenizer: Tokenizer = None,
        prompt_manager: PromptTemplateManager = None,
        validator: QuestionValidator = None
    ):
        """
        Initialize the QuestionGenerator.
        
        Args:
            llm_client: LLM client for generating questions.
            tokenizer: Tokenizer for text processing. If None, creates default.
            prompt_manager: Prompt template manager. If None, creates default.
            validator: Question validator. If None, uses QuestionValidator.
        """
        self.llm_client = llm_client
        self.tokenizer = tokenizer or Tokenizer()
        self.prompt_manager = prompt_manager or PromptTemplateManager()
        self.validator = validator or QuestionValidator()
    
    async def generate_questions(
        self,
        novel_path: str,
        num_questions: int,
        sampling_strategy: str = "stratified",
        context_window_size: int = 500,
        concurrency: int = 5,
        retry_times: int = 3,
        output_path: Optional[str] = None
    ) -> List[Dict]:
        """
        Main entry point for question generation.
        
        Args:
            novel_path: Path to the novel text file.
            num_questions: Number of questions to generate.
            sampling_strategy: Sampling strategy ("stratified" or "random").
            context_window_size: Size of context window in tokens.
            concurrency: Number of concurrent generation tasks.
            retry_times: Maximum retry attempts for failed generations.
            output_path: Optional path to save generated questions.
            
        Returns:
            List of generated question dictionaries.
        """
        logger.info(f"Starting question generation from {novel_path}")
        logger.info(f"Target: {num_questions} questions, Strategy: {sampling_strategy}")
        
        # Read novel text
        logger.info("Reading novel text...")
        novel_text = FileIO.read_novel(novel_path)
        
        # Tokenize novel
        logger.info("Tokenizing novel...")
        novel_tokens = self.tokenizer.encode(novel_text)
        total_tokens = len(novel_tokens)
        logger.info(f"Novel contains {total_tokens} tokens")
        
        # Sample positions
        logger.info(f"Sampling {num_questions} positions using {sampling_strategy} strategy...")
        positions = self._sample_positions(
            total_tokens,
            num_questions,
            sampling_strategy
        )
        logger.info(f"Sampled {len(positions)} positions")
        
        # Generate questions concurrently
        logger.info(f"Generating questions with concurrency={concurrency}...")
        questions = await self._generate_questions_concurrent(
            novel_tokens,
            positions,
            context_window_size,
            concurrency,
            retry_times
        )
        
        # Filter out None values (failed generations)
        valid_questions = [q for q in questions if q is not None]
        logger.info(
            f"Successfully generated {len(valid_questions)}/{len(positions)} questions"
        )
        
        # Save to file if output path provided
        if output_path:
            self._save_questions(
                valid_questions,
                output_path,
                novel_path,
                sampling_strategy,
                context_window_size
            )
            logger.info(f"Questions saved to {output_path}")
        
        return valid_questions
    
    def _sample_positions(
        self,
        total_tokens: int,
        num_samples: int,
        strategy: str
    ) -> List[int]:
        """
        Sample positions based on strategy.
        
        Args:
            total_tokens: Total number of tokens in novel.
            num_samples: Number of positions to sample.
            strategy: Sampling strategy name.
            
        Returns:
            List of sampled token positions, sorted.
        """
        sampling_strategy = get_sampling_strategy(strategy)
        return sampling_strategy.sample(total_tokens, num_samples)
    
    def _extract_context(
        self,
        tokens: List[int],
        position: int,
        window_size: int
    ) -> Tuple[str, int, int]:
        """
        Extract context window with boundary alignment.
        
        Args:
            tokens: Full token list.
            position: Center position for extraction.
            window_size: Size of context window in tokens.
            
        Returns:
            Tuple of (context_text, start_token_pos, end_token_pos).
        """
        context_tokens, start_pos, end_pos = self.tokenizer.extract_context_from_tokens(
            tokens,
            position,
            window_size
        )
        
        context_text = self.tokenizer.decode(context_tokens)
        
        return context_text, start_pos, end_pos
    
    async def _generate_single_question(
        self,
        context: str,
        position: int,
        start_pos: int,
        end_pos: int,
        retry_times: int = 3
    ) -> Optional[Dict]:
        """
        Generate one question from context with validation and retry.
        
        Args:
            context: Context text for question generation.
            position: Original sampled position.
            start_pos: Start token position of context.
            end_pos: End token position of context.
            retry_times: Maximum retry attempts.
            
        Returns:
            Generated question dictionary, or None if all attempts failed.
        """
        # Randomly choose question type
        import random
        question_types = ["single_choice", "multiple_choice"]
        question_type = random.choice(question_types)
        
        for attempt in range(retry_times):
            try:
                # Get prompt from template manager
                system_prompt, user_prompt = self.prompt_manager.get_question_generation_prompt(
                    context,
                    question_type
                )
                
                # Log context length for debugging
                context_token_count = len(self.tokenizer.encode(context))
                logger.debug(f"Context length: {context_token_count} tokens")
                
                # Generate question via LLM
                response = await self.llm_client.generate(
                    user_prompt,
                    system_prompt,
                    max_retries=1  # LLM client has its own retry logic
                )
                
                if response is None:
                    logger.warning(
                        f"LLM returned None for position {position}, "
                        f"attempt {attempt + 1}/{retry_times}"
                    )
                    continue
                
                # Log response length for debugging
                logger.debug(f"Response length: {len(response)} chars")
                
                # Parse JSON response
                question = self._parse_question_response(response)
                
                if question is None:
                    # Log more details about the failed response
                    response_preview = response[:300] if response else "None"
                    logger.warning(
                        f"Failed to parse response for position {position}, "
                        f"attempt {attempt + 1}/{retry_times}. "
                        f"Response preview: {response_preview}"
                    )
                    continue
                
                # Add position information
                question["position"] = {
                    "start_pos": start_pos,
                    "end_pos": end_pos
                }
                
                # Validate question
                is_valid, error_msg = self.validator.validate(question)
                
                if is_valid:
                    logger.debug(f"Successfully generated question at position {position}")
                    return question
                else:
                    logger.warning(
                        f"Validation failed for position {position}: {error_msg}, "
                        f"attempt {attempt + 1}/{retry_times}"
                    )
                    # Try again with different question type
                    question_type = random.choice(question_types)
                    continue
            
            except Exception as e:
                import traceback
                logger.error(
                    f"Error generating question at position {position}: {type(e).__name__}: {e}, "
                    f"attempt {attempt + 1}/{retry_times}"
                )
                logger.debug(f"Full traceback: {traceback.format_exc()}")
                continue
        
        logger.error(
            f"Failed to generate valid question at position {position} "
            f"after {retry_times} attempts"
        )
        return None
    
    def _parse_question_response(self, response: str) -> Optional[Dict]:
        """
        Parse LLM response to extract question JSON.
        
        Tries multiple strategies:
        1. Direct JSON parse
        2. Extract JSON from markdown code blocks
        3. Regex extraction of JSON object (handles nested objects)
        
        Args:
            response: LLM response text.
            
        Returns:
            Parsed question dictionary, or None if parsing failed.
        """
        import re
        
        if not response or not response.strip():
            logger.debug("Empty response received")
            return None
        
        # Clean up response - remove potential BOM and leading/trailing whitespace
        response = response.strip()
        
        # Strategy 1: Direct JSON parse
        try:
            question = json.loads(response)
            if isinstance(question, dict):
                return question
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Direct JSON parse failed: {e}")
        
        # Strategy 2: Extract from markdown code blocks
        code_block_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        match = re.search(code_block_pattern, response, re.DOTALL)
        if match:
            try:
                json_str = match.group(1).strip()
                question = json.loads(json_str)
                if isinstance(question, dict):
                    return question
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Markdown code block parse failed: {e}")
        
        # Strategy 3: Extract JSON object with brace matching (handles nested objects)
        try:
            # Find opening brace
            start_idx = response.find('{')
            if start_idx == -1:
                logger.debug("No opening brace found in response")
                return None
            
            # Count braces to find matching closing brace
            brace_count = 0
            end_idx = start_idx
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(response)):
                char = response[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"':
                    in_string = not in_string
                    continue
                
                if in_string:
                    continue
                
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if brace_count == 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                question = json.loads(json_str)
                if isinstance(question, dict):
                    return question
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.debug(f"Brace matching parse failed: {e}")
        
        # Log first 500 chars of failed response for debugging
        logger.debug(f"Failed to parse response: {response[:500]}...")
        return None
    
    async def _generate_questions_concurrent(
        self,
        tokens: List[int],
        positions: List[int],
        window_size: int,
        concurrency: int,
        retry_times: int
    ) -> List[Optional[Dict]]:
        """
        Generate questions concurrently using asyncio.
        
        Args:
            tokens: Full token list.
            positions: List of positions to generate questions for.
            window_size: Context window size.
            concurrency: Maximum concurrent tasks.
            retry_times: Maximum retry attempts per question.
            
        Returns:
            List of generated questions (None for failed generations).
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def generate_with_semaphore(pos: int, idx: int) -> Optional[Dict]:
            async with semaphore:
                logger.info(f"Generating question {idx + 1}/{len(positions)} at position {pos}")
                
                # Extract context
                context, start_pos, end_pos = self._extract_context(
                    tokens,
                    pos,
                    window_size
                )
                
                # Generate question
                question = await self._generate_single_question(
                    context,
                    pos,
                    start_pos,
                    end_pos,
                    retry_times
                )
                
                return question
        
        # Create tasks for all positions
        tasks = [
            generate_with_semaphore(pos, idx)
            for idx, pos in enumerate(positions)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to None
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Question generation {i} failed with exception: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _save_questions(
        self,
        questions: List[Dict],
        output_path: str,
        novel_path: str,
        sampling_strategy: str,
        context_window_size: int
    ) -> None:
        """
        Save generated questions to JSONL file with metadata.
        
        Args:
            questions: List of question dictionaries.
            output_path: Output file path.
            novel_path: Source novel file path.
            sampling_strategy: Sampling strategy used.
            context_window_size: Context window size used.
        """
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "model_name": self.llm_client.model_name,
            "novel_path": novel_path,
            "total_questions": len(questions),
            "sampling_strategy": sampling_strategy,
            "context_window_size": context_window_size,
            "config": {
                "temperature": self.llm_client.temperature,
                "max_tokens": self.llm_client.max_tokens,
                "timeout": self.llm_client.timeout
            }
        }
        
        FileIO.write_jsonl(output_path, questions, metadata)
