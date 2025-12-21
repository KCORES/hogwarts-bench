"""
Prompt template management module for hogwarts-bench.

This module provides the PromptTemplateManager class for loading and managing
prompt templates used in question generation and testing.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class PromptTemplateManager:
    """
    Manages prompt templates for question generation and testing.
    
    Supports loading templates from JSON files with validation and fallback
    to default templates if custom templates are not provided.
    """
    
    # Default question generation prompt template
    # Note: Use {{ and }} to escape braces in format strings
    DEFAULT_QUESTION_GENERATION_TEMPLATE = {
        "system": (
            "你是一位专业的测试题目设计专家，擅长根据文本内容创建高质量的测试问题。"
            "你需要根据提供的上下文生成结构化的测试题目。"
        ),
        "user": (
            "请基于以下文本内容生成一个测试题目：\n\n"
            "{context}\n\n"
            "要求：\n"
            "1. 生成一个{question_type}类型的问题\n"
            "2. 问题应该测试对文本细节的理解和记忆\n"
            "3. 对于单选题(single_choice)，提供4个选项，其中1个正确答案和3个干扰项\n"
            "4. 对于多选题(multiple_choice)，提供4个选项，其中至少2个正确答案和至少2个干扰项\n"
            "5. 干扰项应该具有迷惑性，但不能是正确答案\n"
            "6. 必须以JSON格式输出，格式如下：\n"
            '{{{{\n'
            '  "question": "问题文本",\n'
            '  "question_type": "single_choice或multiple_choice",\n'
            '  "choice": {{{{\n'
            '    "a": "选项A",\n'
            '    "b": "选项B",\n'
            '    "c": "选项C",\n'
            '    "d": "选项D"\n'
            '  }}}},\n'
            '  "answer": ["a"]\n'
            '}}}}\n\n'
            "请直接输出JSON，不要添加任何其他说明文字。"
        ),
        "constraints": [
            "输出必须是有效的JSON格式",
            "多选题必须包含至少2个干扰选项",
            "答案必须是choice中的有效选项"
        ]
    }
    
    # Default testing prompt template
    # Note: Use {{ and }} to escape braces in format strings
    DEFAULT_TESTING_TEMPLATE = {
        "system": (
            "你是一位专业的阅读理解专家。请仔细阅读提供的文本内容，"
            "并根据文本内容准确回答问题。你的回答必须基于文本内容，不要编造信息。"
        ),
        "user": (
            "请阅读以下文本：\n\n"
            "{context}\n\n"
            "---\n\n"
            "问题：{question}\n\n"
            "选项：\n"
            "{choices}\n\n"
            "请根据文本内容选择正确答案。\n"
            "要求：\n"
            "1. 仔细阅读文本，确保答案准确\n"
            "2. 对于单选题，选择一个最符合文本内容的选项\n"
            "3. 对于多选题，选择所有符合文本内容的选项\n"
            "4. 必须以JSON格式输出答案，格式如下：\n"
            '{{{{"answer": ["a"]}}}}  // 单选题示例\n'
            '{{{{"answer": ["a", "c"]}}}}  // 多选题示例\n\n'
            "请直接输出JSON格式的答案，不要添加任何其他说明文字。"
        ),
        "constraints": [
            "输出必须是有效的JSON格式",
            "answer字段必须是数组类型",
            "答案必须基于文本内容，不能编造"
        ]
    }
    
    # Default validation prompt template
    # Note: Use {{ and }} to escape braces in format strings
    DEFAULT_VALIDATION_TEMPLATE = {
        "system": (
            "你是一位严格的问题质量审核专家。你的任务是验证测试问题的准确性，"
            "确保问题可以仅从给定的上下文中回答，且答案有原文依据支撑。\n\n"
            "重要规则：\n"
            "1. 只能使用给定的上下文内容来回答问题，不要使用任何外部知识\n"
            "2. 必须提供支持答案的原文引用（精确引用原文片段）\n"
            "3. 如果原文中找不到明确依据，必须标记为不可回答"
        ),
        "user": (
            "请根据以下上下文验证这道测试题目：\n\n"
            "【上下文】\n{context}\n\n"
            "【问题】\n{question}\n\n"
            "【选项】\n{choices}\n\n"
            "请完成以下任务：\n"
            "1. 仅根据上下文内容，独立回答这道题目\n"
            "2. 引用支持你答案的原文片段（必须是原文的精确引用）\n"
            "3. 判断这道题是否可以仅从上下文回答\n"
            "4. 给出你的置信度评级\n\n"
            "必须以JSON格式输出，格式如下：\n"
            '{{{{\n'
            '  "answer": ["a"],\n'
            '  "evidence": "原文引用片段...",\n'
            '  "is_answerable": true,\n'
            '  "confidence": "high",\n'
            '  "reasoning": "简要说明你的推理过程"\n'
            '}}}}\n\n'
            "字段说明：\n"
            "- answer: 你的答案，格式为选项字母列表，如 [\"a\"] 或 [\"a\", \"c\"]\n"
            "- evidence: 支持答案的原文精确引用（必须是上下文中的原文）\n"
            "- is_answerable: 是否可以仅从上下文回答（true/false）\n"
            "- confidence: 置信度评级（high/medium/low）\n"
            "- reasoning: 简要说明推理过程\n\n"
            "请直接输出JSON，不要添加任何其他说明文字。"
        ),
        "constraints": [
            "输出必须是有效的JSON格式",
            "answer必须是选项中的有效字母",
            "evidence必须是上下文中的原文引用",
            "confidence只能是high、medium或low",
            "不能使用上下文以外的知识"
        ]
    }
    
    def __init__(self, template_dir: str = "prompts/"):
        """
        Initialize the PromptTemplateManager.
        
        Args:
            template_dir: Directory containing template JSON files.
                         Defaults to "prompts/" in the project root.
        """
        self.template_dir = Path(template_dir)
        self.question_generation_template = None
        self.testing_template = None
        self.validation_template = None
        
        # Try to load custom templates if they exist
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from the template directory."""
        # Load question generation template
        question_gen_path = self.template_dir / "question_generation.json"
        if question_gen_path.exists():
            try:
                self.question_generation_template = self._load_template_file(
                    question_gen_path
                )
            except Exception as e:
                print(f"Warning: Failed to load question generation template: {e}")
                print("Using default template instead.")
                self.question_generation_template = self.DEFAULT_QUESTION_GENERATION_TEMPLATE
        else:
            self.question_generation_template = self.DEFAULT_QUESTION_GENERATION_TEMPLATE
        
        # Load testing template
        testing_path = self.template_dir / "testing.json"
        if testing_path.exists():
            try:
                self.testing_template = self._load_template_file(testing_path)
            except Exception as e:
                print(f"Warning: Failed to load testing template: {e}")
                print("Using default template instead.")
                self.testing_template = self.DEFAULT_TESTING_TEMPLATE
        else:
            self.testing_template = self.DEFAULT_TESTING_TEMPLATE
        
        # Load validation template
        validation_path = self.template_dir / "validation.json"
        if validation_path.exists():
            try:
                self.validation_template = self._load_template_file(validation_path)
            except Exception as e:
                print(f"Warning: Failed to load validation template: {e}")
                print("Using default template instead.")
                self.validation_template = self.DEFAULT_VALIDATION_TEMPLATE
        else:
            self.validation_template = self.DEFAULT_VALIDATION_TEMPLATE
    
    def _load_template_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load and validate a template from a JSON file.
        
        Args:
            file_path: Path to the template JSON file.
            
        Returns:
            Dictionary containing the template data.
            
        Raises:
            ValueError: If the template structure is invalid.
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        
        # Validate template structure
        self._validate_template(template)
        
        return template
    
    def _validate_template(self, template: Dict[str, Any]):
        """
        Validate the structure of a template.
        
        Args:
            template: Template dictionary to validate.
            
        Raises:
            ValueError: If the template structure is invalid.
        """
        required_fields = ["system", "user"]
        
        for field in required_fields:
            if field not in template:
                raise ValueError(
                    f"Template missing required field: {field}. "
                    f"Required fields: {required_fields}"
                )
            
            if not isinstance(template[field], str):
                raise ValueError(
                    f"Template field '{field}' must be a string, "
                    f"got {type(template[field]).__name__}"
                )
        
        # Validate constraints field if present
        if "constraints" in template:
            if not isinstance(template["constraints"], list):
                raise ValueError(
                    "Template field 'constraints' must be a list of strings"
                )
            for constraint in template["constraints"]:
                if not isinstance(constraint, str):
                    raise ValueError(
                        "All constraints must be strings"
                    )
    
    def get_question_generation_prompt(
        self,
        context: str,
        question_type: str = "single_choice"
    ) -> tuple[str, str]:
        """
        Get the formatted prompt for question generation.
        
        Args:
            context: The text context to generate questions from.
            question_type: Type of question to generate 
                          ("single_choice" or "multiple_choice").
                          Defaults to "single_choice".
        
        Returns:
            Tuple of (system_prompt, user_prompt) with placeholders filled.
        """
        template = self.question_generation_template
        
        system_prompt = template["system"]
        user_prompt = template["user"].format(
            context=context,
            question_type=question_type
        )
        
        return system_prompt, user_prompt
    
    def get_testing_prompt(
        self,
        context: str,
        question: str,
        choices: Dict[str, str]
    ) -> tuple[str, str]:
        """
        Get the formatted prompt for testing.
        
        Args:
            context: The text context for answering the question.
            question: The question text.
            choices: Dictionary of answer choices (e.g., {"a": "...", "b": "..."}).
        
        Returns:
            Tuple of (system_prompt, user_prompt) with placeholders filled.
        """
        template = self.testing_template
        
        # Format choices as a readable string
        choices_str = "\n".join([
            f"{key}. {value}" for key, value in choices.items()
        ])
        
        system_prompt = template["system"]
        user_prompt = template["user"].format(
            context=context,
            question=question,
            choices=choices_str
        )
        
        return system_prompt, user_prompt
    
    def load_custom_template(
        self,
        template_path: str,
        template_type: str = "question_generation"
    ):
        """
        Load a custom template from a specific file path.
        
        Args:
            template_path: Path to the custom template JSON file.
            template_type: Type of template to load 
                          ("question_generation", "testing", or "validation").
        
        Raises:
            ValueError: If template_type is invalid or template is malformed.
            FileNotFoundError: If the template file does not exist.
        """
        valid_types = ["question_generation", "testing", "validation"]
        if template_type not in valid_types:
            raise ValueError(
                f"Invalid template_type: {template_type}. "
                f"Must be one of: {valid_types}"
            )
        
        template = self._load_template_file(Path(template_path))
        
        if template_type == "question_generation":
            self.question_generation_template = template
        elif template_type == "testing":
            self.testing_template = template
        else:
            self.validation_template = template
    
    def get_validation_prompt(
        self,
        context: str,
        question: str,
        choices: str
    ) -> tuple[str, str]:
        """
        Get the formatted prompt for question validation.
        
        Args:
            context: The text context for validation.
            question: The question text to validate.
            choices: Formatted choices string (e.g., "A. option1\\nB. option2").
        
        Returns:
            Tuple of (system_prompt, user_prompt) with placeholders filled.
        """
        template = self.validation_template
        
        system_prompt = template["system"]
        user_prompt = template["user"].format(
            context=context,
            question=question,
            choices=choices
        )
        
        return system_prompt, user_prompt
    
    def get_template_info(self) -> Dict[str, Any]:
        """
        Get information about currently loaded templates.
        
        Returns:
            Dictionary containing template information.
        """
        return {
            "template_dir": str(self.template_dir),
            "question_generation_template": {
                "loaded": self.question_generation_template is not None,
                "is_default": (
                    self.question_generation_template == 
                    self.DEFAULT_QUESTION_GENERATION_TEMPLATE
                )
            },
            "testing_template": {
                "loaded": self.testing_template is not None,
                "is_default": (
                    self.testing_template == 
                    self.DEFAULT_TESTING_TEMPLATE
                )
            },
            "validation_template": {
                "loaded": self.validation_template is not None,
                "is_default": (
                    self.validation_template == 
                    self.DEFAULT_VALIDATION_TEMPLATE
                )
            }
        }
