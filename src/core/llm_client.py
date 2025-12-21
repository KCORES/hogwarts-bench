"""LLM client with retry logic and error handling."""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from openai import AsyncOpenAI, OpenAIError, APITimeoutError, RateLimitError, APIConnectionError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """Unified interface for LLM API calls with retry logic."""
    
    def __init__(self, config: Dict):
        """Initialize OpenAI client with config.
        
        Args:
            config: Configuration dictionary containing:
                - api_key: API key for authentication
                - base_url: API endpoint URL
                - model_name: Model identifier
                - temperature: Generation temperature
                - max_tokens: Maximum response tokens
                - timeout: Request timeout in seconds
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            timeout=config["timeout"]
        )
        self.model_name = config["model_name"]
        self.temperature = config["temperature"]
        self.max_tokens = config["max_tokens"]
        self.timeout = config["timeout"]
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """Generate response from LLM.
        
        Args:
            prompt: User prompt text
            system_prompt: Optional system prompt
            max_retries: Maximum number of retry attempts
            
        Returns:
            Generated response text, or None if all retries failed
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return await self._retry_with_backoff(
            self._single_generate,
            messages,
            max_retries
        )
    
    async def generate_batch(
        self, 
        prompts: List[str], 
        system_prompt: Optional[str] = None,
        concurrency: int = 5,
        max_retries: int = 3
    ) -> List[Optional[str]]:
        """Generate responses concurrently.
        
        Args:
            prompts: List of user prompts
            system_prompt: Optional system prompt applied to all requests
            concurrency: Maximum number of concurrent requests
            max_retries: Maximum number of retry attempts per request
            
        Returns:
            List of generated responses (None for failed requests)
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def generate_with_semaphore(prompt: str) -> Optional[str]:
            async with semaphore:
                return await self.generate(prompt, system_prompt, max_retries)
        
        tasks = [generate_with_semaphore(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to None
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch request {i} failed with exception: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _single_generate(self, messages: List[Dict]) -> str:
        """Execute single generation request.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Generated response text
            
        Raises:
            OpenAIError: For API errors
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
        except APITimeoutError as e:
            logger.error(f"Request timeout: {e}")
            raise
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise
        except APIConnectionError as e:
            logger.error(f"Network connection error: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _retry_with_backoff(
        self,
        func,
        messages: List[Dict],
        max_retries: int = 3
    ) -> Optional[str]:
        """Retry failed requests with exponential backoff.
        
        Args:
            func: Async function to retry
            messages: Messages to pass to the function
            max_retries: Maximum number of retry attempts
            
        Returns:
            Function result, or None if all retries failed
        """
        base_delay = 1  # Initial delay in seconds
        
        for attempt in range(max_retries):
            try:
                result = await func(messages)
                if attempt > 0:
                    logger.info(f"Request succeeded on attempt {attempt + 1}")
                return result
            
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate limit hit, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Rate limit error persisted after {max_retries} attempts: {e}"
                    )
                    return None
            
            except (APITimeoutError, APIConnectionError) as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Network error, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Network error persisted after {max_retries} attempts: {e}"
                    )
                    return None
            
            except OpenAIError as e:
                # For other API errors, don't retry
                logger.error(f"Non-retryable API error: {e}")
                return None
            
            except Exception as e:
                # Unexpected errors
                logger.error(f"Unexpected error: {e}")
                return None
        
        return None
