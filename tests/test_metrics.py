"""
Tests for the metrics calculation module.
"""

import pytest
from src.reporter.metrics import (
    calculate_accuracy,
    calculate_multi_choice_metrics,
    categorize_result,
    calculate_score,
    calculate_all_metrics
)


class TestCalculateAccuracy:
    """Test cases for calculate_accuracy function."""
    
    def test_all_correct_single_choice(self):
        """Test accuracy when all single choice answers are correct."""
        results = [
            {
                "question_type": "single_choice",
                "correct_answer": ["a"],
                "model_answer": ["a"]
            },
            {
                "question_type": "single_choice",
                "correct_answer": ["b"],
                "model_answer": ["b"]
            }
        ]
        
        accuracy = calculate_accuracy(results)
        assert accuracy == 1.0
    
    def test_all_incorrect_single_choice(self):
        """Test accuracy when all single choice answers are incorrect."""
        results = [
            {
                "question_type": "single_choice",
                "correct_answer": ["a"],
                "model_answer": ["b"]
            },
            {
                "question_type": "single_choice",
                "correct_answer": ["c"],
                "model_answer": ["d"]
            }
        ]
        
        accuracy = calculate_accuracy(results)
        assert accuracy == 0.0
    
    def test_mixed_single_choice(self):
        """Test accuracy with mixed correct and incorrect answers."""
        results = [
            {
                "question_type": "single_choice",
                "correct_answer": ["a"],
                "model_answer": ["a"]
            },
            {
                "question_type": "single_choice",
                "correct_answer": ["b"],
                "model_answer": ["c"]
            },
            {
                "question_type": "single_choice",
                "correct_answer": ["d"],
                "model_answer": ["d"]
            }
        ]
        
        accuracy = calculate_accuracy(results)
        assert accuracy == pytest.approx(2.0 / 3.0)
    
    def test_ignores_multiple_choice(self):
        """Test that multiple choice questions are ignored in accuracy calculation."""
        results = [
            {
                "question_type": "single_choice",
                "correct_answer": ["a"],
                "model_answer": ["a"]
            },
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a", "b"],
                "model_answer": ["a", "b"]
            }
        ]
        
        accuracy = calculate_accuracy(results)
        assert accuracy == 1.0
    
    def test_empty_results(self):
        """Test accuracy with empty results list."""
        results = []
        accuracy = calculate_accuracy(results)
        assert accuracy == 0.0
    
    def test_no_single_choice_questions(self):
        """Test accuracy when there are no single choice questions."""
        results = [
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a", "b"],
                "model_answer": ["a", "b"]
            }
        ]
        
        accuracy = calculate_accuracy(results)
        assert accuracy == 0.0


class TestCalculateMultiChoiceMetrics:
    """Test cases for calculate_multi_choice_metrics function."""
    
    def test_perfect_multiple_choice(self):
        """Test metrics when all multiple choice answers are perfect."""
        results = [
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a", "b"],
                "model_answer": ["a", "b"]
            },
            {
                "question_type": "multiple_choice",
                "correct_answer": ["c"],
                "model_answer": ["c"]
            }
        ]
        
        metrics = calculate_multi_choice_metrics(results)
        assert metrics["avg_precision"] == 1.0
        assert metrics["avg_recall"] == 1.0
        assert metrics["avg_f1"] == 1.0
    
    def test_partial_multiple_choice(self):
        """Test metrics with partial correct answers."""
        results = [
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a", "b", "c"],
                "model_answer": ["a", "b"]  # Missing c, precision=1.0, recall=2/3
            }
        ]
        
        metrics = calculate_multi_choice_metrics(results)
        assert metrics["avg_precision"] == 1.0
        assert metrics["avg_recall"] == pytest.approx(2.0 / 3.0)
        assert metrics["avg_f1"] == pytest.approx(0.8)
    
    def test_extra_answers_multiple_choice(self):
        """Test metrics when model provides extra incorrect answers."""
        results = [
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a"],
                "model_answer": ["a", "b"]  # Extra b, precision=0.5, recall=1.0
            }
        ]
        
        metrics = calculate_multi_choice_metrics(results)
        assert metrics["avg_precision"] == 0.5
        assert metrics["avg_recall"] == 1.0
        assert metrics["avg_f1"] == pytest.approx(2.0 / 3.0)
    
    def test_no_correct_answers_multiple_choice(self):
        """Test metrics when model provides no correct answers."""
        results = [
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a", "b"],
                "model_answer": ["c", "d"]
            }
        ]
        
        metrics = calculate_multi_choice_metrics(results)
        assert metrics["avg_precision"] == 0.0
        assert metrics["avg_recall"] == 0.0
        assert metrics["avg_f1"] == 0.0
    
    def test_empty_model_answer(self):
        """Test metrics when model provides no answer."""
        results = [
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a", "b"],
                "model_answer": []
            }
        ]
        
        metrics = calculate_multi_choice_metrics(results)
        assert metrics["avg_precision"] == 0.0
        assert metrics["avg_recall"] == 0.0
        assert metrics["avg_f1"] == 0.0
    
    def test_ignores_single_choice(self):
        """Test that single choice questions are ignored."""
        results = [
            {
                "question_type": "single_choice",
                "correct_answer": ["a"],
                "model_answer": ["a"]
            },
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a", "b"],
                "model_answer": ["a", "b"]
            }
        ]
        
        metrics = calculate_multi_choice_metrics(results)
        assert metrics["avg_precision"] == 1.0
        assert metrics["avg_recall"] == 1.0
        assert metrics["avg_f1"] == 1.0
    
    def test_empty_results(self):
        """Test metrics with empty results list."""
        results = []
        metrics = calculate_multi_choice_metrics(results)
        assert metrics["avg_precision"] == 0.0
        assert metrics["avg_recall"] == 0.0
        assert metrics["avg_f1"] == 0.0
    
    def test_macro_average(self):
        """Test that macro-average is calculated correctly."""
        results = [
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a", "b"],
                "model_answer": ["a"]  # precision=1.0, recall=0.5, f1=0.667
            },
            {
                "question_type": "multiple_choice",
                "correct_answer": ["c"],
                "model_answer": ["c", "d"]  # precision=0.5, recall=1.0, f1=0.667
            }
        ]
        
        metrics = calculate_multi_choice_metrics(results)
        assert metrics["avg_precision"] == pytest.approx(0.75)
        assert metrics["avg_recall"] == pytest.approx(0.75)
        assert metrics["avg_f1"] == pytest.approx(2.0 / 3.0)


