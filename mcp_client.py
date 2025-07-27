import gc
import json
import sys
import asyncio
import logging
from typing import Optional, Any
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl

# Set up MCP logging
mcp_logger = logging.getLogger('mcp.client')


class MCPClient:
    def __init__(
        self,
        command: str,
        args: list[str],
        env: Optional[dict] = None,
    ):
        self._command = command
        self._args = args
        self._env = env
        self._session: Optional[ClientSession] = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()
        self._client_id = f"{command}_{'-'.join(args)}"
        
        mcp_logger.info(f"Initializing MCP client: {self._client_id}")
        mcp_logger.debug(f"Command: {command}, Args: {args}, Env: {env}")

    async def connect(self):
        mcp_logger.info(f"Connecting to MCP server: {self._client_id}")
        
        server_params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=self._env,
        )
        
        try:
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            _stdio, _write = stdio_transport
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(_stdio, _write)
            )
            await self._session.initialize()
            
            mcp_logger.info(f"Successfully connected to MCP server: {self._client_id}")
            
        except Exception as e:
            mcp_logger.error(f"Failed to connect to MCP server {self._client_id}: {e}")
            raise

    def session(self) -> ClientSession:
        if self._session is None:
            raise ConnectionError(
                "Client session not initialized or cache not populated. Call connect_to_server first."
            )
        return self._session

    async def list_tools(self) -> list[types.Tool]:
        mcp_logger.debug(f"Listing tools from server: {self._client_id}")
        result = await self.session().list_tools()
        mcp_logger.info(f"Retrieved {len(result.tools)} tools from {self._client_id}: {[tool.name for tool in result.tools]}")
        return result.tools

    async def call_tool(
        self, tool_name: str, tool_input: dict
    ) -> types.CallToolResult | None:
        mcp_logger.info(f"Calling tool '{tool_name}' on server {self._client_id}")
        mcp_logger.debug(f"Tool input: {tool_input}")
        
        try:
            result = await self.session().call_tool(tool_name, tool_input)
            mcp_logger.info(f"Tool '{tool_name}' completed successfully")
            mcp_logger.debug(f"Tool result: {result}")
            return result
        except Exception as e:
            mcp_logger.error(f"Tool '{tool_name}' failed on server {self._client_id}: {e}")
            raise

    async def list_prompts(self) -> list[types.Prompt]:
        mcp_logger.debug(f"Listing prompts from server: {self._client_id}")
        result = await self.session().list_prompts()
        mcp_logger.info(f"Retrieved {len(result.prompts)} prompts from {self._client_id}: {[prompt.name for prompt in result.prompts]}")
        return result.prompts

    async def get_prompt(self, prompt_name, args: dict[str, str]):
        mcp_logger.info(f"Getting prompt '{prompt_name}' from server {self._client_id}")
        mcp_logger.debug(f"Prompt args: {args}")
        
        try:
            result = await self.session().get_prompt(prompt_name, args)
            mcp_logger.info(f"Prompt '{prompt_name}' retrieved successfully with {len(result.messages)} messages")
            return result.messages
        except Exception as e:
            mcp_logger.error(f"Failed to get prompt '{prompt_name}' from server {self._client_id}: {e}")
            raise

    async def read_resource(self, uri: str) -> Any:
        mcp_logger.info(f"Reading resource '{uri}' from server {self._client_id}")
        
        try:
            result = await self.session().read_resource(AnyUrl(uri))
            resource = result.contents[0]

            if isinstance(resource, types.TextResourceContents):
                mcp_logger.debug(f"Resource '{uri}' is text content with MIME type: {resource.mimeType}")
                if resource.mimeType == "application/json":
                    parsed_data = json.loads(resource.text)
                    mcp_logger.info(f"Resource '{uri}' parsed as JSON")
                    return parsed_data
                
                mcp_logger.info(f"Resource '{uri}' returned as text content")
                return resource.text
            else:
                mcp_logger.warning(f"Resource '{uri}' is not text content: {type(resource)}")
                return resource
        except Exception as e:
            mcp_logger.error(f"Failed to read resource '{uri}' from server {self._client_id}: {e}")
            raise

    async def cleanup(self):
        mcp_logger.info(f"Cleaning up MCP client: {self._client_id}")
        await self._exit_stack.aclose()
        self._session = None
        mcp_logger.debug(f"MCP client cleanup completed: {self._client_id}")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


# For testing
async def main():
    async with MCPClient(
        # If using Python without UV, update command to 'python' and remove "run" from args.
        command="uv",
        args=["run", "mcp_server.py"],
    ) as _client:
        # result = await _client.call_tool("read_doc_contents", {"doc_id": "deposition.md"})
        result = await _client.list_tools()
        print(result)

    # Give asyncio time to finalize transports and close pipes
    await asyncio.sleep(0.1)
    gc.collect()  # Trigger finalizers


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
