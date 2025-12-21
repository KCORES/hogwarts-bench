"""
Answer parser module for parsing LLM responses with fallback strategies.

This module implements a robust answer parsing system that handles various
LLM response formats using multiple strategies:
1. Direct JSON parsing (primary strategy)
2. Regex extraction (fallback strategy)
3. Error handling for unparseable responses
"""

import json
import re
from typing import Tuple, List


def parse_answer(response: str) -> Tuple[List[str], str]:
    """
    Parse LLM response to extract answer with fallback strategies.
    
    This function attempts to parse the LLM response using multiple strategies:
    1. Direct JSON parsing using json.loads
    2. Regex extraction to find JSON within the response
    3. Mark as parsing error if all strategies fail
    
    Args:
        response: The raw response string from the LLM
        
    Returns:
        A tuple containing:
        - List of answer strings (e.g., ["a"], ["a", "c"], or [])
        - Parsing status: "success", "regex_extracted", or "parsing_error"
        
    Examples:
        >>> parse_answer('{"answer": ["a"]}')
        (["a"], "success")
        
        >>> parse_answer('Here is my answer: {"answer": ["b", "c"]} Hope this helps!')
        (["b", "c"], "regex_extracted")
        
        >>> parse_answer('I cannot answer this question')
        ([], "parsing_error")
    """
    # Handle edge case: empty or None response
    if not response or not response.strip():
        return [], "parsing_error"
    
    # Strategy 1: Direct JSON parse
    try:
        data = json.loads(response.strip())
        answer = data.get("answer", [])
        # Ensure answer is a list
        if not isinstance(answer, list):
            answer = [answer] if answer else []
        return answer, "success"
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    
    # Strategy 2: Regex extraction
    # Look for JSON object in the response (handles cases where LLM adds extra text)
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            answer = data.get("answer", [])
            # Ensure answer is a list
            if not isinstance(answer, list):
                answer = [answer] if answer else []
            return answer, "regex_extracted"
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    
    # Strategy 3: Parsing failed
    return [], "parsing_error"


def is_valid_answer(answer: List[str], valid_choices: List[str]) -> bool:
    """
    Validate that all answers are valid choices.
    
    Args:
        answer: List of answer strings to validate
        valid_choices: List of valid choice keys (e.g., ["a", "b", "c", "d"])
        
    Returns:
        True if all answers are valid choices, False otherwise
        
    Examples:
        >>> is_valid_answer(["a", "b"], ["a", "b", "c", "d"])
        True
        
        >>> is_valid_answer(["a", "e"], ["a", "b", "c", "d"])
        False
    """
    if not answer:
        return False
    return all(ans in valid_choices for ans in answer)
