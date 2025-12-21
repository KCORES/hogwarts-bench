"""
Evidence matcher for validating that quoted evidence exists in source context.

This module provides fuzzy matching capabilities to verify that LLM-provided
evidence citations actually exist in the original context text.
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Tuple, Optional


class EvidenceMatcher:
    """
    Matches evidence text against source context with fuzzy matching support.
    
    Handles minor differences in whitespace, punctuation, and formatting
    while still requiring substantial textual overlap.
    """
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize the evidence matcher.
        
        Args:
            similarity_threshold: Minimum similarity score (0.0-1.0) for a match.
                                  Default is 0.8 (80% similarity).
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        self.similarity_threshold = similarity_threshold
    
    def find_evidence(
        self,
        evidence: str,
        context: str
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Find evidence text within the context.
        
        Attempts multiple matching strategies:
        1. Exact substring match (after normalization)
        2. Sliding window similarity match
        
        Args:
            evidence: The evidence text to find (from LLM response)
            context: The source context to search in
            
        Returns:
            Tuple of (found, similarity_score, matched_text):
            - found: Whether evidence was found above threshold
            - similarity_score: Best similarity score found (0.0-1.0)
            - matched_text: The matching text from context, or None if not found
        """
        if not evidence or not evidence.strip():
            return False, 0.0, None
        
        if not context or not context.strip():
            return False, 0.0, None
        
        # Normalize both texts
        norm_evidence = self._normalize_text(evidence)
        norm_context = self._normalize_text(context)
        
        # Strategy 1: Exact substring match
        if norm_evidence in norm_context:
            # Find the original text that matches
            matched = self._find_original_match(evidence, context)
            return True, 1.0, matched
        
        # Strategy 2: Sliding window similarity match
        best_score = 0.0
        best_match = None
        
        # Use sliding window with size based on evidence length
        window_size = len(norm_evidence)
        
        # Allow some flexibility in window size (±20%)
        min_window = max(10, int(window_size * 0.8))
        max_window = int(window_size * 1.2)
        
        for ws in range(min_window, max_window + 1):
            for i in range(len(norm_context) - ws + 1):
                window = norm_context[i:i + ws]
                score = self._calculate_similarity(norm_evidence, window)
                
                if score > best_score:
                    best_score = score
                    # Get corresponding original text
                    best_match = self._extract_original_window(context, i, ws)
        
        found = best_score >= self.similarity_threshold
        return found, best_score, best_match if found else None
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.
        
        Normalizations applied:
        - Unicode normalization (NFKC)
        - Lowercase conversion
        - Collapse multiple whitespace to single space
        - Remove leading/trailing whitespace
        - Normalize common punctuation variants
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text string
        """
        # Unicode normalization
        text = unicodedata.normalize('NFKC', text)
        
        # Lowercase
        text = text.lower()
        
        # Normalize whitespace (collapse multiple spaces, newlines, tabs)
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize common punctuation variants
        # Chinese/Japanese punctuation to standard
        punctuation_map = {
            '，': ',',
            '。': '.',
            '！': '!',
            '？': '?',
            '：': ':',
            '；': ';',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '【': '[',
            '】': ']',
            '（': '(',
            '）': ')',
        }
        for orig, repl in punctuation_map.items():
            text = text.replace(orig, repl)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.
        
        Uses SequenceMatcher ratio which gives a value between 0.0 and 1.0.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _find_original_match(self, evidence: str, context: str) -> str:
        """
        Find the original (non-normalized) text that matches the evidence.
        
        Args:
            evidence: Evidence text to find
            context: Source context
            
        Returns:
            The matching portion of the original context
        """
        norm_evidence = self._normalize_text(evidence)
        norm_context = self._normalize_text(context)
        
        # Find position in normalized context
        pos = norm_context.find(norm_evidence)
        if pos == -1:
            return evidence  # Fallback to evidence itself
        
        # Map back to original context (approximate)
        # This is a simplified approach - for exact mapping we'd need
        # character-by-character tracking during normalization
        return context[pos:pos + len(evidence)]
    
    def _extract_original_window(
        self,
        context: str,
        norm_start: int,
        norm_length: int
    ) -> str:
        """
        Extract a window from the original context based on normalized positions.
        
        This is an approximation since normalization changes string length.
        
        Args:
            context: Original context text
            norm_start: Start position in normalized text
            norm_length: Length in normalized text
            
        Returns:
            Approximate matching window from original context
        """
        # Simple approximation: use same positions
        # This works reasonably well when normalization doesn't change length much
        end = min(norm_start + norm_length, len(context))
        start = max(0, norm_start)
        return context[start:end]
