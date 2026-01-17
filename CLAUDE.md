# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VoiceRAG is an application pattern demonstrating RAG (Retrieval Augmented Generation) with voice interfaces using Azure AI Search and the GPT-4o Realtime API for Audio. Users speak into the browser, audio is processed by Azure OpenAI's real-time API, RAG retrieves documents from Azure AI Search, and responses are played as audio with citations.

**RAG is optional**: The app can run as a standalone voice assistant without Azure AI Search. When `AZURE_SEARCH_ENDPOINT` and `AZURE_SEARCH_INDEX` are not set, the app operates in voice assistant mode.

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
4. Search tool queries Azure AI Search for RAG
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

Optional (for RAG mode):
- `AZURE_SEARCH_ENDPOINT` - Search service endpoint
- `AZURE_SEARCH_INDEX` - Index name

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
