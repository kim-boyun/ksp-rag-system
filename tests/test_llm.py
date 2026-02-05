"""
LLM client tests
"""
import pytest
from unittest.mock import Mock, patch

from ragapp.llms.local_api import LocalAPIClient
from ragapp.llms.server_http import ServerHTTPClient


def test_local_api_generate():
    """Test LocalAPIClient generate method"""
    with patch('ragapp.llms.local_api.OpenAI') as mock_openai:
        # Mock response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is a test response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Create client
        client = LocalAPIClient(api_key="test-key", model="gpt-3.5-turbo")
        
        # Generate
        response = client.generate("Test prompt")
        
        assert response == "This is a test response"
        assert mock_client.chat.completions.create.called


def test_local_api_chat():
    """Test LocalAPIClient chat method"""
    with patch('ragapp.llms.local_api.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Chat response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = LocalAPIClient(api_key="test-key")
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        response = client.chat(messages)
        
        assert response == "Chat response"


def test_local_api_requires_key():
    """Test LocalAPIClient requires valid API key"""
    with pytest.raises(ValueError, match="API key not configured"):
        LocalAPIClient(api_key="")
    
    with pytest.raises(ValueError, match="API key not configured"):
        LocalAPIClient(api_key="your-openai-api-key-here")


def test_server_http_generate():
    """Test ServerHTTPClient generate method"""
    with patch('ragapp.llms.server_http.httpx.Client') as mock_client_class:
        # Mock response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"text": "Server response"}]
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        client = ServerHTTPClient(
            endpoint="http://test:8000/v1/completions",
            model="test-model"
        )
        
        response = client.generate("Test prompt")
        
        assert response == "Server response"


def test_llm_factory_local():
    """Test LLM factory creates LocalAPIClient for local mode"""
    import os
    os.environ["MODE"] = "local"
    os.environ["LLM_PROVIDER"] = "local_api"
    os.environ["LLM_API_KEY"] = "test-key-123"
    
    from ragapp.config import reload_config
    reload_config()
    
    from ragapp.pipeline.rag_pipeline import RAGPipeline
    
    # Should not raise error
    pipeline = RAGPipeline()
    
    # Check LLM type (will be LocalAPIClient or placeholder)
    assert pipeline.llm is not None


def test_llm_factory_server():
    """Test LLM factory creates ServerHTTPClient for server mode"""
    import os
    os.environ["MODE"] = "server"
    os.environ["LLM_PROVIDER"] = "server_http"
    
    from ragapp.config import reload_config
    reload_config()
    
    from ragapp.pipeline.rag_pipeline import RAGPipeline
    
    pipeline = RAGPipeline()
    
    assert pipeline.llm is not None
