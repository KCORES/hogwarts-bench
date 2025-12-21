"""
Tests for the QuestionValidator module.
"""

import pytest
from src.core.validator import QuestionValidator


class TestQuestionValidator:
    """Test cases for QuestionValidator."""
    
    def test_valid_single_choice_question(self):
        """Test validation of a valid single choice question."""
        question = {
            "question": "What is the capital of France?",
            "question_type": "single_choice",
            "choice": {
                "a": "London",
                "b": "Paris",
                "c": "Berlin",
                "d": "Madrid"
            },
            "answer": ["b"],
            "position": {
                "start_pos": 100,
                "end_pos": 150
            }
        }
        
        is_valid, error = QuestionValidator.validate(question)
        assert is_valid is True
        assert error == ""
    
    def test_valid_multiple_choice_question(self):
        """Test validation of a valid multiple choice question."""
        question = {
            "question": "Which of the following are primary colors?",
            "question_type": "multiple_choice",
            "choice": {
                "a": "Red",
                "b": "Green",
                "c": "Blue",
                "d": "Yellow",
                "e": "Purple"
            },
            "answer": ["a", "c", "d"],  # 2 distractors: b and e
            "position": {
                "start_pos": 200,
                "end_pos": 250
            }
        }
        
        is_valid, error = QuestionValidator.validate(question)
        assert is_valid is True
        assert error == ""
    
    def test_valid_negative_question(self):
        """Test validation of a valid negative question."""
        question = {
            "question": "Which of the following did NOT happen in the story?",
            "question_type": "negative_question",
            "choice": {
                "a": "Event A occurred",
                "b": "Event B occurred",
                "c": "Event C occurred"
            },
            "answer": ["c"],
            "position": {
                "start_pos": 300,
                "end_pos": 400
            }
        }
        
        is_valid, error = QuestionValidator.validate(question)
        assert is_valid is True
        assert error == ""
    
    def test_missing_required_field(self):
        """Test validation fails when required field is missing."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            # Missing 'answer' field
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "Missing required fields" in error
        assert "answer" in error
    
    def test_invalid_question_type(self):
        """Test validation fails for invalid question_type."""
        question = {
            "question": "Test question",
            "question_type": "invalid_type",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["a"],
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_content(question)
        assert is_valid is False
        assert "Invalid question_type" in error
    
    def test_answer_not_in_choices(self):
        """Test validation fails when answer is not a valid choice key."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["c"],  # 'c' is not in choices
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_answer_choices(question)
        assert is_valid is False
        assert "Invalid answer keys" in error
        assert "c" in error
    
    def test_multiple_choice_insufficient_distractors(self):
        """Test validation fails when multiple choice has less than 2 distractors."""
        question = {
            "question": "Test question",
            "question_type": "multiple_choice",
            "choice": {"a": "Option A", "b": "Option B", "c": "Option C"},
            "answer": ["a", "b"],  # Only 1 distractor (c)
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_content(question)
        assert is_valid is False
        assert "at least 2 distractor options" in error
    
    def test_empty_question_text(self):
        """Test validation fails for empty question text."""
        question = {
            "question": "",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["a"],
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "non-empty string" in error
    
    def test_choice_not_dict(self):
        """Test validation fails when choice is not a dictionary."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": ["a", "b"],  # Should be dict, not list
            "answer": ["a"],
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "must be a dictionary" in error
    
    def test_insufficient_choices(self):
        """Test validation fails when there are less than 2 choices."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Only one option"},
            "answer": ["a"],
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "at least 2 options" in error
    
    def test_answer_not_list(self):
        """Test validation fails when answer is not a list."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": "a",  # Should be list, not string
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "must be a list" in error
    
    def test_empty_answer_list(self):
        """Test validation fails when answer list is empty."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": [],
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "at least one answer" in error
    
    def test_position_missing_fields(self):
        """Test validation fails when position is missing required fields."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["a"],
            "position": {"start_pos": 0}  # Missing end_pos
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "start_pos" in error or "end_pos" in error
    
    def test_position_invalid_types(self):
        """Test validation fails when position values are not integers."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["a"],
            "position": {"start_pos": "0", "end_pos": "10"}  # Should be int
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "must be an integer" in error
    
    def test_position_negative_start(self):
        """Test validation fails when start_pos is negative."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["a"],
            "position": {"start_pos": -1, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "non-negative" in error
    
    def test_position_end_before_start(self):
        """Test validation fails when end_pos is before start_pos."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["a"],
            "position": {"start_pos": 100, "end_pos": 50}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert ">=" in error or "start_pos" in error
    
    def test_question_not_dict(self):
        """Test validation fails when question is not a dictionary."""
        question = "This is not a dict"
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "must be a dictionary" in error
    
    def test_choice_value_not_string(self):
        """Test validation fails when choice value is not a string."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": 123},  # b should be string
            "answer": ["a"],
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is False
        assert "must be a string" in error
    
    def test_answer_element_not_string(self):
        """Test validation fails when answer element is not a string."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": [1],  # Should be string
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_answer_choices(question)
        assert is_valid is False
        assert "must be a string" in error
    
    def test_multiple_choice_with_exactly_two_distractors(self):
        """Test validation passes for multiple choice with exactly 2 distractors."""
        question = {
            "question": "Test question",
            "question_type": "multiple_choice",
            "choice": {
                "a": "Option A",
                "b": "Option B",
                "c": "Option C",
                "d": "Option D"
            },
            "answer": ["a", "b"],  # 2 distractors (c, d)
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate(question)
        assert is_valid is True
        assert error == ""
    
    def test_validate_structure_method(self):
        """Test validate_structure method independently."""
        question = {
            "question": "Test question",
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["a"],
            "position": {"start_pos": 0, "end_pos": 10}
        }
        
        is_valid, error = QuestionValidator.validate_structure(question)
        assert is_valid is True
        assert error == ""
    
    def test_validate_content_method(self):
        """Test validate_content method independently."""
        question = {
            "question_type": "single_choice",
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["a"]
        }
        
        is_valid, error = QuestionValidator.validate_content(question)
        assert is_valid is True
        assert error == ""
    
    def test_validate_answer_choices_method(self):
        """Test validate_answer_choices method independently."""
        question = {
            "choice": {"a": "Option A", "b": "Option B"},
            "answer": ["a"]
        }
        
        is_valid, error = QuestionValidator.validate_answer_choices(question)
        assert is_valid is True
        assert error == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
