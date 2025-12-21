"""Tests for QuestionGenerator class."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.generator.question_generator import QuestionGenerator
from src.core.llm_client import LLMClient
from src.core.tokenizer import Tokenizer
from src.core.validator import QuestionValidator
from src.core.prompt_template import PromptTemplateManager


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = Mock(spec=LLMClient)
    client.model_name = "test-model"
    client.temperature = 0.7
    client.max_tokens = 2000
    client.timeout = 60
    
    # Mock the generate method to return a valid question JSON
    async def mock_generate(prompt, system_prompt=None, max_retries=3):
        return json.dumps({
            "question": "What is the main character's name?",
            "question_type": "single_choice",
            "choice": {
                "a": "Harry Potter",
                "b": "Ron Weasley",
                "c": "Hermione Granger",
                "d": "Draco Malfoy"
            },
            "answer": ["a"]
        })
    
    client.generate = AsyncMock(side_effect=mock_generate)
    return client


@pytest.fixture
def question_generator(mock_llm_client):
    """Create a QuestionGenerator instance with mocked dependencies."""
    return QuestionGenerator(
        llm_client=mock_llm_client,
        tokenizer=Tokenizer(),
        prompt_manager=PromptTemplateManager(),
        validator=QuestionValidator()
    )


def test_question_generator_initialization(mock_llm_client):
    """Test QuestionGenerator initialization."""
    generator = QuestionGenerator(llm_client=mock_llm_client)
    
    assert generator.llm_client == mock_llm_client
    assert generator.tokenizer is not None
    assert generator.prompt_manager is not None
    assert generator.validator is not None


def test_sample_positions(question_generator):
    """Test position sampling."""
    positions = question_generator._sample_positions(
        total_tokens=10000,
        num_samples=10,
        strategy="random"
    )
    
    assert len(positions) == 10
    assert all(0 <= pos < 10000 for pos in positions)
    assert positions == sorted(positions)  # Should be sorted


def test_extract_context(question_generator):
    """Test context extraction."""
    # Create a simple token list
    test_text = "This is a test sentence. This is another sentence. And one more."
    tokens = question_generator.tokenizer.encode(test_text)
    
    context, start_pos, end_pos = question_generator._extract_context(
        tokens=tokens,
        position=len(tokens) // 2,
        window_size=10
    )
    
    assert isinstance(context, str)
    assert len(context) > 0
    assert isinstance(start_pos, int)
    assert isinstance(end_pos, int)
    assert start_pos < end_pos


def test_parse_question_response_direct_json(question_generator):
    """Test parsing direct JSON response."""
    response = json.dumps({
        "question": "Test question?",
        "question_type": "single_choice",
        "choice": {"a": "Option A", "b": "Option B"},
        "answer": ["a"]
    })
    
    result = question_generator._parse_question_response(response)
    
    assert result is not None
    assert result["question"] == "Test question?"
    assert result["question_type"] == "single_choice"


def test_parse_question_response_markdown(question_generator):
    """Test parsing JSON from markdown code block."""
    response = """Here is the question:
```json
{
    "question": "Test question?",
    "question_type": "single_choice",
    "choice": {"a": "Option A", "b": "Option B"},
    "answer": ["a"]
}
```
"""
    
    result = question_generator._parse_question_response(response)
    
    assert result is not None
    assert result["question"] == "Test question?"


def test_parse_question_response_invalid(question_generator):
    """Test parsing invalid response."""
    response = "This is not a valid JSON response"
    
    result = question_generator._parse_question_response(response)
    
    assert result is None


def test_generate_single_question(question_generator):
    """Test single question generation."""
    context = "Harry Potter was a young wizard who lived with his aunt and uncle."
    
    # Run async function in event loop
    question = asyncio.run(question_generator._generate_single_question(
        context=context,
        position=100,
        start_pos=50,
        end_pos=150,
        retry_times=3
    ))
    
    assert question is not None
    assert "question" in question
    assert "question_type" in question
    assert "choice" in question
    assert "answer" in question
    assert "position" in question
    assert question["position"]["start_pos"] == 50
    assert question["position"]["end_pos"] == 150


def test_generate_single_question_with_retry(mock_llm_client):
    """Test single question generation with retry on validation failure."""
    # First call returns invalid JSON, second call returns valid
    call_count = 0
    
    async def mock_generate_with_retry(prompt, system_prompt=None, max_retries=3):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            return "Invalid response"
        else:
            return json.dumps({
                "question": "What is the main character's name?",
                "question_type": "single_choice",
                "choice": {
                    "a": "Harry Potter",
                    "b": "Ron Weasley",
                    "c": "Hermione Granger",
                    "d": "Draco Malfoy"
                },
                "answer": ["a"]
            })
    
    mock_llm_client.generate = AsyncMock(side_effect=mock_generate_with_retry)
    
    generator = QuestionGenerator(llm_client=mock_llm_client)
    
    question = asyncio.run(generator._generate_single_question(
        context="Test context",
        position=100,
        start_pos=50,
        end_pos=150,
        retry_times=3
    ))
    
    assert question is not None
    assert call_count == 2  # Should have retried once


def test_generate_single_question_all_retries_fail(mock_llm_client):
    """Test single question generation when all retries fail."""
    # Always return invalid response
    async def mock_generate_fail(prompt, system_prompt=None, max_retries=3):
        return "Invalid response"
    
    mock_llm_client.generate = AsyncMock(side_effect=mock_generate_fail)
    
    generator = QuestionGenerator(llm_client=mock_llm_client)
    
    question = asyncio.run(generator._generate_single_question(
        context="Test context",
        position=100,
        start_pos=50,
        end_pos=150,
        retry_times=2
    ))
    
    assert question is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
