"""
Metrics calculation module for test result analysis.

This module provides functions to calculate various performance metrics
for single-choice and multiple-choice questions, including accuracy,
precision, recall, F1-score, and result categorization.
"""

from typing import Dict, List, Tuple


def calculate_accuracy(results: List[dict]) -> float:
    """
    Calculate accuracy for single-choice questions.
    
    Args:
        results: List of test result dictionaries
        
    Returns:
        Accuracy as a float between 0.0 and 1.0
    """
    correct = sum(
        1 for r in results 
        if r["question_type"] == "single_choice" 
        and r["model_answer"] == r["correct_answer"]
    )
    total = sum(
        1 for r in results 
        if r["question_type"] == "single_choice"
    )
    return correct / total if total > 0 else 0.0


def calculate_multi_choice_metrics(results: List[dict]) -> Dict[str, float]:
    """
    Calculate precision, recall, and F1-score for multiple-choice questions.
    Returns macro-averaged metrics across all multiple-choice questions.
    
    Args:
        results: List of test result dictionaries
        
    Returns:
        Dictionary containing avg_precision, avg_recall, and avg_f1
    """
    precisions, recalls, f1_scores = [], [], []
    
    for result in results:
        if result["question_type"] != "multiple_choice":
            continue
            
        correct = set(result["correct_answer"])
        predicted = set(result["model_answer"])
        
        # Calculate precision
        if len(predicted) == 0:
            precision = 0.0
        else:
            precision = len(correct & predicted) / len(predicted)
            
        # Calculate recall
        if len(correct) == 0:
            recall = 0.0
        else:
            recall = len(correct & predicted) / len(correct)
            
        # Calculate F1-score
        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * (precision * recall) / (precision + recall)
            
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)
    
    return {
        "avg_precision": sum(precisions) / len(precisions) if precisions else 0.0,
        "avg_recall": sum(recalls) / len(recalls) if recalls else 0.0,
        "avg_f1": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    }


def categorize_result(result: dict) -> str:
    """
    Categorize a test result as correct, partially correct, incorrect, or parsing error.
    
    Args:
        result: Test result dictionary
        
    Returns:
        Category string: "correct", "partially_correct", "incorrect", or "parsing_error"
    """
    # Check for parsing errors first
    if result.get("parsing_status") == "parsing_error":
        return "parsing_error"
    
    # Check if model refused to answer
    if not result.get("model_answer") or len(result["model_answer"]) == 0:
        return "parsing_error"
    
    question_type = result["question_type"]
    correct_answer = set(result["correct_answer"])
    model_answer = set(result["model_answer"])
    
    if question_type == "single_choice":
        # For single choice, it's either correct or incorrect
        if model_answer == correct_answer:
            return "correct"
        else:
            return "incorrect"
    
    elif question_type == "multiple_choice":
        # For multiple choice, check for partial correctness
        intersection = correct_answer & model_answer
        
        if len(intersection) == 0:
            # No correct answers selected
            return "incorrect"
        elif model_answer == correct_answer:
            # All correct, no extras
            return "correct"
        else:
            # Some correct, but not all or has extras
            return "partially_correct"
    
    else:
        # For other question types (e.g., negative_question), treat like single choice
        if model_answer == correct_answer:
            return "correct"
        else:
            return "incorrect"


def calculate_score(result: dict) -> float:
    """
    Calculate a score for a single test result.
    
    For single-choice: 1.0 if correct, 0.0 if incorrect
    For multiple-choice: F1-score based on precision and recall
    
    Args:
        result: Test result dictionary
        
    Returns:
        Score as a float between 0.0 and 1.0
    """
    # Check for parsing errors
    if result.get("parsing_status") == "parsing_error":
        return 0.0
    
    # Check if model refused to answer
    if not result.get("model_answer") or len(result["model_answer"]) == 0:
        return 0.0
    
    question_type = result["question_type"]
    correct_answer = set(result["correct_answer"])
    model_answer = set(result["model_answer"])
    
    if question_type == "single_choice" or question_type == "negative_question":
        # Binary score for single choice
        return 1.0 if model_answer == correct_answer else 0.0
    
    elif question_type == "multiple_choice":
        # F1-score for multiple choice
        if len(model_answer) == 0:
            precision = 0.0
        else:
            precision = len(correct_answer & model_answer) / len(model_answer)
        
        if len(correct_answer) == 0:
            recall = 0.0
        else:
            recall = len(correct_answer & model_answer) / len(correct_answer)
        
        if precision + recall == 0:
            return 0.0
        else:
            return 2 * (precision * recall) / (precision + recall)
    
    return 0.0


def calculate_all_metrics(results: List[dict]) -> Dict[str, any]:
    """
    Calculate comprehensive metrics for all test results.
    
    Args:
        results: List of test result dictionaries
        
    Returns:
        Dictionary containing all calculated metrics and statistics
    """
    # Basic counts
    total_questions = len(results)
    
    # Count by question type
    single_choice_count = sum(1 for r in results if r["question_type"] == "single_choice")
    multiple_choice_count = sum(1 for r in results if r["question_type"] == "multiple_choice")
    negative_question_count = sum(1 for r in results if r["question_type"] == "negative_question")
    
    # Count by result category
    categorized_results = [categorize_result(r) for r in results]
    correct_count = categorized_results.count("correct")
    partially_correct_count = categorized_results.count("partially_correct")
    incorrect_count = categorized_results.count("incorrect")
    parsing_error_count = categorized_results.count("parsing_error")
    
    # Calculate accuracy for single-choice questions
    single_choice_accuracy = calculate_accuracy(results)
    
    # Calculate metrics for multiple-choice questions
    multi_choice_metrics = calculate_multi_choice_metrics(results)
    
    # Calculate overall average score
    scores = [calculate_score(r) for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    return {
        "total_questions": total_questions,
        "single_choice_count": single_choice_count,
        "multiple_choice_count": multiple_choice_count,
        "negative_question_count": negative_question_count,
        "correct_count": correct_count,
        "partially_correct_count": partially_correct_count,
        "incorrect_count": incorrect_count,
        "parsing_error_count": parsing_error_count,
        "single_choice_accuracy": single_choice_accuracy,
        "multi_choice_precision": multi_choice_metrics["avg_precision"],
        "multi_choice_recall": multi_choice_metrics["avg_recall"],
        "multi_choice_f1": multi_choice_metrics["avg_f1"],
        "average_score": avg_score
    }
