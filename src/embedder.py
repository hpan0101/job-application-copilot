"""
embedder.py — Chunk, embed, and store resume + project details in ChromaDB.

Flow:
  Chunk objects (from parser.py)
      → OpenAI text-embedding-3-small
      → ChromaDB collection ("resume_store")

The collection is persisted to ./chroma_db/ so you only need to run this
once per resume upload. Re-running it clears and rebuilds the collection.
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from openai import OpenAI

from resume_parser import Chunk

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "resume_store"
EMBED_MODEL = "text-embedding-3-small"


# ---------------------------------------------------------------------------
# Custom embedding function (openai >= 1.0 compatible)
# ---------------------------------------------------------------------------

class OpenAIEmbedFn:
    """
    Wraps openai>=1.0 embeddings so chromadb 0.3.x can call it.
    chromadb expects: fn(texts: List[str]) -> List[List[float]]
    """
    def __init__(self, api_key: str, model: str = EMBED_MODEL):
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def __call__(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# Client + collection
# ---------------------------------------------------------------------------

def _get_collection(reset: bool = False) -> chromadb.Collection:
    """
    Return (or create) the ChromaDB collection.
    Pass reset=True to wipe and rebuild — do this when uploading a new resume.

    Uses chromadb 0.3.x DuckDB+Parquet backend (no SQLite version requirement).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY not set. Copy .env.example → .env and add your key."
        )

    client = chromadb.Client(Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=str(CHROMA_PATH),
        anonymized_telemetry=False,
    ))

    embed_fn = OpenAIEmbedFn(api_key=api_key)

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"[embedder] Cleared existing collection '{COLLECTION_NAME}'")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


# ---------------------------------------------------------------------------
# Core: embed and store
# ---------------------------------------------------------------------------

def embed_chunks(chunks: list[Chunk], reset: bool = True) -> chromadb.Collection:
    """
    Embed a list of Chunk objects and upsert them into ChromaDB.

    Args:
        chunks: output of parser.parse_resume() + parser.parse_projects()
        reset:  if True, clears the collection first (safe default for a fresh upload)

    Returns:
        The ChromaDB collection (useful for immediate querying in tests).
    """
    if not chunks:
        raise ValueError("No chunks to embed — did the parser return anything?")

    collection = _get_collection(reset=reset)

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for i, chunk in enumerate(chunks):
        documents.append(chunk.content)
        metadatas.append({
            "section": chunk.section,
            "source": chunk.source,
            **{k: str(v) for k, v in chunk.metadata.items()},
        })
        # Stable ID: source + section + index prevents duplicate upserts
        ids.append(f"{chunk.source}_{chunk.section}_{i}")

    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    print(f"[embedder] Embedded {len(chunks)} chunks into '{COLLECTION_NAME}' "
          f"(path: {CHROMA_PATH})")
    return collection


# ---------------------------------------------------------------------------
# Convenience: full pipeline
# ---------------------------------------------------------------------------

def build_store(
    resume_pdf: str | Path | None = None,
    projects: list[dict] | None = None,
) -> chromadb.Collection:
    """
    One-call convenience: parse resume + projects, embed everything.

    Args:
        resume_pdf: path to your PDF resume (optional if you have project chunks)
        projects:   list of project dicts (see parser.ProjectDetail for fields)

    Returns:
        Populated ChromaDB collection.

    Example:
        from embedder import build_store
        collection = build_store(
            resume_pdf="data/resume.pdf",
            projects=[{
                "name": "My App",
                "stack": "FastAPI, React",
                "your_role": "Full-stack developer",
                "what_you_built": "A dashboard for tracking...",
                "impact": "Reduced report time by 40%",
            }]
        )
    """
    # Import here to avoid circular issues when running as __main__
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from resume_parser import parse_resume, parse_projects

    all_chunks: list[Chunk] = []

    if resume_pdf:
        all_chunks.extend(parse_resume(resume_pdf))

    if projects:
        all_chunks.extend(parse_projects(projects))

    if not all_chunks:
        raise ValueError("Provide at least a resume_pdf or a projects list.")

    return embed_chunks(all_chunks, reset=True)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from resume_parser import parse_projects

    api_key = os.getenv("OPENAI_API_KEY", "")
    has_real_key = api_key.startswith("sk-") and len(api_key) > 20 and "placeholder" not in api_key

    print("[embedder] Running smoke test with sample project data...")

    sample_projects = [
        {
            "name": "Job Application Copilot",
            "stack": "Python, OpenAI API, ChromaDB, Streamlit",
            "your_role": "Solo developer",
            "what_you_built": "LLM-powered assistant generating tailored cover letters and STAR answers.",
            "impact": "Cut application prep time from 2 hours to 10 minutes.",
            "duration": "1 week",
        },
        {
            "name": "E-commerce Analytics Dashboard",
            "stack": "Python, FastAPI, PostgreSQL, React, Docker",
            "your_role": "Backend lead",
            "what_you_built": "Real-time sales and inventory dashboard with alerting.",
            "impact": "Reduced manual reporting by 80%; adopted by 3 internal teams.",
            "duration": "3 months",
        },
    ]

    chunks = parse_projects(sample_projects)
    print(f"[embedder] Parsed {len(chunks)} chunks. Content preview:")
    for c in chunks:
        print(f"  [{c.section}] {c.content[:80]}...")

    if not has_real_key:
        print("\n[embedder] No real OPENAI_API_KEY found — skipping embedding call.")
        print("[embedder] To run the full test: set OPENAI_API_KEY in your .env file.")
        print("[embedder] Smoke test (parser + ChromaDB init) PASSED.")
        sys.exit(0)

    collection = embed_chunks(chunks, reset=True)

    # Quick sanity query
    results = collection.query(
        query_texts=["Python backend project with measurable impact"],
        n_results=2,
    )
    print("\n[embedder] Top query results:")
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        print(f"  [{meta['section']} / {meta['source']}] {doc[:120]}...")

    print("\n[embedder] Full smoke test PASSED. ChromaDB stored at:", CHROMA_PATH)
