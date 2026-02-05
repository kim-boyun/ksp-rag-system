"""
Server HTTP client for GPU server LLMs
Supports vLLM, TGI, and other OpenAI-compatible HTTP endpoints
"""
from typing import List, Dict, Any
import httpx
from loguru import logger

from ragapp.llms.base import BaseLLM
from ragapp.config import get_config


class ServerHTTPClient(BaseLLM):
    """
    Server HTTP client for vLLM or other OpenAI-compatible endpoints
    """
    
    def __init__(self, endpoint: str = None, model: str = None):
        """
        Initialize server HTTP client
        
        Args:
            endpoint: HTTP endpoint URL (uses config if None)
            model: Model name (uses config if None)
        """
        config = get_config()
        
        self.endpoint = endpoint or config.server_llm_endpoint
        self.model = model or config.server_llm_model
        self.temperature = config.llm_temperature
        self.max_tokens = config.llm_max_tokens
        
        logger.info(f"ServerHTTPClient initialized")
        logger.info(f"Endpoint: {self.endpoint}")
        logger.info(f"Model: {self.model}")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ) -> str:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Temperature
            
        Returns:
            Generated text
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        # vLLM completions API format
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(self.endpoint, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract text from response
                if "choices" in data:
                    return data["choices"][0].get("text", "")
                elif "text" in data:
                    return data["text"]
                else:
                    logger.error(f"Unexpected response format: {data}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Server HTTP call failed: {e}")
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
        
        # Convert chat to single prompt (for completion-only endpoints)
        # Or use chat endpoint if available
        chat_endpoint = self.endpoint.replace("/completions", "/chat/completions")
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            with httpx.Client(timeout=120.0) as client:
                # Try chat endpoint first
                try:
                    response = client.post(chat_endpoint, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    if "choices" in data:
                        return data["choices"][0]["message"]["content"]
                        
                except (httpx.HTTPStatusError, KeyError):
                    # Fallback: convert to prompt and use completions
                    prompt = self._messages_to_prompt(messages)
                    return self.generate(prompt, max_tokens, temperature)
                    
        except Exception as e:
            logger.error(f"Server HTTP call failed: {e}")
            raise
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to single prompt"""
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
