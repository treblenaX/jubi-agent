"""
Jubi Multi-Agent Harness - LLM Provider Service

This module provides a unified interface for LLM client management,
supporting multiple models with fallback routing and configuration.
"""

from typing import Optional, Dict, Any, List
from langchain_ollama import ChatOllama
from app.core.config import settings


class LLMProvider:
    """
    Unified LLM provider with model switching and fallback support.
    
    This class manages multiple LLM clients and provides a consistent
    interface for all agent operations.
    """
    
    def __init__(self, default_model: str = None):
        """
        Initialize the LLM provider.
        
        Args:
            default_model: Default model name (uses settings if not provided)
        """
        self.default_model = default_model or settings.OLLAMA_MODEL
        self._clients: Dict[str, ChatOllama] = {}
        self._fallback_chain: List[str] = []
    
    def create_client(self, model: str, **kwargs) -> ChatOllama:
        """
        Create an LLM client for a specific model.
        
        Args:
            model: Model name from Ollama library
            **kwargs: Additional configuration (temperature, num_ctx, etc.)
            
        Returns:
            Configured ChatOllama instance
        """
        client = ChatOllama(
            model=model,
            temperature=kwargs.get("temperature", settings.OLLAMA_TEMPERATURE),
            num_ctx=kwargs.get("num_ctx", settings.OLLAMA_NUM_CTX),
            keep_alive=kwargs.get("keep_alive", settings.OLLAMA_KEEP_ALIVE),
            base_url=kwargs.get("base_url", settings.OLLAMA_BASE_URL)
        )
        
        self._clients[model] = client
        return client
    
    def get_client(self, model: Optional[str] = None) -> ChatOllama:
        """
        Get an LLM client for a specific model or the default.
        
        Args:
            model: Model name (uses default if not provided)
            
        Returns:
            Configured ChatOllama instance
        """
        model = model or self.default_model
        
        if model not in self._clients:
            self._clients[model] = self.create_client(model)
        
        return self._clients[model]
    
    def chat(self, prompt: str, model: Optional[str] = None, **kwargs) -> Any:
        """
        Send a chat request to the LLM.
        
        Args:
            prompt: Chat prompt
            model: Model to use (uses default if not provided)
            **kwargs: Additional message history or options
            
        Returns:
            LLM response
        """
        client = self.get_client(model)
        return client.invoke(prompt, **kwargs)
    
    def stream(self, prompt: str, model: Optional[str] = None, **kwargs) -> Any:
        """
        Stream a chat response from the LLM.
        
        Args:
            prompt: Chat prompt
            model: Model to use (uses default if not provided)
            **kwargs: Additional options
            
        Returns:
            Streaming response generator
        """
        client = self.get_client(model)
        return client.stream(prompt, **kwargs)
    
    def add_fallback(self, model: str) -> None:
        """
        Add a fallback model for when the primary fails.
        
        Args:
            model: Fallback model name
        """
        self._fallback_chain.append(model)
    
    def get_fallback_chain(self) -> List[str]:
        """
        Get the list of fallback models in priority order.
        
        Returns:
            List of model names
        """
        return self._fallback_chain.copy()


# Create a global provider instance
provider = LLMProvider(default_model=settings.OLLAMA_MODEL)
