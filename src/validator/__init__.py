"""
Question validation module for detecting and filtering hallucinations.

This module provides tools for validating LLM-generated questions by:
- Verifying answers through LLM backtesting
- Matching evidence against source text
- Checking answerability from context
"""

from .evidence_matcher import EvidenceMatcher
from .validation_result import ValidationResult
from .answer_comparator import compare_answers
from .question_validator import QuestionValidator

__all__ = [
    "EvidenceMatcher",
    "ValidationResult", 
    "compare_answers",
    "QuestionValidator",
]
