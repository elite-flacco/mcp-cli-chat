"""Tests for mcp_server module."""
import pytest
from unittest.mock import patch, Mock
from mcp.server.fastmcp.prompts.base import UserMessage

# Import the functions and data directly from mcp_server
import mcp_server
from mcp_server import read_document, edit_document, list_docs, fetch_doc, format_document, docs


class TestMCPServerTools:
    """Test MCP server tool functions."""

    def setup_method(self):
        """Reset docs to original state before each test."""
        mcp_server.docs = {
            "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
            "report.pdf": "The report details the state of a 20m condenser tower.",
            "financials.docx": "These financials outline the project's budget and expenditures.",
            "outlook.pdf": "This document presents the projected future performance of the system.",
            "plan.md": "The plan outlines the steps for the project's implementation.",
            "spec.txt": "These specifications define the technical requirements for the equipment.",
        }

    def test_read_document_valid_id(self):
        """Test reading a document with valid ID."""
        doc_id = "report.pdf"
        expected_content = "The report details the state of a 20m condenser tower."
        
        result = read_document(doc_id)
        
        assert result == expected_content

    def test_read_document_invalid_id(self):
        """Test reading a document with invalid ID raises ValueError."""
        doc_id = "nonexistent.pdf"
        
        with pytest.raises(ValueError, match="Document with id nonexistent.pdf not found"):
            read_document(doc_id)

    def test_read_document_all_docs(self):
        """Test reading all available documents."""
        for doc_id, expected_content in docs.items():
            result = read_document(doc_id)
            assert result == expected_content

    def test_edit_document_valid_replacement(self):
        """Test editing a document with valid replacement."""
        doc_id = "report.pdf"
        old_content = "20m condenser tower"
        new_content = "25m condenser tower"
        expected_result = "The report details the state of a 25m condenser tower."
        
        result = edit_document(doc_id, old_content, new_content)
        
        assert result == expected_result
        # Verify the document was actually updated
        assert docs[doc_id] == expected_result

    def test_edit_document_invalid_id(self):
        """Test editing a document with invalid ID raises ValueError."""
        doc_id = "nonexistent.pdf"
        old_content = "test"
        new_content = "new test"
        
        with pytest.raises(ValueError, match="Document with id nonexistent.pdf not found"):
            edit_document(doc_id, old_content, new_content)

    def test_edit_document_no_match(self):
        """Test editing a document where old_content doesn't exist."""
        doc_id = "report.pdf"
        old_content = "nonexistent text"
        new_content = "replacement text"
        original_content = docs[doc_id]
        
        result = edit_document(doc_id, old_content, new_content)
        
        # Should return original content unchanged
        assert result == original_content
        assert docs[doc_id] == original_content

    def test_edit_document_multiple_replacements(self):
        """Test editing a document with multiple occurrences of old_content."""
        doc_id = "report.pdf"
        # First, modify the document to have repeated text
        docs[doc_id] = "The report details the state. The report is important."
        old_content = "The report"
        new_content = "This report"
        expected_result = "This report details the state. This report is important."
        
        result = edit_document(doc_id, old_content, new_content)
        
        assert result == expected_result
        assert docs[doc_id] == expected_result

    def test_edit_document_empty_replacement(self):
        """Test editing a document by removing text (empty replacement)."""
        doc_id = "report.pdf"
        old_content = " condenser"
        new_content = ""
        expected_result = "The report details the state of a 20m tower."
        
        result = edit_document(doc_id, old_content, new_content)
        
        assert result == expected_result
        assert docs[doc_id] == expected_result


class TestMCPServerResources:
    """Test MCP server resource functions."""

    def setup_method(self):
        """Reset docs to original state before each test."""
        mcp_server.docs = {
            "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
            "report.pdf": "The report details the state of a 20m condenser tower.",
            "financials.docx": "These financials outline the project's budget and expenditures.",
            "outlook.pdf": "This document presents the projected future performance of the system.",
            "plan.md": "The plan outlines the steps for the project's implementation.",
            "spec.txt": "These specifications define the technical requirements for the equipment.",
        }

    def test_list_docs(self):
        """Test listing all document IDs."""
        result = list_docs()
        
        expected_keys = list(docs.keys())
        assert isinstance(result, list)
        assert set(result) == set(expected_keys)
        assert len(result) == len(expected_keys)

    def test_list_docs_empty(self):
        """Test listing docs when docs dictionary is empty."""
        mcp_server.docs = {}
        
        result = list_docs()
        
        assert result == []

    def test_fetch_doc_valid_id(self):
        """Test fetching a document with valid ID."""
        doc_id = "financials.docx"
        expected_content = "These financials outline the project's budget and expenditures."
        
        result = fetch_doc(doc_id)
        
        assert result == expected_content

    def test_fetch_doc_invalid_id(self):
        """Test fetching a document with invalid ID raises ValueError."""
        doc_id = "missing.txt"
        
        with pytest.raises(ValueError, match="Doc with id missing.txt not found"):
            fetch_doc(doc_id)

    def test_fetch_doc_all_docs(self):
        """Test fetching all available documents."""
        for doc_id, expected_content in docs.items():
            result = fetch_doc(doc_id)
            assert result == expected_content


