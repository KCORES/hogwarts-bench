"""
Question validator core logic for validating LLM-generated questions.

This module implements the QuestionValidator class which orchestrates the
validation process: calling verification LLM, matching evidence, comparing
answers, and producing validation results.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from ..core.llm_client import LLMClient
from ..core.tokenizer import Tokenizer
from ..core.prompt_template import PromptTemplateManager
from .evidence_matcher import EvidenceMatcher
from .validation_result import ValidationResult, CONFIDENCE_LEVELS
from .answer_comparator import compare_answers, parse_answer_from_response


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionValidator:
    """
    Core validator for checking question quality through LLM backtesting.
    
    Validates questions by:
    1. Having a verification LLM independently answer the question
    2. Comparing the model's answer with the labeled answer
    3. Verifying that evidence exists in the source context
    4. Checking answerability and confidence levels
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        prompt_manager: PromptTemplateManager = None,
        similarity_threshold: float = 0.8,
        confidence_threshold: str = "medium"
    ):
        """
        Initialize the question validator.
        
        Args:
            llm_client: LLM client for verification calls
            prompt_manager: Prompt template manager (creates default if None)
            similarity_threshold: Minimum similarity for evidence matching
            confidence_threshold: Minimum confidence level required
        """
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager or PromptTemplateManager()
        self.evidence_matcher = EvidenceMatcher(similarity_threshold)
        self.tokenizer = Tokenizer()
        
        # Validate confidence threshold
        if confidence_threshold.lower() not in CONFIDENCE_LEVELS:
            raise ValueError(
                f"Invalid confidence_threshold: {confidence_threshold}. "
                f"Must be one of: {CONFIDENCE_LEVELS}"
            )
        self.confidence_threshold = confidence_threshold.lower()
        
        logger.info(
            f"QuestionValidator initialized with "
            f"similarity_threshold={similarity_threshold}, "
            f"confidence_threshold={confidence_threshold}"
        )
    
    async def validate_question(
        self,
        question: Dict[str, Any],
        context: str
    ) -> ValidationResult:
        """
        Validate a single question against its context.
        
        Args:
            question: Question dictionary with question, choice, answer fields
            context: Source context text
            
        Returns:
            ValidationResult with all validation details
        """
        # Extract question fields
        question_text = question.get("question", "")
        choices = question.get("choice", {})
        labeled_answer = question.get("answer", [])
        question_type = question.get("question_type", "single_choice")
        
        # Format choices for prompt
        choices_text = self._format_choices(choices)
        
        # Get validation prompt
        system_prompt, user_prompt = self.prompt_manager.get_validation_prompt(
            context=context,
            question=question_text,
            choices=choices_text
        )
        
        # Call verification LLM
        response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_retries=3
        )
        
        # Handle failed LLM call
        if response is None:
            logger.warning(f"LLM returned None for question: {question_text[:50]}...")
            return ValidationResult(
                question=question,
                is_valid=False,
                model_answer=[],
                answer_matches=False,
                evidence="",
                evidence_found=False,
                evidence_similarity=0.0,
                is_answerable=False,
                confidence="low",
                failure_reasons=["LLM verification call failed"]
            )
        
        # Parse LLM response
        parsed = self._parse_validation_response(response)
        
        if parsed is None:
            logger.warning(f"Failed to parse validation response: {response[:200]}...")
            return ValidationResult(
                question=question,
                is_valid=False,
                model_answer=[],
                answer_matches=False,
                evidence="",
                evidence_found=False,
                evidence_similarity=0.0,
                is_answerable=False,
                confidence="low",
                failure_reasons=["Failed to parse LLM response"]
            )
        
        # Extract parsed fields
        model_answer = parse_answer_from_response(parsed.get("answer", []))
        evidence = parsed.get("evidence", "")
        is_answerable = parsed.get("is_answerable", False)
        confidence = parsed.get("confidence", "low").lower()
        reasoning = parsed.get("reasoning", "")
        
        # Validate confidence value
        if confidence not in CONFIDENCE_LEVELS:
            confidence = "low"
        
        # Compare answers
        answer_matches = compare_answers(labeled_answer, model_answer, question_type)
        
        # Match evidence
        evidence_found, evidence_similarity, _ = self.evidence_matcher.find_evidence(
            evidence, context
        )
        
        # Check confidence threshold
        meets_confidence = ValidationResult.meets_confidence_threshold(
            confidence, self.confidence_threshold
        )
        
        # Determine overall validity and collect failure reasons
        failure_reasons = []
        
        if not answer_matches:
            failure_reasons.append(
                f"Answer mismatch: model={model_answer}, labeled={labeled_answer}"
            )
        
        if not evidence_found:
            failure_reasons.append(
                f"Evidence not found in context (similarity={evidence_similarity:.2f})"
            )
        
        if not is_answerable:
            failure_reasons.append("Question marked as not answerable from context")
        
        if not meets_confidence:
            failure_reasons.append(
                f"Confidence too low: {confidence} < {self.confidence_threshold}"
            )
        
        is_valid = (
            answer_matches and
            evidence_found and
            is_answerable and
            meets_confidence
        )
        
        return ValidationResult(
            question=question,
            is_valid=is_valid,
            model_answer=model_answer,
            answer_matches=answer_matches,
            evidence=evidence,
            evidence_found=evidence_found,
            evidence_similarity=evidence_similarity,
            is_answerable=is_answerable,
            confidence=confidence,
            failure_reasons=failure_reasons,
            reasoning=reasoning
        )

    
    async def validate_batch(
        self,
        questions: List[Dict[str, Any]],
        novel_tokens: List[int],
        concurrency: int = 5,
        retry_times: int = 3
    ) -> Tuple[List[ValidationResult], Dict[str, int]]:
        """
        Validate multiple questions concurrently.
        
        Args:
            questions: List of question dictionaries
            novel_tokens: Tokenized novel for context extraction
            concurrency: Maximum concurrent validation requests
            retry_times: Maximum retry attempts per question
            
        Returns:
            Tuple of (results_list, statistics_dict)
        """
        logger.info(f"Starting batch validation of {len(questions)} questions")
        logger.info(f"Concurrency: {concurrency}")
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def validate_with_semaphore(
            question: Dict[str, Any],
            idx: int
        ) -> ValidationResult:
            async with semaphore:
                logger.info(f"Validating question {idx + 1}/{len(questions)}")
                
                # Extract context for this question
                context = self._extract_context_for_question(question, novel_tokens)
                
                # Validate
                result = await self.validate_question(question, context)
                
                status = "PASS" if result.is_valid else "FAIL"
                logger.info(f"Question {idx + 1}: {status}")
                
                return result
        
        # Create tasks
        tasks = [
            validate_with_semaphore(q, i)
            for i, q in enumerate(questions)
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Question {i + 1} failed with exception: {result}")
                # Create error result
                processed_results.append(ValidationResult(
                    question=questions[i],
                    is_valid=False,
                    model_answer=[],
                    answer_matches=False,
                    evidence="",
                    evidence_found=False,
                    evidence_similarity=0.0,
                    is_answerable=False,
                    confidence="low",
                    failure_reasons=[f"Exception: {str(result)}"]
                ))
            else:
                processed_results.append(result)
        
        # Calculate statistics
        stats = self._calculate_statistics(processed_results)
        
        # Log summary
        self._log_summary(stats)
        
        return processed_results, stats
    
    def _extract_context_for_question(
        self,
        question: Dict[str, Any],
        novel_tokens: List[int]
    ) -> str:
        """
        Extract the context that was used to generate this question.
        
        Uses the position metadata stored in the question.
        
        Args:
            question: Question dictionary with position field
            novel_tokens: Full novel token list
            
        Returns:
            Context text string
        """
        position = question.get("position", {})
        start_pos = position.get("start_pos", 0)
        end_pos = position.get("end_pos", len(novel_tokens))
        
        # Extract tokens
        context_tokens = novel_tokens[start_pos:end_pos]
        
        # Decode to text
        context = self.tokenizer.decode(context_tokens)
        
        return context
    
    def _format_choices(self, choices: Dict[str, str]) -> str:
        """
        Format choices dictionary into readable string.
        
        Args:
            choices: Dictionary mapping option letters to text
            
        Returns:
            Formatted string like "A. option1\nB. option2\n..."
        """
        lines = []
        for key in sorted(choices.keys()):
            lines.append(f"{key.upper()}. {choices[key]}")
        return "\n".join(lines)
    
    def _parse_validation_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM validation response to extract JSON.
        
        Tries multiple strategies:
        1. Direct JSON parse
        2. Extract from markdown code blocks
        3. Regex extraction of JSON object
        
        Args:
            response: LLM response text
            
        Returns:
            Parsed dictionary or None if parsing failed
        """
        if not response or not response.strip():
            return None
        
        response = response.strip()
        
        # Strategy 1: Direct JSON parse
        try:
            result = json.loads(response)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Strategy 2: Extract from markdown code blocks
        code_block_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        match = re.search(code_block_pattern, response, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1).strip())
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Strategy 3: Find JSON object with brace matching
        try:
            start_idx = response.find('{')
            if start_idx == -1:
                return None
            
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
                result = json.loads(json_str)
                if isinstance(result, dict):
                    return result
        except (json.JSONDecodeError, ValueError, IndexError):
            pass
        
        return None
    
    def _calculate_statistics(
        self,
        results: List[ValidationResult]
    ) -> Dict[str, int]:
        """
        Calculate validation statistics.
        
        Args:
            results: List of validation results
            
        Returns:
            Dictionary with statistics
        """
        total = len(results)
        passed = sum(1 for r in results if r.is_valid)
        failed = total - passed
        
        # Count failure reasons
        answer_mismatch = sum(1 for r in results if not r.answer_matches)
        evidence_not_found = sum(1 for r in results if not r.evidence_found)
        not_answerable = sum(1 for r in results if not r.is_answerable)
        low_confidence = sum(
            1 for r in results
            if not ValidationResult.meets_confidence_threshold(
                r.confidence, self.confidence_threshold
            )
        )
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "answer_mismatch": answer_mismatch,
            "evidence_not_found": evidence_not_found,
            "not_answerable": not_answerable,
            "low_confidence": low_confidence,
        }
    
    def _log_summary(self, stats: Dict[str, Any]):
        """Log validation summary statistics."""
        logger.info("=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total questions: {stats['total']}")
        logger.info(f"Passed: {stats['passed']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Pass rate: {stats['pass_rate']:.1%}")
        logger.info("")
        logger.info("Failure breakdown:")
        logger.info(f"  Answer mismatch: {stats['answer_mismatch']}")
        logger.info(f"  Evidence not found: {stats['evidence_not_found']}")
        logger.info(f"  Not answerable: {stats['not_answerable']}")
        logger.info(f"  Low confidence: {stats['low_confidence']}")
        logger.info("=" * 60)
