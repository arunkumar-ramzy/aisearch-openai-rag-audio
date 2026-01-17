# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VoiceRAG is an application pattern demonstrating RAG (Retrieval Augmented Generation) with voice interfaces using the GPT-4o Realtime API for Audio. Users speak into the browser, audio is processed by Azure OpenAI's real-time API, RAG retrieves documents, and responses are played as audio with citations.

**RAG Provider Options**:
- **Azure AI Search**: Cloud-based vector search with semantic ranking (original implementation)
- **ChromaDB**: Local vector database for privacy and offline use (new)
- **No RAG**: Standalone voice assistant mode

## Development Commands

### Environment Setup
```bash
# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r app/backend/requirements.txt
cd app/frontend && npm install && cd ../..
```

### Running Development Server
```bash
./scripts/start.sh      # Linux/Mac
pwsh .\scripts\start.ps1  # Windows
```
Access at http://localhost:8765

### Linting
```bash
# Python
ruff check app/backend

# Frontend
cd app/frontend && npm run format
```

### Building Frontend
```bash
cd app/frontend && npm run build
```
Frontend builds to `app/backend/static/` (served by Python backend).

### Deployment to Azure
```bash
azd auth login
azd env new
azd up  # Provision resources and deploy (incurs Azure costs)
azd down  # Remove resources when done
```

## Architecture

### Multi-Tier Structure
- **Frontend**: React TypeScript with Vite (`app/frontend/`)
- **Backend**: Python aiohttp WebSocket server (`app/backend/`)
- **Infrastructure**: Bicep templates for Azure Container Apps (`infra/`)

### Key Components
- `app/backend/app.py` - Main aiohttp server, serves frontend and WebSocket endpoint
- `app/backend/rtmt.py` - RTMiddleTier class handles Azure OpenAI Realtime API integration
- `app/backend/ragtools.py` - RAG tools for Azure AI Search queries
- `app/backend/chromaragtools.py` - RAG tools for ChromaDB local vector store
- `app/backend/ingest_chroma.py` - Document ingestion script for ChromaDB
- `app/frontend/src/main.tsx` - React entry point
- WebSocket endpoint: `/realtime` - bidirectional audio streaming between frontend and Azure OpenAI

### Authentication Flow
- Local development: `AzureDeveloperCliCredential` (when using azd) or `DefaultAzureCredential`
- Deployed: Managed Identity
- API keys optional via `AZURE_OPENAI_API_KEY`, `AZURE_SEARCH_API_KEY`

### Data Flow
1. Browser microphone captures audio
2. Frontend sends audio via WebSocket to `/realtime`
3. Backend RTMiddleTier relays to Azure OpenAI GPT-4o Realtime API
4. Search tool queries the configured RAG provider (Azure AI Search or ChromaDB)
5. Response audio streamed back to browser
6. Citations displayed from search results

## Important Context

### Primary Reference
**AGENTS.md is the authoritative source for development practices.** Trust it first before searching the codebase for setup, deployment, and testing procedures.

### Environment Variables (Required)
- `AZURE_TENANT_ID` - Azure tenant ID
- `AZURE_OPENAI_ENDPOINT` - OpenAI service endpoint
- `AZURE_OPENAI_REALTIME_DEPLOYMENT` - GPT-4o realtime deployment name
- `AZURE_OPENAI_REALTIME_VOICE_CHOICE` - Voice (alloy, echo, shimmer)

**For Azure AI Search RAG**:
- `AZURE_SEARCH_ENDPOINT` - Search service endpoint
- `AZURE_SEARCH_INDEX` - Index name
- Set `RAG_PROVIDER=azure` or leave unset

**For ChromaDB Local RAG**:
- `RAG_PROVIDER=chroma` - Use ChromaDB for local RAG
- `CHROMA_DB_PATH` - Path to ChromaDB storage (default: ./chroma_db)
- `CHROMA_COLLECTION_NAME` - Collection name (default: voice_rag)
- `CHROMA_EMBEDDING_PROVIDER` - Embedding provider: `sentence-transformers` (default) or `openai`
- `CHROMA_EMBEDDING_MODEL` - Model name (default: all-MiniLM-L6-v2 for local, text-embedding-3-small for OpenAI)

Optional (authentication):
- `AZURE_OPENAI_API_KEY`, `AZURE_SEARCH_API_KEY` - API keys instead of Entra ID
- `RUNNING_IN_PRODUCTION` - Disable .env file loading

### Python Version
Must be Python 3.11 or higher.

### Frontend Build Target
Frontend builds into `app/backend/static/` which is served by the Python backend at root path `/`.

### Azure Region Constraints
GPT-4o realtime API only available in specific regions (eastus2, swedencentral).

### Costs
Azure resources incur costs immediately after `azd up`. Clean up with `azd down`.

### ChromaDB Local RAG Setup

For local, privacy-focused RAG without cloud services:

1. **Set environment variables**:
   ```bash
   export RAG_PROVIDER=chroma
   # Optional: Customize storage location
   export CHROMA_DB_PATH=./chroma_db
   ```

2. **Install dependencies**:
   ```bash
   pip install chromadb sentence-transformers
   # Or for PDF/DOCX support:
   pip install pypdf python-docx
   ```

3. **Ingest documents**:
   ```bash
   # Ingest a directory of documents
   python app/backend/ingest_chroma.py ./my_documents/

   # Or a single file
   python app/backend/ingest_chroma.py my_document.txt

   # With custom collection name
   python app/backend/ingest_chroma.py --collection my_kb ./docs/

   # Clear and reload
   python app/backend/ingest_chroma.py --clear ./docs/
   ```

4. **Run the app**:
   ```bash
   ./scripts/start.sh
   ```

The app will automatically detect `RAG_PROVIDER=chroma` and use ChromaDB for local vector search.
