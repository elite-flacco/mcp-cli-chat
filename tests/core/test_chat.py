"""Tests for core.chat module."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from anthropic.types import Message

from core.chat import Chat
from core.claude import Claude
from mcp_client import MCPClient


class TestChat:
    """Test the Chat base class."""

    @pytest.fixture
    def mock_claude_service(self):
        """Create a mock Claude service."""
        claude = Mock(spec=Claude)
        claude.chat = AsyncMock()
        claude.add_assistant_message = Mock()
        claude.add_user_message = Mock()
        claude.text_from_message = Mock(return_value="Mock response")
        return claude

    @pytest.fixture
    def mock_clients(self):
        """Create mock MCP clients."""
        return {"test_client": Mock(spec=MCPClient)}

    @pytest.fixture
    def chat_instance(self, mock_claude_service, mock_clients):
        """Create a Chat instance for testing."""
        return Chat(claude_service=mock_claude_service, clients=mock_clients)

    @pytest.fixture
    def mock_response(self):
        """Create a mock response from Claude."""
        response = Mock(spec=Message)
        response.stop_reason = "end_turn"
        return response

    def test_init(self, mock_claude_service, mock_clients):
        """Test Chat initialization."""
        chat = Chat(claude_service=mock_claude_service, clients=mock_clients)
        
        assert chat.claude_service == mock_claude_service
        assert chat.clients == mock_clients
        assert chat.messages == []

    async def test_process_query(self, chat_instance):
        """Test the base _process_query method."""
        query = "Hello, how are you?"
        
        await chat_instance._process_query(query)
        
        assert len(chat_instance.messages) == 1
        assert chat_instance.messages[0]["role"] == "user"
        assert chat_instance.messages[0]["content"] == query

    @patch('core.chat.ToolManager')
    async def test_run_basic_conversation(self, mock_tool_manager, chat_instance, mock_response):
        """Test a basic conversation flow."""
        query = "Hello, how are you?"
        mock_tools = [{"name": "test_tool", "description": "A test tool"}]
        mock_tool_manager.get_all_tools.return_value = mock_tools
        
        # Configure the Claude service mock
        chat_instance.claude_service.chat.return_value = mock_response
        chat_instance.claude_service.text_from_message.return_value = "I'm doing well, thanks!"
        
        result = await chat_instance.run(query)
        
        # Verify the flow
        assert result == "I'm doing well, thanks!"
        mock_tool_manager.get_all_tools.assert_called_once_with(chat_instance.clients)
        chat_instance.claude_service.chat.assert_called_once()
        chat_instance.claude_service.add_assistant_message.assert_called_once()

    @patch('core.chat.ToolManager')
    async def test_run_with_tool_use(self, mock_tool_manager, chat_instance):
        """Test conversation flow with tool use."""
        query = "Hello, use a tool please"
        mock_tools = [{"name": "test_tool", "description": "A test tool"}]
        mock_tool_manager.get_all_tools.return_value = mock_tools
        
        # First response requests tool use
        tool_use_response = Mock(spec=Message)
        tool_use_response.stop_reason = "tool_use"
        
        # Second response ends the conversation
        final_response = Mock(spec=Message)
        final_response.stop_reason = "end_turn"
        
        chat_instance.claude_service.chat.side_effect = [tool_use_response, final_response]
        chat_instance.claude_service.text_from_message.side_effect = [
            "Using tool...", 
            "Tool completed successfully!"
        ]
        
        # Mock tool execution
        mock_tool_results = [{"type": "text", "text": "Tool result"}]
        mock_tool_manager.execute_tool_requests.return_value = mock_tool_results
        
        with patch('builtins.print') as mock_print:
            result = await chat_instance.run(query)
        
        # Verify the flow
        assert result == "Tool completed successfully!"
        assert chat_instance.claude_service.chat.call_count == 2
        mock_tool_manager.execute_tool_requests.assert_called_once()
        chat_instance.claude_service.add_user_message.assert_called_with(
            chat_instance.messages, mock_tool_results
        )
        mock_print.assert_called_once_with("Using tool...")

    @patch('core.chat.ToolManager')
    async def test_run_multiple_tool_iterations(self, mock_tool_manager, chat_instance):
        """Test conversation with multiple tool use iterations."""
        query = "Complex task requiring multiple tools"
        mock_tools = [{"name": "test_tool", "description": "A test tool"}]
        mock_tool_manager.get_all_tools.return_value = mock_tools
        
        # Multiple responses with tool use, then final response
        responses = []
        for i in range(3):
            response = Mock(spec=Message)
            response.stop_reason = "tool_use"
            responses.append(response)
        
        final_response = Mock(spec=Message)
        final_response.stop_reason = "end_turn"
        responses.append(final_response)
        
        chat_instance.claude_service.chat.side_effect = responses
        chat_instance.claude_service.text_from_message.side_effect = [
            f"Tool iteration {i+1}" for i in range(3)
        ] + ["Final result"]
        
        # Mock tool execution
        mock_tool_results = [{"type": "text", "text": f"Tool result {i+1}"} for i in range(3)]
        mock_tool_manager.execute_tool_requests.side_effect = [
            [mock_tool_results[i]] for i in range(3)
        ]
        
        with patch('builtins.print') as mock_print:
            result = await chat_instance.run(query)
        
        # Verify the flow
        assert result == "Final result"
        assert chat_instance.claude_service.chat.call_count == 4
        assert mock_tool_manager.execute_tool_requests.call_count == 3
        assert mock_print.call_count == 3

    @patch('core.chat.ToolManager')
    async def test_run_with_empty_tool_response(self, mock_tool_manager, chat_instance):
        """Test handling of empty tool responses."""
        query = "Test empty tool response"
        mock_tools = [{"name": "test_tool", "description": "A test tool"}]
        mock_tool_manager.get_all_tools.return_value = mock_tools
        
        # Tool use response with empty text
        tool_use_response = Mock(spec=Message)
        tool_use_response.stop_reason = "tool_use"
        
        # Final response
        final_response = Mock(spec=Message)
        final_response.stop_reason = "end_turn"
        
        chat_instance.claude_service.chat.side_effect = [tool_use_response, final_response]
        chat_instance.claude_service.text_from_message.side_effect = ["", "Final result"]
        
        # Mock tool execution
        mock_tool_results = [{"type": "text", "text": "Tool result"}]
        mock_tool_manager.execute_tool_requests.return_value = mock_tool_results
        
        with patch('builtins.print') as mock_print:
            result = await chat_instance.run(query)
        
        # Verify empty response doesn't get printed
        assert result == "Final result"
        mock_print.assert_not_called()

    async def test_messages_accumulation(self, chat_instance):
        """Test that messages accumulate properly during conversation."""
        query1 = "First message"
        query2 = "Second message"
        
        await chat_instance._process_query(query1)
        await chat_instance._process_query(query2)
        
        assert len(chat_instance.messages) == 2
        assert chat_instance.messages[0]["content"] == query1
        assert chat_instance.messages[1]["content"] == query2