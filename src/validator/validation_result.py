"""
Validation result data model for question validation.

This module defines the ValidationResult dataclass that captures all
information about a question validation attempt.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


# Valid confidence levels in order from lowest to highest
CONFIDENCE_LEVELS = ["low", "medium", "high"]


@dataclass
class ValidationResult:
    """
    Data class representing the result of validating a single question.
    
    Attributes:
        question: Original question dictionary
        is_valid: Whether the question passed all validation checks
        model_answer: Answer provided by the verification LLM
        answer_matches: Whether model answer matches the labeled answer
        evidence: Evidence text provided by the verification LLM
        evidence_found: Whether evidence was found in the context
        evidence_similarity: Similarity score of evidence match (0.0-1.0)
        is_answerable: Whether the question is answerable from context
        confidence: Confidence level (high/medium/low)
        failure_reasons: List of reasons why validation failed (empty if valid)
        reasoning: Optional reasoning provided by the LLM
    """
    
    question: Dict[str, Any]
    is_valid: bool
    model_answer: List[str]
    answer_matches: bool
    evidence: str
    evidence_found: bool
    evidence_similarity: float
    is_answerable: bool
    confidence: str
    failure_reasons: List[str] = field(default_factory=list)
    reasoning: Optional[str] = None
    
    def __post_init__(self):
        """Validate the data after initialization."""
        # Ensure confidence is valid
        if self.confidence not in CONFIDENCE_LEVELS:
            self.confidence = "low"
        
        # Ensure similarity is in valid range
        self.evidence_similarity = max(0.0, min(1.0, self.evidence_similarity))
        
        # Ensure consistency: if is_valid is False, failure_reasons should not be empty
        if not self.is_valid and not self.failure_reasons:
            self.failure_reasons = ["Unknown validation failure"]
        
        # Ensure consistency: if is_valid is True, failure_reasons should be empty
        if self.is_valid:
            self.failure_reasons = []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert validation result to dictionary format.
        
        Returns:
            Dictionary containing all validation fields
        """
        return {
            "is_valid": self.is_valid,
            "model_answer": self.model_answer,
            "answer_matches": self.answer_matches,
            "evidence": self.evidence,
            "evidence_found": self.evidence_found,
            "evidence_similarity": self.evidence_similarity,
            "is_answerable": self.is_answerable,
            "confidence": self.confidence,
            "failure_reasons": self.failure_reasons,
            "reasoning": self.reasoning,
        }
    
    def to_question_with_validation(self) -> Dict[str, Any]:
        """
        Merge validation result with original question data.
        
        Returns:
            Original question dictionary with added 'validation' field
        """
        result = dict(self.question)
        result["validation"] = self.to_dict()
        return result
    
    @classmethod
    def from_dict(
        cls,
        question: Dict[str, Any],
        validation_data: Dict[str, Any]
    ) -> "ValidationResult":
        """
        Create ValidationResult from question and validation dictionaries.
        
        Args:
            question: Original question dictionary
            validation_data: Dictionary containing validation fields
            
        Returns:
            ValidationResult instance
        """
        return cls(
            question=question,
            is_valid=validation_data.get("is_valid", False),
            model_answer=validation_data.get("model_answer", []),
            answer_matches=validation_data.get("answer_matches", False),
            evidence=validation_data.get("evidence", ""),
            evidence_found=validation_data.get("evidence_found", False),
            evidence_similarity=validation_data.get("evidence_similarity", 0.0),
            is_answerable=validation_data.get("is_answerable", False),
            confidence=validation_data.get("confidence", "low"),
            failure_reasons=validation_data.get("failure_reasons", []),
            reasoning=validation_data.get("reasoning"),
        )
    
    @staticmethod
    def compare_confidence(conf1: str, conf2: str) -> int:
        """
        Compare two confidence levels.
        
        Args:
            conf1: First confidence level
            conf2: Second confidence level
            
        Returns:
            -1 if conf1 < conf2, 0 if equal, 1 if conf1 > conf2
        """
        levels = {level: i for i, level in enumerate(CONFIDENCE_LEVELS)}
        idx1 = levels.get(conf1.lower(), 0)
        idx2 = levels.get(conf2.lower(), 0)
        
        if idx1 < idx2:
            return -1
        elif idx1 > idx2:
            return 1
        return 0
    
    @staticmethod
    def meets_confidence_threshold(confidence: str, threshold: str) -> bool:
        """
        Check if confidence meets or exceeds threshold.
        
        Args:
            confidence: Actual confidence level
            threshold: Required minimum confidence level
            
        Returns:
            True if confidence >= threshold
        """
        return ValidationResult.compare_confidence(confidence, threshold) >= 0
