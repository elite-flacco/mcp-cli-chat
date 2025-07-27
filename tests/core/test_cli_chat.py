"""Tests for core.cli_chat module."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from mcp.types import Prompt, PromptMessage

from core.cli_chat import CliChat, convert_prompt_message_to_message_param, convert_prompt_messages_to_message_params
from core.claude import Claude
from mcp_client import MCPClient


class TestCliChat:
    """Test the CliChat class."""

    @pytest.fixture
    def mock_claude_service(self):
        """Create a mock Claude service."""
        claude = Mock(spec=Claude)
        claude.chat = AsyncMock(return_value="Mock response")
        return claude

    @pytest.fixture
    def mock_doc_client(self):
        """Create a mock document client."""
        client = Mock(spec=MCPClient)
        client.list_prompts = AsyncMock()
        client.read_resource = AsyncMock()
        client.get_prompt = AsyncMock()
        return client

    @pytest.fixture
    def mock_clients(self, mock_doc_client):
        """Create mock MCP clients."""
        return {"doc_client": mock_doc_client}

    @pytest.fixture
    def cli_chat(self, mock_doc_client, mock_clients, mock_claude_service):
        """Create a CliChat instance for testing."""
        return CliChat(
            doc_client=mock_doc_client,
            clients=mock_clients,
            claude_service=mock_claude_service
        )

    def test_init(self, mock_doc_client, mock_clients, mock_claude_service):
        """Test CliChat initialization."""
        cli_chat = CliChat(
            doc_client=mock_doc_client,
            clients=mock_clients,
            claude_service=mock_claude_service
        )
        
        assert cli_chat.doc_client == mock_doc_client
        assert cli_chat.clients == mock_clients
        assert cli_chat.claude_service == mock_claude_service
        assert cli_chat.messages == []

    async def test_list_prompts(self, cli_chat):
        """Test listing available prompts."""
        mock_prompts = [
            Mock(spec=Prompt),
            Mock(spec=Prompt)
        ]
        cli_chat.doc_client.list_prompts.return_value = mock_prompts
        
        result = await cli_chat.list_prompts()
        
        assert result == mock_prompts
        cli_chat.doc_client.list_prompts.assert_called_once()

    async def test_list_docs_ids(self, cli_chat):
        """Test listing document IDs."""
        mock_doc_ids = ["doc1.pdf", "doc2.md", "doc3.txt"]
        cli_chat.doc_client.read_resource.return_value = mock_doc_ids
        
        result = await cli_chat.list_docs_ids()
        
        assert result == mock_doc_ids
        cli_chat.doc_client.read_resource.assert_called_once_with("docs://documents")

    async def test_get_doc_content(self, cli_chat):
        """Test getting document content."""
        doc_id = "test_doc.pdf"
        mock_content = "This is test document content."
        cli_chat.doc_client.read_resource.return_value = mock_content
        
        result = await cli_chat.get_doc_content(doc_id)
        
        assert result == mock_content
        cli_chat.doc_client.read_resource.assert_called_once_with(f"docs://documents/{doc_id}")

    async def test_get_prompt(self, cli_chat):
        """Test getting a prompt."""
        command = "summarize"
        doc_id = "test_doc.pdf"
        mock_messages = [Mock(spec=PromptMessage)]
        cli_chat.doc_client.get_prompt.return_value = mock_messages
        
        result = await cli_chat.get_prompt(command, doc_id)
        
        assert result == mock_messages
        cli_chat.doc_client.get_prompt.assert_called_once_with(command, {"doc_id": doc_id})

    async def test_extract_resources_with_mentions(self, cli_chat):
        """Test extracting resources from query with document mentions."""
        query = "Please analyze @report.pdf and @data.csv for insights"
        mock_doc_ids = ["report.pdf", "data.csv", "other.txt"]
        mock_content_1 = "Report content here"
        mock_content_2 = "CSV data here"
        
        cli_chat.doc_client.read_resource.side_effect = [
            mock_doc_ids,  # For list_docs_ids
            mock_content_1,  # For report.pdf
            mock_content_2   # For data.csv
        ]
        
        result = await cli_chat._extract_resources(query)
        
        expected = (
            '\n<document id="report.pdf">\nReport content here\n</document>\n'
            '\n<document id="data.csv">\nCSV data here\n</document>\n'
        )
        assert result == expected
        assert cli_chat.doc_client.read_resource.call_count == 3

    async def test_extract_resources_no_mentions(self, cli_chat):
        """Test extracting resources from query without mentions."""
        query = "Just a regular query without document references"
        mock_doc_ids = ["report.pdf", "data.csv"]
        
        cli_chat.doc_client.read_resource.return_value = mock_doc_ids
        
        result = await cli_chat._extract_resources(query)
        
        assert result == ""
        cli_chat.doc_client.read_resource.assert_called_once_with("docs://documents")

    async def test_extract_resources_invalid_mentions(self, cli_chat):
        """Test extracting resources with mentions that don't exist."""
        query = "Please analyze @nonexistent.pdf"
        mock_doc_ids = ["report.pdf", "data.csv"]
        
        cli_chat.doc_client.read_resource.return_value = mock_doc_ids
        
        result = await cli_chat._extract_resources(query)
        
        assert result == ""
        cli_chat.doc_client.read_resource.assert_called_once_with("docs://documents")

    async def test_process_command_valid(self, cli_chat):
        """Test processing a valid command."""
        query = "/summarize test_doc.pdf"
        mock_messages = [Mock(spec=PromptMessage)]
        cli_chat.doc_client.get_prompt.return_value = mock_messages
        
        with patch('core.cli_chat.convert_prompt_messages_to_message_params') as mock_convert:
            mock_convert.return_value = [{"role": "user", "content": "Summarize this document"}]
            
            result = await cli_chat._process_command(query)
        
        assert result is True
        cli_chat.doc_client.get_prompt.assert_called_once_with("summarize", {"doc_id": "test_doc.pdf"})
        assert len(cli_chat.messages) == 1

    async def test_process_command_no_doc_id(self, cli_chat):
        """Test processing a command without document ID."""
        query = "/format"
        mock_messages = [Mock(spec=PromptMessage)]
        cli_chat.doc_client.get_prompt.return_value = mock_messages
        
        with patch('core.cli_chat.convert_prompt_messages_to_message_params') as mock_convert:
            mock_convert.return_value = [{"role": "user", "content": "Format this"}]
            
            result = await cli_chat._process_command(query)
        
        assert result is True
        cli_chat.doc_client.get_prompt.assert_called_once_with("format", {"doc_id": ""})

    async def test_process_command_not_command(self, cli_chat):
        """Test processing a query that's not a command."""
        query = "This is not a command"
        
        result = await cli_chat._process_command(query)
        
        assert result is False
        cli_chat.doc_client.get_prompt.assert_not_called()

    async def test_process_query_as_command(self, cli_chat):
        """Test processing a query that is a command."""
        query = "/summarize report.pdf"
        mock_messages = [Mock(spec=PromptMessage)]
        cli_chat.doc_client.get_prompt.return_value = mock_messages
        
        with patch('core.cli_chat.convert_prompt_messages_to_message_params') as mock_convert:
            mock_convert.return_value = [{"role": "user", "content": "Summarize"}]
            
            await cli_chat._process_query(query)
        
        # Should process as command, not add regular query to messages
        assert len(cli_chat.messages) == 1
        assert "Summarize" in cli_chat.messages[0]["content"]

    async def test_process_query_regular_with_resources(self, cli_chat):
        """Test processing a regular query with document resources."""
        query = "What does @report.pdf say about sales?"
        mock_doc_ids = ["report.pdf"]
        mock_content = "Sales increased by 20%"
        
        cli_chat.doc_client.read_resource.side_effect = [
            mock_doc_ids,
            mock_content
        ]
        
        await cli_chat._process_query(query)
        
        assert len(cli_chat.messages) == 1
        message_content = cli_chat.messages[0]["content"]
        assert query in message_content
        assert "Sales increased by 20%" in message_content
        assert '<document id="report.pdf">' in message_content

    async def test_process_query_regular_no_resources(self, cli_chat):
        """Test processing a regular query without document resources."""
        query = "What is the weather like today?"
        mock_doc_ids = ["report.pdf"]
        
        cli_chat.doc_client.read_resource.return_value = mock_doc_ids
        
        await cli_chat._process_query(query)
        
        assert len(cli_chat.messages) == 1
        message_content = cli_chat.messages[0]["content"]
        assert query in message_content
        assert "context" in message_content.lower()

    async def test_process_query_async(self, cli_chat):
        """Test the async query processing method."""
        query = "Test async query"
        expected_response = "Async response"
        
        cli_chat.claude_service.chat.return_value = expected_response
        cli_chat.doc_client.read_resource.return_value = []
        
        result = await cli_chat.process_query_async(query)
        
        assert result == expected_response
        assert len(cli_chat.messages) == 2  # User query + assistant response
        assert cli_chat.messages[0]["role"] == "user"
        assert cli_chat.messages[1]["role"] == "assistant"
        assert cli_chat.messages[1]["content"] == expected_response


