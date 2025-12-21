"""Report generator module."""

from .metrics import (
    calculate_accuracy,
    calculate_multi_choice_metrics,
    categorize_result,
    calculate_score,
    calculate_all_metrics
)

from .visualization import (
    create_scatter_plot
)

from .report_generator import (
    ReportGenerator
)

__all__ = [
    "calculate_accuracy",
    "calculate_multi_choice_metrics",
    "categorize_result",
    "calculate_score",
    "calculate_all_metrics",
    "create_scatter_plot",
    "ReportGenerator",
]
