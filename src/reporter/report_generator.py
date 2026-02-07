"""
Report generator core logic for creating HTML reports.

This module provides the ReportGenerator class that loads test results,
calculates metrics, generates visualizations, and produces standalone HTML reports.
"""

import json
import random
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from ..core.file_io import FileIO
from .metrics import calculate_all_metrics, categorize_result, calculate_score
from .visualization import create_scatter_plot


class ReportGenerator:
    """Generate comprehensive HTML reports from test results."""
    
    def __init__(self, results_path: str):
        """
        Initialize ReportGenerator by loading test results.
        
        Args:
            results_path: Path to test results JSONL file
            
        Raises:
            FileNotFoundError: If results file doesn't exist
            IOError: If results file cannot be read
        """
        self.results_path = results_path
        self.metadata, self.results = FileIO.read_jsonl(results_path)
        
        if not self.results:
            raise ValueError(f"No results found in {results_path}")
    
    def generate_report(self, output_path: str, error_examples: int = 10) -> None:
        """
        Generate complete standalone HTML report.
        
        Args:
            output_path: Path for output HTML file
            error_examples: Number of error examples to include (default: 10)
            
        Raises:
            IOError: If report cannot be written
        """
        # Calculate metrics
        metrics = calculate_all_metrics(self.results)
        
        # Generate HTML sections
        html_content = self._generate_html_report(metrics, error_examples)
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            raise IOError(f"Failed to write report file: {e}")
    
    def _generate_html_report(self, metrics: Dict[str, Any], 
                             error_examples: int) -> str:
        """
        Generate complete HTML report with all sections.
        
        Args:
            metrics: Calculated metrics dictionary
            error_examples: Number of error examples to include
            
        Returns:
            Complete HTML string
        """
        # Generate individual sections
        summary_html = self._generate_summary_section(metrics)
        visualization_html = self._generate_visualization_section()
        error_analysis_html = self._generate_error_analysis(error_examples)
        
        # Combine into complete HTML document
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hogwarts-Bench Test Report</title>
    {self._get_embedded_css()}
</head>
<body>
    <div class="container">
        <header>
            <h1>🧙 Hogwarts-Bench Test Report</h1>
            <p class="subtitle">Long-Context LLM Evaluation Results</p>
        </header>
        
        {summary_html}
        
        {visualization_html}
        
        {error_analysis_html}
        
        <footer>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Hogwarts-Bench Framework</p>
        </footer>
    </div>
