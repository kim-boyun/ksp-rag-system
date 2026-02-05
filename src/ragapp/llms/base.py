"""
Base LLM client interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseLLM(ABC):
    """
    Base LLM client interface
    Supports both chat and completion APIs
    """
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Chat completion
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Assistant's response
        """
        pass
