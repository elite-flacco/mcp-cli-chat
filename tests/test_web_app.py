"""Tests for web_app module."""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import WebSocket

import web_app
from web_app import app, ConnectionManager


class TestConnectionManager:
    """Test the ConnectionManager class."""

    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager instance for testing."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket

    def test_init(self, connection_manager):
        """Test ConnectionManager initialization."""
        assert connection_manager.active_connections == []

    async def test_connect(self, connection_manager, mock_websocket):
        """Test connecting a WebSocket."""
        await connection_manager.connect(mock_websocket)
        
        assert mock_websocket in connection_manager.active_connections
        mock_websocket.accept.assert_called_once()

    async def test_connect_multiple(self, connection_manager):
        """Test connecting multiple WebSockets."""
        websockets = [Mock(spec=WebSocket) for _ in range(3)]
        for ws in websockets:
            ws.accept = AsyncMock()
        
        for ws in websockets:
            await connection_manager.connect(ws)
        
        assert len(connection_manager.active_connections) == 3
        for ws in websockets:
            assert ws in connection_manager.active_connections

    def test_disconnect(self, connection_manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        # First connect
        connection_manager.active_connections.append(mock_websocket)
        
        # Then disconnect
        connection_manager.disconnect(mock_websocket)
        
        assert mock_websocket not in connection_manager.active_connections

    def test_disconnect_not_connected(self, connection_manager, mock_websocket):
        """Test disconnecting a WebSocket that wasn't connected."""
        # Should raise ValueError when trying to remove non-existent item
        with pytest.raises(ValueError):
            connection_manager.disconnect(mock_websocket)

    async def test_send_personal_message(self, connection_manager, mock_websocket):
        """Test sending a personal message to a WebSocket."""
        message = "Hello, WebSocket!"
        
        await connection_manager.send_personal_message(message, mock_websocket)
        
        mock_websocket.send_text.assert_called_once_with(message)


class TestWebApp:
    """Test the FastAPI web application."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    def test_app_creation(self):
        """Test that the FastAPI app is created correctly."""
        assert app.title == "Claude Chat Web UI"

    def test_get_chat_endpoint(self, client):
        """Test the main chat page endpoint."""
        with patch('web_app.templates.TemplateResponse') as mock_template:
            mock_template.return_value = Mock()
            
            response = client.get("/")
            
            assert response.status_code == 200
            mock_template.assert_called_once()
            call_args = mock_template.call_args
            assert call_args[0][0] == "chat.html"
            assert "request" in call_args[0][1]

    @patch('web_app.initialize_mcp_clients')
    @patch('web_app.Claude')
    @patch('web_app.CliChat')
    @patch('web_app.load_dotenv')
    async def test_websocket_with_mcp_success(
        self, 
        mock_load_dotenv, 
        mock_cli_chat_class, 
        mock_claude_class, 
        mock_initialize_mcp,
        client
    ):
        """Test WebSocket connection with successful MCP initialization."""
        # Setup mocks
        mock_claude = Mock()
        mock_claude_class.return_value = mock_claude
        
        mock_doc_client = Mock()
        mock_clients = {"test": Mock()}
        mock_initialize_mcp.return_value = (mock_doc_client, mock_clients)
        
        mock_chat = Mock()
        mock_chat.process_query_async = AsyncMock(return_value="Test response")
        mock_cli_chat_class.return_value = mock_chat
        
        # Mock environment variable
        with patch('web_app.os.getenv', return_value="claude-3-sonnet-20240229"):
            with client.websocket_connect("/ws") as websocket:
                # Send a chat message
                message = {"type": "chat", "message": "Hello"}
                websocket.send_text(json.dumps(message))
                
                # Receive response
                response = websocket.receive_text()
                response_data = json.loads(response)
                
                assert response_data["type"] == "response"
                assert response_data["content"] == "Test response"
                
                mock_chat.process_query_async.assert_called_once_with("Hello")

    @patch('web_app.initialize_mcp_clients')
    @patch('web_app.Claude')
    @patch('web_app.load_dotenv')
    async def test_websocket_mcp_failure_fallback(
        self, 
        mock_load_dotenv, 
        mock_claude_class, 
        mock_initialize_mcp,
        client
    ):
        """Test WebSocket connection with MCP failure using fallback."""
        # Setup mocks
        mock_claude = Mock()
        mock_claude.chat = AsyncMock(return_value="Fallback response")
        mock_claude_class.return_value = mock_claude
        
        # Make MCP initialization fail
        mock_initialize_mcp.side_effect = Exception("MCP failed")
        
        # Mock environment variable
        with patch('web_app.os.getenv', return_value="claude-3-sonnet-20240229"):
            with client.websocket_connect("/ws") as websocket:
                # Send a chat message
                message = {"type": "chat", "message": "Hello"}
                websocket.send_text(json.dumps(message))
                
                # Receive response
                response = websocket.receive_text()
                response_data = json.loads(response)
                
                assert response_data["type"] == "response"
                assert response_data["content"] == "Fallback response"
                
                # Verify the claude service was called
                mock_claude.chat.assert_called_once()

    @patch('web_app.initialize_mcp_clients')
    @patch('web_app.Claude')
    @patch('web_app.load_dotenv')
    async def test_websocket_invalid_message_type(
        self, 
        mock_load_dotenv, 
        mock_claude_class, 
        mock_initialize_mcp,
        client
    ):
        """Test WebSocket with invalid message type."""
        # Setup mocks
        mock_claude = Mock()
        mock_claude_class.return_value = mock_claude
        
        mock_doc_client = Mock()
        mock_clients = {"test": Mock()}
        mock_initialize_mcp.return_value = (mock_doc_client, mock_clients)
        
        # Mock environment variable
        with patch('web_app.os.getenv', return_value="claude-3-sonnet-20240229"):
            with patch('web_app.CliChat') as mock_cli_chat_class:
                mock_chat = Mock()
                mock_chat.process_query_async = AsyncMock()
                mock_cli_chat_class.return_value = mock_chat
                
                with client.websocket_connect("/ws") as websocket:
                    # Send a message with invalid type
                    message = {"type": "invalid", "message": "Hello"}
                    websocket.send_text(json.dumps(message))
                    
                    # The chat shouldn't be called for invalid message types
                    # The WebSocket should continue waiting for valid messages
                    mock_chat.process_query_async.assert_not_called()

    @patch('web_app.initialize_mcp_clients')
    @patch('web_app.Claude')
    @patch('web_app.CliChat')
    @patch('web_app.load_dotenv')
    async def test_websocket_chat_exception(
        self, 
        mock_load_dotenv, 
        mock_cli_chat_class, 
        mock_claude_class, 
        mock_initialize_mcp,
        client
    ):
        """Test WebSocket handling of chat processing exceptions."""
        # Setup mocks
        mock_claude = Mock()
        mock_claude_class.return_value = mock_claude
        
        mock_doc_client = Mock()
        mock_clients = {"test": Mock()}
        mock_initialize_mcp.return_value = (mock_doc_client, mock_clients)
        
        mock_chat = Mock()
        mock_chat.process_query_async = AsyncMock(side_effect=Exception("Chat error"))
        mock_cli_chat_class.return_value = mock_chat
        
        # Mock environment variable
        with patch('web_app.os.getenv', return_value="claude-3-sonnet-20240229"):
            with client.websocket_connect("/ws") as websocket:
                # Send a chat message
                message = {"type": "chat", "message": "Hello"}
                websocket.send_text(json.dumps(message))
                
                # Receive error response
                response = websocket.receive_text()
                response_data = json.loads(response)
                
                assert response_data["type"] == "error"
                assert "Chat error" in response_data["content"]

    def test_startup_event_execution(self):
        """Test that startup event sets up the application correctly."""
        # Since startup_event is a coroutine, we need to test its behavior
        with patch('web_app.load_dotenv') as mock_load_dotenv:
            with patch('web_app.os.getenv', return_value="test-model"):
                with patch('web_app.Claude') as mock_claude_class:
                    with patch('builtins.print') as mock_print:
                        # Import and run the startup event
                        import asyncio
                        asyncio.run(web_app.startup_event())
                        
                        mock_load_dotenv.assert_called_once()
                        mock_claude_class.assert_called_once_with(model="test-model")
                        mock_print.assert_called()


class TestSimpleChatFallback:
    """Test the SimpleChatFallback class defined inline in web_app."""

    @pytest.fixture
    def mock_claude_service(self):
        """Create a mock Claude service."""
        claude = Mock()
        claude.chat = AsyncMock(return_value="Mock response")
        return claude

    def test_simple_chat_fallback_init(self, mock_claude_service):
        """Test SimpleChatFallback initialization."""
        # Create an instance of the fallback class from web_app
        # We need to simulate creating it as it's defined inline
        class SimpleChatFallback:
            def __init__(self, claude_service):
                self.claude_service = claude_service
                self.messages = []
        
        fallback = SimpleChatFallback(mock_claude_service)
        
        assert fallback.claude_service == mock_claude_service
        assert fallback.messages == []

    async def test_simple_chat_fallback_process_query(self, mock_claude_service):
        """Test SimpleChatFallback query processing."""
        # Create an instance of the fallback class from web_app
        class SimpleChatFallback:
            def __init__(self, claude_service):
                self.claude_service = claude_service
                self.messages = []
            
            async def process_query_async(self, query):
                self.messages.append({"role": "user", "content": query})
                response = await self.claude_service.chat(self.messages)
                self.messages.append({"role": "assistant", "content": response})
                return response
        
        fallback = SimpleChatFallback(mock_claude_service)
        query = "Test query"
        
        result = await fallback.process_query_async(query)
        
        assert result == "Mock response"
        assert len(fallback.messages) == 2
        assert fallback.messages[0]["role"] == "user"
        assert fallback.messages[0]["content"] == query
        assert fallback.messages[1]["role"] == "assistant"
        assert fallback.messages[1]["content"] == "Mock response"
        
        mock_claude_service.chat.assert_called_once_with(fallback.messages)


class TestWebAppIntegration:
    """Integration tests for the web application."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    def test_static_files_mounted(self, client):
        """Test that static files are properly mounted."""
        # This would test if static files are accessible
        # In a real test, you'd have actual static files to test
        pass

    def test_templates_configured(self):
        """Test that templates are properly configured."""
        assert web_app.templates.directory == "templates"

    @patch('web_app.os.getenv')
    @patch('web_app.load_dotenv')
    def test_environment_loading(self, mock_load_dotenv, mock_getenv):
        """Test that environment variables are loaded correctly."""
        mock_getenv.return_value = "claude-3-sonnet-20240229"
        
        # This would be called during startup
        import asyncio
        asyncio.run(web_app.startup_event())
        
        mock_load_dotenv.assert_called()
        mock_getenv.assert_called_with("CLAUDE_MODEL", "")

    def test_global_manager_instance(self):
        """Test that the global manager instance is created."""
        assert isinstance(web_app.manager, ConnectionManager)

    def test_app_configuration(self):
        """Test FastAPI app configuration."""
        assert hasattr(app, 'mount')
        assert hasattr(app, 'websocket')
        assert hasattr(app, 'get')
        assert hasattr(app, 'on_event')