class TestCategorizeResult:
    """Test cases for categorize_result function."""
    
    def test_correct_single_choice(self):
        """Test categorization of correct single choice answer."""
        result = {
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": ["a"],
            "parsing_status": "success"
        }
        
        category = categorize_result(result)
        assert category == "correct"
    
    def test_incorrect_single_choice(self):
        """Test categorization of incorrect single choice answer."""
        result = {
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": ["b"],
            "parsing_status": "success"
        }
        
        category = categorize_result(result)
        assert category == "incorrect"
    
    def test_correct_multiple_choice(self):
        """Test categorization of correct multiple choice answer."""
        result = {
            "question_type": "multiple_choice",
            "correct_answer": ["a", "b"],
            "model_answer": ["a", "b"],
            "parsing_status": "success"
        }
        
        category = categorize_result(result)
        assert category == "correct"
    
    def test_partially_correct_multiple_choice(self):
        """Test categorization of partially correct multiple choice answer."""
        result = {
            "question_type": "multiple_choice",
            "correct_answer": ["a", "b", "c"],
            "model_answer": ["a", "b"],
            "parsing_status": "success"
        }
        
        category = categorize_result(result)
        assert category == "partially_correct"
    
    def test_partially_correct_with_extra_answers(self):
        """Test categorization when model has correct and extra answers."""
        result = {
            "question_type": "multiple_choice",
            "correct_answer": ["a"],
            "model_answer": ["a", "b"],
            "parsing_status": "success"
        }
        
        category = categorize_result(result)
        assert category == "partially_correct"
    
    def test_incorrect_multiple_choice(self):
        """Test categorization of incorrect multiple choice answer."""
        result = {
            "question_type": "multiple_choice",
            "correct_answer": ["a", "b"],
            "model_answer": ["c", "d"],
            "parsing_status": "success"
        }
        
        category = categorize_result(result)
        assert category == "incorrect"
    
    def test_parsing_error(self):
        """Test categorization of parsing error."""
        result = {
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": [],
            "parsing_status": "parsing_error"
        }
        
        category = categorize_result(result)
        assert category == "parsing_error"
    
    def test_empty_model_answer(self):
        """Test categorization when model provides no answer."""
        result = {
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": [],
            "parsing_status": "success"
        }
        
        category = categorize_result(result)
        assert category == "parsing_error"
    
    def test_negative_question_correct(self):
        """Test categorization of correct negative question."""
        result = {
            "question_type": "negative_question",
            "correct_answer": ["c"],
            "model_answer": ["c"],
            "parsing_status": "success"
        }
        
        category = categorize_result(result)
        assert category == "correct"
    
    def test_negative_question_incorrect(self):
        """Test categorization of incorrect negative question."""
        result = {
            "question_type": "negative_question",
            "correct_answer": ["c"],
            "model_answer": ["a"],
            "parsing_status": "success"
        }
        
        category = categorize_result(result)
        assert category == "incorrect"


