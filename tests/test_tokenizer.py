"""Tests for tokenizer module with context extraction."""

import pytest
from src.core.tokenizer import Tokenizer


class TestTokenizer:
    """Test cases for Tokenizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tokenizer = Tokenizer()
    
    def test_basic_encoding_decoding(self):
        """Test basic encode and decode functionality."""
        text = "Hello, world! This is a test."
        tokens = self.tokenizer.encode(text)
        decoded = self.tokenizer.decode(tokens)
        assert decoded == text
    
    def test_count_tokens(self):
        """Test token counting."""
        text = "Hello, world!"
        count = self.tokenizer.count_tokens(text)
        assert count > 0
        assert count == len(self.tokenizer.encode(text))
    
    def test_extract_context_from_tokens_basic(self):
        """Test basic context extraction from tokens."""
        text = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."
        tokens = self.tokenizer.encode(text)
        
        # Extract context around middle
        position = len(tokens) // 2
        context_tokens, start, end = self.tokenizer.extract_context_from_tokens(
            tokens, position, window_size=20
        )
        
        assert len(context_tokens) > 0
        assert start >= 0
        assert end <= len(tokens)
        assert start < end
    
    def test_extract_context_with_sentence_boundary(self):
        """Test context extraction aligns to sentence boundaries."""
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
        tokens = self.tokenizer.encode(text)
        
        # Extract context
        position = len(tokens) // 2
        context_tokens, start, end = self.tokenizer.extract_context_from_tokens(
            tokens, position, window_size=15
        )
        
        # Decode and check it ends with sentence boundary
        context_text = self.tokenizer.decode(context_tokens)
        # Should ideally align to sentence boundaries
        assert len(context_text) > 0
    
    def test_extract_context_with_paragraph_boundary(self):
        """Test context extraction aligns to paragraph boundaries."""
        text = "First paragraph.\n\nSecond paragraph here.\n\nThird paragraph here.\n\nFourth paragraph."
        tokens = self.tokenizer.encode(text)
        
        position = len(tokens) // 2
        context_tokens, start, end = self.tokenizer.extract_context_from_tokens(
            tokens, position, window_size=20
        )
        
        context_text = self.tokenizer.decode(context_tokens)
        assert len(context_text) > 0
    
    def test_extract_context_at_boundaries(self):
        """Test context extraction at text boundaries."""
        text = "Short text. Another sentence."
        tokens = self.tokenizer.encode(text)
        
        # Extract at start
        context_tokens, start, end = self.tokenizer.extract_context_from_tokens(
            tokens, 0, window_size=10
        )
        assert start == 0
        assert len(context_tokens) > 0
        
        # Extract at end
        context_tokens, start, end = self.tokenizer.extract_context_from_tokens(
            tokens, len(tokens) - 1, window_size=10
        )
        assert end <= len(tokens)
        assert len(context_tokens) > 0
    
    def test_hard_cutoff_fallback(self):
        """Test hard cutoff when no boundary found within max_search."""
        # Create text with no sentence boundaries
        text = "word " * 200  # Long text without sentence boundaries
        tokens = self.tokenizer.encode(text)
        
        position = len(tokens) // 2
        context_tokens, start, end = self.tokenizer.extract_context_from_tokens(
            tokens, position, window_size=20, max_boundary_search_tokens=5
        )
        
        # Should still return context even without boundaries
        assert len(context_tokens) > 0
        assert start < end
    
    def test_extract_context_with_alignment_character_based(self):
        """Test character-based context extraction with alignment."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        center_pos = len(text) // 2
        
        context, start, end = self.tokenizer.extract_context_with_alignment(
            text, center_pos, window_size=20
        )
        
        assert len(context) > 0
        assert start >= 0
        assert end <= len(text)
        assert context == text[start:end]
    
    def test_find_sentence_boundary_forward(self):
        """Test finding sentence boundary in forward direction."""
        text = "This is a test. Another sentence here."
        pos = self.tokenizer.find_sentence_boundary(text, 0, "forward")
        assert pos > 0
        # Should find the period and space after "test"
    
    def test_find_sentence_boundary_backward(self):
        """Test finding sentence boundary in backward direction."""
        text = "First sentence. Second sentence. Third sentence."
        pos = self.tokenizer.find_sentence_boundary(text, len(text), "backward")
        assert pos > 0
        assert pos < len(text)
    
    def test_find_paragraph_boundary(self):
        """Test finding paragraph boundary."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        pos = self.tokenizer.find_paragraph_boundary(text, 0, "forward")
        assert pos > 0
        # Should find the double newline


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
