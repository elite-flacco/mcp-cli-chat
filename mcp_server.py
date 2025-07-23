from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("DocumentMCP", log_level="ERROR")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}


@mcp.tool(
    name="read_doc_contents",
    description="Reads the contents of a document and return it as a string.",
)
def read_document(
    doc_id: str = Field(..., description="The ID of the document to read.")
) -> str:
    if doc_id not in docs:
        raise ValueError("Document with id {} not found".format(doc_id))
    return docs.get(doc_id)


@mcp.tool(
    name="edit_doc_contents",
    description="Edits the contents of a document and return it as a string.",
)
def edit_document(
    doc_id: str = Field(..., description="The ID of the document to edit."),
    old_content: str = Field(..., description="The text to be replaced."),
    new_content: str = Field(..., description="The new text to replace with."),
) -> str:
    if doc_id not in docs:
        raise ValueError("Document with id {} not found".format(doc_id))
    docs[doc_id] = docs.get(doc_id).replace(old_content, new_content)
    return docs.get(doc_id)


@mcp.resource("docs://documents", mime_type="application/json")
def list_docs() -> list[str]:
    return list(docs.keys())


@mcp.resource("docs://documents/{doc_id}", mime_type="text/plain")
def fetch_doc(doc_id: str) -> str:
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")
    return docs[doc_id]


# TODO: Write a prompt to rewrite a doc in markdown format
# TODO: Write a prompt to summarize a doc

if __name__ == "__main__":
    mcp.run(transport="stdio")
