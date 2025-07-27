#!/usr/bin/env python3
"""
Quick test script to verify the web interface setup
"""
import sys
import os
from pathlib import Path

def test_web_interface():
    print("Testing Claude Chat Web Interface...")
    
    # Check if CSS was built
    css_file = Path("static/dist/style.css")
    if css_file.exists():
        print("[OK] CSS build successful")
        print(f"     CSS file size: {css_file.stat().st_size} bytes")
    else:
        print("[ERROR] CSS file not found")
        return False
    
    # Check HTML template
    html_file = Path("templates/chat.html")
    if html_file.exists():
        print("[OK] HTML template exists")
    else:
        print("[ERROR] HTML template not found")
        return False
    
    # Check if environment variables are set
    from dotenv import load_dotenv
    load_dotenv()
    
    if os.getenv("ANTHROPIC_API_KEY"):
        print("[OK] ANTHROPIC_API_KEY is set")
    else:
        print("[ERROR] ANTHROPIC_API_KEY not set")
        return False
        
    if os.getenv("CLAUDE_MODEL"):
        print("[OK] CLAUDE_MODEL is set")
    else:
        print("[ERROR] CLAUDE_MODEL not set")
        return False
    
    print("\n[SUCCESS] Web interface setup complete!")
    print("Run 'uv run start_web.py' and open http://localhost:8000")
    return True

if __name__ == "__main__":
    success = test_web_interface()
    sys.exit(0 if success else 1)