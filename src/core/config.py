"""Configuration manager for loading and validating settings."""

import os
from typing import Dict, Optional
from dotenv import load_dotenv


class Config:
    """Manages configuration loading and validation."""
    
    @staticmethod
    def load_from_env(env_path: Optional[str] = None) -> Dict:
        """Load configuration from .env file.
        
        Args:
            env_path: Path to .env file. If None, searches for .env in current directory.
            
        Returns:
            Dictionary containing configuration parameters.
        """
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
        
        config = {
            # LLM Configuration
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
            "model_name": os.getenv("MODEL_NAME", ""),
            "temperature": float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("DEFAULT_MAX_TOKENS", "2000")),
            "timeout": int(os.getenv("DEFAULT_TIMEOUT", "60")),
            
            # Concurrency Settings
            "default_concurrency": int(os.getenv("DEFAULT_CONCURRENCY", "5")),
            "default_retry_times": int(os.getenv("DEFAULT_RETRY_TIMES", "3")),
        }
        
        return config
    
    @staticmethod
    def validate_config(config: Dict) -> bool:
        """Validate required configuration parameters.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            True if configuration is valid.
            
        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        required_fields = ["api_key", "model_name"]
        
        for field in required_fields:
            if not config.get(field):
                raise ValueError(f"Missing required configuration: {field}")
        
        # Validate numeric ranges
        if config["temperature"] < 0 or config["temperature"] > 2:
            raise ValueError("Temperature must be between 0 and 2")
        
        if config["max_tokens"] <= 0:
            raise ValueError("max_tokens must be positive")
        
        if config["timeout"] <= 0:
            raise ValueError("timeout must be positive")
        
        return True
    
    @staticmethod
    def get_llm_config(config: Dict) -> Dict:
        """Return LLM-specific configuration.
        
        Args:
            config: Full configuration dictionary.
            
        Returns:
            Dictionary containing only LLM-related parameters.
        """
        return {
            "api_key": config["api_key"],
            "base_url": config["base_url"],
            "model_name": config["model_name"],
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
            "timeout": config["timeout"],
        }
