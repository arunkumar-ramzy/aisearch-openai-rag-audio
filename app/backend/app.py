import logging
import os
from pathlib import Path

from aiohttp import web
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

from rtmt import RTMiddleTier

# RAG tools are optional - only import if available
try:
    from ragtools import attach_rag_tools
    AZURE_RAG_AVAILABLE = True
except ImportError:
    AZURE_RAG_AVAILABLE = False

try:
    from chromaragtools import attach_chroma_rag_tools
    CHROMA_RAG_AVAILABLE = True
except ImportError:
    CHROMA_RAG_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voicerag")

async def create_app():
    if not os.environ.get("RUNNING_IN_PRODUCTION"):
        logger.info("Running in development mode, loading from .env file")
        load_dotenv()

    llm_key = os.environ.get("AZURE_OPENAI_API_KEY")
    search_key = os.environ.get("AZURE_SEARCH_API_KEY")

    credential = None
    if not llm_key or not search_key:
        if tenant_id := os.environ.get("AZURE_TENANT_ID"):
            logger.info("Using AzureDeveloperCliCredential with tenant_id %s", tenant_id)
            credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
        else:
            logger.info("Using DefaultAzureCredential")
            credential = DefaultAzureCredential()
    llm_credential = AzureKeyCredential(llm_key) if llm_key else credential
    search_credential = AzureKeyCredential(search_key) if search_key else credential

    app = web.Application()

    rtmt = RTMiddleTier(
        credentials=llm_credential,
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment=os.environ["AZURE_OPENAI_REALTIME_DEPLOYMENT"],
        voice_choice=os.environ.get("AZURE_OPENAI_REALTIME_VOICE_CHOICE") or "alloy"
        )

    # Check which RAG provider is configured
    rag_provider = os.environ.get("RAG_PROVIDER", "").lower()

    # Azure Search is configured if endpoint and index are set
    azure_search_configured = (
        os.environ.get("AZURE_SEARCH_ENDPOINT") and
        os.environ.get("AZURE_SEARCH_INDEX")
    )

    # ChromaDB is always available (uses local storage by default)
    chroma_db_configured = rag_provider in ("chroma", "chromadb") or CHROMA_RAG_AVAILABLE

    # Determine RAG mode
    rag_enabled = False
    if azure_search_configured and (rag_provider in ("", "azure") or not chroma_db_configured):
        rag_enabled = True
        rag_mode = "azure"
    elif chroma_db_configured and rag_provider in ("chroma", "chromadb"):
        rag_enabled = True
        rag_mode = "chroma"
    # Auto-detect: prefer ChromaDB if RAG_PROVIDER not specified and ChromaDB is available
    elif chroma_db_configured and not rag_provider and not azure_search_configured:
        rag_enabled = True
        rag_mode = "chroma"

    if rag_enabled and rag_mode == "azure" and AZURE_RAG_AVAILABLE:
        logger.info("Azure Search is configured - RAG mode enabled")
        rtmt.system_message = """
            You are a helpful assistant. Only answer questions based on information you searched in the knowledge base, accessible with the 'search' tool.
            The user is listening to answers with audio, so it's *super* important that answers are as short as possible, a single sentence if at all possible.
            Never read file names or source names or keys out loud.
            Always use the following step-by-step instructions to respond:
            1. Always use the 'search' tool to check the knowledge base before answering a question.
            2. Always use the 'report_grounding' tool to report the source of information from the knowledge base.
            3. Produce an answer that's as short as possible. If the answer isn't in the knowledge base, say you don't know.
        """.strip()

        attach_rag_tools(rtmt,
            credentials=search_credential,
            search_endpoint=os.environ.get("AZURE_SEARCH_ENDPOINT"),
            search_index=os.environ.get("AZURE_SEARCH_INDEX"),
            semantic_configuration=os.environ.get("AZURE_SEARCH_SEMANTIC_CONFIGURATION") or None,
            identifier_field=os.environ.get("AZURE_SEARCH_IDENTIFIER_FIELD") or "chunk_id",
            content_field=os.environ.get("AZURE_SEARCH_CONTENT_FIELD") or "chunk",
            embedding_field=os.environ.get("AZURE_SEARCH_EMBEDDING_FIELD") or "text_vector",
            title_field=os.environ.get("AZURE_SEARCH_TITLE_FIELD") or "title",
            use_vector_query=(os.getenv("AZURE_SEARCH_USE_VECTOR_QUERY", "true") == "true")
            )
    elif rag_enabled and rag_mode == "chroma" and CHROMA_RAG_AVAILABLE:
        logger.info("ChromaDB is configured - RAG mode enabled")
        rtmt.system_message = """
            You are a helpful assistant. Only answer questions based on information you searched in the knowledge base, accessible with the 'search' tool.
            The user is listening to answers with audio, so it's *super* important that answers are as short as possible, a single sentence if at all possible.
            Never read file names or source names or keys out loud.
            Always use the following step-by-step instructions to respond:
            1. Always use the 'search' tool to check the knowledge base before answering a question.
            2. Always use the 'report_grounding' tool to report the source of information from the knowledge base.
            3. Produce an answer that's as short as possible. If the answer isn't in the knowledge base, say you don't know.
        """.strip()

        attach_chroma_rag_tools(
            rtmt,
            db_path=os.environ.get("CHROMA_DB_PATH"),
            collection_name=os.environ.get("CHROMA_COLLECTION_NAME") or "voice_rag"
        )
    else:
        logger.info("RAG is not configured - voice assistant mode without RAG")
        rtmt.system_message = """
            You are a helpful voice assistant.
            The user is listening to answers with audio, so it's *super* important that answers are as short as possible, a single sentence if at all possible.
            Provide helpful, friendly responses to the user's questions and requests.
        """.strip()

    rtmt.attach_to_app(app, "/realtime")

    current_directory = Path(__file__).parent
    app.add_routes([web.get('/', lambda _: web.FileResponse(current_directory / 'static/index.html'))])
    app.router.add_static('/', path=current_directory / 'static', name='static')
    
    return app

if __name__ == "__main__":
    host = "localhost"
    port = 8765
    web.run_app(create_app(), host=host, port=port)
