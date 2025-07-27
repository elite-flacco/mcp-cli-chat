#!/usr/bin/env python3
"""
Simple test web server to isolate issues
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Simple Test")

@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return """
    <html>
        <head><title>Test</title></head>
        <body>
            <h1>Simple Test Server</h1>
            <p>If you see this, the basic web server works.</p>
        </body>
    </html>
    """

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    print("Starting simple test server...")
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=False)