#!/usr/bin/env python3
"""
Document ingestion script for ChromaDB RAG.

This script loads documents from various sources and adds them to a ChromaDB collection.
Supports:
- Text files (.txt)
- Markdown files (.md)
- PDF files (.pdf)
- Word documents (.docx)
- Directories (recursive)

Usage:
    # Ingest a single file
    python ingest_chroma.py path/to/document.txt

    # Ingest a directory
    python ingest_chroma.py path/to/documents/

    # Ingest with custom collection name
    python ingest_chroma.py --collection my_knowledge_base path/to/documents/

    # Clear collection before ingestion
    python ingest_chroma.py --clear path/to/documents/
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Generator

# Optional: For PDF and DOCX support
try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into chunks of approximately chunk_size characters.

    Args:
        text: The text to chunk
        chunk_size: Target chunk size in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    # Split by paragraphs first
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += ("\n\n" + para if current_chunk else para)
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())

            # If paragraph is larger than chunk_size, split it
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                        current_chunk += (" " + sentence if current_chunk else sentence)
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    # Add overlap
    if overlap > 0 and len(chunks) > 1:
        overlapped_chunks = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_chunk = overlapped_chunks[-1]
            current = chunks[i]
            # Get last 'overlap' characters from previous chunk
            overlap_text = prev_chunk[-overlap:] if len(prev_chunk) > overlap else prev_chunk
            overlapped_chunks.append(overlap_text + "\n" + current)
        return overlapped_chunks

    return chunks


def read_text_file(path: Path) -> str:
    """Read a text file, handling encoding issues."""
    encodings = ['utf-8', 'latin-1', 'cp1252']
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode file: {path}")


def read_pdf_file(path: Path) -> str:
    """Read text from a PDF file."""
    if not PDF_SUPPORT:
        raise ImportError("pypdf is required for PDF support. Install with: pip install pypdf")

    text = ""
    with open(path, 'rb') as f:
        pdf_reader = pypdf.PdfReader(f)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    return text


def read_docx_file(path: Path) -> str:
    """Read text from a Word document."""
    if not DOCX_SUPPORT:
        raise ImportError("python-docx is required for DOCX support. Install with: pip install python-docx")

    doc = docx.Document(path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def read_document(path: Path) -> str:
    """Read a document based on its file extension."""
    suffix = path.suffix.lower()

    if suffix in ['.txt', '.md']:
        return read_text_file(path)
    elif suffix == '.pdf':
        return read_pdf_file(path)
    elif suffix == '.docx':
        return read_docx_file(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def discover_documents(path: Path) -> Generator[Path, None, None]:
    """
    Discover all supported documents in a path.

    Args:
        path: Path to file or directory

    Yields:
        Paths to supported documents
    """
    supported_extensions = {'.txt', '.md'}
    if PDF_SUPPORT:
        supported_extensions.add('.pdf')
    if DOCX_SUPPORT:
        supported_extensions.add('.docx')

    if path.is_file():
        if path.suffix.lower() in supported_extensions:
            yield path
        else:
            print(f"Warning: Skipping unsupported file: {path}", file=sys.stderr)
    elif path.is_dir():
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in supported_extensions:
                    yield file_path


def main():
    parser = argparse.ArgumentParser(
        description='Ingest documents into ChromaDB for VoiceRAG',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest a single text file
  python ingest_chroma.py my_document.txt

  # Ingest all documents in a directory
  python ingest_chroma.py ./documents/

  # Use custom collection name
  python ingest_chroma.py --collection my_kb ./documents/

  # Clear collection before ingestion
  python ingest_chroma.py --clear ./documents/

  # Set chunk size
  python ingest_chroma.py --chunk-size 1000 ./documents/
        """
    )

    parser.add_argument(
        'path',
        type=str,
        help='Path to document file or directory'
    )
    parser.add_argument(
        '--collection',
        type=str,
        default='voice_rag',
        help='ChromaDB collection name (default: voice_rag)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='./chroma_db',
        help='ChromaDB database path (default: ./chroma_db)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=500,
        help='Target chunk size in characters (default: 500)'
    )
    parser.add_argument(
        '--overlap',
        type=int,
        default=50,
        help='Character overlap between chunks (default: 50)'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear collection before ingestion'
    )
    parser.add_argument(
        '--embedding-model',
        type=str,
        default=None,
        help='Embedding model name (default: all-MiniLM-L6-v2 for local, or text-embedding-3-small for OpenAI)'
    )
    parser.add_argument(
        '--embedding-provider',
        type=str,
        choices=['sentence-transformers', 'openai'],
        default='sentence-transformers',
        help='Embedding provider (default: sentence-transformers)'
    )

    args = parser.parse_args()

    # Import ChromaDB
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        print("Error: ChromaDB is not installed. Install with: pip install chromadb", file=sys.stderr)
        sys.exit(1)

    # Initialize ChromaDB
    print(f"Opening ChromaDB at: {args.db_path}")
    Path(args.db_path).mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=args.db_path,
        settings=Settings(anonymized_telemetry=False, allow_reset=True)
    )

    # Set up embedding function
    if args.embedding_provider == 'openai':
        from chromadb.utils import embedding_functions
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('AZURE_OPENAI_API_KEY')
        api_base = os.getenv('OPENAI_API_BASE') or os.getenv('AZURE_OPENAI_ENDPOINT')
        model = args.embedding_model or os.getenv('CHROMA_EMBEDDING_MODEL', 'text-embedding-3-small')

        if api_base and 'azure' in api_base.lower():
            embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                api_base=api_base,
                api_type='azure',
                model_name=model
            )
        else:
            embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name=model
            )
        print(f"Using OpenAI embeddings: {model}")
    else:
        from chromadb.utils import embedding_functions
        model = args.embedding_model or os.getenv('CHROMA_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model,
            device='cpu'
        )
        print(f"Using sentence-transformers model: {model}")

    # Get or create collection
    if args.clear:
        try:
            client.delete_collection(args.collection)
            print(f"Cleared collection: {args.collection}")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=args.collection,
        embedding_function=embedding_function
    )

    # Discover documents
    doc_path = Path(args.path)
    if not doc_path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    documents = list(discover_documents(doc_path))
    if not documents:
        print(f"No supported documents found at: {args.path}")
        sys.exit(0)

    print(f"Found {len(documents)} document(s) to process")

    # Process documents
    total_chunks = 0
    for doc_path in documents:
        print(f"Processing: {doc_path}")

        try:
            text = read_document(doc_path)
            chunks = chunk_text(text, chunk_size=args.chunk_size, overlap=args.overlap)

            ids = []
            docs = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_path.stem}_{i}"
                ids.append(chunk_id)
                docs.append(chunk)
                metadatas.append({
                    'title': doc_path.name,
                    'source': str(doc_path),
                    'chunk_index': i
                })

            if ids:
                collection.add(
                    documents=docs,
                    ids=ids,
                    metadatas=metadatas
                )
                total_chunks += len(chunks)
                print(f"  Added {len(chunks)} chunk(s)")

        except Exception as e:
            print(f"  Error processing {doc_path}: {e}", file=sys.stderr)

    print(f"\nDone! Added {total_chunks} chunk(s) to collection '{args.collection}'")
    print(f"Total documents in collection: {collection.count()}")


if __name__ == '__main__':
    main()
