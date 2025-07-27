import logging
from typing import Optional, Dict, Any, List, Union
from anthropic import Anthropic
from anthropic.types import Message, MessageParam

# Set up logging
logger = logging.getLogger(__name__)
conversation_logger = logging.getLogger('conversation')

class Claude:
    def __init__(self, model: str):
        self.client = Anthropic()
        self.model = model

    def add_user_message(self, messages: list, message):
        user_message = {
            "role": "user",
            "content": message.content
            if isinstance(message, Message)
            else message,
        }
        messages.append(user_message)

    def add_assistant_message(self, messages: list, message):
        assistant_message = {
            "role": "assistant",
            "content": message.content
            if isinstance(message, Message)
            else message,
        }
        messages.append(assistant_message)

    def text_from_message(self, message: Message):
        return "\n".join(
            [block.text for block in message.content if block.type == "text"]
        )

    def chat(
        self,
        messages: List[MessageParam],
        system: Optional[str] = None,
        temperature: float = 1.0,
        stop_sequences: List[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        thinking: bool = False,
        thinking_budget: int = 1024,
    ) -> Message:
        """
        Send a chat message to the Claude API with logging.
        
        Args:
            messages: List of message objects for the conversation
            system: Optional system message to set the assistant's behavior
            temperature: Controls randomness in the response (0.0 to 1.0)
            stop_sequences: List of strings that will stop generation if encountered
            tools: List of tools the model can use
            thinking: Whether to enable thinking mode
            thinking_budget: Token budget for thinking when thinking mode is enabled
            
        Returns:
            Message: The assistant's response message
        """
        if stop_sequences is None:
            stop_sequences = []
            
        params: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 8000,
            "messages": messages,
            "temperature": temperature,
            "stop_sequences": stop_sequences,
        }

        if thinking:
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            }

        if tools:
            params["tools"] = tools

        if system:
            params["system"] = system

        # Log the request metadata
        logger.info(
            "Sending request to Claude API",
            extra={
                "model": self.model,
                "message_count": len(messages),
                "has_tools": bool(tools),
                "has_system": bool(system),
                "temperature": temperature,
            },
        )
        
        # Log conversation to dedicated conversation log
        conversation_logger.info("=" * 80)
        conversation_logger.info("NEW CLAUDE API REQUEST")
        conversation_logger.info(f"Model: {self.model} | Messages: {len(messages)} | Tools: {bool(tools)} | Temperature: {temperature}")
        
        if system:
            conversation_logger.info("SYSTEM MESSAGE:")
            conversation_logger.info(f"{system}")
            conversation_logger.info("-" * 40)
        
        conversation_logger.info("CONVERSATION HISTORY:")
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            conversation_logger.info(f"[{i+1}] {role}:")
            conversation_logger.info(f"{content}")
            conversation_logger.info("-" * 40)
        
        if tools:
            conversation_logger.info(f"AVAILABLE TOOLS: {len(tools)} tools")
            for tool in tools:
                tool_name = tool.get("name", "unknown")
                conversation_logger.info(f"  - {tool_name}")
            conversation_logger.info("-" * 40)
        
        logger.debug("Claude API request details", extra={"params": params})

        try:
            # Make the API call
            message = self.client.messages.create(**params)
            
            # Log the successful response metadata
            logger.info(
                "Received response from Claude API",
                extra={
                    "model": message.model,
                    "stop_reason": message.stop_reason,
                    "usage": {
                        "input_tokens": message.usage.input_tokens,
                        "output_tokens": message.usage.output_tokens,
                    },
                },
            )
            
            # Log the assistant's response to conversation log
            response_text = self.text_from_message(message)
            conversation_logger.info("CLAUDE RESPONSE:")
            conversation_logger.info(f"Stop Reason: {message.stop_reason}")
            conversation_logger.info(f"Tokens - Input: {message.usage.input_tokens}, Output: {message.usage.output_tokens}")
            conversation_logger.info("Response Content:")
            conversation_logger.info(response_text)
            
            # Log tool calls if present
            if hasattr(message, 'content') and message.content:
                tool_calls = [block for block in message.content if hasattr(block, 'type') and block.type == 'tool_use']
                if tool_calls:
                    conversation_logger.info("TOOL CALLS:")
                    for tool_call in tool_calls:
                        conversation_logger.info(f"  Tool: {tool_call.name}")
                        conversation_logger.info(f"  Input: {tool_call.input}")
            
            conversation_logger.info("=" * 80)
            
            logger.debug("Claude API response details", extra={"response": message.model_dump()})
            
            return message
            
        except Exception as e:
            # Log any errors
            logger.error(
                "Error calling Claude API",
                exc_info=True,
                extra={
                    "error": str(e),
                    "model": self.model,
                    "message_count": len(messages),
                },
            )
            raise  # Re-raise the exception for the caller to handle
