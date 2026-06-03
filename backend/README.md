# PDF Chatbot Backend

Backend package metadata and the Docker build expect this file to exist inside the backend build context.

The full backend documentation lives at `../docs/backend.md` in the repository root.

Short flow: upload route -> document upload service -> PDF reader utility -> ingestion service -> chunking -> embedding -> Qdrant vector store -> retrieval service -> chatbot service -> answer generation.