class TestMCPServerPrompts:
    """Test MCP server prompt functions."""

    def test_format_document_prompt_structure(self):
        """Test that format_document returns correct prompt structure."""
        doc_id = "test_doc.pdf"
        
        result = format_document(doc_id)
        
        # Should return a list with one UserMessage
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], UserMessage)

    def test_format_document_prompt_content(self):
        """Test that format_document prompt contains expected content."""
        doc_id = "report.pdf"
        
        result = format_document(doc_id)
        
        message = result[0]
        prompt_content = message.content
        
        # Check that the prompt contains expected elements
        assert doc_id in prompt_content
        assert "markdown" in prompt_content.lower()
        assert "edit_document" in prompt_content
        assert "headers" in prompt_content
        assert "bullet points" in prompt_content
        assert "<document_id>" in prompt_content
        assert "</document_id>" in prompt_content

    def test_format_document_different_doc_ids(self):
        """Test format_document with different document IDs."""
        doc_ids = ["test1.md", "test2.pdf", "test3.docx"]
        
        for doc_id in doc_ids:
            result = format_document(doc_id)
            message = result[0]
            
            assert doc_id in message.content
            assert isinstance(result, list)
            assert len(result) == 1

    def test_format_document_prompt_instructions(self):
        """Test that format_document prompt contains proper instructions."""
        doc_id = "example.txt"
        
        result = format_document(doc_id)
        
        prompt_content = result[0].content
        
        # Check for key instructions
        assert "reformat" in prompt_content.lower()
        assert "don't change the meaning" in prompt_content.lower()
        assert "don't explain your changes" in prompt_content.lower()
        assert "final version" in prompt_content.lower()


class TestMCPServerIntegration:
    """Integration tests for MCP server functionality."""

    def setup_method(self):
        """Reset docs to original state before each test."""
        mcp_server.docs = {
            "test.md": "# Original Title\nThis is the original content.",
        }

    def test_read_edit_cycle(self):
        """Test reading, editing, and reading again."""
        doc_id = "test.md"
        
        # Read original content
        original = read_document(doc_id)
        assert "Original Title" in original
        
        # Edit the document
        edited = edit_document(doc_id, "Original Title", "Updated Title")
        assert "Updated Title" in edited
        assert "Original Title" not in edited
        
        # Read again to verify persistence
        updated = read_document(doc_id)
        assert updated == edited
        assert "Updated Title" in updated

    def test_list_and_fetch_consistency(self):
        """Test that list_docs and fetch_doc are consistent."""
        # Get list of all doc IDs
        doc_ids = list_docs()
        
        # Verify we can fetch each listed document
        for doc_id in doc_ids:
            content = fetch_doc(doc_id)
            assert isinstance(content, str)
            assert len(content) > 0
            
            # Also verify read_document works for the same ID
            read_content = read_document(doc_id)
            assert content == read_content

    def test_multiple_edits_same_document(self):
        """Test multiple sequential edits on the same document."""
        doc_id = "test.md"
        
        # First edit
        result1 = edit_document(doc_id, "Original", "First")
        assert "First Title" in result1
        
        # Second edit
        result2 = edit_document(doc_id, "First", "Second")
        assert "Second Title" in result2
        assert "First Title" not in result2
        
        # Third edit
        result3 = edit_document(doc_id, "original", "final")
        assert "final content" in result3
        
        # Verify final state
        final_content = read_document(doc_id)
        assert final_content == result3

    def test_format_prompt_with_existing_doc(self):
        """Test format prompt references an existing document."""
        doc_id = "test.md"
        
        # Ensure the document exists
        assert doc_id in docs
        
        # Get format prompt
        messages = format_document(doc_id)
        prompt_content = messages[0].content
        
        # Verify the prompt references the existing document
        assert doc_id in prompt_content
        
        # The prompt should instruct to use edit_document tool
        assert "edit_document" in prompt_content