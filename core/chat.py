import logging
from core.claude import Claude
from mcp_client import MCPClient
from core.tools import ToolManager
from anthropic.types import MessageParam

# Set up logging
logger = logging.getLogger(__name__)


class Chat:
    def __init__(self, claude_service: Claude, clients: dict[str, MCPClient]):
        self.claude_service: Claude = claude_service
        self.clients: dict[str, MCPClient] = clients
        self.messages: list[MessageParam] = []

    async def _process_query(self, query: str):
        logger.info(f"Base chat processing query: {query[:50]}...")
        self.messages.append({"role": "user", "content": query})
        logger.debug(f"Added user message to conversation. Total messages: {len(self.messages)}")

    async def run(
        self,
        query: str,
    ) -> str:
        logger.info("=== STARTING CHAT SESSION ===")
        logger.info(f"User query: {query}")
        
        final_text_response = ""

        await self._process_query(query)

        # Get available tools
        all_tools = await ToolManager.get_all_tools(self.clients)
        logger.info(f"Available tools for conversation: {len(all_tools)} tools")
        for tool in all_tools:
            logger.debug(f"  - {tool.get('name', 'unknown')}")

        iteration = 0
        while True:
            iteration += 1
            logger.info(f"=== CHAT ITERATION {iteration} ===")
            logger.debug(f"Sending {len(self.messages)} messages to Claude")

            response = self.claude_service.chat(
                messages=self.messages,
                tools=all_tools,
            )

            self.claude_service.add_assistant_message(self.messages, response)

            if response.stop_reason == "tool_use":
                logger.info("Claude requested tool execution")
                response_text = self.claude_service.text_from_message(response)
                if response_text:
                    print(response_text)
                    logger.debug(f"Displayed intermediate response to user: {response_text[:100]}...")
                
                logger.info("Executing tool requests...")
                tool_result_parts = await ToolManager.execute_tool_requests(
                    self.clients, response
                )

                self.claude_service.add_user_message(
                    self.messages, tool_result_parts
                )
                logger.info("Tool results added to conversation, continuing...")
            else:
                logger.info(f"Conversation completed with stop reason: {response.stop_reason}")
                final_text_response = self.claude_service.text_from_message(
                    response
                )
                logger.info(f"Final response length: {len(final_text_response)} characters")
                break

        logger.info("=== CHAT SESSION COMPLETED ===")
        return final_text_response
