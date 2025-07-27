"""Tests for mcp_client module."""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import AsyncExitStack
from mcp import ClientSession, types
from pydantic import AnyUrl

from mcp_client import MCPClient


class TestMCPClient:
    """Test the MCPClient class."""

    @pytest.fixture
    def client_args(self):
        """Provide standard client arguments."""
        return {
            "command": "uv",
            "args": ["run", "mcp_server.py"],
            "env": {"TEST_MODE": "true"}
        }

    @pytest.fixture
    def mcp_client(self, client_args):
        """Create an MCPClient instance for testing."""
        return MCPClient(**client_args)

    @pytest.fixture
    def mock_session(self):
        """Create a mock ClientSession."""
        session = Mock(spec=ClientSession)
        session.initialize = AsyncMock()
        session.list_tools = AsyncMock()
        session.call_tool = AsyncMock()
        session.list_prompts = AsyncMock()
        session.get_prompt = AsyncMock()
        session.read_resource = AsyncMock()
        return session

    def test_init(self, client_args):
        """Test MCPClient initialization."""
        client = MCPClient(**client_args)
        
        assert client._command == "uv"
        assert client._args == ["run", "mcp_server.py"]
        assert client._env == {"TEST_MODE": "true"}
        assert client._session is None
        assert client._client_id == "uv_run-mcp_server.py"
        assert isinstance(client._exit_stack, AsyncExitStack)

    def test_init_without_env(self):
        """Test MCPClient initialization without environment variables."""
        client = MCPClient(command="python", args=["server.py"])
        
        assert client._command == "python"
        assert client._args == ["server.py"]
        assert client._env is None
        assert client._client_id == "python_server.py"

    def test_init_empty_args(self):
        """Test MCPClient initialization with empty args."""
        client = MCPClient(command="python", args=[])
        
        assert client._command == "python"
        assert client._args == []
        assert client._client_id == "python_"

    @patch('mcp_client.stdio_client')
    @patch('mcp_client.StdioServerParameters')
    @patch('mcp_client.ClientSession')
    async def test_connect_success(
        self, 
        mock_client_session_class, 
        mock_stdio_params_class, 
        mock_stdio_client,
        mcp_client,
        mock_session
    ):
        """Test successful connection to MCP server."""
        # Setup mocks
        mock_stdio_transport = (Mock(), Mock())
        mock_stdio_client.return_value.__aenter__ = AsyncMock(return_value=mock_stdio_transport)
        mock_stdio_client.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_session_class.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the exit stack behavior
        mcp_client._exit_stack.enter_async_context = AsyncMock()
        mcp_client._exit_stack.enter_async_context.side_effect = [
            mock_stdio_transport,
            mock_session
        ]
        
        await mcp_client.connect()
        
        # Verify connection was established
        assert mcp_client._session == mock_session
        mock_session.initialize.assert_called_once()

    @patch('mcp_client.stdio_client')
    async def test_connect_failure(self, mock_stdio_client, mcp_client):
        """Test connection failure handling."""
        # Setup mock to raise exception
        mock_stdio_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await mcp_client.connect()
        
        assert mcp_client._session is None

    def test_session_not_connected(self, mcp_client):
        """Test accessing session when not connected raises error."""
        with pytest.raises(ConnectionError, match="Client session not initialized"):
            mcp_client.session()

    def test_session_connected(self, mcp_client, mock_session):
        """Test accessing session when connected."""
        mcp_client._session = mock_session
        
        result = mcp_client.session()
        
        assert result == mock_session

    async def test_list_tools(self, mcp_client, mock_session):
        """Test listing tools from MCP server."""
        # Setup mock
        mcp_client._session = mock_session
        mock_tools = [
            Mock(spec=types.Tool, name="tool1"),
            Mock(spec=types.Tool, name="tool2")
        ]
        mock_result = Mock()
        mock_result.tools = mock_tools
        mock_session.list_tools.return_value = mock_result
        
        result = await mcp_client.list_tools()
        
        assert result == mock_tools
        mock_session.list_tools.assert_called_once()

    async def test_call_tool_success(self, mcp_client, mock_session):
        """Test successful tool call."""
        # Setup mock
        mcp_client._session = mock_session
        tool_name = "read_document"
        tool_input = {"doc_id": "test.pdf"}
        mock_result = Mock(spec=types.CallToolResult)
        mock_session.call_tool.return_value = mock_result
        
        result = await mcp_client.call_tool(tool_name, tool_input)
        
        assert result == mock_result
        mock_session.call_tool.assert_called_once_with(tool_name, tool_input)

    async def test_call_tool_failure(self, mcp_client, mock_session):
        """Test tool call failure handling."""
        # Setup mock
        mcp_client._session = mock_session
        tool_name = "failing_tool"
        tool_input = {"param": "value"}
        mock_session.call_tool.side_effect = Exception("Tool execution failed")
        
        with pytest.raises(Exception, match="Tool execution failed"):
            await mcp_client.call_tool(tool_name, tool_input)

    async def test_list_prompts(self, mcp_client, mock_session):
        """Test listing prompts from MCP server."""
        # Setup mock
        mcp_client._session = mock_session
        mock_prompts = [
            Mock(spec=types.Prompt, name="prompt1"),
            Mock(spec=types.Prompt, name="prompt2")
        ]
        mock_result = Mock()
        mock_result.prompts = mock_prompts
        mock_session.list_prompts.return_value = mock_result
        
        result = await mcp_client.list_prompts()
        
        assert result == mock_prompts
        mock_session.list_prompts.assert_called_once()

    async def test_get_prompt_success(self, mcp_client, mock_session):
        """Test successful prompt retrieval."""
        # Setup mock
        mcp_client._session = mock_session
        prompt_name = "format"
        args = {"doc_id": "test.pdf"}
        mock_messages = [Mock(), Mock()]
        mock_result = Mock()
        mock_result.messages = mock_messages
        mock_session.get_prompt.return_value = mock_result
        
        result = await mcp_client.get_prompt(prompt_name, args)
        
        assert result == mock_messages
        mock_session.get_prompt.assert_called_once_with(prompt_name, args)

    async def test_get_prompt_failure(self, mcp_client, mock_session):
        """Test prompt retrieval failure handling."""
        # Setup mock
        mcp_client._session = mock_session
        prompt_name = "nonexistent"
        args = {"doc_id": "test.pdf"}
        mock_session.get_prompt.side_effect = Exception("Prompt not found")
        
        with pytest.raises(Exception, match="Prompt not found"):
            await mcp_client.get_prompt(prompt_name, args)

    async def test_read_resource_text(self, mcp_client, mock_session):
        """Test reading a text resource."""
        # Setup mock
        mcp_client._session = mock_session
        uri = "docs://documents/test.pdf"
        mock_text_content = Mock(spec=types.TextResourceContents)
        mock_text_content.mimeType = "text/plain"
        mock_text_content.text = "Document content"
        mock_result = Mock()
        mock_result.contents = [mock_text_content]
        mock_session.read_resource.return_value = mock_result
        
        result = await mcp_client.read_resource(uri)
        
        assert result == "Document content"
        mock_session.read_resource.assert_called_once()
        # Verify AnyUrl was used
        call_args = mock_session.read_resource.call_args[0][0]
        assert isinstance(call_args, AnyUrl)

    async def test_read_resource_json(self, mcp_client, mock_session):
        """Test reading a JSON resource."""
        # Setup mock
        mcp_client._session = mock_session
        uri = "docs://documents"
        json_data = {"docs": ["doc1.pdf", "doc2.md"]}
        mock_text_content = Mock(spec=types.TextResourceContents)
        mock_text_content.mimeType = "application/json"
        mock_text_content.text = json.dumps(json_data)
        mock_result = Mock()
        mock_result.contents = [mock_text_content]
        mock_session.read_resource.return_value = mock_result
        
        result = await mcp_client.read_resource(uri)
        
        assert result == json_data
        mock_session.read_resource.assert_called_once()

    async def test_read_resource_non_text(self, mcp_client, mock_session):
        """Test reading a non-text resource."""
        # Setup mock
        mcp_client._session = mock_session
        uri = "binary://resource"
        mock_binary_content = Mock()  # Not TextResourceContents
        mock_result = Mock()
        mock_result.contents = [mock_binary_content]
        mock_session.read_resource.return_value = mock_result
        
        result = await mcp_client.read_resource(uri)
        
        assert result == mock_binary_content
        mock_session.read_resource.assert_called_once()

    async def test_read_resource_failure(self, mcp_client, mock_session):
        """Test resource reading failure handling."""
        # Setup mock
        mcp_client._session = mock_session
        uri = "invalid://resource"
        mock_session.read_resource.side_effect = Exception("Resource not found")
        
        with pytest.raises(Exception, match="Resource not found"):
            await mcp_client.read_resource(uri)

    async def test_cleanup(self, mcp_client):
        """Test client cleanup."""
        # Setup mock session
        mock_session = Mock()
        mcp_client._session = mock_session
        mcp_client._exit_stack.aclose = AsyncMock()
        
        await mcp_client.cleanup()
        
        mcp_client._exit_stack.aclose.assert_called_once()
        assert mcp_client._session is None

    async def test_context_manager(self, client_args):
        """Test MCPClient as async context manager."""
        with patch.object(MCPClient, 'connect', new_callable=AsyncMock) as mock_connect:
            with patch.object(MCPClient, 'cleanup', new_callable=AsyncMock) as mock_cleanup:
                async with MCPClient(**client_args) as client:
                    assert isinstance(client, MCPClient)
                
                mock_connect.assert_called_once()
                mock_cleanup.assert_called_once()

    async def test_context_manager_with_exception(self, client_args):
        """Test MCPClient context manager with exception."""
        with patch.object(MCPClient, 'connect', new_callable=AsyncMock) as mock_connect:
            with patch.object(MCPClient, 'cleanup', new_callable=AsyncMock) as mock_cleanup:
                with pytest.raises(ValueError):
                    async with MCPClient(**client_args) as client:
                        raise ValueError("Test exception")
                
                mock_connect.assert_called_once()
                mock_cleanup.assert_called_once()

    def test_client_id_generation(self):
        """Test client ID generation with different inputs."""
        test_cases = [
            ("python", ["script.py"], "python_script.py"),
            ("uv", ["run", "server.py"], "uv_run-server.py"),
            ("node", ["index.js", "--port", "3000"], "node_index.js---port-3000"),
            ("cmd", [], "cmd_"),
        ]
        
        for command, args, expected_id in test_cases:
            client = MCPClient(command=command, args=args)
            assert client._client_id == expected_id


