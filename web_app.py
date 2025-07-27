from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import asyncio
import sys
from typing import List
import logging

from core.cli_chat import CliChat
from core.claude import Claude

# Fix Windows subprocess issue
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="Claude Chat Web UI")

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global chat instance
chat_instance = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    global chat_instance
    print("Web app started successfully")
    print("Ready to accept connections")

@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        # Use simplified chat without MCP for now to avoid startup issues
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        claude_model = os.getenv("CLAUDE_MODEL", "")
        claude_service = Claude(model=claude_model)
        
        class SimpleChatFallback:
            def __init__(self, claude_service):
                self.claude_service = claude_service
                self.messages = []
            
            async def process_query_async(self, query):
                self.messages.append({"role": "user", "content": query})
                response = await self.claude_service.chat(self.messages)
                self.messages.append({"role": "assistant", "content": response})
                return response
        
        session_chat = SimpleChatFallback(claude_service)
        print("WebSocket connected with simplified chat")
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat":
                user_message = message_data.get("message", "")
                
                # Process the message
                response = await session_chat.process_query_async(user_message)
                
                # Send response back
                await manager.send_personal_message(
                    json.dumps({"type": "response", "content": response}),
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket connection closed")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await manager.send_personal_message(
            json.dumps({"type": "error", "content": str(e)}),
            websocket
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)