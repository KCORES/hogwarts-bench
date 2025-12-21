"""
Depth scheduler for depth-aware testing.

This module provides the DepthScheduler class that assigns test depths
to questions based on different scheduling strategies.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class DepthMode(Enum):
    """Depth scheduling mode."""
    
    LEGACY = "legacy"
    """Legacy mode - no depth-aware testing, use original context."""
    
    UNIFORM = "uniform"
    """Uniform mode - distribute questions evenly across 5 depth bins."""
    
    FIXED = "fixed"
    """Fixed mode - all questions tested at a single fixed depth."""


@dataclass
class DepthAssignment:
    """Assignment of a question to a specific depth and context length."""
    
    question_index: int
    """Index of the question in the original list."""
    
    target_depth: float
    """Target depth for evidence placement (0.0-1.0)."""
    
    depth_bin: str
    """Depth bin label: "0%", "25%", "50%", "75%", "100%"."""
    
    context_length: int
    """Context length to use for this test."""


class DepthScheduler:
    """
    Schedules depth assignments for questions.
    
    Supports three modes:
    - LEGACY: No depth scheduling, questions tested with original context
    - UNIFORM: Questions distributed evenly across 5 depth bins (0%, 25%, 50%, 75%, 100%)
    - FIXED: All questions tested at a single fixed depth
    """
    
    DEPTH_BINS = [0.0, 0.25, 0.50, 0.75, 1.0]
    DEPTH_LABELS = ["0%", "25%", "50%", "75%", "100%"]
    
    def __init__(
        self,
        mode: DepthMode,
        fixed_depth: Optional[float] = None,
        context_lengths: Optional[List[int]] = None
    ):
        """
        Initialize the depth scheduler.
        
        Args:
            mode: Scheduling mode (LEGACY, UNIFORM, or FIXED)
            fixed_depth: Depth value for FIXED mode (0.0-1.0)
            context_lengths: List of context lengths to test
            
        Raises:
            ValueError: If FIXED mode without fixed_depth, or invalid fixed_depth
        """
        self.mode = mode
        self.fixed_depth = fixed_depth
        self.context_lengths = context_lengths or []
        
        # Validate FIXED mode
        if mode == DepthMode.FIXED:
            if fixed_depth is None:
                raise ValueError("FIXED mode requires fixed_depth parameter")
            if not 0.0 <= fixed_depth <= 1.0:
                raise ValueError(f"fixed_depth must be between 0.0 and 1.0, got {fixed_depth}")
        
        logger.debug(
            f"DepthScheduler initialized: mode={mode.value}, "
            f"fixed_depth={fixed_depth}, context_lengths={context_lengths}"
        )
    
    def schedule(
        self,
        questions: List[Dict[str, Any]]
    ) -> List[DepthAssignment]:
        """
        Schedule depth assignments for questions.
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            List of DepthAssignment objects
            
        Raises:
            ValueError: If mode is LEGACY (not supported for scheduling)
        """
        if self.mode == DepthMode.LEGACY:
            raise ValueError("LEGACY mode does not support depth scheduling")
        
        if not questions:
            return []
        
        if not self.context_lengths:
            raise ValueError("context_lengths must be provided for depth scheduling")
        
        if self.mode == DepthMode.UNIFORM:
            return self._schedule_uniform(questions, self.context_lengths)
        elif self.mode == DepthMode.FIXED:
            return self._schedule_fixed(questions, self.context_lengths)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
    
    def _schedule_uniform(
        self,
        questions: List[Dict[str, Any]],
        context_lengths: List[int]
    ) -> List[DepthAssignment]:
        """
        Distribute questions uniformly across depth bins and context lengths.
        
        Each question is assigned to one (depth_bin, context_length) combination.
        The distribution aims to have equal coverage across all combinations.
        
        Args:
            questions: List of question dictionaries
            context_lengths: List of context lengths
            
        Returns:
            List of DepthAssignment objects
        """
        assignments = []
        num_questions = len(questions)
        num_depths = len(self.DEPTH_BINS)
        num_lengths = len(context_lengths)
        
        # Total number of combinations
        total_combinations = num_depths * num_lengths
        
        for idx, question in enumerate(questions):
            # Cycle through combinations
            combo_idx = idx % total_combinations
            depth_idx = combo_idx % num_depths
            length_idx = combo_idx // num_depths
            
            target_depth = self.DEPTH_BINS[depth_idx]
            depth_bin = self.DEPTH_LABELS[depth_idx]
            context_length = context_lengths[length_idx % num_lengths]
            
            assignment = DepthAssignment(
                question_index=idx,
                target_depth=target_depth,
                depth_bin=depth_bin,
                context_length=context_length
            )
            assignments.append(assignment)
        
        # Log distribution summary
        self._log_distribution(assignments, context_lengths)
        
        return assignments
    
    def _schedule_fixed(
        self,
        questions: List[Dict[str, Any]],
        context_lengths: List[int]
    ) -> List[DepthAssignment]:
        """
        Assign all questions to a fixed depth, cycling through context lengths.
        
        Args:
            questions: List of question dictionaries
            context_lengths: List of context lengths
            
        Returns:
            List of DepthAssignment objects
        """
        assignments = []
        
        # Find the closest depth bin for the fixed depth
        depth_bin = self._get_depth_bin_label(self.fixed_depth)
        
        for idx, question in enumerate(questions):
            # Cycle through context lengths
            context_length = context_lengths[idx % len(context_lengths)]
            
            assignment = DepthAssignment(
                question_index=idx,
                target_depth=self.fixed_depth,
                depth_bin=depth_bin,
                context_length=context_length
            )
            assignments.append(assignment)
        
        logger.info(
            f"Fixed depth scheduling: {len(assignments)} questions at depth {self.fixed_depth} ({depth_bin})"
        )
        
        return assignments
    
    def _get_depth_bin_label(self, depth: float) -> str:
        """
        Get the depth bin label for a given depth value.
        
        Args:
            depth: Depth value (0.0-1.0)
            
        Returns:
            Closest depth bin label
        """
        # Find closest bin
        min_diff = float('inf')
        closest_label = self.DEPTH_LABELS[0]
        
        for bin_value, label in zip(self.DEPTH_BINS, self.DEPTH_LABELS):
            diff = abs(depth - bin_value)
            if diff < min_diff:
                min_diff = diff
                closest_label = label
        
        return closest_label
    
    def _log_distribution(
        self,
        assignments: List[DepthAssignment],
        context_lengths: List[int]
    ) -> None:
        """
        Log the distribution of assignments across depth bins and context lengths.
        
        Args:
            assignments: List of depth assignments
            context_lengths: List of context lengths
        """
        # Count by depth bin
        depth_counts = {label: 0 for label in self.DEPTH_LABELS}
        for a in assignments:
            depth_counts[a.depth_bin] += 1
        
        # Count by context length
        length_counts = {length: 0 for length in context_lengths}
        for a in assignments:
            if a.context_length in length_counts:
                length_counts[a.context_length] += 1
        
        logger.info(f"Uniform depth scheduling: {len(assignments)} total assignments")
        logger.info(f"  By depth: {depth_counts}")
        logger.info(f"  By context length: {length_counts}")
