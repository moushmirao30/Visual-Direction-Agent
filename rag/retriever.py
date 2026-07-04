"""
rag/retriever.py
Queries ChromaDB to retrieve the most relevant design theory chunks
for a given aesthetic keyword or query string.

Called at runtime by rag_tool.py (Agent 02's tool).
Does NOT call any LLM — pure vector similarity search.

Deduplication:
  Agent 02 runs 4 sequential RAG queries. Without dedup, the same high-ranking
  chunk (e.g. the AURU brand overview) appears in all 4 results, wasting context
  and inflating token use. The retriever tracks seen chunk IDs within a session.

  Call get_retriever().reset_session() at the start of each Agent 02 run.
  The session resets automatically between separate crew.py executions.
"""

import os
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# ── Paths (must match ingest.py) ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "visual_direction_kb"
# all-MiniLM-L6-v2 via onnxruntime — same model/vectors as the
# sentence-transformers version but without the PyTorch stack, so it fits
# the 512MB/0.1-CPU Render free tier (torch import alone stalled health checks).


def _excluded_sources() -> list[str]:
    """
    Reads EVAL_EXCLUDE_SOURCES (comma-separated knowledge-base filenames) from
    the environment and returns them as a list.

    Why an env var instead of a function argument?
      The retrieval call path is: Agent 02 -> rag_tool -> retrieve() -> query().
      Threading a new parameter through every layer would touch agent code and
      risk the live demo. The env var is a zero-touch lever: the eval harness
      sets it before running the held-out 'quiet luxury wellness' benchmark to
      exclude auru_brand_research.txt, proving the system converges on AURU's
      direction WITHOUT the answer sitting in the knowledge base. When the var
      is unset (normal demo + every other run) behaviour is identical to before.
    """
    raw = os.environ.get("EVAL_EXCLUDE_SOURCES", "").strip()
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


# ── Retriever class ───────────────────────────────────────────────────────────

class DesignKnowledgeRetriever:
    """
    Wraps ChromaDB queries for design theory knowledge retrieval.
    Instantiate once, call query() many times (client reuse saves overhead).

    Maintains a session-level deduplication set — chunks already returned
    in this session are excluded from subsequent queries.
    """

    def __init__(self):
        if not CHROMA_DIR.exists():
            raise FileNotFoundError(
                f"ChromaDB not found at {CHROMA_DIR}. "
                "Run 'python -m rag.ingest' first."
            )

        embedding_fn = ONNXMiniLM_L6_V2(
            preferred_providers=["CPUExecutionProvider"]
        )
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn,
        )
        self._seen_ids: set[str] = set()  # dedup state for current session

    def reset_session(self) -> None:
        """
        Clears the deduplication state.
        Call this at the start of each Agent 02 run so that all queries
        within one run deduplicate against each other, but separate runs
        start fresh.
        """
        self._seen_ids.clear()

    def query(self, query_text: str, n_results: int = 5) -> str:
        """
        Retrieves the top-n most relevant chunks for the query,
        excluding any chunk already returned in this session.

        Fetches n_results * 2 candidates to ensure enough unique chunks
        are available after deduplication filtering.
        """
        total = self.collection.count()
        # Fetch extra candidates to account for dedup filtering
        fetch_n = min(n_results * 2, total)

        # Held-out evaluation: exclude named source documents at the DB level so
        # they can never be retrieved. Used to de-leak the AURU benchmark.
        excluded = _excluded_sources()
        where_filter = {"source": {"$nin": excluded}} if excluded else None

        query_kwargs = dict(
            query_texts=[query_text],
            n_results=fetch_n,
            include=["documents", "metadatas", "distances"],
        )
        if where_filter is not None:
            query_kwargs["where"] = where_filter

        results = self.collection.query(**query_kwargs)

        if not results["documents"] or not results["documents"][0]:
            return "No relevant design theory found for this query."

        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]
        ids       = results["ids"][0]

        # Filter out already-seen chunks, keep up to n_results unique ones
        unique = [
            (doc, meta, dist, chunk_id)
            for doc, meta, dist, chunk_id in zip(docs, metas, distances, ids)
            if chunk_id not in self._seen_ids
        ][:n_results]

        if not unique:
            return "No new design theory chunks available for this query (all relevant chunks already retrieved)."

        # Mark returned chunks as seen
        for _, _, _, chunk_id in unique:
            self._seen_ids.add(chunk_id)

        # Format retrieved chunks for LLM consumption
        formatted = []
        for i, (doc, meta, dist, _) in enumerate(unique, 1):
            similarity = round(1 - dist, 3)
            source    = meta.get("source", "unknown")
            section   = meta.get("section", "")
            aesthetic = meta.get("aesthetic", "")

            label = f"[{i}] {source}"
            if aesthetic and aesthetic != "GENERAL":
                label += f" — {aesthetic}"
            elif section:
                label += f" — {section}"

            formatted.append(
                f"{label} (relevance: {similarity})\n"
                f"{doc.strip()}\n"
            )

        return "\n---\n".join(formatted)


# ── Module-level singleton ────────────────────────────────────────────────────
# Initialised on first import — avoids re-connecting ChromaDB on every tool call.
_retriever_instance: DesignKnowledgeRetriever | None = None


def get_retriever() -> DesignKnowledgeRetriever:
    """Returns the module-level singleton retriever (lazy init)."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = DesignKnowledgeRetriever()
    return _retriever_instance


def retrieve(query_text: str, n_results: int = 5) -> str:
    """
    Convenience function — retrieves relevant design theory for a query.
    Used by rag_tool.py and tests.
    """
    return get_retriever().query(query_text, n_results=n_results)


# ── Quick test (run directly) ─────────────────────────────────────────────────

if __name__ == "__main__":
    test_queries = [
        "quiet luxury wellness colour palette",
        "typography pairing for premium brand",
        "negative space and layout principles",
    ]

    retriever = get_retriever()
    retriever.reset_session()  # fresh session for test

    print("Testing retriever with deduplication...\n")
    for q in test_queries:
        print(f"QUERY: '{q}'")
        print("=" * 60)
        result = retriever.query(q, n_results=2)
        print(result[:800])
        print(f"\nSeen chunks so far: {len(retriever._seen_ids)}\n")
