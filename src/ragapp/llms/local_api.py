"""
Local API client (OpenAI-compatible APIs)
Uses personal API keys for development
"""
from typing import List, Dict, Any, Iterator
from openai import OpenAI
from loguru import logger

from ragapp.llms.base import BaseLLM
from ragapp.config import get_config


class LocalAPIClient(BaseLLM):
    """
    Local API client using OpenAI API
    Supports OpenAI, Azure OpenAI, and compatible APIs
    """
    
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        """
        Initialize local API client
        
        Args:
            api_key: API key (uses config if None)
            model: Model name (uses config if None)
            base_url: Base URL for API (optional, for compatible APIs)
        """
        config = get_config()
        
        self.api_key = api_key or config.llm_api_key
        self.model = model or config.llm_model
        self.temperature = config.llm_temperature
        self.max_tokens = config.llm_max_tokens
        
        if not self.api_key or self.api_key == "" or "your-" in self.api_key:
            raise ValueError(
                "OpenAI API key not configured. "
                "Set LLM_API_KEY in .env (from .env.local) with your actual API key"
            )
        
        # Initialize OpenAI client
        client_kwargs = {"api_key": self.api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self.client = OpenAI(**client_kwargs)
        
        logger.info(f"LocalAPIClient initialized")
        logger.info(f"Model: {self.model}")
        logger.info(f"Temperature: {self.temperature}")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        system_prompt: str = None,
        **kwargs
    ) -> str:
        """
        Generate text from prompt using chat completion
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens (uses config default if None)
            temperature: Temperature (uses config default if None)
            system_prompt: Optional system message (when set, uses chat with [system, user])
            
        Returns:
            Generated text
        """
        if system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            return self.chat(messages, max_tokens, temperature, **kwargs)
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, max_tokens, temperature, **kwargs)

    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        system_prompt: str = None,
        **kwargs
    ) -> Iterator[str]:
        """Generate text from prompt, yielding chunks."""
        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI stream failed: {e}")
            raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ) -> str:
        """
        Chat completion
        
        Args:
            messages: List of message dicts
            max_tokens: Maximum tokens
            temperature: Temperature
            
        Returns:
            Assistant's response
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
