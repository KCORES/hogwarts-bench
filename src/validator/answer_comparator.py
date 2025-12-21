"""
Answer comparison logic for question validation.

This module provides functions to compare model answers with labeled answers
for both single-choice and multiple-choice questions.
"""

from typing import List


def compare_answers(
    labeled_answer: List[str],
    model_answer: List[str],
    question_type: str
) -> bool:
    """
    Compare model answer with labeled answer.
    
    For single-choice questions: requires exact match (same single answer)
    For multiple-choice questions: requires set equality (same answers, any order)
    
    Args:
        labeled_answer: The correct answer(s) from the question data
        model_answer: The answer(s) provided by the verification model
        question_type: Type of question ("single_choice" or "multiple_choice")
        
    Returns:
        True if answers match according to question type rules
    """
    # Normalize answers to lowercase for comparison
    labeled_normalized = normalize_answers(labeled_answer)
    model_normalized = normalize_answers(model_answer)
    
    if question_type == "single_choice":
        return compare_single_choice(labeled_normalized, model_normalized)
    elif question_type == "multiple_choice":
        return compare_multiple_choice(labeled_normalized, model_normalized)
    else:
        # Unknown question type - fall back to exact list match
        return labeled_normalized == model_normalized


def compare_single_choice(
    labeled_answer: List[str],
    model_answer: List[str]
) -> bool:
    """
    Compare answers for single-choice questions.
    
    Requires exact match: both must have exactly one answer and they must be equal.
    
    Args:
        labeled_answer: Normalized labeled answer list
        model_answer: Normalized model answer list
        
    Returns:
        True if both have exactly one answer and they match
    """
    # Single choice should have exactly one answer
    if len(labeled_answer) != 1 or len(model_answer) != 1:
        # If labeled has one but model has different count, it's wrong
        if len(labeled_answer) == 1:
            return False
        # If labeled has wrong count, compare as lists
        return labeled_answer == model_answer
    
    return labeled_answer[0] == model_answer[0]


def compare_multiple_choice(
    labeled_answer: List[str],
    model_answer: List[str]
) -> bool:
    """
    Compare answers for multiple-choice questions.
    
    Requires set equality: same answers regardless of order.
    
    Args:
        labeled_answer: Normalized labeled answer list
        model_answer: Normalized model answer list
        
    Returns:
        True if both contain exactly the same set of answers
    """
    return set(labeled_answer) == set(model_answer)


def normalize_answers(answers: List[str]) -> List[str]:
    """
    Normalize answer list for comparison.
    
    Normalizations:
    - Convert to lowercase
    - Strip whitespace
    - Remove empty strings
    - Sort for consistent ordering
    
    Args:
        answers: List of answer strings
        
    Returns:
        Normalized and sorted list of answers
    """
    if not answers:
        return []
    
    normalized = []
    for answer in answers:
        if answer is not None:
            clean = str(answer).lower().strip()
            if clean:
                normalized.append(clean)
    
    return sorted(normalized)


def parse_answer_from_response(answer_value) -> List[str]:
    """
    Parse answer from LLM response into a list of strings.
    
    Handles various formats:
    - List of strings: ["a", "b"]
    - Single string: "a"
    - String with comma: "a, b"
    
    Args:
        answer_value: Answer value from LLM response (can be list or string)
        
    Returns:
        List of answer strings
    """
    if answer_value is None:
        return []
    
    if isinstance(answer_value, list):
        return [str(a).strip() for a in answer_value if a is not None]
    
    if isinstance(answer_value, str):
        # Check if it's a comma-separated list
        if ',' in answer_value:
            return [a.strip() for a in answer_value.split(',') if a.strip()]
        return [answer_value.strip()] if answer_value.strip() else []
    
    # Fallback: convert to string
    return [str(answer_value)]
