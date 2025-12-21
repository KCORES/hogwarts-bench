"""
Question pre-checker module for validating question data before testing.

This module provides functionality to check questions for validation status
before executing tests, preventing wasted API calls on invalid data.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional


logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of checking a single question."""
    index: int
    question_preview: str
    has_validation: bool
    is_valid: Optional[bool]
    failure_reasons: List[str]


class QuestionCheckError(Exception):
    """Exception raised when question pre-check fails."""
    
    def __init__(self, message: str, check_results: List[CheckResult]):
        super().__init__(message)
        self.check_results = check_results


class QuestionChecker:
    """
    Pre-checks questions before testing to ensure data quality.
    
    Validates that:
    1. All questions have validation metadata (unless skip_validation=True)
    2. All questions have is_valid=True (unless ignore_invalid=True)
    """
    
    def check_questions(
        self,
        questions: List[Dict[str, Any]],
        skip_validation: bool = False,
        ignore_invalid: bool = False
    ) -> Tuple[List[Dict[str, Any]], List[CheckResult]]:
        """
        Check all questions and return valid ones.
        
        Args:
            questions: List of question dictionaries
            skip_validation: If True, skip validation field check entirely
            ignore_invalid: If True, filter out invalid questions instead of erroring
            
        Returns:
            Tuple of (valid_questions, check_results)
            
        Raises:
            QuestionCheckError: If validation fails and ignore_invalid=False
        """
        if skip_validation:
            logger.info("Skipping validation check (--skip-validation enabled)")
            return questions, []
        
        check_results = []
        missing_validation = []
        invalid_questions = []
        valid_questions = []
        
        for idx, question in enumerate(questions):
            question_preview = self._get_question_preview(question)
            validation = question.get("validation")
            
            # Check if validation field exists
            if validation is None:
                result = CheckResult(
                    index=idx,
                    question_preview=question_preview,
                    has_validation=False,
                    is_valid=None,
                    failure_reasons=["Missing 'validation' field"]
                )
                check_results.append(result)
                missing_validation.append(result)
                continue
            
            # Check if is_valid is True
            is_valid = validation.get("is_valid", False)
            failure_reasons = validation.get("failure_reasons", [])
            
            result = CheckResult(
                index=idx,
                question_preview=question_preview,
                has_validation=True,
                is_valid=is_valid,
                failure_reasons=failure_reasons if not is_valid else []
            )
            check_results.append(result)
            
            if is_valid:
                valid_questions.append(question)
            else:
                invalid_questions.append(result)
        
        # Handle missing validation fields (always error)
        if missing_validation:
            self._log_missing_validation(missing_validation)
            raise QuestionCheckError(
                f"Found {len(missing_validation)} questions without validation metadata. "
                "Please run validation first with: python -m src.validate",
                missing_validation
            )
        
        # Handle invalid questions
        if invalid_questions:
            if ignore_invalid:
                # Filter out invalid questions
                self._log_ignored_invalid(invalid_questions)
                logger.info(
                    f"Filtered out {len(invalid_questions)} invalid questions "
                    f"(--ignore-invalid enabled)"
                )
            else:
                # Error out
                self._log_invalid_questions(invalid_questions)
                raise QuestionCheckError(
                    f"Found {len(invalid_questions)} questions that failed validation. "
                    "Use --ignore-invalid to skip these questions, or re-validate the data.",
                    invalid_questions
                )
        
        # Check if any questions remain
        if not valid_questions:
            raise QuestionCheckError(
                "No valid questions remaining after filtering. "
                "All questions either lack validation or failed validation.",
                check_results
            )
        
        logger.info(
            f"Pre-check passed: {len(valid_questions)}/{len(questions)} questions valid"
        )
        
        return valid_questions, check_results
    
    def _get_question_preview(self, question: Dict[str, Any], max_length: int = 50) -> str:
        """Get a preview of the question text for logging."""
        text = question.get("question", "")
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
    
    def _log_missing_validation(self, results: List[CheckResult]):
        """Log questions missing validation metadata."""
        logger.error("=" * 60)
        logger.error("VALIDATION CHECK FAILED: Missing validation metadata")
        logger.error("=" * 60)
        logger.error(f"Found {len(results)} questions without 'validation' field:")
        logger.error("")
        
        for result in results[:10]:  # Show first 10
            logger.error(f"  Question {result.index + 1}: {result.question_preview}")
        
        if len(results) > 10:
            logger.error(f"  ... and {len(results) - 10} more")
        
        logger.error("")
        logger.error("Please run validation first:")
        logger.error("  python -m src.validate --novel <novel> --questions <questions> --output <output>")
        logger.error("=" * 60)
    
    def _log_invalid_questions(self, results: List[CheckResult]):
        """Log questions that failed validation."""
        logger.error("=" * 60)
        logger.error("VALIDATION CHECK FAILED: Invalid questions found")
        logger.error("=" * 60)
        logger.error(f"Found {len(results)} questions that failed validation:")
        logger.error("")
        
        for result in results[:10]:  # Show first 10
            logger.error(f"  Question {result.index + 1}: {result.question_preview}")
            for reason in result.failure_reasons[:2]:  # Show first 2 reasons
                logger.error(f"    - {reason}")
        
        if len(results) > 10:
            logger.error(f"  ... and {len(results) - 10} more")
        
        logger.error("")
        logger.error("Options:")
        logger.error("  1. Use --ignore-invalid to skip invalid questions")
        logger.error("  2. Re-validate the questions with different settings")
        logger.error("  3. Manually review and fix the question data")
        logger.error("=" * 60)
    
    def _log_ignored_invalid(self, results: List[CheckResult]):
        """Log questions being ignored due to --ignore-invalid."""
        logger.warning("=" * 60)
        logger.warning(f"Ignoring {len(results)} invalid questions (--ignore-invalid)")
        logger.warning("=" * 60)
        
        for result in results[:5]:  # Show first 5
            logger.warning(f"  Question {result.index + 1}: {result.question_preview}")
            if result.failure_reasons:
                logger.warning(f"    Reason: {result.failure_reasons[0]}")
        
        if len(results) > 5:
            logger.warning(f"  ... and {len(results) - 5} more")
        
        logger.warning("=" * 60)
