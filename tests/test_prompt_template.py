"""
Tests for the PromptTemplateManager module.
"""

import json
import os
import tempfile
from pathlib import Path
import pytest

from src.core.prompt_template import PromptTemplateManager


class TestPromptTemplateManager:
    """Test cases for PromptTemplateManager."""
    
    def test_default_templates_loaded(self):
        """Test that default templates are loaded when no custom templates exist."""
        # Use a non-existent directory to ensure defaults are used
        manager = PromptTemplateManager(template_dir="nonexistent_dir/")
        
        assert manager.question_generation_template is not None
        assert manager.testing_template is not None
        
        # Verify template info
        info = manager.get_template_info()
        assert info["question_generation_template"]["loaded"] is True
        assert info["question_generation_template"]["is_default"] is True
        assert info["testing_template"]["loaded"] is True
        assert info["testing_template"]["is_default"] is True
    
    def test_get_question_generation_prompt(self):
        """Test getting formatted question generation prompt."""
        manager = PromptTemplateManager(template_dir="nonexistent_dir/")
        
        context = "这是一段测试文本。"
        question_type = "single_choice"
        
        system_prompt, user_prompt = manager.get_question_generation_prompt(
            context=context,
            question_type=question_type
        )
        
        assert isinstance(system_prompt, str)
        assert isinstance(user_prompt, str)
        assert context in user_prompt
        assert question_type in user_prompt
    
    def test_get_testing_prompt(self):
        """Test getting formatted testing prompt."""
        manager = PromptTemplateManager(template_dir="nonexistent_dir/")
        
        context = "这是一段测试文本。"
        question = "这是什么？"
        choices = {
            "a": "选项A",
            "b": "选项B",
            "c": "选项C",
            "d": "选项D"
        }
        
        system_prompt, user_prompt = manager.get_testing_prompt(
            context=context,
            question=question,
            choices=choices
        )
        
        assert isinstance(system_prompt, str)
        assert isinstance(user_prompt, str)
        assert context in user_prompt
        assert question in user_prompt
        assert "选项A" in user_prompt
        assert "选项B" in user_prompt
    
    def test_load_custom_template(self):
        """Test loading a custom template from file."""
        # Create a temporary custom template
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_template = {
                "system": "Custom system prompt",
                "user": "Custom user prompt with {context}",
                "constraints": ["Custom constraint"]
            }
            
            template_path = Path(tmpdir) / "custom.json"
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(custom_template, f)
            
            manager = PromptTemplateManager(template_dir="nonexistent_dir/")
            manager.load_custom_template(
                str(template_path),
                template_type="question_generation"
            )
            
            assert manager.question_generation_template == custom_template
    
    def test_template_validation_missing_field(self):
        """Test that validation fails for templates missing required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Template missing 'user' field
            invalid_template = {
                "system": "System prompt only"
            }
            
            template_path = Path(tmpdir) / "invalid.json"
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(invalid_template, f)
            
            manager = PromptTemplateManager(template_dir="nonexistent_dir/")
            
            with pytest.raises(ValueError, match="missing required field"):
                manager.load_custom_template(
                    str(template_path),
                    template_type="testing"
                )
    
    def test_template_validation_invalid_type(self):
        """Test that validation fails for invalid field types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Template with non-string system field
            invalid_template = {
                "system": ["Not a string"],
                "user": "User prompt"
            }
            
            template_path = Path(tmpdir) / "invalid.json"
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(invalid_template, f)
            
            manager = PromptTemplateManager(template_dir="nonexistent_dir/")
            
            with pytest.raises(ValueError, match="must be a string"):
                manager.load_custom_template(
                    str(template_path),
                    template_type="testing"
                )
    
    def test_load_from_prompts_directory(self):
        """Test loading templates from the default prompts directory."""
        # This test assumes the prompts/ directory exists with template files
        if Path("prompts/question_generation.json").exists():
            manager = PromptTemplateManager(template_dir="prompts/")
            
            assert manager.question_generation_template is not None
            assert manager.testing_template is not None
            
            # Should not be using defaults if files exist
            info = manager.get_template_info()
            assert info["question_generation_template"]["loaded"] is True
            assert info["testing_template"]["loaded"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
