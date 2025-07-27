import logging
from typing import List, Tuple
from mcp.types import Prompt, PromptMessage
from anthropic.types import MessageParam

from core.chat import Chat
from core.claude import Claude
from mcp_client import MCPClient

# Set up logging
logger = logging.getLogger(__name__)


class CliChat(Chat):
    def __init__(
        self,
        doc_client: MCPClient,
        clients: dict[str, MCPClient],
        claude_service: Claude,
    ):
        super().__init__(clients=clients, claude_service=claude_service)

        self.doc_client: MCPClient = doc_client

    async def list_prompts(self) -> list[Prompt]:
        return await self.doc_client.list_prompts()

    async def list_docs_ids(self) -> list[str]:
        logger.debug("Listing available document IDs")
        doc_ids = await self.doc_client.read_resource("docs://documents")
        logger.info(f"Found {len(doc_ids)} available documents: {doc_ids}")
        return doc_ids

    async def get_doc_content(self, doc_id: str) -> str:
        logger.info(f"Retrieving content for document: {doc_id}")
        content = await self.doc_client.read_resource(f"docs://documents/{doc_id}")
        logger.debug(f"Document '{doc_id}' content length: {len(content)} characters")
        return content

    async def get_prompt(
        self, command: str, doc_id: str
    ) -> list[PromptMessage]:
        logger.info(f"Getting prompt '{command}' for document: {doc_id}")
        messages = await self.doc_client.get_prompt(command, {"doc_id": doc_id})
        logger.debug(f"Prompt '{command}' returned {len(messages)} messages")
        return messages

    async def _extract_resources(self, query: str) -> str:
        logger.debug(f"Extracting document references from query: {query[:100]}...")
        mentions = [word[1:] for word in query.split() if word.startswith("@")]
        logger.info(f"Found document mentions: {mentions}")

        doc_ids = await self.list_docs_ids()
        mentioned_docs: list[Tuple[str, str]] = []

        for doc_id in doc_ids:
            if doc_id in mentions:
                logger.info(f"Loading content for mentioned document: {doc_id}")
                content = await self.get_doc_content(doc_id)
                mentioned_docs.append((doc_id, content))

        if mentioned_docs:
            logger.info(f"Successfully loaded {len(mentioned_docs)} referenced documents")
        else:
            logger.debug("No document references found or loaded")

        return "".join(
            f'\n<document id="{doc_id}">\n{content}\n</document>\n'
            for doc_id, content in mentioned_docs
        )

    async def _process_command(self, query: str) -> bool:
        if not query.startswith("/"):
            return False

        logger.info(f"Processing command: {query}")
        words = query.split()
        command = words[0].replace("/", "")
        doc_id = words[1] if len(words) > 1 else ""
        
        logger.info(f"Executing command '{command}' with document: {doc_id}")

        messages = await self.doc_client.get_prompt(
            command, {"doc_id": doc_id}
        )

        converted_messages = convert_prompt_messages_to_message_params(messages)
        self.messages += converted_messages
        logger.info(f"Command '{command}' added {len(converted_messages)} messages to conversation")
        return True

    async def _process_query(self, query: str):
        logger.info(f"Processing user query: {query[:100]}...")
        
        if await self._process_command(query):
            logger.info("Query processed as command")
            return

        logger.debug("Query is not a command, processing as regular query")
        added_resources = await self._extract_resources(query)

        prompt = f"""
        The user has a question:
        <query>
        {query}
        </query>

        The following context may be useful in answering their question:
        <context>
        {added_resources}
        </context>

        Note the user's query might contain references to documents like "@report.docx". The "@" is only
        included as a way of mentioning the doc. The actual name of the document would be "report.docx".
        If the document content is included in this prompt, you don't need to use an additional tool to read the document.
        Answer the user's question directly and concisely. Start with the exact information they need. 
        Don't refer to or mention the provided context in any way - just use it to inform your answer.
        """

        self.messages.append({"role": "user", "content": prompt})
        logger.info(f"Added user query to conversation. Total messages: {len(self.messages)}")
        
        if added_resources:
            logger.debug(f"Query includes {len([m for m in query.split() if m.startswith('@')])} document references")
        else:
            logger.debug("Query does not reference any documents")


def convert_prompt_message_to_message_param(
    prompt_message: "PromptMessage",
) -> MessageParam:
    role = "user" if prompt_message.role == "user" else "assistant"

    content = prompt_message.content

    # Check if content is a dict-like object with a "type" field
    if isinstance(content, dict) or hasattr(content, "__dict__"):
        content_type = (
            content.get("type", None)
            if isinstance(content, dict)
            else getattr(content, "type", None)
        )
        if content_type == "text":
            content_text = (
                content.get("text", "")
                if isinstance(content, dict)
                else getattr(content, "text", "")
            )
            return {"role": role, "content": content_text}

    if isinstance(content, list):
        text_blocks = []
        for item in content:
            # Check if item is a dict-like object with a "type" field
            if isinstance(item, dict) or hasattr(item, "__dict__"):
                item_type = (
                    item.get("type", None)
                    if isinstance(item, dict)
                    else getattr(item, "type", None)
                )
                if item_type == "text":
                    item_text = (
                        item.get("text", "")
                        if isinstance(item, dict)
                        else getattr(item, "text", "")
                    )
                    text_blocks.append({"type": "text", "text": item_text})

        if text_blocks:
            return {"role": role, "content": text_blocks}

    return {"role": role, "content": ""}


def convert_prompt_messages_to_message_params(
    prompt_messages: List[PromptMessage],
) -> List[MessageParam]:
    return [
        convert_prompt_message_to_message_param(msg) for msg in prompt_messages
    ]
