## DIVE Architecture (Mermaid)

This file contains a high-level architecture diagram for the DIVE platform. The diagram is written in Mermaid so it can be rendered in many Markdown viewers and GitHub.

```mermaid
flowchart TD
  subgraph Frontend
    A[User Browser<br/>React + Vite]
  end

  subgraph Backend
    B[FastAPI Backend<br/>API + WebSocket]
  end

  subgraph GCP
    C[GCS Bucket<br/>documents/project_id/...]
    D[Cloud Function Gen2<br/>Processing Pipeline]
    E[Vertex AI /<br/>Embedding Provider]
    F[Cloud SQL Postgres<br/>+ pgvector]
    G[Pub/Sub<br/>optional]
  end

  A -->|HTTPS API| B
  B -->|Write metadata /<br/>signed URLs| C
  C -->|Object finalization<br/>event| D
  D -->|Extraction: Gemini<br/>PyMuPDF, pypdf<br/>OCR, LangChain| D
  D -->|Chunking &<br/>Embeddings| E
  E -->|Embeddings| F
  D -->|Write metadata<br/>chunks, logs| F
  D -->|Publish events| G
  B -->|Vector search /<br/>RAG| F
  B -->|Real-time updates<br/>via WebSocket| A

  classDef cloud fill:#e1f5ff,stroke:#0066cc,stroke-width:2px
  classDef frontend fill:#fff4e6,stroke:#ff9800,stroke-width:2px
  classDef backend fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
  
  class C,D,E,F,G cloud
  class A frontend
  class B backend

  %% Notes
  %% - The pipeline uses multiple processors for extraction. Gemini (if available) is used as one option; fallbacks include PyMuPDF, pypdf, OCR, and LangChain-based processors.
```

### Notes

- The Cloud Function contains `pipeline_processor.py` which orchestrates extraction, chunking, embedding and writing to the DB. Gemini is integrated as a high-quality extractor when configured, but the pipeline uses local processors as fallbacks for resiliency and cost control.
- The backend (FastAPI) serves the API, user auth/authorization, and RAG orchestration. It queries `document_vectors` (pgvector) for similarity searches and composes prompts for the LLMs.
- Pub/Sub is optional and used when you need decoupled notifications or fan-out processing.

For more details see the component READMEs in the repository.