class TestCalculateScore:
    """Test cases for calculate_score function."""
    
    def test_correct_single_choice_score(self):
        """Test score for correct single choice answer."""
        result = {
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": ["a"],
            "parsing_status": "success"
        }
        
        score = calculate_score(result)
        assert score == 1.0
    
    def test_incorrect_single_choice_score(self):
        """Test score for incorrect single choice answer."""
        result = {
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": ["b"],
            "parsing_status": "success"
        }
        
        score = calculate_score(result)
        assert score == 0.0
    
    def test_perfect_multiple_choice_score(self):
        """Test score for perfect multiple choice answer."""
        result = {
            "question_type": "multiple_choice",
            "correct_answer": ["a", "b"],
            "model_answer": ["a", "b"],
            "parsing_status": "success"
        }
        
        score = calculate_score(result)
        assert score == 1.0
    
    def test_partial_multiple_choice_score(self):
        """Test score for partial multiple choice answer."""
        result = {
            "question_type": "multiple_choice",
            "correct_answer": ["a", "b", "c"],
            "model_answer": ["a", "b"],
            "parsing_status": "success"
        }
        
        score = calculate_score(result)
        # precision = 1.0, recall = 2/3, f1 = 0.8
        assert score == pytest.approx(0.8)
    
    def test_parsing_error_score(self):
        """Test score for parsing error."""
        result = {
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": [],
            "parsing_status": "parsing_error"
        }
        
        score = calculate_score(result)
        assert score == 0.0
    
    def test_empty_model_answer_score(self):
        """Test score when model provides no answer."""
        result = {
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": [],
            "parsing_status": "success"
        }
        
        score = calculate_score(result)
        assert score == 0.0
    
    def test_negative_question_score(self):
        """Test score for negative question."""
        result = {
            "question_type": "negative_question",
            "correct_answer": ["c"],
            "model_answer": ["c"],
            "parsing_status": "success"
        }
        
        score = calculate_score(result)
        assert score == 1.0


class TestCalculateAllMetrics:
    """Test cases for calculate_all_metrics function."""
    
    def test_comprehensive_metrics(self):
        """Test comprehensive metrics calculation with mixed results."""
        results = [
            {
                "question_type": "single_choice",
                "correct_answer": ["a"],
                "model_answer": ["a"],
                "parsing_status": "success"
            },
            {
                "question_type": "single_choice",
                "correct_answer": ["b"],
                "model_answer": ["c"],
                "parsing_status": "success"
            },
            {
                "question_type": "multiple_choice",
                "correct_answer": ["a", "b"],
                "model_answer": ["a", "b"],
                "parsing_status": "success"
            },
            {
                "question_type": "multiple_choice",
                "correct_answer": ["c", "d"],
                "model_answer": ["c"],
                "parsing_status": "success"
            },
            {
                "question_type": "negative_question",
                "correct_answer": ["e"],
                "model_answer": [],
                "parsing_status": "parsing_error"
            }
        ]
        
        metrics = calculate_all_metrics(results)
        
        assert metrics["total_questions"] == 5
        assert metrics["single_choice_count"] == 2
        assert metrics["multiple_choice_count"] == 2
        assert metrics["negative_question_count"] == 1
        assert metrics["correct_count"] == 2
        assert metrics["partially_correct_count"] == 1
        assert metrics["incorrect_count"] == 1
        assert metrics["parsing_error_count"] == 1
        assert metrics["single_choice_accuracy"] == 0.5
        assert metrics["multi_choice_precision"] == pytest.approx(0.75)
        assert metrics["multi_choice_recall"] == pytest.approx(0.75)
        assert metrics["average_score"] > 0.0
    
    def test_empty_results_all_metrics(self):
        """Test all metrics with empty results."""
        results = []
        metrics = calculate_all_metrics(results)
        
        assert metrics["total_questions"] == 0
        assert metrics["single_choice_count"] == 0
        assert metrics["multiple_choice_count"] == 0
        assert metrics["correct_count"] == 0
        assert metrics["average_score"] == 0.0
    
    def test_all_correct_metrics(self):
        """Test metrics when all answers are correct."""
        results = [
            {
                "question_type": "single_choice",
                "correct_answer": ["a"],
                "model_answer": ["a"],
                "parsing_status": "success"
            },
            {
                "question_type": "multiple_choice",
                "correct_answer": ["b", "c"],
                "model_answer": ["b", "c"],
                "parsing_status": "success"
            }
        ]
        
        metrics = calculate_all_metrics(results)
        
        assert metrics["correct_count"] == 2
        assert metrics["incorrect_count"] == 0
        assert metrics["parsing_error_count"] == 0
        assert metrics["single_choice_accuracy"] == 1.0
        assert metrics["multi_choice_f1"] == 1.0
        assert metrics["average_score"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

