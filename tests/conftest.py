"""Shared test fixtures and configuration for the test suite."""
import pytest
import os
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Set test environment variables
os.environ["TEST_MODE"] = "true"
os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
os.environ["CLAUDE_MODEL"] = "claude-3-sonnet-20240229"


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    env_vars = {
        "ANTHROPIC_API_KEY": "test-api-key",
        "CLAUDE_MODEL": "claude-3-sonnet-20240229",
        "TEST_MODE": "true"
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = Mock()
    client.messages = Mock()
    client.messages.create = Mock()
    return client


@pytest.fixture
def mock_claude_response():
    """Create a mock Claude API response."""
    from anthropic.types import Message
    from anthropic.types.text_block import TextBlock
    
    response = Mock(spec=Message)
    text_block = Mock(spec=TextBlock)
    text_block.type = "text"
    text_block.text = "This is a test response from Claude."
    response.content = [text_block]
    response.stop_reason = "end_turn"
    return response


@pytest.fixture
def sample_documents():
    """Provide sample documents for testing."""
    return {
        "test_report.pdf": "This is a test report containing important information.",
        "test_data.csv": "name,value\ntest1,100\ntest2,200",
        "test_memo.md": "# Test Memo\n\nThis is a test memo with **bold** text.",
    }


@pytest.fixture
def mock_mcp_tools():
    """Create mock MCP tools for testing."""
    from mcp.types import Tool
    
    tools = [
        Mock(spec=Tool, name="read_doc_contents", description="Read document contents"),
        Mock(spec=Tool, name="edit_doc_contents", description="Edit document contents"),
    ]
    return tools


@pytest.fixture
def mock_mcp_prompts():
    """Create mock MCP prompts for testing."""
    from mcp.types import Prompt
    
    prompts = [
        Mock(spec=Prompt, name="format", description="Format document"),
        Mock(spec=Prompt, name="summarize", description="Summarize document"),
    ]
    return prompts


@pytest.fixture
async def mock_mcp_client_session():
    """Create a mock MCP client session."""
    from mcp import ClientSession
    
    session = Mock(spec=ClientSession)
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock()
    session.call_tool = AsyncMock()
    session.list_prompts = AsyncMock()
    session.get_prompt = AsyncMock()
    session.read_resource = AsyncMock()
    return session


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_logging():
    """Mock logging to prevent log output during tests."""
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = Mock()
        mock_logger.debug = Mock()
        mock_logger.info = Mock()
        mock_logger.warning = Mock()
        mock_logger.error = Mock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def temp_test_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test_document.txt"
    test_file.write_text("This is test content for testing file operations.")
    return str(test_file)


# Mark tests that require network access
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "network: marks tests as requiring network access"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# Skip network tests by default unless explicitly requested
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers."""
    if config.getoption("--run-network"):
        # --run-network given in cli: do not skip network tests
        return
    
    skip_network = pytest.mark.skip(reason="need --run-network option to run")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_network)


def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="run network tests"
    )
    parser.addoption(
        "--run-slow",
        action="store_true", 
        default=False,
        help="run slow tests"
    )


# Fixtures for FastAPI testing
@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    from fastapi import WebSocket
    
    websocket = Mock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_fastapi_request():
    """Create a mock FastAPI request."""
    from fastapi import Request
    
    request = Mock(spec=Request)
    request.url = Mock()
    request.headers = {}
    request.query_params = {}
    return request