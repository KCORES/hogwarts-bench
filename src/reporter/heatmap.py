"""
Heatmap generator module for visualizing question coverage and accuracy.

This module provides functions to create heatmaps showing:
- Question distribution across context regions (coverage)
- Model performance across context regions (accuracy)
- Combined view of both coverage and accuracy
"""

import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import List, Tuple, Optional

import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)

# Project branding
PROJECT_TITLE = "KCORES Hogwarts Bench"
LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'assets', 'images', 'kcores-llm-arena-logo-black.png')


def _get_logo_base64() -> Optional[str]:
    """
    Load logo image and convert to base64 for embedding in Plotly.
    
    Returns:
        Base64 encoded image string or None if loading fails
    """
    try:
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, 'rb') as f:
                logo_data = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/png;base64,{logo_data}"
    except Exception as e:
        logger.warning(f"Failed to load logo: {e}")
    return None


def _add_branding(fig: go.Figure, height: int = 450, width: int = 1200) -> None:
    """
    Add project title and logo to a Plotly figure.
    
    Args:
        fig: Plotly figure to modify
        height: Figure height for positioning calculations
        width: Figure width for positioning calculations
    """
    # Add logo as layout image (bottom right with 8px padding)
    logo_base64 = _get_logo_base64()
    if logo_base64:
        # Calculate 8px padding in paper coordinates
        x_padding = 8 / width   # 8px from right edge
        y_padding = 8 / height  # 8px from bottom edge
        
        fig.add_layout_image(
            dict(
                source=logo_base64,
                xref="paper",
                yref="paper",
                x=1.0 - x_padding,
                y=y_padding,
                sizex=0.12,
                sizey=0.12,
                xanchor="right",
                yanchor="bottom",
                opacity=0.8,
                layer="above"
            )
        )


def _to_fullscreen_html(fig: go.Figure, div_id: str) -> str:
    """
    Convert a Plotly figure to fullscreen responsive HTML.
    
    Args:
        fig: Plotly figure to convert
        div_id: ID for the div element
        
    Returns:
        Full HTML page string with responsive styling
    """
    # Get the plotly div content
    plot_div = fig.to_html(
        include_plotlyjs='cdn',
        div_id=div_id,
        full_html=False,
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'responsive': True
        }
    )
    
    # Wrap in fullscreen HTML with 50vh height
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KCORES Hogwarts Bench - Heatmap</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        html, body {{
            width: 100%;
            height: 100%;
        }}
        #{div_id} {{
            width: 100vw;
            height: 100vh;
            min-height: 1000px;
        }}
        .plotly-graph-div {{
            width: 100% !important;
            height: 100% !important;
        }}
    </style>
</head>
<body>
    {plot_div}
    <script>
        window.addEventListener('resize', function() {{
            Plotly.Plots.resize(document.getElementById('{div_id}'));
        }});
    </script>
