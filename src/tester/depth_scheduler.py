"""
Depth scheduler for depth-aware testing.

This module provides the DepthScheduler class that assigns test depths
to questions based on different scheduling strategies.
"""

import logging
import random
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


def sample_questions_by_depth(
    questions: List[Dict[str, Any]],
    max_questions: int,
    novel_length: int
) -> List[Dict[str, Any]]:
    """
    Sample questions uniformly across depth bins.
    
    This function groups questions by their depth (based on position.end_pos
    relative to novel_length) and samples uniformly from each depth bin
    to ensure balanced coverage across different depths.
    
    Depth bins are: 0-20%, 20-40%, 40-60%, 60-80%, 80-100%
    
    Args:
        questions: List of question dictionaries with position information
        max_questions: Maximum number of questions to sample
        novel_length: Total length of novel in tokens (for depth calculation)
        
    Returns:
        Sampled list of questions with balanced depth distribution
    """
    if not questions or max_questions <= 0:
        return []
    
    if max_questions >= len(questions):
        return questions
    
    # Define depth bins (5 bins: 0-20%, 20-40%, 40-60%, 60-80%, 80-100%)
    num_bins = 5
    bin_boundaries = [i / num_bins for i in range(num_bins + 1)]
    
    # Group questions by depth bin
    depth_bins: List[List[Dict[str, Any]]] = [[] for _ in range(num_bins)]
    
    for question in questions:
        position = question.get("position", {})
        end_pos = position.get("end_pos", 0)
        
        # Calculate depth as ratio of end_pos to novel_length
        if novel_length > 0:
            depth = end_pos / novel_length
        else:
            depth = 0.0
        
        # Clamp depth to [0, 1]
        depth = max(0.0, min(1.0, depth))
        
        # Find the appropriate bin
        bin_idx = min(int(depth * num_bins), num_bins - 1)
        depth_bins[bin_idx].append(question)
    
    # Log bin distribution before sampling
    bin_labels = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
    logger.info(f"Question distribution by depth before sampling:")
    for i, (label, bin_questions) in enumerate(zip(bin_labels, depth_bins)):
        logger.info(f"  {label}: {len(bin_questions)} questions")
    
    # Calculate samples per bin
    # Try to distribute evenly, but handle bins with fewer questions
    samples_per_bin = max_questions // num_bins
    remaining_samples = max_questions % num_bins
    
    sampled_questions = []
    extra_needed = 0
    
    # First pass: sample from each bin
    for i, bin_questions in enumerate(depth_bins):
        target_samples = samples_per_bin
        if i < remaining_samples:
            target_samples += 1
        
        if len(bin_questions) <= target_samples:
            # Take all questions from this bin
            sampled_questions.extend(bin_questions)
            extra_needed += target_samples - len(bin_questions)
        else:
            # Random sample from this bin
            sampled = random.sample(bin_questions, target_samples)
            sampled_questions.extend(sampled)
    
    # Second pass: if some bins had fewer questions, sample extra from other bins
    if extra_needed > 0:
        # Collect remaining questions not yet sampled
        sampled_set = set(id(q) for q in sampled_questions)
        remaining_questions = [
            q for q in questions if id(q) not in sampled_set
        ]
        
        if remaining_questions:
            extra_samples = min(extra_needed, len(remaining_questions))
            extra = random.sample(remaining_questions, extra_samples)
            sampled_questions.extend(extra)
    
    # Log final distribution
    logger.info(f"Sampled {len(sampled_questions)} questions from {len(questions)} total")
    
    # Recalculate distribution after sampling
    final_bins = [0] * num_bins
    for question in sampled_questions:
        position = question.get("position", {})
        end_pos = position.get("end_pos", 0)
        if novel_length > 0:
            depth = end_pos / novel_length
        else:
            depth = 0.0
        depth = max(0.0, min(1.0, depth))
        bin_idx = min(int(depth * num_bins), num_bins - 1)
        final_bins[bin_idx] += 1
    
    logger.info(f"Question distribution by depth after sampling:")
    for label, count in zip(bin_labels, final_bins):
        logger.info(f"  {label}: {count} questions")
    
    return sampled_questions
