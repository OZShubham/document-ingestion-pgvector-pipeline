## DIVE Architecture (Mermaid)

This file contains a high-level architecture diagram for the DIVE platform. The diagram is written in Mermaid so it can be rendered in many Markdown viewers and GitHub.

```mermaid
flowchart TD
  subgraph Frontend
    A[User Browser\n(React + Vite)]
  end

  subgraph Backend
    B[FastAPI Backend\n(API + WebSocket)]
  end

  subgraph GCP
    C[GCS Bucket\n(documents/{project_id}/...)]
    D[Cloud Function (Gen2)\nProcessing Pipeline]
    E[Vertex AI / Embedding Provider]
    F[Cloud SQL (Postgres) + pgvector]
    G[Pub/Sub (optional)]
  end

  A -->|HTTPS API| B
  B -->|Write metadata / signed URLs| C
  C -->|Object finalization event| D
  D -->|Extraction (Gemini, PyMuPDF, pypdf, OCR, LangChain processors)| D
  D -->|Chunking & Embeddings| E
  E -->|Embeddings| F
  D -->|Write metadata, chunks, logs| F
  D -->|Publish events| G
  B -->|Vector search / RAG| F
  B -->|Real-time updates via WS| A

  click D "./cloud_function/README.md" "Cloud Function docs"
  click B "./backend/README.md" "Backend docs"
  click A "./frontend/README.md" "Frontend docs"

  classDef cloud fill:#f9f,stroke:#333,stroke-width:1px;
  class C,D,E,F,G cloud;

  %% Notes
  %% - The pipeline uses multiple processors for extraction. Gemini (if available) is used as one option; fallbacks include PyMuPDF, pypdf, OCR, and LangChain-based processors.
```

### Notes

- The Cloud Function contains `pipeline_processor.py` which orchestrates extraction, chunking, embedding and writing to the DB. Gemini is integrated as a high-quality extractor when configured, but the pipeline uses local processors as fallbacks for resiliency and cost control.
- The backend (FastAPI) serves the API, user auth/authorization, and RAG orchestration. It queries `document_vectors` (pgvector) for similarity searches and composes prompts for the LLMs.
- Pub/Sub is optional and used when you need decoupled notifications or fan-out processing.

For more details see the component READMEs in the repository.
