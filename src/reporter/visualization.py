"""
Visualization generator module for creating interactive Plotly charts.

This module provides functions to create scatter plots with trend lines
for visualizing test results across token positions.
"""

from typing import List, Tuple
import plotly.graph_objects as go
from .metrics import calculate_score, categorize_result


def _assign_color(result: dict) -> str:
    """
    Assign color based on result correctness.
    
    Args:
        result: Test result dictionary
        
    Returns:
        Color hex code string
    """
    category = categorize_result(result)
    score = calculate_score(result)
    
    if category == "parsing_error":
        return "#6c757d"  # Gray for parsing errors
    elif score == 1.0:
        return "#28a745"  # Green for correct
    elif score > 0.0:
        return "#ffc107"  # Yellow for partially correct
    else:
        return "#dc3545"  # Red for incorrect


def _calculate_trend_line(positions: List[int], scores: List[float], 
                         window_size: int = 20) -> Tuple[List[int], List[float]]:
    """
    Calculate smoothed trend line using moving average.
    
    Args:
        positions: List of token positions
        scores: List of corresponding scores
        window_size: Window size for moving average (default: 20)
        
    Returns:
        Tuple of (trend_positions, trend_scores)
    """
    if len(positions) < window_size:
        # Not enough data points for moving average
        return positions, scores
    
    # Sort by position
    sorted_data = sorted(zip(positions, scores), key=lambda x: x[0])
    sorted_positions = [p for p, _ in sorted_data]
    sorted_scores = [s for _, s in sorted_data]
    
    trend_positions = []
    trend_scores = []
    
    # Calculate moving average
    for i in range(len(sorted_positions)):
        # Determine window boundaries
        start_idx = max(0, i - window_size // 2)
        end_idx = min(len(sorted_positions), i + window_size // 2 + 1)
        
        # Calculate average score in window
        window_scores = sorted_scores[start_idx:end_idx]
        avg_score = sum(window_scores) / len(window_scores)
        
        trend_positions.append(sorted_positions[i])
        trend_scores.append(avg_score)
    
    return trend_positions, trend_scores


def create_scatter_plot(results: List[dict], context_length: int) -> str:
    """
    Create interactive scatter plot with trend line.
    
    Args:
        results: List of test result dictionaries
        context_length: Total context length used in testing
        
    Returns:
        Plotly HTML div string for embedding
    """
    if not results:
        return "<div>No results to visualize</div>"
    
    # Extract data from results
    positions = []
    scores = []
    colors = []
    hover_texts = []
    
    for result in results:
        # Get position (use start_pos from position dict)
        position = result.get("position", {}).get("start_pos", 0)
        positions.append(position)
        
        # Calculate score
        score = calculate_score(result)
        scores.append(score)
        
        # Assign color
        color = _assign_color(result)
        colors.append(color)
        
        # Create hover text
        question_text = result.get("question", "")
        # Truncate long questions
        if len(question_text) > 100:
            question_text = question_text[:97] + "..."
        
        correct_answer = ", ".join(result.get("correct_answer", []))
        model_answer = ", ".join(result.get("model_answer", []))
        
        hover_text = (
            f"<b>Question:</b> {question_text}<br>"
            f"<b>Correct Answer:</b> {correct_answer}<br>"
            f"<b>Model Answer:</b> {model_answer}<br>"
            f"<b>Score:</b> {score:.2f}<br>"
            f"<b>Position:</b> {position}"
        )
        hover_texts.append(hover_text)
    
    # Create scatter plot
    scatter = go.Scatter(
        x=positions,
        y=scores,
        mode='markers',
        marker=dict(
            color=colors,
            size=8,
            opacity=0.7,
            line=dict(width=1, color='white')
        ),
        text=hover_texts,
        hovertemplate='%{text}<extra></extra>',
        name='Test Results'
    )
    
    # Calculate trend line
    trend_positions, trend_scores = _calculate_trend_line(positions, scores)
    
    trend_line = go.Scatter(
        x=trend_positions,
        y=trend_scores,
        mode='lines',
        line=dict(
            color='rgba(0, 0, 0, 0.5)',
            width=3,
            dash='solid'
        ),
        name='Trend Line (Moving Average)',
        hovertemplate='Position: %{x}<br>Avg Score: %{y:.2f}<extra></extra>'
    )
    
    # Create figure
    fig = go.Figure(data=[scatter, trend_line])
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'Performance Across Token Positions',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        xaxis=dict(
            title='Token Position',
            range=[0, context_length],
            gridcolor='rgba(200, 200, 200, 0.3)'
        ),
        yaxis=dict(
            title='Performance Score',
            range=[-0.05, 1.05],
            gridcolor='rgba(200, 200, 200, 0.3)'
        ),
        plot_bgcolor='white',
        hovermode='closest',
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='rgba(0, 0, 0, 0.2)',
            borderwidth=1
        ),
        width=1200,
        height=600
    )
    
    # Add color legend as annotations
    annotations = [
        dict(
            x=0.98,
            y=0.98,
            xref='paper',
            yref='paper',
            text=(
                '<b>Color Legend:</b><br>'
                '<span style="color:#28a745">● Correct (1.0)</span><br>'
                '<span style="color:#ffc107">● Partially Correct (0.0-1.0)</span><br>'
                '<span style="color:#dc3545">● Incorrect (0.0)</span><br>'
                '<span style="color:#6c757d">● Parsing Error</span>'
            ),
            showarrow=False,
            align='left',
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='rgba(0, 0, 0, 0.2)',
            borderwidth=1,
            borderpad=10,
            font=dict(size=11)
        )
    ]
    fig.update_layout(annotations=annotations)
    
    # Return HTML div
    return fig.to_html(
        include_plotlyjs='cdn',
        div_id='scatter-plot',
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d']
        }
    )
