"""
Tests for the report generator module.
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.reporter.report_generator import ReportGenerator


@pytest.fixture
def sample_results_file():
    """Create a temporary results file for testing."""
    results_data = [
        {
            "question": "What is Harry's house?",
            "question_type": "single_choice",
            "choice": {"a": "Gryffindor", "b": "Slytherin", "c": "Hufflepuff", "d": "Ravenclaw"},
            "correct_answer": ["a"],
            "model_answer": ["a"],
            "parsing_status": "success",
            "position": {"start_pos": 1000, "end_pos": 1050},
            "score": 1.0
        },
        {
            "question": "Who are Harry's best friends?",
            "question_type": "multiple_choice",
            "choice": {"a": "Ron", "b": "Hermione", "c": "Draco", "d": "Neville"},
            "correct_answer": ["a", "b"],
            "model_answer": ["a", "b"],
            "parsing_status": "success",
            "position": {"start_pos": 5000, "end_pos": 5100},
            "score": 1.0,
            "metrics": {"precision": 1.0, "recall": 1.0, "f1_score": 1.0}
        },
        {
            "question": "What is Voldemort's real name?",
            "question_type": "single_choice",
            "choice": {"a": "Tom Riddle", "b": "Tom Marvolo Riddle", "c": "Lord Voldemort", "d": "He Who Must Not Be Named"},
            "correct_answer": ["b"],
            "model_answer": ["a"],
            "parsing_status": "success",
            "position": {"start_pos": 10000, "end_pos": 10100},
            "score": 0.0
        }
    ]
    
    metadata = {
        "tested_at": "2024-01-01T12:00:00",
        "model_name": "test-model",
        "novel_path": "data/harry_potter.txt",
        "question_set_path": "data/questions.jsonl",
        "context_length": 50000,
        "padding_size": 500,
        "total_questions": 100,
        "tested_questions": 3
    }
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(json.dumps({"metadata": metadata}) + '\n')
        for result in results_data:
            f.write(json.dumps(result) + '\n')
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink()


class TestReportGenerator:
    """Test cases for ReportGenerator class."""
    
    def test_initialization(self, sample_results_file):
        """Test ReportGenerator initialization."""
        generator = ReportGenerator(sample_results_file)
        
        assert generator.results_path == sample_results_file
        assert len(generator.results) == 3
        assert generator.metadata["model_name"] == "test-model"
        assert generator.metadata["context_length"] == 50000
    
    def test_initialization_missing_file(self):
        """Test initialization with missing file."""
        with pytest.raises(FileNotFoundError):
            ReportGenerator("nonexistent_file.jsonl")
    
    def test_initialization_empty_results(self):
        """Test initialization with empty results."""
        # Create empty results file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            f.write(json.dumps({"metadata": {}}) + '\n')
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="No results found"):
                ReportGenerator(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_generate_report(self, sample_results_file):
        """Test report generation."""
        generator = ReportGenerator(sample_results_file)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name
        
        try:
            generator.generate_report(output_path, error_examples=5)
            
            # Check that file was created
            assert Path(output_path).exists()
            
            # Read and verify HTML content
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Verify key sections are present
            assert "<!DOCTYPE html>" in html_content
            assert "Hogwarts-Bench Test Report" in html_content
            assert "Test Summary" in html_content
            assert "Performance Visualization" in html_content
            assert "Error Analysis" in html_content
            assert "test-model" in html_content
            assert "50,000 tokens" in html_content
            
        finally:
            Path(output_path).unlink()
    
    def test_generate_summary_section(self, sample_results_file):
        """Test summary section generation."""
        generator = ReportGenerator(sample_results_file)
        
        from src.reporter.metrics import calculate_all_metrics
        metrics = calculate_all_metrics(generator.results)
        
        summary_html = generator._generate_summary_section(metrics)
        
        # Verify summary contains key information
        assert "Test Summary" in summary_html
        assert "test-model" in summary_html
        assert "50,000 tokens" in summary_html
        assert "Performance Metrics" in summary_html
        assert "Result Distribution" in summary_html
    
    def test_generate_visualization_section(self, sample_results_file):
        """Test visualization section generation."""
        generator = ReportGenerator(sample_results_file)
        
        viz_html = generator._generate_visualization_section()
        
        # Verify visualization section is present
        assert "Performance Visualization" in viz_html
        assert "scatter plot" in viz_html.lower()
    
    def test_generate_error_analysis(self, sample_results_file):
        """Test error analysis section generation."""
        generator = ReportGenerator(sample_results_file)
        
        error_html = generator._generate_error_analysis(num_examples=5)
        
        # Verify error analysis section
        assert "Error Analysis" in error_html
        # Should have at least one error (the incorrect answer)
        assert "Case #1" in error_html or "Excellent!" in error_html
    
    def test_generate_error_analysis_no_errors(self):
        """Test error analysis when there are no errors."""
        # Create results with all correct answers
        results_data = [
            {
                "question": "Test question",
                "question_type": "single_choice",
                "choice": {"a": "Answer A", "b": "Answer B"},
                "correct_answer": ["a"],
                "model_answer": ["a"],
                "parsing_status": "success",
                "position": {"start_pos": 1000, "end_pos": 1050},
                "score": 1.0
            }
        ]
        
        metadata = {
            "tested_at": "2024-01-01T12:00:00",
            "model_name": "test-model",
            "context_length": 50000
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            f.write(json.dumps({"metadata": metadata}) + '\n')
            for result in results_data:
                f.write(json.dumps(result) + '\n')
            temp_path = f.name
        
        try:
            generator = ReportGenerator(temp_path)
            error_html = generator._generate_error_analysis(num_examples=5)
            
            # Should show success message
            assert "Excellent!" in error_html or "No errors" in error_html
        finally:
            Path(temp_path).unlink()
    
    def test_get_embedded_css(self, sample_results_file):
        """Test CSS embedding."""
        generator = ReportGenerator(sample_results_file)
        
        css = generator._get_embedded_css()
        
        # Verify CSS is present
        assert "<style>" in css
        assert "</style>" in css
        assert "body" in css
        assert ".container" in css


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
