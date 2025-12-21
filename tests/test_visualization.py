"""
Tests for the visualization module.
"""

import pytest
from src.reporter.visualization import (
    create_scatter_plot,
    _assign_color,
    _calculate_trend_line
)


def test_assign_color_correct():
    """Test color assignment for correct answers."""
    result = {
        "question_type": "single_choice",
        "correct_answer": ["a"],
        "model_answer": ["a"],
        "parsing_status": "success"
    }
    color = _assign_color(result)
    assert color == "#28a745"  # Green


def test_assign_color_incorrect():
    """Test color assignment for incorrect answers."""
    result = {
        "question_type": "single_choice",
        "correct_answer": ["a"],
        "model_answer": ["b"],
        "parsing_status": "success"
    }
    color = _assign_color(result)
    assert color == "#dc3545"  # Red


def test_assign_color_partially_correct():
    """Test color assignment for partially correct answers."""
    result = {
        "question_type": "multiple_choice",
        "correct_answer": ["a", "b"],
        "model_answer": ["a"],
        "parsing_status": "success"
    }
    color = _assign_color(result)
    assert color == "#ffc107"  # Yellow


def test_assign_color_parsing_error():
    """Test color assignment for parsing errors."""
    result = {
        "question_type": "single_choice",
        "correct_answer": ["a"],
        "model_answer": [],
        "parsing_status": "parsing_error"
    }
    color = _assign_color(result)
    assert color == "#6c757d"  # Gray


def test_calculate_trend_line_basic():
    """Test trend line calculation with basic data."""
    positions = [100, 200, 300, 400, 500]
    scores = [0.8, 0.9, 0.7, 0.85, 0.75]
    
    trend_pos, trend_scores = _calculate_trend_line(positions, scores, window_size=3)
    
    assert len(trend_pos) == len(positions)
    assert len(trend_scores) == len(scores)
    assert all(0.0 <= s <= 1.0 for s in trend_scores)


def test_calculate_trend_line_insufficient_data():
    """Test trend line with insufficient data points."""
    positions = [100, 200]
    scores = [0.8, 0.9]
    
    trend_pos, trend_scores = _calculate_trend_line(positions, scores, window_size=20)
    
    # Should return original data when not enough points
    assert trend_pos == positions
    assert trend_scores == scores


def test_create_scatter_plot_basic():
    """Test scatter plot creation with basic results."""
    results = [
        {
            "question": "What is the capital of France?",
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": ["a"],
            "parsing_status": "success",
            "position": {"start_pos": 1000, "end_pos": 1050}
        },
        {
            "question": "Which are primary colors?",
            "question_type": "multiple_choice",
            "correct_answer": ["a", "b"],
            "model_answer": ["a"],
            "parsing_status": "success",
            "position": {"start_pos": 2000, "end_pos": 2050}
        }
    ]
    
    html = create_scatter_plot(results, context_length=50000)
    
    assert isinstance(html, str)
    assert "scatter-plot" in html
    assert "Performance Across Token Positions" in html
    assert "plotly" in html.lower()


def test_create_scatter_plot_empty_results():
    """Test scatter plot with empty results."""
    html = create_scatter_plot([], context_length=50000)
    
    assert isinstance(html, str)
    assert "No results to visualize" in html


def test_create_scatter_plot_long_question():
    """Test scatter plot with long question text (should be truncated)."""
    long_question = "A" * 150  # 150 characters
    
    results = [
        {
            "question": long_question,
            "question_type": "single_choice",
            "correct_answer": ["a"],
            "model_answer": ["a"],
            "parsing_status": "success",
            "position": {"start_pos": 1000, "end_pos": 1050}
        }
    ]
    
    html = create_scatter_plot(results, context_length=50000)
    
    assert isinstance(html, str)
    assert "..." in html  # Should contain ellipsis for truncation
