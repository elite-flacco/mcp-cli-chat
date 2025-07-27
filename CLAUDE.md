# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

This project uses uv for dependency management. Set up the environment:

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

Required environment variables in `.env`:
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `CLAUDE_MODEL`: Claude model to use (optional, defaults to empty)
- `USE_UV`: Set to "1" to use uv for running scripts (optional)

## Running the Application

### CLI Interface
```bash
# With uv (recommended)
uv run main.py

# Without uv
python main.py

# With additional MCP servers
uv run main.py additional_server.py
```

### Web Interface
```bash
# Start the web UI
uv run start_web.py

# Or with Python directly
python start_web.py
```
Then open your browser to http://localhost:8000

## Development Commands

### Testing

This project includes a comprehensive test suite using pytest. Install test dependencies:

```bash
# Install test dependencies
uv pip install -e ".[test]"
```

Run tests with these commands:

```bash
# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=core --cov=. --cov-report=html --cov-report=term-missing

# Run tests in verbose mode
uv run pytest -v

# Run only unit tests
uv run pytest -m unit

# Run only integration tests  
uv run pytest -m integration

# Run tests for a specific module
uv run pytest tests/core/test_claude.py

# Run tests with specific pattern
uv run pytest -k "test_chat"
```

Alternative using project scripts (if configured):
```bash
uv run test                    # Run all tests
uv run test-coverage          # Run with coverage
uv run test-verbose           # Run in verbose mode
uv run test-unit             # Run unit tests only
uv run test-integration      # Run integration tests only
```

### Test Structure

The test suite is organized as follows:

- `tests/core/test_claude.py` - Tests for Anthropic API wrapper
- `tests/core/test_chat.py` - Tests for base chat functionality  
- `tests/core/test_cli_chat.py` - Tests for CLI chat with document support
- `tests/test_mcp_server.py` - Tests for MCP document server
- `tests/test_mcp_client.py` - Tests for MCP client communication
- `tests/test_web_app.py` - Tests for FastAPI web interface
- `tests/conftest.py` - Shared fixtures and test configuration

### Test Markers

Tests are marked with the following categories:

- `@pytest.mark.unit` - Fast unit tests that don't require external dependencies
- `@pytest.mark.integration` - Integration tests that test component interactions
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.network` - Tests requiring network access (skipped by default)

### Coverage Reports

HTML coverage reports are generated in the `htmlcov/` directory. Open `htmlcov/index.html` in your browser to view detailed coverage information.

### Debugging Tests

For debugging failing tests:

```bash
# Run tests with Python debugger
uv run pytest --pdb

# Run tests with more detailed output
uv run pytest -vvv --tb=long

# Run a single test method
uv run pytest tests/core/test_claude.py::TestClaude::test_chat_basic -v
```

### MCP Debugging

To run the MCP inspector for debugging:
```bash
mcp dev mcp_server.py
```

## Architecture

This is an MCP (Model Control Protocol) chat application with the following core components:

### Core Structure
- `main.py`: Entry point that sets up logging, initializes MCP clients, and starts the CLI
- `web_app.py`: FastAPI web interface with WebSocket chat support
- `start_web.py`: Web server startup script
- `core/claude.py`: Anthropic API wrapper with comprehensive logging
- `core/cli_chat.py`: Main chat logic that handles document retrieval and command processing
- `core/cli.py`: CLI interface with auto-completion and command suggestions
- `mcp_server.py`: MCP server providing document tools, resources, and prompts
- `mcp_client.py`: MCP client for communicating with servers
- `templates/`: HTML templates for the web interface
- `static/`: CSS and static files built with Tailwind CSS

### Key Features
- **Document System**: Reference documents using `@document_id` syntax
- **Command System**: Execute prompts using `/command` syntax with tab completion
- **MCP Integration**: Extensible tool and resource system via MCP protocol
- **Auto-completion**: Smart completion for commands and document references

### Document Management
Documents are stored in `mcp_server.py` in the `docs` dictionary. The server provides:
- `read_doc_contents` tool for reading documents
- `edit_doc_contents` tool for editing documents
- Resource endpoints for listing and fetching documents
- Prompts like `format` for document processing

### Chat Flow
1. User input is processed by `CliChat._process_query()`
2. Commands starting with `/` are handled by `_process_command()`
3. Document references with `@` are extracted by `_extract_resources()`
4. Regular queries are sent to Claude with extracted document context

### Logging
Comprehensive logging is configured in `main.py` with both console and file output to `logs/` directory. The Claude service logs API requests, responses, and errors with detailed metadata.