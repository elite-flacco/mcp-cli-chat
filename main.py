import asyncio
import sys
import os
import gc
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from contextlib import AsyncExitStack

from mcp_client import MCPClient
from core.claude import Claude
from core.cli_chat import CliChat
from core.cli import CliApp

# Load environment variables
load_dotenv()

def setup_logging():
    """Set up comprehensive logging configuration with file-only handlers for detailed communication tracking."""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create a timestamp for the log files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create separate log files for different components
    main_log_file = logs_dir / f"main_{timestamp}.log"
    conversation_log_file = logs_dir / f"conversation_{timestamp}.log"
    mcp_log_file = logs_dir / f"mcp_communication_{timestamp}.log"
    
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure root logger to only log to files
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            # Main application log file
            logging.FileHandler(main_log_file, encoding='utf-8')
        ]
    )
    
    # Create specialized loggers
    
    # Conversation logger for Claude API communications
    conversation_logger = logging.getLogger('conversation')
    conversation_handler = logging.FileHandler(conversation_log_file, encoding='utf-8')
    conversation_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    conversation_logger.addHandler(conversation_handler)
    conversation_logger.setLevel(logging.INFO)
    conversation_logger.propagate = False  # Don't propagate to root logger
    
    # MCP communication logger
    mcp_logger = logging.getLogger('mcp')
    mcp_handler = logging.FileHandler(mcp_log_file, encoding='utf-8')
    mcp_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    mcp_logger.addHandler(mcp_handler)
    mcp_logger.setLevel(logging.DEBUG)
    mcp_logger.propagate = False  # Don't propagate to root logger
    
    # Suppress noisy HTTP loggers
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("=== CLI CHAT APPLICATION STARTED ===")
    logger.info(f"Main log: {main_log_file.absolute()}")
    logger.info(f"Conversation log: {conversation_log_file.absolute()}")
    logger.info(f"MCP communication log: {mcp_log_file.absolute()}")
    
    return logger

# Anthropic Config
claude_model = os.getenv("CLAUDE_MODEL", "")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")


assert claude_model, "Error: CLAUDE_MODEL cannot be empty. Update .env"
assert anthropic_api_key, (
    "Error: ANTHROPIC_API_KEY cannot be empty. Update .env"
)


async def main():
    # Set up logging
    logger = setup_logging()
    
    try:
        logger.info("Starting CLI Chat application")
        logger.info(f"Using Claude model: {claude_model}")
        
        claude_service = Claude(model=claude_model)

        server_scripts = sys.argv[1:]
        clients = {}

        command, args = (
            ("uv", ["run", "mcp_server.py"])
            if os.getenv("USE_UV", "0") == "1"
            else ("python", ["mcp_server.py"])
        )

        async with AsyncExitStack() as stack:
            doc_client = await stack.enter_async_context(
                MCPClient(command=command, args=args)
            )
            clients["doc_client"] = doc_client

            for i, server_script in enumerate(server_scripts):
                client_id = f"client_{i}_{server_script}"
                client = await stack.enter_async_context(
                    MCPClient(command="uv", args=["run", server_script])
                )
                clients[client_id] = client

            chat = CliChat(
                doc_client=doc_client,
                clients=clients,
                claude_service=claude_service,
            )

            cli = CliApp(chat)
            await cli.initialize()
            await cli.run()

            # Give asyncio time to finalize transports and close pipes
            await asyncio.sleep(0.1)
            gc.collect()  # Trigger finalizers
            
            logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.critical("Application error", exc_info=True)
        raise


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
