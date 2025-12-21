"""Tokenizer wrapper using tiktoken for consistent tokenization."""

import re
from typing import List, Tuple
import tiktoken


class Tokenizer:
    """Wrapper for tiktoken encoder with boundary detection utilities."""
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """Initialize tiktoken encoder.
        
        Args:
            encoding_name: Name of the tiktoken encoding to use.
        """
        self.encoder = tiktoken.get_encoding(encoding_name)
    
    def encode(self, text: str) -> List[int]:
        """Convert text to token IDs.
        
        Args:
            text: Input text to tokenize.
            
        Returns:
            List of token IDs.
        """
        return self.encoder.encode(text)
    
    def decode(self, tokens: List[int]) -> str:
        """Convert token IDs to text.
        
        Args:
            tokens: List of token IDs.
            
        Returns:
            Decoded text string.
        """
        return self.encoder.decode(tokens)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text.
        
        Args:
            text: Input text.
            
        Returns:
            Number of tokens.
        """
        return len(self.encode(text))
    
    def find_sentence_boundary(self, text: str, target_pos: int, 
                              direction: str = "forward") -> int:
        """Find nearest sentence boundary from target position.
        
        Args:
            text: Text to search in.
            target_pos: Starting position to search from.
            direction: Search direction, "forward" or "backward".
            
        Returns:
            Position of nearest sentence boundary, or target_pos if none found.
        """
        # Sentence boundary pattern: punctuation followed by whitespace or newline
        sentence_pattern = r'[.!?][\s\n]'
        
        if direction == "forward":
            # Search forward from target_pos
            match = re.search(sentence_pattern, text[target_pos:])
            if match:
                return target_pos + match.end()
        else:
            # Search backward from target_pos
            text_before = text[:target_pos]
            matches = list(re.finditer(sentence_pattern, text_before))
            if matches:
                return matches[-1].end()
        
        return target_pos
    
    def find_paragraph_boundary(self, text: str, target_pos: int,
                               direction: str = "forward") -> int:
        """Find nearest paragraph boundary from target position.
        
        Args:
            text: Text to search in.
            target_pos: Starting position to search from.
            direction: Search direction, "forward" or "backward".
            
        Returns:
            Position of nearest paragraph boundary, or target_pos if none found.
        """
        # Paragraph boundary: double newlines
        paragraph_pattern = r'\n\n'
        
        if direction == "forward":
            match = re.search(paragraph_pattern, text[target_pos:])
            if match:
                return target_pos + match.end()
        else:
            text_before = text[:target_pos]
            matches = list(re.finditer(paragraph_pattern, text_before))
            if matches:
                return matches[-1].end()
        
        return target_pos
    
    def extract_context_with_alignment(self, text: str, center_pos: int,
                                      window_size: int, 
                                      max_boundary_search_tokens: int = 100) -> Tuple[str, int, int]:
        """Extract context window with boundary alignment.
        
        Args:
            text: Full text to extract from.
            center_pos: Center position (in characters) for extraction.
            window_size: Number of tokens to extract around center.
            max_boundary_search_tokens: Maximum tokens to search for boundary (default: 100).
            
        Returns:
            Tuple of (aligned_context, start_pos, end_pos) where positions are in characters.
        """
        # Encode full text to work with tokens
        tokens = self.encode(text)
        total_tokens = len(tokens)
        
        # Convert character position to approximate token position
        text_before_center = text[:center_pos]
        approx_token_pos = len(self.encode(text_before_center))
        
        # Calculate token window
        half_window = window_size // 2
        start_token = max(0, approx_token_pos - half_window)
        end_token = min(total_tokens, approx_token_pos + half_window)
        
        # Decode to get initial context
        context_tokens = tokens[start_token:end_token]
        initial_context = self.decode(context_tokens)
        
        # Find character positions in original text
        text_before_start = self.decode(tokens[:start_token])
        start_char_pos = len(text_before_start)
        end_char_pos = start_char_pos + len(initial_context)
        
        # Calculate max search distance in characters (approximate)
        # Estimate ~4 characters per token on average
        max_search_chars = max_boundary_search_tokens * 4
        
        # Try to align to sentence boundaries
        aligned_start = self._align_boundary(text, start_char_pos, "backward", max_search=max_search_chars)
        aligned_end = self._align_boundary(text, end_char_pos, "forward", max_search=max_search_chars)
        
        # Extract aligned context
        aligned_context = text[aligned_start:aligned_end]
        
        return aligned_context, aligned_start, aligned_end
    
    def extract_context_from_tokens(self, tokens: List[int], position: int,
                                   window_size: int,
                                   max_boundary_search_tokens: int = 100) -> Tuple[List[int], int, int]:
        """Extract context window from token list with boundary alignment.
        
        This method works directly with tokens and aligns boundaries by decoding
        and checking for sentence/paragraph boundaries.
        
        Args:
            tokens: Full token list.
            position: Center token position for extraction.
            window_size: Number of tokens to extract around center.
            max_boundary_search_tokens: Maximum tokens to search for boundary (default: 100).
            
        Returns:
            Tuple of (context_tokens, start_token_pos, end_token_pos).
        """
        total_tokens = len(tokens)
        
        # Calculate initial token window
        half_window = window_size // 2
        start_token = max(0, position - half_window)
        end_token = min(total_tokens, position + half_window)
        
        # Try to align start boundary
        aligned_start = self._align_token_boundary(
            tokens, start_token, "backward", max_boundary_search_tokens
        )
        
        # Try to align end boundary
        aligned_end = self._align_token_boundary(
            tokens, end_token, "forward", max_boundary_search_tokens
        )
        
        # Extract aligned context tokens
        context_tokens = tokens[aligned_start:aligned_end]
        
        return context_tokens, aligned_start, aligned_end
    
    def _align_token_boundary(self, tokens: List[int], pos: int, 
                             direction: str, max_search: int = 100) -> int:
        """Align token position to nearest sentence or paragraph boundary.
        
        Args:
            tokens: Full token list.
            pos: Token position to align.
            direction: Search direction, "forward" or "backward".
            max_search: Maximum tokens to search.
            
        Returns:
            Aligned token position.
        """
        if direction == "forward":
            search_end = min(len(tokens), pos + max_search)
            search_tokens = tokens[pos:search_end]
            
            # Decode and search for boundaries
            search_text = self.decode(search_tokens)
            
            # Try paragraph boundary first
            para_match = re.search(r'\n\n', search_text)
            if para_match:
                # Find token position corresponding to this character position
                text_before_boundary = search_text[:para_match.end()]
                boundary_tokens = len(self.encode(text_before_boundary))
                return pos + boundary_tokens
            
            # Try sentence boundary
            sent_match = re.search(r'[.!?][\s\n]', search_text)
            if sent_match:
                text_before_boundary = search_text[:sent_match.end()]
                boundary_tokens = len(self.encode(text_before_boundary))
                return pos + boundary_tokens
        else:
            search_start = max(0, pos - max_search)
            search_tokens = tokens[search_start:pos]
            
            # Decode and search for boundaries
            search_text = self.decode(search_tokens)
            
            # Try paragraph boundary
            para_matches = list(re.finditer(r'\n\n', search_text))
            if para_matches:
                last_match = para_matches[-1]
                text_before_boundary = search_text[:last_match.end()]
                boundary_tokens = len(self.encode(text_before_boundary))
                return search_start + boundary_tokens
            
            # Try sentence boundary
            sent_matches = list(re.finditer(r'[.!?][\s\n]', search_text))
            if sent_matches:
                last_match = sent_matches[-1]
                text_before_boundary = search_text[:last_match.end()]
                boundary_tokens = len(self.encode(text_before_boundary))
                return search_start + boundary_tokens
        
        # No boundary found within max_search, return original position (hard cutoff)
        return pos
    
    def _align_boundary(self, text: str, pos: int, direction: str, 
                       max_search: int = 100) -> int:
        """Align position to nearest sentence or paragraph boundary.
        
        Args:
            text: Text to search in.
            pos: Position to align.
            direction: Search direction.
            max_search: Maximum characters to search.
            
        Returns:
            Aligned position.
        """
        # Try paragraph boundary first
        if direction == "forward":
            search_text = text[pos:pos + max_search]
            para_match = re.search(r'\n\n', search_text)
            if para_match:
                return pos + para_match.end()
            
            # Try sentence boundary
            sent_match = re.search(r'[.!?][\s\n]', search_text)
            if sent_match:
                return pos + sent_match.end()
        else:
            search_start = max(0, pos - max_search)
            search_text = text[search_start:pos]
            
            # Try paragraph boundary
            para_matches = list(re.finditer(r'\n\n', search_text))
            if para_matches:
                return search_start + para_matches[-1].end()
            
            # Try sentence boundary
            sent_matches = list(re.finditer(r'[.!?][\s\n]', search_text))
            if sent_matches:
                return search_start + sent_matches[-1].end()
        
        # No boundary found, return original position (hard cutoff)
        return pos
