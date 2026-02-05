"""
Configuration tests
"""
import os
import pytest
from ragapp.config import AppConfig, get_config, reload_config


def test_config_local_mode():
    """Test local mode configuration"""
    os.environ["MODE"] = "local"
    config = reload_config()
    
    assert config.mode == "local"
    assert config.is_local_mode is True
    assert config.is_server_mode is False
    assert config.get_retriever_type() == "bm25+faiss"
    assert "openai" in config.get_llm_endpoint()


def test_config_server_mode():
    """Test server mode configuration"""
    os.environ["MODE"] = "server"
    config = reload_config()
    
    assert config.mode == "server"
    assert config.is_local_mode is False
    assert config.is_server_mode is True
    assert config.get_retriever_type() == "elasticsearch"
    assert "vllm" in config.get_llm_endpoint() or "8000" in config.get_llm_endpoint()


def test_config_validation():
    """Test configuration validation"""
    config = AppConfig(
        mode="local",
        top_k=5,
        chunk_size=512
    )
    
    assert config.top_k == 5
    assert config.chunk_size == 512


def test_config_defaults():
    """Test default configuration values"""
    config = AppConfig()
    
    assert config.mode in ["local", "server"]
    assert config.top_k > 0
    assert config.chunk_size > 0
    assert config.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]