class TestMCPClientIntegration:
    """Integration tests for MCPClient functionality."""

    @pytest.fixture
    def connected_client(self, client_args, mock_session):
        """Create a connected MCPClient for testing."""
        client = MCPClient(**client_args)
        client._session = mock_session
        return client

    async def test_tool_workflow(self, connected_client, mock_session):
        """Test complete tool workflow: list tools, then call tool."""
        # Setup mocks for list_tools
        mock_tools = [
            Mock(spec=types.Tool, name="read_document"),
            Mock(spec=types.Tool, name="edit_document")
        ]
        mock_tools_result = Mock()
        mock_tools_result.tools = mock_tools
        mock_session.list_tools.return_value = mock_tools_result
        
        # Setup mocks for call_tool
        mock_tool_result = Mock(spec=types.CallToolResult)
        mock_session.call_tool.return_value = mock_tool_result
        
        # Execute workflow
        tools = await connected_client.list_tools()
        assert len(tools) == 2
        assert tools[0].name == "read_document"
        
        result = await connected_client.call_tool("read_document", {"doc_id": "test.pdf"})
        assert result == mock_tool_result

    async def test_prompt_workflow(self, connected_client, mock_session):
        """Test complete prompt workflow: list prompts, then get prompt."""
        # Setup mocks for list_prompts
        mock_prompts = [
            Mock(spec=types.Prompt, name="format"),
            Mock(spec=types.Prompt, name="summarize")
        ]
        mock_prompts_result = Mock()
        mock_prompts_result.prompts = mock_prompts
        mock_session.list_prompts.return_value = mock_prompts_result
        
        # Setup mocks for get_prompt
        mock_messages = [Mock(), Mock()]
        mock_prompt_result = Mock()
        mock_prompt_result.messages = mock_messages
        mock_session.get_prompt.return_value = mock_prompt_result
        
        # Execute workflow
        prompts = await connected_client.list_prompts()
        assert len(prompts) == 2
        assert prompts[0].name == "format"
        
        messages = await connected_client.get_prompt("format", {"doc_id": "test.pdf"})
        assert messages == mock_messages

    async def test_resource_workflow(self, connected_client, mock_session):
        """Test reading different types of resources."""
        # Test reading document list (JSON)
        json_data = ["doc1.pdf", "doc2.md"]
        mock_json_content = Mock(spec=types.TextResourceContents)
        mock_json_content.mimeType = "application/json"
        mock_json_content.text = json.dumps(json_data)
        mock_json_result = Mock()
        mock_json_result.contents = [mock_json_content]
        
        # Test reading specific document (text)
        doc_content = "Document content here"
        mock_text_content = Mock(spec=types.TextResourceContents)
        mock_text_content.mimeType = "text/plain"
        mock_text_content.text = doc_content
        mock_text_result = Mock()
        mock_text_result.contents = [mock_text_content]
        
        mock_session.read_resource.side_effect = [mock_json_result, mock_text_result]
        
        # Execute workflow
        doc_list = await connected_client.read_resource("docs://documents")
        assert doc_list == json_data
        
        doc_text = await connected_client.read_resource("docs://documents/doc1.pdf")
        assert doc_text == doc_content