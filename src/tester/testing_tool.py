"""
Testing tool core logic for executing tests on target LLM.

This module implements the TestingTool class which orchestrates the testing
process: loading questions, preparing context, executing tests concurrently,
and saving results with metadata.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..core.llm_client import LLMClient
from ..core.tokenizer import Tokenizer
from ..core.file_io import FileIO
from ..core.prompt_template import PromptTemplateManager
from .parser import parse_answer
from .question_checker import QuestionChecker, QuestionCheckError
from .context_builder import ContextBuilder
from .depth_scheduler import DepthScheduler, DepthMode, DepthAssignment


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestingTool:
    """
    Core testing tool for executing tests on target LLM.
    
    This class handles the complete testing pipeline:
    1. Load novel and questions
    2. Prepare context from novel
    3. Filter questions based on context length
    4. Execute tests concurrently
    5. Parse and validate answers
    6. Save results with metadata
    """
    
    def __init__(self, config: Dict, llm_client: LLMClient):
        """
        Initialize TestingTool with configuration and LLM client.
        
        Args:
            config: Configuration dictionary containing test parameters
            llm_client: Initialized LLM client for making API calls
        """
        self.config = config
        self.llm_client = llm_client
        self.tokenizer = Tokenizer()
        self.file_io = FileIO()
        self.prompt_manager = PromptTemplateManager()
        self.question_checker = QuestionChecker()
        
        logger.info("TestingTool initialized")
    
    async def run_tests(
        self,
        novel_path: str,
        question_set_path: str,
        context_length: int,
        padding_size: int = 500,
        concurrency: int = 5,
        output_path: Optional[str] = None,
        skip_validation: bool = False,
        ignore_invalid: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for testing.
        
        This method orchestrates the complete testing pipeline:
        1. Load novel and tokenize
        2. Load question set
        3. Pre-check questions for validation status
        4. Prepare context (first N tokens)
        5. Filter questions that fit in context
        6. Execute tests concurrently
        7. Save results to JSONL
        
        Args:
            novel_path: Path to novel text file
            question_set_path: Path to question set JSONL file
            context_length: Number of tokens to use as context
            padding_size: Buffer tokens to ensure answer region not truncated (default: 500)
            concurrency: Number of concurrent test requests (default: 5)
            output_path: Optional path to save results (default: auto-generated)
            skip_validation: Skip validation field check entirely (default: False)
            ignore_invalid: Filter out invalid questions instead of erroring (default: False)
            
        Returns:
            List of test result dictionaries
            
        Raises:
            QuestionCheckError: If validation check fails
        """
        logger.info(f"Starting test run with context_length={context_length}")
        logger.info(f"Novel: {novel_path}")
        logger.info(f"Questions: {question_set_path}")
        
        # Load novel and tokenize
        logger.info("Loading and tokenizing novel...")
        novel_text = self.file_io.read_novel(novel_path)
        novel_tokens = self.tokenizer.encode(novel_text)
        logger.info(f"Novel loaded: {len(novel_tokens)} tokens")
        
        # Load question set
        logger.info("Loading question set...")
        metadata, questions = self.file_io.read_jsonl(question_set_path)
        logger.info(f"Loaded {len(questions)} questions")
        
        # Pre-check questions for validation status (before any API calls)
        logger.info("Pre-checking questions for validation status...")
        questions, check_results = self.question_checker.check_questions(
            questions=questions,
            skip_validation=skip_validation,
            ignore_invalid=ignore_invalid
        )
        
        # Prepare context
        logger.info(f"Preparing context ({context_length} tokens)...")
        context = self._prepare_context(novel_tokens, context_length)
        logger.info(f"Context prepared: {len(context)} characters")
        
        # Filter questions
        logger.info(f"Filtering questions (padding_size={padding_size})...")
        filtered_questions = self._filter_questions(
            questions, context_length, padding_size
        )
        logger.info(
            f"Filtered to {len(filtered_questions)} questions "
            f"(removed {len(questions) - len(filtered_questions)})"
        )
        
        if not filtered_questions:
            logger.warning("No questions passed filtering!")
            return []
        
        # Execute tests concurrently
        logger.info(f"Executing tests (concurrency={concurrency})...")
        results = await self._test_batch(
            context, filtered_questions, concurrency
        )
        logger.info(f"Testing complete: {len(results)} results")
        
        # Calculate summary statistics
        self._log_summary(results)
        
        # Save results if output path provided
        if output_path:
            self._save_results(
                results, output_path, novel_path, question_set_path,
                context_length, padding_size, metadata
            )
        
        return results
    
    def _prepare_context(
        self,
        novel_tokens: List[int],
        context_length: int
    ) -> str:
        """
        Extract first N tokens as context.
        
        Args:
            novel_tokens: Full novel token list
            context_length: Number of tokens to extract
            
        Returns:
            Context text string
        """
        # Extract first N tokens
        context_tokens = novel_tokens[:context_length]
        
        # Decode to text
        context = self.tokenizer.decode(context_tokens)
        
        return context
    
    def _filter_questions(
        self,
        questions: List[Dict[str, Any]],
        context_length: int,
        padding_size: int
    ) -> List[Dict[str, Any]]:
        """
        Filter questions that fit in context.
        
        Questions are included if:
        answer_end_position + padding_size <= context_length
        
        This ensures the answer region is not truncated and has
        sufficient buffer space.
        
        Args:
            questions: List of question dictionaries
            context_length: Total context length in tokens
            padding_size: Buffer tokens after answer region
            
        Returns:
            Filtered list of questions
        """
        filtered = []
        
        for question in questions:
            # Get answer position
            position = question.get("position", {})
            end_pos = position.get("end_pos", 0)
            
            # Check if question fits in context with padding
            if end_pos + padding_size <= context_length:
                filtered.append(question)
            else:
                logger.debug(
                    f"Filtered out question: end_pos={end_pos}, "
                    f"required={end_pos + padding_size}, "
                    f"context_length={context_length}"
                )
        
        return filtered
    
    async def _test_batch(
        self,
        context: str,
        questions: List[Dict[str, Any]],
        concurrency: int
    ) -> List[Dict[str, Any]]:
        """
        Execute tests concurrently using asyncio.
        
        Args:
            context: Prepared context text
            questions: List of questions to test
            concurrency: Maximum concurrent requests
            
        Returns:
            List of test results
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def test_with_semaphore(question: Dict[str, Any], idx: int) -> Dict[str, Any]:
            async with semaphore:
                logger.info(f"Testing question {idx + 1}/{len(questions)}")
                return await self._test_single_question(context, question)
        
        tasks = [
            test_with_semaphore(question, idx)
            for idx, question in enumerate(questions)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Question {i + 1} failed with exception: {result}")
                # Create error result
                question = questions[i]
                processed_results.append({
                    "question": question.get("question", ""),
                    "question_type": question.get("question_type", ""),
                    "choice": question.get("choice", {}),
                    "correct_answer": question.get("answer", []),
                    "model_answer": [],
                    "parsing_status": "error",
                    "position": question.get("position", {}),
                    "score": 0.0,
                    "metrics": {}
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _test_single_question(
        self,
        context: str,
        question: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test one question.
        
        This method:
        1. Formats the testing prompt
        2. Calls LLM to get answer
        3. Parses the response
        4. Calculates score and metrics
        5. Returns structured result
        
        Args:
            context: Context text for answering
            question: Question dictionary
            
        Returns:
            Test result dictionary with all fields
        """
        # Extract question fields
        question_text = question.get("question", "")
        question_type = question.get("question_type", "")
        choices = question.get("choice", {})
        correct_answer = question.get("answer", [])
        position = question.get("position", {})
        
        # Get testing prompt
        system_prompt, user_prompt = self.prompt_manager.get_testing_prompt(
            context=context,
            question=question_text,
            choices=choices
        )
        
        # Call LLM
        response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt
        )
        
        # Handle None response (all retries failed)
        if response is None:
            logger.warning(f"LLM returned None for question: {question_text[:50]}...")
            return {
                "question": question_text,
                "question_type": question_type,
                "choice": choices,
                "correct_answer": correct_answer,
                "model_answer": [],
                "parsing_status": "timeout",
                "position": position,
                "score": 0.0,
                "metrics": {}
            }
        
        # Parse answer
        model_answer, parsing_status = parse_answer(response)
        
        # Calculate score and metrics
        score, metrics = self._calculate_score(
            correct_answer, model_answer, question_type
        )
        
        # Build result
        result = {
            "question": question_text,
            "question_type": question_type,
            "choice": choices,
            "correct_answer": correct_answer,
            "model_answer": model_answer,
            "parsing_status": parsing_status,
            "position": position,
            "score": score,
            "metrics": metrics
        }
        
        return result
    
    def _calculate_score(
        self,
        correct_answer: List[str],
        model_answer: List[str],
        question_type: str
    ) -> tuple[float, Dict[str, float]]:
        """
        Calculate score and metrics for a test result.
        
        For single-choice questions:
        - Score is 1.0 if correct, 0.0 otherwise
        
        For multiple-choice questions:
        - Calculate precision, recall, and F1 score
        - Score is the F1 score
        
        Args:
            correct_answer: List of correct answer keys
            model_answer: List of model's answer keys
            question_type: Type of question
            
        Returns:
            Tuple of (score, metrics_dict)
        """
        metrics = {}
        
        if question_type == "single_choice":
            # Simple accuracy for single choice
            if model_answer == correct_answer:
                score = 1.0
            else:
                score = 0.0
        
        elif question_type == "multiple_choice":
            # Calculate precision, recall, F1 for multiple choice
            correct_set = set(correct_answer)
            predicted_set = set(model_answer)
            
            # Precision
            if len(predicted_set) == 0:
                precision = 0.0
            else:
                precision = len(correct_set & predicted_set) / len(predicted_set)
            
            # Recall
            if len(correct_set) == 0:
                recall = 0.0
            else:
                recall = len(correct_set & predicted_set) / len(correct_set)
            
            # F1 score
            if precision + recall == 0:
                f1 = 0.0
            else:
                f1 = 2 * (precision * recall) / (precision + recall)
            
            metrics = {
                "precision": precision,
                "recall": recall,
                "f1_score": f1
            }
            
            score = f1
        
        else:
            # Unknown question type, default to 0
            score = 0.0
        
        return score, metrics
    
    def _validate_context_lengths(
        self,
        context_lengths: List[int],
        novel_length: int,
        questions: List[Dict[str, Any]],
        padding_size: int
    ) -> None:
        """
        Validate context lengths against novel and question set.
        
        Checks:
        1. Context lengths must not exceed novel length
        2. Context lengths must be large enough to contain at least some questions
        
        Args:
            context_lengths: List of context lengths to validate
            novel_length: Total length of novel in tokens
            questions: List of questions with position information
            padding_size: Padding size for evidence
            
        Raises:
            ValueError: If context lengths are invalid
        """
        # Check maximum context length against novel
        max_context = max(context_lengths)
        if max_context > novel_length:
            raise ValueError(
                f"Maximum context length ({max_context:,} tokens) exceeds "
                f"novel length ({novel_length:,} tokens). "
                f"Please reduce --context-lengths to at most {novel_length:,}."
            )
        
        # Find minimum evidence end position in questions
        min_evidence_end = float('inf')
        max_evidence_end = 0
        
        for q in questions:
            position = q.get("position", {})
            end_pos = position.get("end_pos", 0)
            if end_pos > 0:
                min_evidence_end = min(min_evidence_end, end_pos)
                max_evidence_end = max(max_evidence_end, end_pos)
        
        if min_evidence_end == float('inf'):
            raise ValueError(
                "No valid position information found in questions. "
                "Questions must have position.end_pos field."
            )
        
        # Check minimum context length
        # Need at least: evidence + padding on both sides
        min_required = min_evidence_end + padding_size
        min_context = min(context_lengths)
        
        if min_context < min_required:
            raise ValueError(
                f"Minimum context length ({min_context:,} tokens) is too small. "
                f"The earliest question evidence ends at position {min_evidence_end:,}, "
                f"requiring at least {min_required:,} tokens (with {padding_size} padding). "
                f"Please increase --context-lengths to at least {min_required:,}."
            )
        
        # Check if any context length can cover questions
        # For depth-aware testing, we need context_length > evidence_length + padding
        usable_questions = 0
        for q in questions:
            position = q.get("position", {})
            start_pos = position.get("start_pos", 0)
            end_pos = position.get("end_pos", 0)
            evidence_length = end_pos - start_pos + 2 * padding_size
            
            # Check if any context length can accommodate this question
            for ctx_len in context_lengths:
                if ctx_len > evidence_length:
                    usable_questions += 1
                    break
        
        if usable_questions == 0:
            raise ValueError(
                f"No questions can be tested with the given context lengths. "
                f"All context lengths are too small to accommodate evidence + padding. "
                f"Maximum evidence span is approximately {max_evidence_end - min_evidence_end:,} tokens. "
                f"Please increase --context-lengths."
            )
        
        # Log validation results
        logger.info(f"Context length validation passed:")
        logger.info(f"  Novel length: {novel_length:,} tokens")
        logger.info(f"  Context lengths: {[f'{c:,}' for c in context_lengths]}")
        logger.info(f"  Questions with valid positions: {len(questions)}")
        logger.info(f"  Questions usable for testing: {usable_questions}")
    
    def _log_summary(self, results: List[Dict[str, Any]]):
        """
        Log summary statistics of test results.
        
        Args:
            results: List of test results
        """
        total = len(results)
        
        # Count by parsing status
        success = sum(1 for r in results if r["parsing_status"] == "success")
        regex_extracted = sum(1 for r in results if r["parsing_status"] == "regex_extracted")
        parsing_error = sum(1 for r in results if r["parsing_status"] == "parsing_error")
        timeout = sum(1 for r in results if r["parsing_status"] == "timeout")
        
        # Calculate average score
        avg_score = sum(r["score"] for r in results) / total if total > 0 else 0.0
        
        # Count by question type
        single_choice = sum(1 for r in results if r["question_type"] == "single_choice")
        multiple_choice = sum(1 for r in results if r["question_type"] == "multiple_choice")
        
        logger.info("=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total questions tested: {total}")
        logger.info(f"  Single choice: {single_choice}")
        logger.info(f"  Multiple choice: {multiple_choice}")
        logger.info("")
        logger.info(f"Parsing status:")
        logger.info(f"  Success: {success}")
        logger.info(f"  Regex extracted: {regex_extracted}")
        logger.info(f"  Parsing error: {parsing_error}")
        logger.info(f"  Timeout: {timeout}")
        logger.info("")
        logger.info(f"Average score: {avg_score:.4f}")
        logger.info("=" * 60)
    
    def _save_results(
        self,
        results: List[Dict[str, Any]],
        output_path: str,
        novel_path: str,
        question_set_path: str,
        context_length: int,
        padding_size: int,
        question_metadata: Dict[str, Any]
    ):
        """
        Save test results to JSONL file with metadata.
        
        Args:
            results: List of test results
            output_path: Path to save results
            novel_path: Path to novel file (for metadata)
            question_set_path: Path to question set (for metadata)
            context_length: Context length used (for metadata)
            padding_size: Padding size used (for metadata)
            question_metadata: Metadata from question set
        """
        # Build metadata
        metadata = {
            "tested_at": datetime.now().isoformat(),
            "model_name": self.config.get("model_name", "unknown"),
            "novel_path": novel_path,
            "question_set_path": question_set_path,
            "context_length": context_length,
            "padding_size": padding_size,
            "total_questions": len(results),
            "tested_questions": len(results),
            "config": self.config,
            "question_set_metadata": question_metadata
        }
        
        # Save to JSONL
        self.file_io.write_jsonl(output_path, results, metadata)
        logger.info(f"Results saved to: {output_path}")

    async def run_depth_aware_tests(
        self,
        novel_path: str,
        question_set_path: str,
        depth_mode: str,
        context_lengths: List[int],
        fixed_depth: Optional[float] = None,
        padding_size: int = 500,
        concurrency: int = 5,
        output_path: Optional[str] = None,
        skip_validation: bool = False,
        ignore_invalid: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute depth-aware tests with evidence at different context depths.
        
        This method dynamically constructs test contexts with evidence placed
        at specified depth positions, enabling evaluation of LLM recall across
        different context depths.
        
        Args:
            novel_path: Path to novel text file
            question_set_path: Path to question set JSONL file
            depth_mode: Depth scheduling mode ("uniform" or "fixed")
            context_lengths: List of context lengths to test
            fixed_depth: Depth value for "fixed" mode (0.0-1.0)
            padding_size: Buffer tokens around evidence (default: 500)
            concurrency: Number of concurrent test requests (default: 5)
            output_path: Optional path to save results
            skip_validation: Skip validation field check (default: False)
            ignore_invalid: Filter out invalid questions (default: False)
            
        Returns:
            List of test result dictionaries with depth information
        """
        logger.info(f"Starting depth-aware test run")
        logger.info(f"  Mode: {depth_mode}")
        logger.info(f"  Context lengths: {context_lengths}")
        logger.info(f"  Fixed depth: {fixed_depth}")
        
        # Load novel and tokenize
        logger.info("Loading and tokenizing novel...")
        novel_text = self.file_io.read_novel(novel_path)
        novel_tokens = self.tokenizer.encode(novel_text)
        novel_length = len(novel_tokens)
        logger.info(f"Novel loaded: {novel_length} tokens")
        
        # Load question set
        logger.info("Loading question set...")
        metadata, questions = self.file_io.read_jsonl(question_set_path)
        logger.info(f"Loaded {len(questions)} questions")
        
        # Validate context lengths against novel and questions
        logger.info("Validating context lengths...")
        self._validate_context_lengths(
            context_lengths=context_lengths,
            novel_length=novel_length,
            questions=questions,
            padding_size=padding_size
        )
        
        # Pre-check questions for validation status
        logger.info("Pre-checking questions for validation status...")
        questions, check_results = self.question_checker.check_questions(
            questions=questions,
            skip_validation=skip_validation,
            ignore_invalid=ignore_invalid
        )
        
        if not questions:
            logger.warning("No questions passed validation check!")
            return []
        
        # Initialize depth scheduler
        mode = DepthMode(depth_mode)
        scheduler = DepthScheduler(
            mode=mode,
            fixed_depth=fixed_depth,
            context_lengths=context_lengths
        )
        
        # Schedule depth assignments
        logger.info("Scheduling depth assignments...")
        assignments = scheduler.schedule(questions)
        logger.info(f"Created {len(assignments)} test assignments")
        
        # Initialize context builder
        context_builder = ContextBuilder(self.tokenizer, novel_tokens)
        
        # Execute tests concurrently
        logger.info(f"Executing depth-aware tests (concurrency={concurrency})...")
        results = await self._test_depth_aware_batch(
            questions=questions,
            assignments=assignments,
            context_builder=context_builder,
            padding_size=padding_size,
            concurrency=concurrency
        )
        logger.info(f"Testing complete: {len(results)} results")
        
        # Calculate summary statistics
        self._log_depth_aware_summary(results)
        
        # Save results if output path provided
        if output_path:
            self._save_depth_aware_results(
                results=results,
                output_path=output_path,
                novel_path=novel_path,
                question_set_path=question_set_path,
                depth_mode=depth_mode,
                context_lengths=context_lengths,
                fixed_depth=fixed_depth,
                padding_size=padding_size,
                question_metadata=metadata
            )
        
        return results
    
    async def _test_depth_aware_batch(
        self,
        questions: List[Dict[str, Any]],
        assignments: List[DepthAssignment],
        context_builder: ContextBuilder,
        padding_size: int,
        concurrency: int
    ) -> List[Dict[str, Any]]:
        """
        Execute depth-aware tests concurrently.
        
        Args:
            questions: List of questions
            assignments: Depth assignments for each question
            context_builder: Context builder instance
            padding_size: Padding around evidence
            concurrency: Maximum concurrent requests
            
        Returns:
            List of test results with depth information
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def test_with_semaphore(
            assignment: DepthAssignment,
            idx: int
        ) -> Dict[str, Any]:
            async with semaphore:
                question = questions[assignment.question_index]
                logger.info(
                    f"Testing question {idx + 1}/{len(assignments)} "
                    f"(depth={assignment.depth_bin}, context={assignment.context_length})"
                )
                return await self._test_single_depth_aware(
                    question=question,
                    assignment=assignment,
                    context_builder=context_builder,
                    padding_size=padding_size
                )
        
        tasks = [
            test_with_semaphore(assignment, idx)
            for idx, assignment in enumerate(assignments)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Assignment {i + 1} failed with exception: {result}")
                assignment = assignments[i]
                question = questions[assignment.question_index]
                processed_results.append({
                    "question": question.get("question", ""),
                    "question_type": question.get("question_type", ""),
                    "choice": question.get("choice", {}),
                    "correct_answer": question.get("answer", []),
                    "model_answer": [],
                    "parsing_status": "error",
                    "position": question.get("position", {}),
                    "score": 0.0,
                    "metrics": {},
                    "depth": assignment.target_depth,
                    "depth_bin": assignment.depth_bin,
                    "test_context_length": assignment.context_length
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _test_single_depth_aware(
        self,
        question: Dict[str, Any],
        assignment: DepthAssignment,
        context_builder: ContextBuilder,
        padding_size: int
    ) -> Dict[str, Any]:
        """
        Test one question with depth-aware context.
        
        Args:
            question: Question dictionary
            assignment: Depth assignment for this question
            context_builder: Context builder instance
            padding_size: Padding around evidence
            
        Returns:
            Test result dictionary with depth information
        """
        # Extract question fields
        question_text = question.get("question", "")
        question_type = question.get("question_type", "")
        choices = question.get("choice", {})
        correct_answer = question.get("answer", [])
        position = question.get("position", {})
        
        # Build context with evidence at target depth
        build_result = context_builder.build_context(
            question=question,
            target_depth=assignment.target_depth,
            context_length=assignment.context_length,
            padding_size=padding_size
        )
        
        if not build_result.success:
            logger.warning(
                f"Context build failed for question: {build_result.error_message}"
            )
            return {
                "question": question_text,
                "question_type": question_type,
                "choice": choices,
                "correct_answer": correct_answer,
                "model_answer": [],
                "parsing_status": "context_build_error",
                "position": position,
                "score": 0.0,
                "metrics": {},
                "depth": assignment.target_depth,
                "depth_bin": assignment.depth_bin,
                "test_context_length": assignment.context_length,
                "error_message": build_result.error_message
            }
        
        # Get testing prompt
        system_prompt, user_prompt = self.prompt_manager.get_testing_prompt(
            context=build_result.context,
            question=question_text,
            choices=choices
        )
        
        # Call LLM
        response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt
        )
        
        # Handle None response
        if response is None:
            logger.warning(f"LLM returned None for question: {question_text[:50]}...")
            return {
                "question": question_text,
                "question_type": question_type,
                "choice": choices,
                "correct_answer": correct_answer,
                "model_answer": [],
                "parsing_status": "timeout",
                "position": position,
                "score": 0.0,
                "metrics": {},
                "depth": assignment.target_depth,
                "depth_bin": assignment.depth_bin,
                "test_context_length": assignment.context_length
            }
        
        # Parse answer
        model_answer, parsing_status = parse_answer(response)
        
        # Calculate score and metrics
        score, metrics = self._calculate_score(
            correct_answer, model_answer, question_type
        )
        
        # Build result with depth information
        result = {
            "question": question_text,
            "question_type": question_type,
            "choice": choices,
            "correct_answer": correct_answer,
            "model_answer": model_answer,
            "parsing_status": parsing_status,
            "position": position,
            "score": score,
            "metrics": metrics,
            "depth": build_result.actual_depth,
            "depth_bin": assignment.depth_bin,
            "test_context_length": assignment.context_length
        }
        
        return result
    
    def _log_depth_aware_summary(self, results: List[Dict[str, Any]]):
        """
        Log summary statistics for depth-aware test results.
        
        Args:
            results: List of test results with depth information
        """
        total = len(results)
        if total == 0:
            logger.info("No results to summarize")
            return
        
        # Overall statistics
        avg_score = sum(r["score"] for r in results) / total
        
        # Group by depth bin
        depth_stats = {}
        for r in results:
            depth_bin = r.get("depth_bin", "unknown")
            if depth_bin not in depth_stats:
                depth_stats[depth_bin] = {"count": 0, "total_score": 0.0}
            depth_stats[depth_bin]["count"] += 1
            depth_stats[depth_bin]["total_score"] += r["score"]
        
        # Group by context length
        length_stats = {}
        for r in results:
            ctx_len = r.get("test_context_length", 0)
            if ctx_len not in length_stats:
                length_stats[ctx_len] = {"count": 0, "total_score": 0.0}
            length_stats[ctx_len]["count"] += 1
            length_stats[ctx_len]["total_score"] += r["score"]
        
        logger.info("=" * 60)
        logger.info("DEPTH-AWARE TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total questions tested: {total}")
        logger.info(f"Overall average score: {avg_score:.4f}")
        logger.info("")
        logger.info("Accuracy by depth:")
        for depth_bin in ["0%", "25%", "50%", "75%", "100%"]:
            if depth_bin in depth_stats:
                stats = depth_stats[depth_bin]
                acc = stats["total_score"] / stats["count"] if stats["count"] > 0 else 0
                logger.info(f"  {depth_bin}: {acc:.4f} ({stats['count']} questions)")
        logger.info("")
        logger.info("Accuracy by context length:")
        for ctx_len in sorted(length_stats.keys()):
            stats = length_stats[ctx_len]
            acc = stats["total_score"] / stats["count"] if stats["count"] > 0 else 0
            logger.info(f"  {ctx_len//1000}K: {acc:.4f} ({stats['count']} questions)")
        logger.info("=" * 60)
    
    def _save_depth_aware_results(
        self,
        results: List[Dict[str, Any]],
        output_path: str,
        novel_path: str,
        question_set_path: str,
        depth_mode: str,
        context_lengths: List[int],
        fixed_depth: Optional[float],
        padding_size: int,
        question_metadata: Dict[str, Any]
    ):
        """
        Save depth-aware test results to JSONL file with metadata.
        
        Args:
            results: List of test results
            output_path: Path to save results
            novel_path: Path to novel file
            question_set_path: Path to question set
            depth_mode: Depth mode used
            context_lengths: Context lengths tested
            fixed_depth: Fixed depth value (if applicable)
            padding_size: Padding size used
            question_metadata: Metadata from question set
        """
        # Build metadata
        metadata = {
            "tested_at": datetime.now().isoformat(),
            "model_name": self.config.get("model_name", "unknown"),
            "novel_path": novel_path,
            "question_set_path": question_set_path,
            "depth_mode": depth_mode,
            "context_lengths": context_lengths,
            "fixed_depth": fixed_depth,
            "depth_bins": ["0%", "25%", "50%", "75%", "100%"],
            "padding_size": padding_size,
            "total_questions": len(results),
            "config": self.config,
            "question_set_metadata": question_metadata
        }
        
        # Save to JSONL
        self.file_io.write_jsonl(output_path, results, metadata)
        logger.info(f"Depth-aware results saved to: {output_path}")
