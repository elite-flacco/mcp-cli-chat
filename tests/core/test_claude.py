"""Tests for core.claude module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from anthropic.types import Message
from anthropic.types.text_block import TextBlock

from core.claude import Claude


class TestClaude:
    """Test the Claude API wrapper."""

    @pytest.fixture
    def claude_service(self):
        """Create a Claude service instance for testing."""
        with patch('core.claude.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client
            claude = Claude(model="claude-3-sonnet-20240229")
            claude.client = mock_client
            return claude

    @pytest.fixture
    def mock_message(self):
        """Create a mock Message object."""
        mock_msg = Mock(spec=Message)
        mock_text_block = Mock(spec=TextBlock)
        mock_text_block.type = "text"
        mock_text_block.text = "Test response"
        mock_msg.content = [mock_text_block]
        return mock_msg

    def test_init(self):
        """Test Claude initialization."""
        with patch('core.claude.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client
            
            claude = Claude(model="claude-3-sonnet-20240229")
            
            assert claude.model == "claude-3-sonnet-20240229"
            assert claude.client == mock_client
            mock_anthropic.assert_called_once()

    def test_add_user_message_with_string(self, claude_service):
        """Test adding a user message from a string."""
        messages = []
        message_content = "Hello, Claude!"
        
        claude_service.add_user_message(messages, message_content)
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == message_content

    def test_add_user_message_with_message_object(self, claude_service, mock_message):
        """Test adding a user message from a Message object."""
        messages = []
        
        claude_service.add_user_message(messages, mock_message)
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == mock_message.content

    def test_add_assistant_message_with_string(self, claude_service):
        """Test adding an assistant message from a string."""
        messages = []
        message_content = "Hello there!"
        
        claude_service.add_assistant_message(messages, message_content)
        
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == message_content

    def test_add_assistant_message_with_message_object(self, claude_service, mock_message):
        """Test adding an assistant message from a Message object."""
        messages = []
        
        claude_service.add_assistant_message(messages, mock_message)
        
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == mock_message.content

    def test_text_from_message(self, claude_service):
        """Test extracting text from a Message object."""
        # Create a mock message with multiple text blocks
        mock_message = Mock(spec=Message)
        text_block1 = Mock(spec=TextBlock)
        text_block1.type = "text"
        text_block1.text = "First part"
        
        text_block2 = Mock(spec=TextBlock)
        text_block2.type = "text"
        text_block2.text = "Second part"
        
        # Add a non-text block to ensure it's filtered out
        non_text_block = Mock()
        non_text_block.type = "image"
        
        mock_message.content = [text_block1, non_text_block, text_block2]
        
        result = claude_service.text_from_message(mock_message)
        
        assert result == "First part\nSecond part"

    def test_chat_basic(self, claude_service):
        """Test basic chat functionality."""
        messages = [{"role": "user", "content": "Hello"}]
        mock_response = Mock(spec=Message)
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Hello response"
        mock_response.content = [mock_text_block]
        claude_service.client.messages.create.return_value = mock_response
        
        result = claude_service.chat(messages)
        
        assert result == mock_response
        claude_service.client.messages.create.assert_called_once()
        call_args = claude_service.client.messages.create.call_args
        assert call_args[1]["model"] == "claude-3-sonnet-20240229"
        assert call_args[1]["messages"] == messages

    def test_chat_with_system_message(self, claude_service):
        """Test chat with system message."""
        messages = [{"role": "user", "content": "Hello"}]
        system_message = "You are a helpful assistant."
        mock_response = Mock(spec=Message)
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 15
        mock_response.usage.output_tokens = 8
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "System response"
        mock_response.content = [mock_text_block]
        claude_service.client.messages.create.return_value = mock_response
        
        result = claude_service.chat(messages, system=system_message)
        
        assert result == mock_response
        call_args = claude_service.client.messages.create.call_args
        assert call_args[1]["system"] == system_message

    def test_chat_with_tools(self, claude_service):
        """Test chat with tools."""
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"name": "test_tool", "description": "A test tool"}]
        mock_response = Mock(spec=Message)
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 12
        mock_response.usage.output_tokens = 6
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Tool response"
        mock_response.content = [mock_text_block]
        claude_service.client.messages.create.return_value = mock_response
        
        result = claude_service.chat(messages, tools=tools)
        
        assert result == mock_response
        call_args = claude_service.client.messages.create.call_args
        assert call_args[1]["tools"] == tools

    def test_chat_with_thinking(self, claude_service):
        """Test chat with thinking mode enabled."""
        messages = [{"role": "user", "content": "Hello"}]
        mock_response = Mock(spec=Message)
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 20
        mock_response.usage.output_tokens = 10
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Thinking response"
        mock_response.content = [mock_text_block]
        claude_service.client.messages.create.return_value = mock_response
        
        result = claude_service.chat(messages, thinking=True, thinking_budget=2048)
        
        assert result == mock_response
        call_args = claude_service.client.messages.create.call_args
        assert call_args[1]["thinking"] == {"type": "enabled", "budget_tokens": 2048}

    def test_chat_with_temperature_and_stop_sequences(self, claude_service):
        """Test chat with temperature and stop sequences."""
        messages = [{"role": "user", "content": "Hello"}]
        temperature = 0.5
        stop_sequences = ["STOP", "END"]
        mock_response = Mock(spec=Message)
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.stop_reason = "stop_sequence"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 18
        mock_response.usage.output_tokens = 9
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Temperature response"
        mock_response.content = [mock_text_block]
        claude_service.client.messages.create.return_value = mock_response
        
        result = claude_service.chat(
            messages, 
            temperature=temperature, 
            stop_sequences=stop_sequences
        )
        
        assert result == mock_response
        call_args = claude_service.client.messages.create.call_args
        assert call_args[1]["temperature"] == temperature
        assert call_args[1]["stop_sequences"] == stop_sequences

    def test_chat_exception_handling(self, claude_service):
        """Test that chat method handles exceptions properly."""
        messages = [{"role": "user", "content": "Hello"}]
        claude_service.client.messages.create.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            claude_service.chat(messages)