</body>
</html>'''
    
    return html


@dataclass
class QuestionPosition:
    """Position information for a question in the context."""
    start_pos: int
    end_pos: int


@dataclass
class QuestionEntry:
    """A question entry with position information."""
    position: QuestionPosition


@dataclass
class ResultEntry:
    """A test result entry with position and score."""
    position: QuestionPosition
    score: float


@dataclass
class BinStats:
    """Statistics for a single bin in the heatmap."""
    start_pos: int
    end_pos: int
    coverage: float  # Normalized coverage [0, 1]
    accuracy: Optional[float]  # Average accuracy [0, 1] or None if no data
    question_count: int  # Number of questions in this bin


@dataclass
class DatasetMetadata:
    """Metadata extracted from JSONL files."""
    model_name: Optional[str] = None
    question_set_path: Optional[str] = None
    novel_path: Optional[str] = None
    context_length: Optional[int] = None
    total_tokens: Optional[int] = None
    total_questions: Optional[int] = None
    tested_at: Optional[str] = None
    generated_at: Optional[str] = None


def extract_metadata(file_path: str) -> DatasetMetadata:
    """
    Extract metadata from the first line of a JSONL file.
    
    Args:
        file_path: Path to the JSONL file
        
    Returns:
        DatasetMetadata object with extracted information
    """
    metadata = DatasetMetadata()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line:
                data = json.loads(first_line)
                if 'metadata' in data:
                    meta = data['metadata']
                    metadata.model_name = meta.get('model_name')
                    metadata.question_set_path = meta.get('question_set_path')
                    metadata.novel_path = meta.get('novel_path')
                    metadata.context_length = meta.get('context_length')
                    metadata.total_tokens = meta.get('total_tokens')
                    metadata.total_questions = meta.get('total_questions')
                    metadata.tested_at = meta.get('tested_at')
                    metadata.generated_at = meta.get('generated_at')
    except Exception as e:
        logger.warning(f"Failed to extract metadata: {e}")
    
    return metadata


def load_question_data(file_path: str) -> Tuple[List[QuestionEntry], int, DatasetMetadata]:
    """
    Load question data from a JSONL file.
    
    Args:
        file_path: Path to the JSONL file containing question data
        
    Returns:
        Tuple of (valid_entries, skipped_count, metadata)
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    valid_entries: List[QuestionEntry] = []
    skipped_count = 0
    metadata = extract_metadata(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                
                # Skip metadata lines
                if 'metadata' in data:
                    continue
                
                # Validate required fields
                position = data.get('position', {})
                start_pos = position.get('start_pos')
                end_pos = position.get('end_pos')
                
                if start_pos is None or end_pos is None:
                    logger.warning(f"Line {line_num}: Missing position.start_pos or position.end_pos")
                    skipped_count += 1
                    continue
                
                entry = QuestionEntry(
                    position=QuestionPosition(start_pos=start_pos, end_pos=end_pos)
                )
                valid_entries.append(entry)
                
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: Invalid JSON - {e}")
                skipped_count += 1
                
    logger.info(f"Loaded {len(valid_entries)} valid entries, skipped {skipped_count}")
    return valid_entries, skipped_count, metadata



def load_result_data(file_path: str) -> Tuple[List[ResultEntry], int, DatasetMetadata]:
    """
    Load test result data from a JSONL file.
    
    Args:
        file_path: Path to the JSONL file containing result data
        
    Returns:
        Tuple of (valid_entries, skipped_count, metadata)
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    valid_entries: List[ResultEntry] = []
    skipped_count = 0
    metadata = extract_metadata(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                
                # Skip metadata lines
                if 'metadata' in data:
                    continue
                
                # Validate required fields
                position = data.get('position', {})
                start_pos = position.get('start_pos')
                end_pos = position.get('end_pos')
                score = data.get('score')
                
                if start_pos is None or end_pos is None:
                    logger.warning(f"Line {line_num}: Missing position.start_pos or position.end_pos")
                    skipped_count += 1
                    continue
                    
                if score is None:
                    logger.warning(f"Line {line_num}: Missing score field")
                    skipped_count += 1
                    continue
                
                entry = ResultEntry(
                    position=QuestionPosition(start_pos=start_pos, end_pos=end_pos),
                    score=float(score)
                )
                valid_entries.append(entry)
                
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: Invalid JSON - {e}")
                skipped_count += 1
            except (ValueError, TypeError) as e:
                logger.warning(f"Line {line_num}: Invalid score value - {e}")
                skipped_count += 1
                
    logger.info(f"Loaded {len(valid_entries)} valid entries, skipped {skipped_count}")
    return valid_entries, skipped_count, metadata



def calculate_coverage_bins(
    questions: List[QuestionEntry],
    context_length: int,
    num_bins: int = 50
) -> List[BinStats]:
    """
    Calculate coverage bins showing question distribution across context.
    
    Args:
        questions: List of question entries with position information
        context_length: Total length of the context in tokens
        num_bins: Number of bins to divide the context into
        
    Returns:
        List of BinStats with coverage values
    """
    if num_bins <= 0:
        raise ValueError("num_bins must be positive")
    if context_length <= 0:
        raise ValueError("context_length must be positive")
    
    bin_size = context_length / num_bins
    bins: List[BinStats] = []
    
    # Initialize bins
    for i in range(num_bins):
        start_pos = int(i * bin_size)
        end_pos = int((i + 1) * bin_size) if i < num_bins - 1 else context_length
        bins.append(BinStats(
            start_pos=start_pos,
            end_pos=end_pos,
            coverage=0.0,
            accuracy=None,
            question_count=0
        ))
    
    if not questions:
        return bins
    
    # Calculate raw coverage for each bin
    raw_coverage = [0.0] * num_bins
    
    for question in questions:
        q_start = question.position.start_pos
        q_end = question.position.end_pos
        q_length = q_end - q_start
        
        if q_length <= 0:
            continue
        
        # Find overlapping bins and calculate proportional coverage
        for i, bin_stat in enumerate(bins):
            # Calculate overlap between question and bin
            overlap_start = max(q_start, bin_stat.start_pos)
            overlap_end = min(q_end, bin_stat.end_pos)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > 0:
                # Proportional contribution of this question to this bin
                proportion = overlap / q_length
                raw_coverage[i] += proportion
    
    # Normalize coverage to [0, 1]
    max_coverage = max(raw_coverage) if raw_coverage else 0
    
    for i, bin_stat in enumerate(bins):
        if max_coverage > 0:
            bins[i].coverage = raw_coverage[i] / max_coverage
        else:
            bins[i].coverage = 0.0
    
    return bins



def calculate_accuracy_bins(
    results: List[ResultEntry],
    context_length: int,
    num_bins: int = 50
) -> List[BinStats]:
    """
    Calculate accuracy bins showing model performance across context.
    
    Args:
        results: List of result entries with position and score
        context_length: Total length of the context in tokens
        num_bins: Number of bins to divide the context into
        
    Returns:
        List of BinStats with accuracy values
    """
    if num_bins <= 0:
        raise ValueError("num_bins must be positive")
    if context_length <= 0:
        raise ValueError("context_length must be positive")
    
    bin_size = context_length / num_bins
    bins: List[BinStats] = []
    
    # Initialize bins with score accumulators
    bin_scores: List[List[float]] = [[] for _ in range(num_bins)]
    
    # Initialize bins
    for i in range(num_bins):
        start_pos = int(i * bin_size)
        end_pos = int((i + 1) * bin_size) if i < num_bins - 1 else context_length
        bins.append(BinStats(
            start_pos=start_pos,
            end_pos=end_pos,
            coverage=0.0,
            accuracy=None,
            question_count=0
        ))
    
    # Assign results to bins based on start_pos
    for result in results:
        start_pos = result.position.start_pos
        
        # Find which bin this result belongs to
        bin_index = int(start_pos / bin_size)
        bin_index = min(bin_index, num_bins - 1)  # Handle edge case
        
        bin_scores[bin_index].append(result.score)
    
    # Calculate average accuracy for each bin
    for i, scores in enumerate(bin_scores):
        bins[i].question_count = len(scores)
        if scores:
            bins[i].accuracy = sum(scores) / len(scores)
        else:
            bins[i].accuracy = None  # No data, distinct from 0.0
    
    return bins



def create_coverage_heatmap(
    bins: List[BinStats], 
    context_length: int,
    metadata: Optional[DatasetMetadata] = None
) -> str:
    """
    Create a coverage heatmap showing question distribution.
    
    Args:
        bins: List of BinStats with coverage values
        context_length: Total context length for x-axis
        metadata: Optional metadata for title display
        
    Returns:
        Plotly HTML string for embedding
    """
    if not bins:
        return "<div>No data to visualize</div>"
    
    # Prepare data for heatmap
    coverage_values = [[b.coverage for b in bins]]
    x_labels = [f"{b.start_pos//1000}K-{b.end_pos//1000}K" for b in bins]
    
    # Create hover text
    hover_text = [[
        f"Position: {b.start_pos:,} - {b.end_pos:,}<br>"
        f"Coverage: {b.coverage:.3f}"
        for b in bins
    ]]
    
    fig = go.Figure(data=go.Heatmap(
        z=coverage_values,
        x=x_labels,
        y=['Coverage'],
        colorscale='Blues',
        showscale=True,
        colorbar=dict(
            title=dict(text='Coverage', side='right')
        ),
        hovertemplate='%{text}<extra></extra>',
        text=hover_text
    ))
    
    # Build subtitle with metadata
    subtitle_parts = ['Question Coverage Across Context']
    if metadata and metadata.novel_path:
        dataset_name = metadata.novel_path.split('/')[-1].replace('.txt', '')
        subtitle_parts = [f'Dataset: {dataset_name}']
    
    subtitle_text = ' | '.join(subtitle_parts)
    title_text = f"<b>{PROJECT_TITLE}</b><br><span style='font-size:14px'>{subtitle_text}</span>"
    
    fig.update_layout(
        title={
            'text': title_text,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis=dict(
            title='Token Position',
            tickangle=45
        ),
        yaxis=dict(
            title='',
            showticklabels=False
        ),
        autosize=True,
        margin=dict(l=50, r=50, t=100, b=100)
    )
    
    # Add branding (logo)
    _add_branding(fig, height=250, width=1200)
    
    return _to_fullscreen_html(fig, 'coverage-heatmap')



def create_accuracy_heatmap(
    bins: List[BinStats], 
    context_length: int,
    metadata: Optional[DatasetMetadata] = None
) -> str:
    """
    Create an accuracy heatmap showing model performance.
    
    Args:
        bins: List of BinStats with accuracy values
        context_length: Total context length for x-axis
        metadata: Optional metadata for title display
        
    Returns:
        Plotly HTML string for embedding
    """
    if not bins:
        return "<div>No data to visualize</div>"
    
    # Prepare data - use -1 for None values (no data)
    accuracy_values = [[b.accuracy if b.accuracy is not None else -1 for b in bins]]
    x_labels = [f"{b.start_pos//1000}K-{b.end_pos//1000}K" for b in bins]
    
    # Create hover text
    hover_text = [[
        f"Position: {b.start_pos:,} - {b.end_pos:,}<br>"
        f"Accuracy: {b.accuracy:.2%}<br>"
        f"Questions: {b.question_count}"
        if b.accuracy is not None else
        f"Position: {b.start_pos:,} - {b.end_pos:,}<br>"
        f"No data"
        for b in bins
    ]]
    
    # Custom colorscale: gray for no data, red-yellow-green for accuracy
    colorscale = [
        [0.0, '#6c757d'],    # Gray for no data (-1 to 0)
        [0.001, '#dc3545'],  # Red for low accuracy
        [0.5, '#ffc107'],    # Yellow for medium accuracy
        [1.0, '#28a745']     # Green for high accuracy
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=accuracy_values,
        x=x_labels,
        y=['Accuracy'],
        colorscale=colorscale,
        zmin=-0.1,
        zmax=1.0,
        showscale=True,
        colorbar=dict(
            title=dict(text='Accuracy', side='right'),
            tickvals=[0, 0.25, 0.5, 0.75, 1.0],
            ticktext=['0%', '25%', '50%', '75%', '100%']
        ),
        hovertemplate='%{text}<extra></extra>',
        text=hover_text
    ))
    
    # Build subtitle with metadata
    subtitle_parts = []
    if metadata:
        if metadata.model_name:
            subtitle_parts.append(f'Model: {metadata.model_name}')
        if metadata.question_set_path:
            dataset_name = metadata.question_set_path.split('/')[-1].replace('.jsonl', '')
            subtitle_parts.append(f'Dataset: {dataset_name}')
    
    if not subtitle_parts:
        subtitle_parts.append('Model Accuracy Across Context')
    
    subtitle_text = ' | '.join(subtitle_parts)
    title_text = f"<b>{PROJECT_TITLE}</b><br><span style='font-size:14px'>{subtitle_text}</span>"
    
    fig.update_layout(
        title={
            'text': title_text,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis=dict(
            title='Token Position',
            tickangle=45
        ),
        yaxis=dict(
            title='',
            showticklabels=False
        ),
        autosize=True,
        margin=dict(l=50, r=50, t=120, b=100)
    )
    
    # Add branding (logo)
    _add_branding(fig, height=270, width=1200)
    
    return _to_fullscreen_html(fig, 'accuracy-heatmap')



def create_combined_heatmap(
    coverage_bins: List[BinStats],
    accuracy_bins: List[BinStats],
    context_length: int,
    question_metadata: Optional[DatasetMetadata] = None,
    result_metadata: Optional[DatasetMetadata] = None
) -> str:
    """
    Create a combined heatmap showing both coverage and accuracy aligned.
    
    Args:
        coverage_bins: List of BinStats with coverage values
        accuracy_bins: List of BinStats with accuracy values
        context_length: Total context length for x-axis
        question_metadata: Optional metadata from question file
        result_metadata: Optional metadata from result file
        
    Returns:
        Plotly HTML string for embedding
    """
    if not coverage_bins or not accuracy_bins:
        return "<div>No data to visualize</div>"
    
    # Create subplots with shared x-axis
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=('Question Coverage', 'Model Accuracy'),
        row_heights=[0.5, 0.5]
    )
    
    x_labels = [f"{b.start_pos//1000}K-{b.end_pos//1000}K" for b in coverage_bins]
    
    # Coverage heatmap
    coverage_values = [[b.coverage for b in coverage_bins]]
    coverage_hover = [[
        f"Position: {b.start_pos:,} - {b.end_pos:,}<br>"
        f"Coverage: {b.coverage:.3f}"
        for b in coverage_bins
    ]]
    
    fig.add_trace(
        go.Heatmap(
            z=coverage_values,
            x=x_labels,
            y=['Coverage'],
            colorscale='Blues',
            showscale=True,
            colorbar=dict(
                title=dict(text='Coverage', side='right'),
                x=1.02,
                y=0.75,
                len=0.4
            ),
            hovertemplate='%{text}<extra></extra>',
            text=coverage_hover
        ),
        row=1, col=1
    )
    
    # Accuracy heatmap
    accuracy_values = [[b.accuracy if b.accuracy is not None else -1 for b in accuracy_bins]]
    accuracy_hover = [[
        f"Position: {b.start_pos:,} - {b.end_pos:,}<br>"
        f"Accuracy: {b.accuracy:.2%}<br>"
        f"Questions: {b.question_count}"
        if b.accuracy is not None else
        f"Position: {b.start_pos:,} - {b.end_pos:,}<br>"
        f"No data"
        for b in accuracy_bins
    ]]
    
    colorscale = [
        [0.0, '#6c757d'],
        [0.001, '#dc3545'],
        [0.5, '#ffc107'],
        [1.0, '#28a745']
    ]
    
    fig.add_trace(
        go.Heatmap(
            z=accuracy_values,
            x=x_labels,
            y=['Accuracy'],
            colorscale=colorscale,
            zmin=-0.1,
            zmax=1.0,
            showscale=True,
            colorbar=dict(
                title=dict(text='Accuracy', side='right'),
                x=1.02,
                y=0.25,
                len=0.4,
                tickvals=[0, 0.25, 0.5, 0.75, 1.0],
                ticktext=['0%', '25%', '50%', '75%', '100%']
            ),
            hovertemplate='%{text}<extra></extra>',
            text=accuracy_hover
        ),
        row=2, col=1
    )
    
    # Build subtitle with metadata
    subtitle_parts = []
    metadata = result_metadata or question_metadata
    if metadata:
        if metadata.model_name:
            subtitle_parts.append(f'Model: {metadata.model_name}')
        if metadata.question_set_path:
            dataset_name = metadata.question_set_path.split('/')[-1].replace('.jsonl', '')
            subtitle_parts.append(f'Dataset: {dataset_name}')
        elif metadata.novel_path:
            dataset_name = metadata.novel_path.split('/')[-1].replace('.txt', '')
            subtitle_parts.append(f'Dataset: {dataset_name}')
    
    if not subtitle_parts:
        subtitle_parts.append('Coverage and Accuracy Across Context')
    
    subtitle_text = ' | '.join(subtitle_parts)
    title_text = f"<b>{PROJECT_TITLE}</b><br><span style='font-size:14px'>{subtitle_text}</span>"
    
    fig.update_layout(
        title={
            'text': title_text,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        autosize=True,
        margin=dict(l=50, r=100, t=120, b=100)
    )
    
    fig.update_xaxes(title_text='Token Position', tickangle=45, row=2, col=1)
    fig.update_yaxes(showticklabels=False, row=1, col=1)
    fig.update_yaxes(showticklabels=False, row=2, col=1)
    
    # Calculate overall average accuracy
    total_correct = 0
    total_questions = 0
    for b in accuracy_bins:
        if b.accuracy is not None and b.question_count > 0:
            total_correct += b.accuracy * b.question_count
            total_questions += b.question_count
    
    avg_accuracy = total_correct / total_questions if total_questions > 0 else 0.0
    
    # Add average accuracy annotation in bottom left
    fig.add_annotation(
        text=f"<b>Average Accuracy: {avg_accuracy:.2%}</b>",
        xref="paper",
        yref="paper",
        x=0.01,
        y=0.01,
        showarrow=False,
        font=dict(size=14, color='#333333'),
        align='left',
        xanchor='left',
        yanchor='bottom',
        bgcolor='rgba(255, 255, 255, 0.8)',
        bordercolor='#cccccc',
        borderwidth=1,
        borderpad=6
    )
    
    # Add branding (logo)
    _add_branding(fig, height=500, width=1200)
    
    return _to_fullscreen_html(fig, 'combined-heatmap')



# ============================================================================
# Depth-Aware Heatmap Functions
# ============================================================================

@dataclass
class DepthBinStats:
    """Statistics for a depth bin at a specific context length."""
    context_length: int
    depth_bin: str  # "0%", "25%", "50%", "75%", "100%"
    accuracy: Optional[float]
    question_count: int


def load_depth_result_data(file_path: str) -> Tuple[List[dict], DatasetMetadata]:
    """
    Load depth-aware test result data from a JSONL file.
    
    Args:
        file_path: Path to the JSONL file containing depth-aware results
        
    Returns:
        Tuple of (valid_entries, metadata)
    """
    valid_entries = []
    metadata = extract_metadata(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                # Skip metadata lines
                if 'metadata' in data:
                    continue
                
                # Validate required depth fields
                depth_bin = data.get('depth_bin')
                test_context_length = data.get('test_context_length')
                score = data.get('score')
                
                if depth_bin is None or test_context_length is None:
                    logger.debug(f"Line {line_num}: Missing depth_bin or test_context_length")
                    continue
                
                if score is None:
                    logger.debug(f"Line {line_num}: Missing score field")
                    continue
                
                valid_entries.append({
                    'depth_bin': depth_bin,
                    'test_context_length': test_context_length,
                    'score': float(score)
                })
                
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: Invalid JSON - {e}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Line {line_num}: Invalid value - {e}")
    
    logger.info(f"Loaded {len(valid_entries)} depth-aware results")
    return valid_entries, metadata


def calculate_depth_bins(
    results: List[dict],
    context_lengths: Optional[List[int]] = None,
    depth_labels: List[str] = ["0%", "25%", "50%", "75%", "100%"]
) -> List[DepthBinStats]:
    """
    Calculate statistics for depth heatmap.
    
    Args:
        results: List of result dicts with depth_bin, test_context_length, score
        context_lengths: List of context lengths (auto-detected if None)
        depth_labels: Depth bin labels
        
    Returns:
        List of DepthBinStats for each (context_length, depth_bin) combination
    """
    if not results:
        return []
    
    # Auto-detect context lengths if not provided
    if context_lengths is None:
        context_lengths = sorted(set(r['test_context_length'] for r in results))
    
    # Group results by (context_length, depth_bin)
    groups = {}
    for r in results:
        key = (r['test_context_length'], r['depth_bin'])
        if key not in groups:
            groups[key] = []
        groups[key].append(r['score'])
    
    # Calculate statistics for each combination
    stats = []
    for ctx_len in context_lengths:
        for depth_bin in depth_labels:
            key = (ctx_len, depth_bin)
            scores = groups.get(key, [])
            
            if scores:
                accuracy = sum(scores) / len(scores)
                question_count = len(scores)
            else:
                accuracy = None
                question_count = 0
            
            stats.append(DepthBinStats(
                context_length=ctx_len,
                depth_bin=depth_bin,
                accuracy=accuracy,
                question_count=question_count
            ))
    
    return stats


def create_depth_heatmap(
    bins: List[DepthBinStats],
    metadata: Optional[DatasetMetadata] = None
) -> str:
    """
    Create a 2D depth heatmap showing accuracy across context lengths and depths.
    
    X-axis: Context length (32K, 64K, 128K, 200K, etc.)
    Y-axis: Depth (0%, 25%, 50%, 75%, 100%)
    Color: Accuracy (green=high, red=low, gray=no data)
    
    Args:
        bins: List of DepthBinStats from calculate_depth_bins
        metadata: Optional metadata for title display
        
    Returns:
        Plotly HTML string for embedding
    """
    if not bins:
        return "<div>No data to visualize</div>"
    
    # Extract unique context lengths and depth labels
    context_lengths = sorted(set(b.context_length for b in bins))
    depth_labels = ["0%", "25%", "50%", "75%", "100%"]
    
    # Build 2D matrix (rows=depth, cols=context_length)
    # Note: Y-axis goes from bottom to top, so we reverse depth_labels
    z_values = []
    hover_texts = []
    
    for depth_bin in reversed(depth_labels):  # Reverse so 0% is at bottom
        row_values = []
        row_hover = []
        
        for ctx_len in context_lengths:
            # Find matching bin
            matching = [b for b in bins 
                       if b.context_length == ctx_len and b.depth_bin == depth_bin]
            
            if matching and matching[0].accuracy is not None:
                bin_stat = matching[0]
                row_values.append(bin_stat.accuracy)
                row_hover.append(
                    f"Context: {ctx_len//1000}K<br>"
                    f"Depth: {depth_bin}<br>"
                    f"Accuracy: {bin_stat.accuracy:.2%}<br>"
                    f"Questions: {bin_stat.question_count}"
                )
            else:
                row_values.append(-0.05)  # Marker for no data
                row_hover.append(
                    f"Context: {ctx_len//1000}K<br>"
                    f"Depth: {depth_bin}<br>"
                    f"No data"
                )
        
        z_values.append(row_values)
        hover_texts.append(row_hover)
    
    # X-axis labels
    x_labels = [f"{ctx//1000}K" for ctx in context_lengths]
    
    # Y-axis labels (reversed to match z_values)
    y_labels = list(reversed(depth_labels))
    
    # Custom colorscale: gray for no data, red-yellow-green for accuracy
    colorscale = [
        [0.0, '#6c757d'],     # Gray for no data (-0.05 to 0)
        [0.05, '#6c757d'],    # Gray boundary
        [0.051, '#dc3545'],   # Red for low accuracy
        [0.5, '#ffc107'],     # Yellow for medium accuracy
        [1.0, '#28a745']      # Green for high accuracy
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=x_labels,
        y=y_labels,
        colorscale=colorscale,
        zmin=-0.05,
        zmax=1.0,
        showscale=True,
        colorbar=dict(
            title=dict(text='Accuracy', side='right'),
            tickvals=[0, 0.25, 0.5, 0.75, 1.0],
            ticktext=['0%', '25%', '50%', '75%', '100%']
        ),
        hovertemplate='%{text}<extra></extra>',
        text=hover_texts
    ))
    
    # Build subtitle with metadata
    subtitle_parts = []
    if metadata:
        if metadata.model_name:
            subtitle_parts.append(f'Model: {metadata.model_name}')
        if metadata.question_set_path:
            dataset_name = metadata.question_set_path.split('/')[-1].replace('.jsonl', '')
            subtitle_parts.append(f'Dataset: {dataset_name}')
    
    if not subtitle_parts:
        subtitle_parts.append('Depth-Aware Accuracy Heatmap')
    
    subtitle_text = ' | '.join(subtitle_parts)
    title_text = f"<b>{PROJECT_TITLE}</b><br><span style='font-size:14px'>{subtitle_text}</span>"
    
    fig.update_layout(
        title={
            'text': title_text,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis=dict(
            title='Context Length',
            side='bottom'
        ),
        yaxis=dict(
            title='Evidence Depth',
            autorange=True
        ),
        autosize=True,
        margin=dict(l=80, r=100, t=120, b=80)
    )
    
    # Add branding (logo)
    _add_branding(fig, height=450, width=1200)
    
    return _to_fullscreen_html(fig, 'depth-heatmap')


def create_combined_depth_heatmap(
    coverage_bins: List[BinStats],
    depth_bins: List[DepthBinStats],
    context_length: int,
    question_metadata: Optional[DatasetMetadata] = None,
    result_metadata: Optional[DatasetMetadata] = None
) -> str:
    """
    Create a combined heatmap showing coverage (1D), depth accuracy (2D), and average accuracy (1D).
    
    Top: Question coverage across context positions (1D heatmap)
    Middle: Depth-aware accuracy (2D heatmap, X=context length, Y=depth)
    Bottom: Average accuracy per context length (1D heatmap, column means of depth heatmap)
    
    Args:
        coverage_bins: List of BinStats with coverage values
        depth_bins: List of DepthBinStats with depth accuracy values
        context_length: Total context length for coverage x-axis
        question_metadata: Optional metadata from question file
        result_metadata: Optional metadata from result file
        
    Returns:
        Plotly HTML string for embedding
    """
    if not coverage_bins and not depth_bins:
        return "<div>No data to visualize</div>"
    
    # Create subplots: coverage on top, depth heatmap in middle, average at bottom
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.16,
        subplot_titles=('Question Coverage Across Context', 'Depth-Aware Accuracy', 'Average Accuracy by Context Length'),
        row_heights=[0.12, 0.76, 0.12]
    )
    
    # === Top: Coverage heatmap (1D) ===
    if coverage_bins:
        coverage_values = [[b.coverage for b in coverage_bins]]
        coverage_x_labels = [f"{b.start_pos//1000}K-{b.end_pos//1000}K" for b in coverage_bins]
        coverage_hover = [[
            f"Position: {b.start_pos:,} - {b.end_pos:,}<br>"
            f"Coverage: {b.coverage:.3f}"
            for b in coverage_bins
        ]]
        
        fig.add_trace(
            go.Heatmap(
                z=coverage_values,
                x=coverage_x_labels,
                y=['Coverage'],
                colorscale='Blues',
                showscale=True,
                colorbar=dict(
                    title=dict(text='Coverage', side='right'),
                    x=1.02,
                    y=0.94,
                    len=0.1
                ),
                hovertemplate='%{text}<extra></extra>',
                text=coverage_hover
            ),
            row=1, col=1
        )
    
    # === Middle: Depth heatmap (2D) with text annotations ===
    depth_x_labels = []
    depth_context_lengths = []
    column_averages = []  # Store column averages for the bottom heatmap
    
    if depth_bins:
        # Extract unique context lengths and depth labels
        depth_context_lengths = sorted(set(b.context_length for b in depth_bins))
        depth_labels = ["0%", "25%", "50%", "75%", "100%"]
        
        # Build 2D matrix (rows=depth, cols=context_length)
        z_values = []
        hover_texts = []
        text_annotations = []  # For displaying percentage on cells
        
        for depth_bin in reversed(depth_labels):  # Reverse so 0% is at bottom
            row_values = []
            row_hover = []
            row_text = []
            
            for ctx_len in depth_context_lengths:
                matching = [b for b in depth_bins 
                           if b.context_length == ctx_len and b.depth_bin == depth_bin]
                
                if matching and matching[0].accuracy is not None:
                    bin_stat = matching[0]
                    row_values.append(bin_stat.accuracy)
                    row_hover.append(
                        f"Context: {ctx_len//1000}K<br>"
                        f"Depth: {depth_bin}<br>"
                        f"Accuracy: {bin_stat.accuracy:.2%}<br>"
                        f"Questions: {bin_stat.question_count}"
                    )
                    # Format as percentage for cell text
                    row_text.append(f"{bin_stat.accuracy:.0%}")
                else:
                    row_values.append(-0.05)
                    row_hover.append(
                        f"Context: {ctx_len//1000}K<br>"
                        f"Depth: {depth_bin}<br>"
                        f"No data"
                    )
                    row_text.append("")  # No text for empty cells
            
            z_values.append(row_values)
            hover_texts.append(row_hover)
            text_annotations.append(row_text)
        
        depth_x_labels = [f"{ctx//1000}K" for ctx in depth_context_lengths]
        depth_y_labels = list(reversed(depth_labels))
        
        # Calculate column averages (mean of each context length across all depths)
        for col_idx in range(len(depth_context_lengths)):
            col_values = []
            for row_idx in range(len(depth_labels)):
                val = z_values[row_idx][col_idx]
                if val >= 0:  # Exclude no-data markers (-0.05)
                    col_values.append(val)
            if col_values:
                column_averages.append(sum(col_values) / len(col_values))
            else:
                column_averages.append(-0.05)  # No data marker
        
        # Custom colorscale for accuracy
        colorscale = [
            [0.0, '#6c757d'],
            [0.05, '#6c757d'],
            [0.051, '#dc3545'],
            [0.5, '#ffc107'],
            [1.0, '#28a745']
        ]
        
        fig.add_trace(
            go.Heatmap(
                z=z_values,
                x=depth_x_labels,
                y=depth_y_labels,
                colorscale=colorscale,
                zmin=-0.05,
                zmax=1.0,
                showscale=True,
                colorbar=dict(
                    title=dict(text='Accuracy', side='right'),
                    x=1.02,
                    y=0.5,
                    len=0.6,
                    yanchor='middle',
                    tickvals=[0, 0.25, 0.5, 0.75, 1.0],
                    ticktext=['0%', '25%', '50%', '75%', '100%']
                ),
                hovertemplate='%{text}<extra></extra>',
                text=hover_texts
            ),
            row=2, col=1
        )
        
        # Add text annotations for each cell in depth heatmap
        for i, depth_bin in enumerate(depth_y_labels):
            for j, ctx_label in enumerate(depth_x_labels):
                cell_text = text_annotations[i][j]
                if cell_text:  # Only add annotation if there's data
                    fig.add_annotation(
                        x=ctx_label,
                        y=depth_bin,
                        text=cell_text,
                        showarrow=False,
                        font=dict(color='white', size=12, family='Arial Black'),
                        xref='x2',
                        yref='y2'
                    )
    
    # === Bottom: Average accuracy heatmap (1D) ===
    if depth_bins and column_averages:
        avg_hover = [[
            f"Context: {ctx//1000}K<br>"
            f"Avg Accuracy: {avg:.2%}"
            if avg >= 0 else
            f"Context: {ctx//1000}K<br>"
            f"No data"
            for ctx, avg in zip(depth_context_lengths, column_averages)
        ]]
        
        # Text annotations for average row
        avg_text_annotations = [
            f"{avg:.0%}" if avg >= 0 else ""
            for avg in column_averages
        ]
        
        fig.add_trace(
            go.Heatmap(
                z=[column_averages],
                x=depth_x_labels,
                y=['Avg'],
                colorscale=colorscale,
                zmin=-0.05,
                zmax=1.0,
                showscale=False,  # Share colorbar with depth heatmap
                hovertemplate='%{text}<extra></extra>',
                text=avg_hover
            ),
            row=3, col=1
        )
        
        # Add text annotations for average heatmap
        for j, ctx_label in enumerate(depth_x_labels):
            cell_text = avg_text_annotations[j]
            if cell_text:
                fig.add_annotation(
                    x=ctx_label,
                    y='Avg',
                    text=cell_text,
                    showarrow=False,
                    font=dict(color='white', size=12, family='Arial Black'),
                    xref='x3',
                    yref='y3'
                )
    
    # Build subtitle with metadata
    subtitle_parts = []
    metadata = result_metadata or question_metadata
    if metadata:
        if metadata.model_name:
            subtitle_parts.append(f'Model: {metadata.model_name}')
        if metadata.question_set_path:
            dataset_name = metadata.question_set_path.split('/')[-1].replace('.jsonl', '')
            subtitle_parts.append(f'Dataset: {dataset_name}')
        elif metadata.novel_path:
            dataset_name = metadata.novel_path.split('/')[-1].replace('.txt', '')
            subtitle_parts.append(f'Dataset: {dataset_name}')
    
    if not subtitle_parts:
        subtitle_parts.append('Coverage and Depth-Aware Accuracy')
    
    subtitle_text = ' | '.join(subtitle_parts)
    title_text = f"<b>{PROJECT_TITLE}</b><br><span style='font-size:14px'>{subtitle_text}</span>"
    
    fig.update_layout(
        title={
            'text': title_text,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        autosize=True,
        margin=dict(l=80, r=120, t=120, b=80)
    )
    
    # Update axes
    fig.update_xaxes(title_text='Token Position', tickangle=45, row=1, col=1)
    fig.update_xaxes(title_text='', row=2, col=1)  # No title for middle
    fig.update_xaxes(title_text='Context Length', row=3, col=1)
    fig.update_yaxes(showticklabels=False, row=1, col=1)
    fig.update_yaxes(title_text='Evidence Depth', row=2, col=1)
    fig.update_yaxes(showticklabels=False, row=3, col=1)
    
    # Add branding (logo)
    _add_branding(fig, height=700, width=1200)
    
    return _to_fullscreen_html(fig, 'combined-depth-heatmap')
