"""
Context builder for depth-aware testing.

This module provides the ContextBuilder class that dynamically constructs
test contexts with evidence placed at specified depth positions.
"""

import logging
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..core.tokenizer import Tokenizer


logger = logging.getLogger(__name__)


@dataclass
class ContextBuildResult:
    """Result of context building operation."""
    
    context: str
    """The constructed context text."""
    
    actual_depth: float
    """Actual depth of evidence in context (0.0-1.0)."""
    
    evidence_start: int
    """Start position of evidence in context (in tokens)."""
    
    evidence_end: int
    """End position of evidence in context (in tokens)."""
    
    prefix_length: int
    """Length of prefix filler (in tokens)."""
    
    suffix_length: int
    """Length of suffix filler (in tokens)."""
    
    evidence_length: int
    """Length of evidence segment (in tokens)."""
    
    total_length: int
    """Total context length (in tokens)."""
    
    success: bool
    """Whether the build was successful."""
    
    error_message: Optional[str] = None
    """Error message if build failed."""


class ContextBuilder:
    """
    Builds test contexts with evidence at specified depth positions.
    
    The context is constructed as: [prefix_filler] + [evidence] + [suffix_filler]
    where the prefix length determines the depth of the evidence.
    
    Depth 0.0 = evidence at the beginning
    Depth 0.5 = evidence in the middle
    Depth 1.0 = evidence at the end
    """
    
    def __init__(self, tokenizer: Tokenizer, novel_tokens: List[int]):
        """
        Initialize the context builder.
        
        Args:
            tokenizer: Tokenizer instance for encoding/decoding
            novel_tokens: Complete novel as a list of tokens
        """
        self.tokenizer = tokenizer
        self.novel_tokens = novel_tokens
        self.novel_length = len(novel_tokens)
        
        logger.debug(f"ContextBuilder initialized with {self.novel_length} tokens")

    def build_context(
        self,
        question: Dict[str, Any],
        target_depth: float,
        context_length: int,
        padding_size: int = 500
    ) -> ContextBuildResult:
        """
        Build a context with evidence at the specified depth.
        
        Args:
            question: Question dictionary containing 'position' with start_pos and end_pos
            target_depth: Target depth for evidence (0.0=start, 0.5=middle, 1.0=end)
            context_length: Desired total context length in tokens
            padding_size: Extra padding around evidence to ensure completeness
            
        Returns:
            ContextBuildResult with the constructed context or error information
        """
        # Validate inputs
        if not 0.0 <= target_depth <= 1.0:
            return ContextBuildResult(
                context="",
                actual_depth=0.0,
                evidence_start=0,
                evidence_end=0,
                prefix_length=0,
                suffix_length=0,
                evidence_length=0,
                total_length=0,
                success=False,
                error_message=f"Invalid target_depth: {target_depth}, must be between 0.0 and 1.0"
            )
        
        # Extract position information
        position = question.get("position", {})
        start_pos = position.get("start_pos")
        end_pos = position.get("end_pos")
        
        if start_pos is None or end_pos is None:
            return ContextBuildResult(
                context="",
                actual_depth=0.0,
                evidence_start=0,
                evidence_end=0,
                prefix_length=0,
                suffix_length=0,
                evidence_length=0,
                total_length=0,
                success=False,
                error_message="Question missing position.start_pos or position.end_pos"
            )
        
        # Extract evidence with padding
        evidence_tokens, actual_start, actual_end = self._extract_evidence(
            start_pos, end_pos, padding_size
        )
        evidence_length = len(evidence_tokens)
        
        # Check if evidence fits in context
        if evidence_length >= context_length:
            return ContextBuildResult(
                context="",
                actual_depth=0.0,
                evidence_start=0,
                evidence_end=0,
                prefix_length=0,
                suffix_length=0,
                evidence_length=evidence_length,
                total_length=0,
                success=False,
                error_message=f"Evidence length ({evidence_length}) exceeds context length ({context_length})"
            )
        
        # Calculate filler lengths based on target depth
        available_filler = context_length - evidence_length
        prefix_length = int(available_filler * target_depth)
        suffix_length = available_filler - prefix_length
        
        # Get filler tokens (excluding evidence region)
        prefix_tokens = self._get_filler_tokens(prefix_length, actual_start, actual_end, position="before")
        suffix_tokens = self._get_filler_tokens(suffix_length, actual_start, actual_end, position="after")
        
        # Assemble context
        context_tokens = prefix_tokens + evidence_tokens + suffix_tokens
        context = self.tokenizer.decode(context_tokens)
        
        # Calculate actual depth
        actual_prefix_len = len(prefix_tokens)
        actual_total_len = len(context_tokens)
        actual_depth = actual_prefix_len / actual_total_len if actual_total_len > 0 else 0.0
        
        return ContextBuildResult(
            context=context,
            actual_depth=actual_depth,
            evidence_start=actual_prefix_len,
            evidence_end=actual_prefix_len + len(evidence_tokens),
            prefix_length=actual_prefix_len,
            suffix_length=len(suffix_tokens),
            evidence_length=len(evidence_tokens),
            total_length=actual_total_len,
            success=True,
            error_message=None
        )

    def _extract_evidence(
        self,
        start_pos: int,
        end_pos: int,
        padding: int
    ) -> Tuple[List[int], int, int]:
        """
        Extract evidence tokens with padding.
        
        Args:
            start_pos: Start position in tokens
            end_pos: End position in tokens
            padding: Extra tokens to include before and after
            
        Returns:
            Tuple of (evidence_tokens, actual_start, actual_end)
        """
        # Apply padding and clamp to valid range
        actual_start = max(0, start_pos - padding)
        actual_end = min(self.novel_length, end_pos + padding)
        
        evidence_tokens = self.novel_tokens[actual_start:actual_end]
        
        return evidence_tokens, actual_start, actual_end
    
    def _get_filler_tokens(
        self,
        length: int,
        exclude_start: int,
        exclude_end: int,
        position: str = "before"
    ) -> List[int]:
        """
        Get filler tokens from the novel, excluding the evidence region.
        
        Args:
            length: Number of tokens needed
            exclude_start: Start of region to exclude
            exclude_end: End of region to exclude
            position: "before" to prefer text before evidence, "after" for after
            
        Returns:
            List of filler tokens
        """
        if length <= 0:
            return []
        
        # Calculate available regions
        before_region = (0, exclude_start)
        after_region = (exclude_end, self.novel_length)
        
        before_available = before_region[1] - before_region[0]
        after_available = after_region[1] - after_region[0]
        
        filler_tokens = []
        
        if position == "before":
            # Prefer taking from before the evidence
            if before_available >= length:
                # Take from the end of the before region (closest to evidence)
                start = exclude_start - length
                filler_tokens = self.novel_tokens[start:exclude_start]
            elif before_available > 0:
                # Take all available before, then fill from after
                filler_tokens = self.novel_tokens[0:exclude_start]
                remaining = length - before_available
                if after_available >= remaining:
                    filler_tokens = self.novel_tokens[exclude_end:exclude_end + remaining] + filler_tokens
                elif after_available > 0:
                    filler_tokens = self.novel_tokens[exclude_end:self.novel_length] + filler_tokens
            elif after_available >= length:
                # No before region, take from after
                filler_tokens = self.novel_tokens[exclude_end:exclude_end + length]
            elif after_available > 0:
                filler_tokens = self.novel_tokens[exclude_end:self.novel_length]
        else:  # position == "after"
            # Prefer taking from after the evidence
            if after_available >= length:
                # Take from the start of the after region (closest to evidence)
                filler_tokens = self.novel_tokens[exclude_end:exclude_end + length]
            elif after_available > 0:
                # Take all available after, then fill from before
                filler_tokens = self.novel_tokens[exclude_end:self.novel_length]
                remaining = length - after_available
                if before_available >= remaining:
                    start = exclude_start - remaining
                    filler_tokens = filler_tokens + self.novel_tokens[start:exclude_start]
                elif before_available > 0:
                    filler_tokens = filler_tokens + self.novel_tokens[0:exclude_start]
            elif before_available >= length:
                # No after region, take from before
                start = exclude_start - length
                filler_tokens = self.novel_tokens[max(0, start):exclude_start]
            elif before_available > 0:
                filler_tokens = self.novel_tokens[0:exclude_start]
        
        # Log warning if we couldn't get enough filler
        if len(filler_tokens) < length:
            logger.warning(
                f"Could only get {len(filler_tokens)} filler tokens, "
                f"requested {length}"
            )
        
        return filler_tokens
