"""
Tests for the answer parser module.
"""

import pytest
from src.tester.parser import parse_answer, is_valid_answer


class TestParseAnswer:
    """Test cases for parse_answer function."""
    
    def test_direct_json_parse_single_answer(self):
        """Test direct JSON parsing with single answer."""
        response = '{"answer": ["a"]}'
        answer, status = parse_answer(response)
        assert answer == ["a"]
        assert status == "success"
    
    def test_direct_json_parse_multiple_answers(self):
        """Test direct JSON parsing with multiple answers."""
        response = '{"answer": ["a", "c"]}'
        answer, status = parse_answer(response)
        assert answer == ["a", "c"]
        assert status == "success"
    
    def test_direct_json_parse_with_whitespace(self):
        """Test direct JSON parsing with leading/trailing whitespace."""
        response = '  {"answer": ["b"]}  '
        answer, status = parse_answer(response)
        assert answer == ["b"]
        assert status == "success"
    
    def test_regex_extraction_with_prefix(self):
        """Test regex extraction when JSON is embedded in text."""
        response = 'Here is my answer: {"answer": ["b", "c"]} Hope this helps!'
        answer, status = parse_answer(response)
        assert answer == ["b", "c"]
        assert status == "regex_extracted"
    
    def test_regex_extraction_multiline(self):
        """Test regex extraction with multiline JSON."""
        response = '''Let me think about this.
        {
            "answer": ["d"]
        }
        That's my final answer.'''
        answer, status = parse_answer(response)
        assert answer == ["d"]
        assert status == "regex_extracted"
    
    def test_empty_response(self):
        """Test handling of empty response."""
        answer, status = parse_answer("")
        assert answer == []
        assert status == "parsing_error"
    
    def test_none_response(self):
        """Test handling of None response."""
        answer, status = parse_answer(None)
        assert answer == []
        assert status == "parsing_error"
    
    def test_whitespace_only_response(self):
        """Test handling of whitespace-only response."""
        answer, status = parse_answer("   \n\t  ")
        assert answer == []
        assert status == "parsing_error"
    
    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        response = '{"answer": ["a"'
        answer, status = parse_answer(response)
        assert answer == []
        assert status == "parsing_error"
    
    def test_no_answer_field(self):
        """Test JSON without answer field."""
        response = '{"result": ["a"]}'
        answer, status = parse_answer(response)
        assert answer == []
        assert status == "success"
    
    def test_empty_answer_field(self):
        """Test JSON with empty answer field."""
        response = '{"answer": []}'
        answer, status = parse_answer(response)
        assert answer == []
        assert status == "success"
    
    def test_non_list_answer_converted(self):
        """Test that non-list answer is converted to list."""
        response = '{"answer": "a"}'
        answer, status = parse_answer(response)
        assert answer == ["a"]
        assert status == "success"
    
    def test_plain_text_response(self):
        """Test handling of plain text without JSON."""
        response = "I think the answer is A"
        answer, status = parse_answer(response)
        assert answer == []
        assert status == "parsing_error"
    
    def test_nested_json_in_text(self):
        """Test extraction of nested JSON from text."""
        response = 'Based on the context, {"answer": ["a", "b"]} is correct.'
        answer, status = parse_answer(response)
        assert answer == ["a", "b"]
        assert status == "regex_extracted"


class TestIsValidAnswer:
    """Test cases for is_valid_answer function."""
    
    def test_valid_single_answer(self):
        """Test validation of single valid answer."""
        assert is_valid_answer(["a"], ["a", "b", "c", "d"]) is True
    
    def test_valid_multiple_answers(self):
        """Test validation of multiple valid answers."""
        assert is_valid_answer(["a", "c"], ["a", "b", "c", "d"]) is True
    
    def test_invalid_answer(self):
        """Test validation of invalid answer."""
        assert is_valid_answer(["e"], ["a", "b", "c", "d"]) is False
    
    def test_partially_invalid_answers(self):
        """Test validation when some answers are invalid."""
        assert is_valid_answer(["a", "e"], ["a", "b", "c", "d"]) is False
    
    def test_empty_answer(self):
        """Test validation of empty answer list."""
        assert is_valid_answer([], ["a", "b", "c", "d"]) is False
    
    def test_all_valid_choices(self):
        """Test validation when all choices are selected."""
        assert is_valid_answer(["a", "b", "c", "d"], ["a", "b", "c", "d"]) is True
