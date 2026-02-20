"""
Server HTTP client for GPU server LLMs
Supports vLLM, TGI, and other OpenAI-compatible HTTP endpoints
"""
import json
from typing import List, Dict, Any, Iterator
import httpx
from loguru import logger

from ragapp.llms.base import BaseLLM
from ragapp.config import get_config


class ServerHTTPClient(BaseLLM):
    """
    Server HTTP client for vLLM or other OpenAI-compatible endpoints
    """
    
    def __init__(self, endpoint: str = None, model: str = None, base_url: str = None):
        """
        Initialize server HTTP client
        
        Args:
            endpoint: Full HTTP endpoint URL (deprecated, use base_url instead)
            model: Model name (uses config if None)
            base_url: Base URL for vLLM server (e.g., http://172.16.0.52:8000)
        """
        config = get_config()
        
        # 우선순위: endpoint (하위 호환) > base_url > config
        if endpoint:
            self.endpoint = endpoint
            logger.warning("Using 'endpoint' parameter is deprecated. Use 'base_url' instead.")
        elif base_url:
            self.endpoint = f"{base_url}/v1/completions"
        else:
            # config에서 BASE_URL 사용
            self.endpoint = config.get_llm_endpoint()
        
        self.base_url = base_url or config.server_llm_base_url
        self.chat_endpoint = config.get_llm_chat_endpoint()
        self.model = model or config.server_llm_model
        self.temperature = config.llm_temperature
        self.max_tokens = config.llm_max_tokens
        
        logger.info(f"ServerHTTPClient initialized")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Completions endpoint: {self.endpoint}")
        logger.info(f"Chat endpoint: {self.chat_endpoint}")
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

    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ) -> Iterator[str]:
        """Generate text from prompt, yielding chunks (SSE)."""
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **kwargs
        }
        try:
            with httpx.Client(timeout=120.0) as client:
                with client.stream("POST", self.endpoint, json=payload) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line or line.strip() != line or not line.startswith("data: "):
                            continue
                        if line.strip() == "data: [DONE]":
                            break
                        try:
                            data = json.loads(line[6:])
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("text", "")
                                if delta:
                                    yield delta
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Server HTTP stream failed: {e}")
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
        
        # Use dedicated chat endpoint
        chat_endpoint = self.chat_endpoint
        
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
