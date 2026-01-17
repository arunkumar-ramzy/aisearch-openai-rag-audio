"""
ChromaDB-based RAG tools for VoiceRAG.
Provides local RAG capabilities using ChromaDB as the vector store.
"""

import os
import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from rtmt import RTMiddleTier, Tool, ToolResult, ToolResultDirection

# Tool schemas (same as Azure implementation for compatibility)
_search_tool_schema = {
    "type": "function",
    "name": "search",
    "description": "Search the knowledge base. The knowledge base is in English, translate to and from English if " + \
                   "needed. Results are formatted as a source name first in square brackets, followed by the text " + \
                   "content, and a line with '-----' at the end of each result.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            }
        },
        "required": ["query"],
        "additionalProperties": False
    }
}

_grounding_tool_schema = {
    "type": "function",
    "name": "report_grounding",
    "description": "Report use of a source from the knowledge base as part of an answer (effectively, cite the source). Sources " + \
                   "appear in square brackets before each knowledge base passage. Always use this tool to cite sources when responding " + \
                   "with information from the knowledge base.",
    "parameters": {
        "type": "object",
        "properties": {
            "sources": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of source names from last statement actually used, do not include the ones not used to formulate a response"
            }
        },
        "required": ["sources"],
        "additionalProperties": False
    }
}

KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_=\-]+$')


class ChromaRAG:
    """ChromaDB-based RAG implementation."""

    def __init__(
        self,
        db_path: str | None = None,
        collection_name: str = "voice_rag",
        embedding_function=None
    ):
        """
        Initialize ChromaDB RAG.

        Args:
            db_path: Path to ChromaDB persistence directory. Defaults to ./chroma_db
            collection_name: Name of the ChromaDB collection
            embedding_function: Optional custom embedding function.
                               If None, uses the default based on configuration.
        """
        self.db_path = db_path or os.getenv("CHROMA_DB_PATH", "./chroma_db")
        self.collection_name = collection_name

        # Ensure the database directory exists
        Path(self.db_path).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Set up embedding function
        self.embedding_function = embedding_function or self._get_embedding_function()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )

    def _get_embedding_function(self):
        """Get the embedding function based on environment configuration."""
        embedding_provider = os.getenv("CHROMA_EMBEDDING_PROVIDER", "sentence-transformers")

        if embedding_provider == "openai":
            from chromadb.utils import embedding_functions
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
            api_base = os.getenv("OPENAI_API_BASE") or os.getenv("AZURE_OPENAI_ENDPOINT")
            model = os.getenv("CHROMA_EMBEDDING_MODEL", "text-embedding-3-small")

            if api_base and "azure" in api_base.lower():
                # Azure OpenAI
                return embedding_functions.OpenAIEmbeddingFunction(
                    api_key=api_key,
                    api_base=api_base,
                    api_type="azure",
                    model_name=model
                )
            else:
                # OpenAI
                return embedding_functions.OpenAIEmbeddingFunction(
                    api_key=api_key,
                    model_name=model
                )
        else:
            # Default: sentence-transformers (local)
            from chromadb.utils import embedding_functions
            model_name = os.getenv("CHROMA_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name,
                device="cpu"
            )

    async def search(self, query: str, n_results: int = 5) -> str:
        """
        Search the knowledge base.

        Args:
            query: Search query string
            n_results: Number of results to return

        Returns:
            Formatted search results
        """
        print(f"Searching for '{query}' in ChromaDB knowledge base.")

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )

        output = ""
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                document = results["documents"][0][i] if results["documents"] else ""
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}

                # Use title from metadata if available, otherwise use doc_id
                source = metadata.get("title", doc_id)
                output += f"[{doc_id}]: {document}\n-----\n"

        return output

    async def get_grounding_details(self, source_ids: list[str]) -> dict:
        """
        Get detailed information for grounding/citations.

        Args:
            source_ids: List of source/chunk IDs

        Returns:
            Dictionary with source details
        """
        if not source_ids:
            return {"sources": []}

        # Filter valid IDs
        valid_ids = [s for s in source_ids if KEY_PATTERN.match(s)]

        if not valid_ids:
            return {"sources": []}

        print(f"Grounding sources: {', '.join(valid_ids)}")

        # Get documents by IDs
        results = self.collection.get(
            ids=valid_ids,
            include=["documents", "metadatas"]
        )

        docs = []
        for i in range(len(results["ids"])):
            doc_id = results["ids"][i]
            document = results["documents"][i] if results["documents"] else ""
            metadata = results["metadatas"][i] if results["metadatas"] else {}

            docs.append({
                "chunk_id": doc_id,
                "title": metadata.get("title", doc_id),
                "chunk": document
            })

        return {"sources": docs}

    def add_documents(
        self,
        documents: list[str],
        ids: list[str] | None = None,
        metadatas: list[dict] | None = None
    ) -> None:
        """
        Add documents to the collection.

        Args:
            documents: List of document texts
            ids: Optional list of unique IDs (generated if not provided)
            metadatas: Optional list of metadata dictionaries
        """
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        self.collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self.collection.count()


def _create_search_tool(chroma_rag: ChromaRAG):
    """Create a search tool function for RTMiddleTier."""
    async def search_tool(args: Any) -> ToolResult:
        result = await chroma_rag.search(args["query"], n_results=5)
        return ToolResult(result, ToolResultDirection.TO_SERVER)
    return search_tool


def _create_grounding_tool(chroma_rag: ChromaRAG):
    """Create a grounding tool function for RTMiddleTier."""
    async def grounding_tool(args: Any) -> ToolResult:
        result = await chroma_rag.get_grounding_details(args["sources"])
        return ToolResult(result, ToolResultDirection.TO_CLIENT)
    return grounding_tool


def attach_chroma_rag_tools(
    rtmt: RTMiddleTier,
    db_path: str | None = None,
    collection_name: str = "voice_rag",
    embedding_function=None
) -> ChromaRAG:
    """
    Attach ChromaDB RAG tools to RTMiddleTier.

    Args:
        rtmt: RTMiddleTier instance
        db_path: Path to ChromaDB persistence directory
        collection_name: Name of the ChromaDB collection
        embedding_function: Optional custom embedding function

    Returns:
        ChromaRAG instance for further operations (like adding documents)
    """
    chroma_rag = ChromaRAG(
        db_path=db_path,
        collection_name=collection_name,
        embedding_function=embedding_function
    )

    rtmt.tools["search"] = Tool(
        schema=_search_tool_schema,
        target=_create_search_tool(chroma_rag)
    )
    rtmt.tools["report_grounding"] = Tool(
        schema=_grounding_tool_schema,
        target=_create_grounding_tool(chroma_rag)
    )

    return chroma_rag