class TestPromptMessageConversion:
    """Test prompt message conversion functions."""

    def test_convert_prompt_message_text_dict(self):
        """Test converting a prompt message with text dict content."""
        mock_message = Mock(spec=PromptMessage)
        mock_message.role = "user"
        mock_message.content = {"type": "text", "text": "Hello world"}
        
        result = convert_prompt_message_to_message_param(mock_message)
        
        assert result == {"role": "user", "content": "Hello world"}

    def test_convert_prompt_message_text_object(self):
        """Test converting a prompt message with text object content."""
        mock_message = Mock(spec=PromptMessage)
        mock_message.role = "assistant"
        mock_content = Mock()
        mock_content.type = "text"
        mock_content.text = "Assistant response"
        mock_message.content = mock_content
        
        result = convert_prompt_message_to_message_param(mock_message)
        
        assert result == {"role": "assistant", "content": "Assistant response"}

    def test_convert_prompt_message_list_content(self):
        """Test converting a prompt message with list content."""
        mock_message = Mock(spec=PromptMessage)
        mock_message.role = "user"
        mock_message.content = [
            {"type": "text", "text": "First part"},
            {"type": "text", "text": "Second part"}
        ]
        
        result = convert_prompt_message_to_message_param(mock_message)
        
        expected_content = [
            {"type": "text", "text": "First part"},
            {"type": "text", "text": "Second part"}
        ]
        assert result == {"role": "user", "content": expected_content}

    def test_convert_prompt_message_list_with_objects(self):
        """Test converting a prompt message with list of objects."""
        mock_message = Mock(spec=PromptMessage)
        mock_message.role = "user"
        
        mock_item1 = Mock()
        mock_item1.type = "text"
        mock_item1.text = "Text block 1"
        
        mock_item2 = Mock()
        mock_item2.type = "text"
        mock_item2.text = "Text block 2"
        
        mock_message.content = [mock_item1, mock_item2]
        
        result = convert_prompt_message_to_message_param(mock_message)
        
        expected_content = [
            {"type": "text", "text": "Text block 1"},
            {"type": "text", "text": "Text block 2"}
        ]
        assert result == {"role": "user", "content": expected_content}

    def test_convert_prompt_message_empty_fallback(self):
        """Test converting a prompt message that falls back to empty content."""
        mock_message = Mock(spec=PromptMessage)
        mock_message.role = "user"
        mock_message.content = "Invalid content type"
        
        result = convert_prompt_message_to_message_param(mock_message)
        
        assert result == {"role": "user", "content": ""}

    def test_convert_prompt_messages_to_message_params(self):
        """Test converting multiple prompt messages."""
        mock_message1 = Mock(spec=PromptMessage)
        mock_message1.role = "user"
        mock_message1.content = {"type": "text", "text": "First message"}
        
        mock_message2 = Mock(spec=PromptMessage)
        mock_message2.role = "assistant"
        mock_message2.content = {"type": "text", "text": "Second message"}
        
        messages = [mock_message1, mock_message2]
        
        result = convert_prompt_messages_to_message_params(messages)
        
        expected = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Second message"}
        ]
        assert result == expected