</body>
</html>"""
        
        return html

    
    def _generate_summary_section(self, metrics: Dict[str, Any]) -> str:
        """
        Generate HTML for summary section with test configuration and metrics.
        
        Args:
            metrics: Calculated metrics dictionary
            
        Returns:
            HTML string for summary section
        """
        # Extract test configuration from metadata
        model_name = self.metadata.get("model_name", "Unknown")
        context_length = self.metadata.get("context_length")
        novel_path = self.metadata.get("novel_path", "Unknown")
        tested_at = self.metadata.get("tested_at", "Unknown")
        total_in_set = self.metadata.get("total_questions", "Unknown")
        tested_count = self.metadata.get("tested_questions", metrics["total_questions"])
        test_mode = self.metadata.get("test_mode", "standard")
        
        # Format context length display
        if context_length is not None:
            context_length_display = f"{context_length:,} tokens"
        elif test_mode == "no_reference":
            context_length_display = "N/A (No-Reference Mode)"
        else:
            context_length_display = "Unknown"
        
        # Format metrics
        single_acc = metrics["single_choice_accuracy"] * 100
        multi_prec = metrics["multi_choice_precision"] * 100
        multi_rec = metrics["multi_choice_recall"] * 100
        multi_f1 = metrics["multi_choice_f1"] * 100
        avg_score = metrics["average_score"] * 100
        
        summary_html = f"""
        <section class="summary">
            <h2>📊 Test Summary</h2>
            
            <div class="config-grid">
                <div class="config-item">
                    <span class="config-label">Model:</span>
                    <span class="config-value">{model_name}</span>
                </div>
                <div class="config-item">
                    <span class="config-label">Context Length:</span>
                    <span class="config-value">{context_length_display}</span>
                </div>
                <div class="config-item">
                    <span class="config-label">Novel:</span>
                    <span class="config-value">{Path(novel_path).name if novel_path != "Unknown" else novel_path}</span>
                </div>
                <div class="config-item">
                    <span class="config-label">Tested At:</span>
                    <span class="config-value">{tested_at}</span>
                </div>
                <div class="config-item">
                    <span class="config-label">Questions in Set:</span>
                    <span class="config-value">{total_in_set}</span>
                </div>
                <div class="config-item">
                    <span class="config-label">Questions Tested:</span>
                    <span class="config-value">{tested_count}</span>
                </div>
            </div>
            
            <h3>Performance Metrics</h3>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{avg_score:.1f}%</div>
                    <div class="metric-label">Overall Score</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{single_acc:.1f}%</div>
                    <div class="metric-label">Single-Choice Accuracy</div>
                    <div class="metric-detail">{metrics["single_choice_count"]} questions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{multi_f1:.1f}%</div>
                    <div class="metric-label">Multi-Choice F1</div>
                    <div class="metric-detail">{metrics["multiple_choice_count"]} questions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{multi_prec:.1f}%</div>
                    <div class="metric-label">Multi-Choice Precision</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{multi_rec:.1f}%</div>
                    <div class="metric-label">Multi-Choice Recall</div>
                </div>
            </div>
            
            <h3>Result Distribution</h3>
            
            <div class="distribution-grid">
                <div class="dist-item correct">
                    <div class="dist-count">{metrics["correct_count"]}</div>
                    <div class="dist-label">Correct</div>
                </div>
                <div class="dist-item partial">
                    <div class="dist-count">{metrics["partially_correct_count"]}</div>
                    <div class="dist-label">Partially Correct</div>
                </div>
                <div class="dist-item incorrect">
                    <div class="dist-count">{metrics["incorrect_count"]}</div>
                    <div class="dist-label">Incorrect</div>
                </div>
                <div class="dist-item error">
                    <div class="dist-count">{metrics["parsing_error_count"]}</div>
                    <div class="dist-label">Parsing Errors</div>
                </div>
            </div>
        </section>
        """
        
        return summary_html
    
    def _generate_visualization_section(self) -> str:
        """
        Generate HTML for visualization section with scatter plot.
        
        Returns:
            HTML string for visualization section
        """
        context_length = self.metadata.get("context_length", 100000)
        
        # Generate scatter plot
        try:
            plot_html = create_scatter_plot(self.results, context_length)
        except Exception as e:
            plot_html = f'<div class="error-message">Failed to generate visualization: {str(e)}</div>'
        
        visualization_html = f"""
        <section class="visualization">
            <h2>📈 Performance Visualization</h2>
            <p class="section-description">
                This scatter plot shows model performance across different token positions in the context.
                Each point represents a test question, colored by correctness. The trend line shows 
                the moving average to identify position bias patterns.
            </p>
            {plot_html}
        </section>
        """
        
        return visualization_html
    
    def _generate_error_analysis(self, num_examples: int) -> str:
        """
        Generate HTML for error analysis section with random error case sampling.
        
        Args:
            num_examples: Number of error examples to include
            
        Returns:
            HTML string for error analysis section
        """
        # Filter for incorrect and partially correct results
        error_results = [
            r for r in self.results 
            if categorize_result(r) in ["incorrect", "partially_correct", "parsing_error"]
        ]
        
        if not error_results:
            return """
            <section class="error-analysis">
                <h2>🎯 Error Analysis</h2>
                <p class="success-message">Excellent! No errors found in the test results.</p>
            </section>
            """
        
        # Randomly sample error cases
        sample_size = min(num_examples, len(error_results))
        sampled_errors = random.sample(error_results, sample_size)
        
        # Generate error case HTML
        error_cases_html = ""
        for idx, result in enumerate(sampled_errors, 1):
            category = categorize_result(result)
            score = calculate_score(result)
            
            # Determine category badge
            if category == "parsing_error":
                badge_class = "badge-error"
                badge_text = "Parsing Error"
            elif category == "partially_correct":
                badge_class = "badge-partial"
                badge_text = "Partially Correct"
            else:
                badge_class = "badge-incorrect"
                badge_text = "Incorrect"
            
            question_text = result.get("question", "N/A")
            question_type = result.get("question_type", "unknown")
            choices = result.get("choice", {})
            correct_answer = ", ".join(result.get("correct_answer", []))
            model_answer = ", ".join(result.get("model_answer", [])) if result.get("model_answer") else "No answer"
            position = result.get("position", {}).get("start_pos", "Unknown")
            
            # Format choices
            choices_html = ""
            for key, value in choices.items():
                choices_html += f"<div class='choice-item'><strong>{key}:</strong> {value}</div>"
            
            error_cases_html += f"""
            <div class="error-case">
                <div class="error-header">
                    <span class="error-number">Case #{idx}</span>
                    <span class="badge {badge_class}">{badge_text}</span>
                    <span class="score-badge">Score: {score:.2f}</span>
                </div>
                
                <div class="error-content">
                    <div class="error-field">
                        <strong>Question Type:</strong> {question_type}
                    </div>
                    <div class="error-field">
                        <strong>Position:</strong> Token {position}
                    </div>
                    <div class="error-field">
                        <strong>Question:</strong>
                        <div class="question-text">{question_text}</div>
                    </div>
                    <div class="error-field">
                        <strong>Choices:</strong>
                        <div class="choices-container">
                            {choices_html}
                        </div>
                    </div>
                    <div class="error-field">
                        <strong>Correct Answer:</strong>
                        <span class="answer-correct">{correct_answer}</span>
                    </div>
                    <div class="error-field">
                        <strong>Model Answer:</strong>
                        <span class="answer-model">{model_answer}</span>
                    </div>
                </div>
            </div>
            """
        
        error_analysis_html = f"""
        <section class="error-analysis">
            <h2>🔍 Error Analysis</h2>
            <p class="section-description">
                Showing {sample_size} randomly sampled error cases out of {len(error_results)} total errors.
                These examples help identify patterns in model failures and areas for improvement.
            </p>
            
            <div class="error-stats">
                <span>Total Errors: <strong>{len(error_results)}</strong></span>
                <span>Error Rate: <strong>{len(error_results) / len(self.results) * 100:.1f}%</strong></span>
            </div>
            
            {error_cases_html}
        </section>
        """
        
        return error_analysis_html

    
    def _get_embedded_css(self) -> str:
        """
        Get embedded CSS styles for the HTML report.
        
        Returns:
            HTML style tag with embedded CSS
        """
        return """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .subtitle {
            font-size: 1.2em;
            opacity: 0.95;
        }
        
        section {
            padding: 40px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        section:last-of-type {
            border-bottom: none;
        }
        
        h2 {
            font-size: 2em;
            margin-bottom: 20px;
            color: #667eea;
            font-weight: 600;
        }
        
        h3 {
            font-size: 1.5em;
            margin: 30px 0 20px 0;
            color: #555;
            font-weight: 600;
        }
        
        .section-description {
            color: #666;
            margin-bottom: 30px;
            font-size: 1.05em;
            line-height: 1.7;
        }
        
        /* Configuration Grid */
        .config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
        }
        
        .config-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
        }
        
        .config-label {
            font-weight: 600;
            color: #555;
        }
        
        .config-value {
            color: #333;
            font-family: 'Courier New', monospace;
        }
        
        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            transition: transform 0.2s;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
        }
        
        .metric-value {
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .metric-label {
            font-size: 1em;
            opacity: 0.95;
            font-weight: 500;
        }
        
        .metric-detail {
            font-size: 0.9em;
            opacity: 0.85;
            margin-top: 5px;
        }
        
        /* Distribution Grid */
        .distribution-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .dist-item {
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 2px solid;
        }
        
        .dist-item.correct {
            background: #d4edda;
            border-color: #28a745;
            color: #155724;
        }
        
        .dist-item.partial {
            background: #fff3cd;
            border-color: #ffc107;
            color: #856404;
        }
        
        .dist-item.incorrect {
            background: #f8d7da;
            border-color: #dc3545;
            color: #721c24;
        }
        
        .dist-item.error {
            background: #e2e3e5;
            border-color: #6c757d;
            color: #383d41;
        }
        
        .dist-count {
            font-size: 2em;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        .dist-label {
            font-size: 0.95em;
            font-weight: 500;
        }
        
        /* Visualization Section */
        .visualization {
            background: #f8f9fa;
        }
        
        #scatter-plot {
            margin: 20px 0;
        }
        
        /* Error Analysis */
        .error-stats {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 15px 25px;
            margin-bottom: 30px;
            display: flex;
            gap: 30px;
            font-size: 1.1em;
        }
        
        .error-case {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 25px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .error-header {
            background: #f8f9fa;
            padding: 15px 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            border-bottom: 1px solid #ddd;
        }
        
        .error-number {
            font-weight: 700;
            font-size: 1.1em;
            color: #667eea;
        }
        
        .badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .badge-error {
            background: #6c757d;
            color: white;
        }
        
        .badge-partial {
            background: #ffc107;
            color: #333;
        }
        
        .badge-incorrect {
            background: #dc3545;
            color: white;
        }
        
        .score-badge {
            margin-left: auto;
            padding: 5px 12px;
            background: #667eea;
            color: white;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
        }
        
        .error-content {
            padding: 20px;
        }
        
        .error-field {
            margin-bottom: 15px;
        }
        
        .error-field strong {
            color: #555;
            display: block;
            margin-bottom: 5px;
        }
        
        .question-text {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
            margin-top: 8px;
            line-height: 1.6;
        }
        
        .choices-container {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-top: 8px;
        }
        
        .choice-item {
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .choice-item:last-child {
            border-bottom: none;
        }
        
        .answer-correct {
            background: #d4edda;
            color: #155724;
            padding: 5px 12px;
            border-radius: 4px;
            font-weight: 600;
            font-family: 'Courier New', monospace;
        }
        
        .answer-model {
            background: #f8d7da;
            color: #721c24;
            padding: 5px 12px;
            border-radius: 4px;
            font-weight: 600;
            font-family: 'Courier New', monospace;
        }
        
        .success-message {
            background: #d4edda;
            border: 2px solid #28a745;
            color: #155724;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            font-size: 1.1em;
            font-weight: 500;
        }
        
        .error-message {
            background: #f8d7da;
            border: 2px solid #dc3545;
            color: #721c24;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            font-size: 1.1em;
        }
        
        footer {
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #666;
        }
        
        footer p {
            margin: 5px 0;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            header h1 {
                font-size: 1.8em;
            }
            
            section {
                padding: 20px;
            }
            
            .config-grid,
            .metrics-grid,
            .distribution-grid {
                grid-template-columns: 1fr;
            }
            
            .error-stats {
                flex-direction: column;
                gap: 10px;
            }
        }
    </style>
        """
