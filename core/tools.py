import json
import logging
from typing import Optional, Literal, List
from mcp.types import CallToolResult, Tool, TextContent
from mcp_client import MCPClient
from anthropic.types import Message, ToolResultBlockParam

# Set up logging
logger = logging.getLogger(__name__)


class ToolManager:
    @classmethod
    async def get_all_tools(cls, clients: dict[str, MCPClient]) -> list[Tool]:
        """Gets all tools from the provided clients."""
        logger.debug(f"Collecting tools from {len(clients)} MCP clients")
        tools = []
        for client_id, client in clients.items():
            logger.debug(f"Getting tools from client: {client_id}")
            tool_models = await client.list_tools()
            client_tools = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                }
                for t in tool_models
            ]
            tools += client_tools
            logger.debug(f"Client {client_id} provided {len(client_tools)} tools: {[t['name'] for t in client_tools]}")
        
        logger.info(f"Total tools available: {len(tools)}")
        return tools

    @classmethod
    async def _find_client_with_tool(
        cls, clients: list[MCPClient], tool_name: str
    ) -> Optional[MCPClient]:
        """Finds the first client that has the specified tool."""
        logger.debug(f"Searching for tool '{tool_name}' across {len(clients)} clients")
        for client in clients:
            tools = await client.list_tools()
            tool = next((t for t in tools if t.name == tool_name), None)
            if tool:
                logger.debug(f"Found tool '{tool_name}' in client {client._client_id}")
                return client
        
        logger.warning(f"Tool '{tool_name}' not found in any client")
        return None

    @classmethod
    def _build_tool_result_part(
        cls,
        tool_use_id: str,
        text: str,
        status: Literal["success"] | Literal["error"],
    ) -> ToolResultBlockParam:
        """Builds a tool result part dictionary."""
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": text,
            "is_error": status == "error",
        }

    @classmethod
    async def execute_tool_requests(
        cls, clients: dict[str, MCPClient], message: Message
    ) -> List[ToolResultBlockParam]:
        """Executes a list of tool requests against the provided clients."""
        tool_requests = [
            block for block in message.content if block.type == "tool_use"
        ]
        
        logger.info(f"Executing {len(tool_requests)} tool requests")
        for req in tool_requests:
            logger.info(f"  - {req.name} (ID: {req.id})")
        
        tool_result_blocks: list[ToolResultBlockParam] = []
        
        for tool_request in tool_requests:
            tool_use_id = tool_request.id
            tool_name = tool_request.name
            tool_input = tool_request.input
            
            logger.info(f"Executing tool '{tool_name}' with ID {tool_use_id}")
            logger.debug(f"Tool input: {tool_input}")

            client = await cls._find_client_with_tool(
                list(clients.values()), tool_name
            )

            if not client:
                logger.error(f"Could not find client for tool '{tool_name}'")
                tool_result_part = cls._build_tool_result_part(
                    tool_use_id, "Could not find that tool", "error"
                )
                tool_result_blocks.append(tool_result_part)
                continue

            try:
                logger.debug(f"Calling tool '{tool_name}' on client {client._client_id}")
                tool_output: CallToolResult | None = await client.call_tool(
                    tool_name, tool_input
                )
                
                items = []
                if tool_output:
                    items = tool_output.content
                    logger.debug(f"Tool output contains {len(items)} content items")
                
                content_list = [
                    item.text for item in items if isinstance(item, TextContent)
                ]
                content_json = json.dumps(content_list)
                
                is_error = tool_output and tool_output.isError
                status = "error" if is_error else "success"
                
                tool_result_part = cls._build_tool_result_part(
                    tool_use_id, content_json, status
                )
                
                logger.info(f"Tool '{tool_name}' completed with status: {status}")
                if is_error:
                    logger.warning(f"Tool '{tool_name}' returned error: {content_json}")
                
            except Exception as e:
                error_message = f"Error executing tool '{tool_name}': {e}"
                logger.error(error_message)
                print(error_message)
                tool_result_part = cls._build_tool_result_part(
                    tool_use_id,
                    json.dumps({"error": error_message}),
                    "error"
                )

            tool_result_blocks.append(tool_result_part)
        
        logger.info(f"Completed execution of {len(tool_result_blocks)} tools")
        return tool_result_blocks
