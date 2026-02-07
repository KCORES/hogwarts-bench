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

    def test_thinking_tags_with_json_examples(self):
        """Test extraction when thinking block contains JSON examples."""
        response = '''<thinking>
1. **分析用户请求：**
    *   **输出格式：** 仅 JSON。
    *   要求的 JSON 格式：`{"answer": ["x"]}`。
</thinking>

{"answer": ["b"]}'''
        answer, status = parse_answer(response)
        assert answer == ["b"]
        assert status == "regex_extracted"

    def test_thinking_tags_with_multiple_json_examples(self):
        """Test extraction when thinking block contains multiple JSON examples."""
        response = '''<thinking>
Let me analyze this:
- Example format: {"answer": ["a"]}
- Another example: {"result": "test"}
- The correct format should be: {"answer": ["wrong"]}
</thinking>

```json
{"answer": ["c"]}
```'''
        answer, status = parse_answer(response)
        assert answer == ["c"]
        assert status == "regex_extracted"

    def test_glm_x_preview_style_response(self):
        """Test parsing GLM-X-Preview style response with detailed thinking."""
        response = '''<thinking>
1. **分析用户请求：**
    *   **角色：** 专业的阅读理解专家。
    *   **任务：** 阅读提供的文本并根据该文本准确回答特定问题。
    *   **限制：** 不要编造信息。答案必须*仅*基于文本。

2. **扫描文本寻找关键词：**
    *   关键词："小天狼星"、"克利切"、"自由"、"放"。

3. **定位相关片段：**
    *   找到片段："我们不能放他自由，他对凤凰社的事情知道得太多了。"

4. **格式化输出：**
    *   要求的 JSON 格式：`{"answer": ["b"]}`。
</thinking>

{"answer": ["b"]}'''
        answer, status = parse_answer(response)
        assert answer == ["b"]
        assert status == "regex_extracted"

    def test_response_with_code_block_json(self):
        """Test extraction when final answer is in markdown code block."""
        response = '''Some thinking here with {"example": "data"}

```json
{"answer": ["d"]}
```'''
        answer, status = parse_answer(response)
        assert answer == ["d"]
        assert status == "regex_extracted"

    def test_multiple_json_objects_returns_last(self):
        """Test that the last valid JSON object is returned."""
        response = '''{"answer": ["a"]} some text {"answer": ["b"]} more text {"answer": ["c"]}'''
        answer, status = parse_answer(response)
        assert answer == ["c"]
        assert status == "regex_extracted"

    def test_invalid_json_in_middle_valid_at_end(self):
        """Test that invalid JSON in middle doesn't break parsing."""
        response = '''{"broken": json here} and then {"answer": ["d"]}'''
        answer, status = parse_answer(response)
        assert answer == ["d"]
        assert status == "regex_extracted"

    def test_json_with_escaped_quotes(self):
        """Test JSON parsing with escaped quotes in strings."""
        response = '''{"note": "some \\"quoted\\" text", "answer": ["a"]}'''
        answer, status = parse_answer(response)
        assert answer == ["a"]
        # Pure JSON is parsed directly with "success" status
        assert status == "success"

    def test_json_with_escaped_quotes_in_text(self):
        """Test JSON with escaped quotes embedded in text."""
        response = '''Some prefix {"note": "some \\"quoted\\" text", "answer": ["a"]} suffix'''
        answer, status = parse_answer(response)
        assert answer == ["a"]
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
