"""
Basic environment tests
"""
import sys
import pytest


def test_python_version():
    """Test Python 3.11 is being used"""
    assert sys.version_info.major == 3
    assert sys.version_info.minor == 11


def test_imports():
    """Test core dependencies can be imported"""
    import torch
    import sentence_transformers
    import pydantic
    import typer
    
    assert torch is not None
    assert sentence_transformers is not None


def test_ragapp_import():
    """Test ragapp package can be imported"""
    import ragapp
    from ragapp.config import get_config
    from ragapp.pipeline.rag_pipeline import RAGPipeline
    
    assert ragapp is not None
    assert get_config is not None
    assert RAGPipeline is not None
