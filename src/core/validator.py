"""Question validator for validating generated questions."""

from typing import Dict, List, Tuple


class QuestionValidator:
    """Validates question structure and content."""
    
    VALID_QUESTION_TYPES = {"single_choice", "multiple_choice", "negative_question"}
    REQUIRED_FIELDS = {"question", "question_type", "choice", "answer", "position"}
    
    @staticmethod
    def validate_structure(question: Dict) -> Tuple[bool, str]:
        """Validate JSON structure of a question.
        
        Args:
            question: Question dictionary to validate.
            
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        # Check if question is a dictionary
        if not isinstance(question, dict):
            return False, "Question must be a dictionary"
        
        # Check for required fields
        missing_fields = QuestionValidator.REQUIRED_FIELDS - set(question.keys())
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Validate question field
        if not isinstance(question.get("question"), str) or not question["question"].strip():
            return False, "Field 'question' must be a non-empty string"
        
        # Validate question_type field
        if not isinstance(question.get("question_type"), str):
            return False, "Field 'question_type' must be a string"
        
        # Validate choice field
        if not isinstance(question.get("choice"), dict):
            return False, "Field 'choice' must be a dictionary"
        
        if len(question["choice"]) < 2:
            return False, "Field 'choice' must contain at least 2 options"
        
        # Validate all choice values are strings
        for key, value in question["choice"].items():
            if not isinstance(value, str):
                return False, f"Choice option '{key}' must be a string"
        
        # Validate answer field
        if not isinstance(question.get("answer"), list):
            return False, "Field 'answer' must be a list"
        
        if len(question["answer"]) == 0:
            return False, "Field 'answer' must contain at least one answer"
        
        # Validate position field
        if not isinstance(question.get("position"), dict):
            return False, "Field 'position' must be a dictionary"
        
        if "start_pos" not in question["position"] or "end_pos" not in question["position"]:
            return False, "Field 'position' must contain 'start_pos' and 'end_pos'"
        
        if not isinstance(question["position"]["start_pos"], int):
            return False, "Field 'position.start_pos' must be an integer"
        
        if not isinstance(question["position"]["end_pos"], int):
            return False, "Field 'position.end_pos' must be an integer"
        
        if question["position"]["start_pos"] < 0:
            return False, "Field 'position.start_pos' must be non-negative"
        
        if question["position"]["end_pos"] < question["position"]["start_pos"]:
            return False, "Field 'position.end_pos' must be >= start_pos"
        
        return True, ""
    
    @staticmethod
    def validate_content(question: Dict) -> Tuple[bool, str]:
        """Validate content quality of a question.
        
        Args:
            question: Question dictionary to validate.
            
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        # Validate question_type value
        question_type = question.get("question_type")
        if question_type not in QuestionValidator.VALID_QUESTION_TYPES:
            valid_types = ", ".join(QuestionValidator.VALID_QUESTION_TYPES)
            return False, f"Invalid question_type '{question_type}'. Must be one of: {valid_types}"
        
        # Validate multiple_choice has at least 2 distractor options
        if question_type == "multiple_choice":
            total_choices = len(question["choice"])
            correct_answers = len(question["answer"])
            distractor_count = total_choices - correct_answers
            
            if distractor_count < 2:
                return False, f"Multiple choice questions must have at least 2 distractor options. Found {distractor_count}"
        
        return True, ""
    
    @staticmethod
    def validate_answer_choices(question: Dict) -> Tuple[bool, str]:
        """Validate that answers are valid choice keys.
        
        Args:
            question: Question dictionary to validate.
            
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        answer = question.get("answer", [])
        choice = question.get("choice", {})
        
        # Check that all answers are valid choice keys
        valid_keys = set(choice.keys())
        invalid_answers = []
        
        for ans in answer:
            if not isinstance(ans, str):
                return False, f"Answer '{ans}' must be a string"
            if ans not in valid_keys:
                invalid_answers.append(ans)
        
        if invalid_answers:
            return False, f"Invalid answer keys: {', '.join(invalid_answers)}. Valid keys are: {', '.join(valid_keys)}"
        
        return True, ""
    
    @staticmethod
    def validate(question: Dict) -> Tuple[bool, str]:
        """Perform complete validation of a question.
        
        This method runs all validation checks in sequence.
        
        Args:
            question: Question dictionary to validate.
            
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        # Validate structure first
        is_valid, error = QuestionValidator.validate_structure(question)
        if not is_valid:
            return False, error
        
        # Validate content
        is_valid, error = QuestionValidator.validate_content(question)
        if not is_valid:
            return False, error
        
        # Validate answer-choice consistency
        is_valid, error = QuestionValidator.validate_answer_choices(question)
        if not is_valid:
            return False, error
        
        return True, ""
