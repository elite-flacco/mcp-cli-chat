#!/usr/bin/env python3
"""
Start the web UI for Claude Chat
"""
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Check required environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set in .env file")
        exit(1)
    
    if not os.getenv("CLAUDE_MODEL"):
        print("Error: CLAUDE_MODEL not set in .env file")
        exit(1)
    
    print("Starting Claude Chat Web UI...")
    print("Open your browser to: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )