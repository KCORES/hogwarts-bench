"""
Answer parser module for parsing LLM responses with fallback strategies.

This module implements a robust answer parsing system that handles various
LLM response formats using multiple strategies:
1. Direct JSON parsing (primary strategy)
2. Regex extraction (fallback strategy) - finds last valid JSON object
3. Error handling for unparseable responses
"""

import json
import re
from typing import Tuple, List, Optional


def _find_last_json_object(text: str) -> Optional[str]:
    """
    Find the last complete JSON object in the text.
    
    This function searches from the end of the text to find the last
    valid JSON object. This is useful when LLM responses contain
    thinking/reasoning blocks with JSON examples before the actual answer.
    
    Args:
        text: The text to search for JSON objects
        
    Returns:
        The last valid JSON object string, or None if not found
    """
    # Find all potential JSON object positions (starting with {)
    # Search from end to beginning
    last_valid_json = None
    
    # Find all '{' positions
    brace_positions = [i for i, c in enumerate(text) if c == '{']
    
    # Try each position from the end
    for start_pos in reversed(brace_positions):
        # Try to find matching closing brace
        depth = 0
        in_string = False
        escape_next = False
        
        for i in range(start_pos, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\' and in_string:
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if in_string:
                continue
                
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    # Found a complete JSON object
                    candidate = text[start_pos:i+1]
                    try:
                        json.loads(candidate)
                        last_valid_json = candidate
                        # Return immediately since we're searching from the end
                        return last_valid_json
                    except (json.JSONDecodeError, ValueError):
                        break
    
    return last_valid_json


def parse_answer(response: str) -> Tuple[List[str], str]:
    """
    Parse LLM response to extract answer with fallback strategies.
    
    This function attempts to parse the LLM response using multiple strategies:
    1. Direct JSON parsing using json.loads
    2. Regex extraction to find the last valid JSON object in the response
       (handles cases where LLM includes thinking blocks with JSON examples)
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
        
        >>> parse_answer('<thinking>example: {"answer": ["x"]}</thinking>{"answer": ["b"]}')
        (["b"], "regex_extracted")
        
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
    
    # Strategy 2: Find the last valid JSON object
    # This handles cases where LLM includes thinking/reasoning with JSON examples
    last_json = _find_last_json_object(response)
    if last_json:
        try:
            data = json.loads(last_json)
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
