"""
rag/ingest.py
One-time (or on-update) script that loads all .txt documents from
knowledge_base/, chunks them into semantic sections, and stores them
in a local ChromaDB collection.

Run from the visual-direction-agent/ folder:
  python -m rag.ingest

Run with --reset to wipe and rebuild the collection:
  python -m rag.ingest --reset

CHUNKING STRATEGY:
  Documents are structured with two levels of dividers:
    Level 1: ===...=== (major section headers)
    Level 2: --- AESTHETIC NAME --- (sub-sections within major sections)

  We chunk at Level 2 where present, at Level 1 otherwise.
  This gives semantically coherent chunks of ~150–500 words each,
  which is optimal for sentence-transformers retrieval.

  Why NOT fixed-size chunking?
    Fixed character/token splits break concepts mid-sentence.
    Our documents are structured — we use that structure.
"""

import os
import sys
import re
import argparse
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
KB_DIR = BASE_DIR / "knowledge_base"
CHROMA_DIR = BASE_DIR / "chroma_db"

# ── Config ────────────────────────────────────────────────────────────────────
COLLECTION_NAME = "visual_direction_kb"
# all-MiniLM-L6-v2 via onnxruntime (~80MB) — must match retriever.py; the
# ONNX runtime avoids PyTorch so retrieval fits Render's free-tier memory.
MIN_CHUNK_LENGTH = 100  # characters — discard chunks shorter than this


# ── Chunking ──────────────────────────────────────────────────────────────────

def parse_chunks(text: str, source_filename: str) -> list[dict]:
    """
    Splits document text into semantic chunks using structural markers.

    Returns list of dicts:
      {
        "text": str,           # the chunk content
        "source": str,         # filename (for metadata + debugging)
        "section": str,        # major section title
        "aesthetic": str,      # aesthetic territory if present (e.g. "QUIET LUXURY")
        "chunk_id": str        # unique ID for ChromaDB
      }
    """
    chunks = []

    # Split on major section dividers (=== lines)
    major_sections = re.split(r'={40,}', text)

    for section_idx, section in enumerate(major_sections):
        section = section.strip()
        if not section or len(section) < MIN_CHUNK_LENGTH:
            continue

        # Extract section title (first non-empty line after stripping)
        lines = [l.strip() for l in section.split('\n') if l.strip()]
        section_title = lines[0] if lines else f"Section {section_idx}"

        # Check if section has aesthetic sub-sections (--- NAME ---)
        if re.search(r'^--- .+ ---$', section, re.MULTILINE):
            # Split into aesthetic sub-chunks
            sub_sections = re.split(r'(?=^--- )', section, flags=re.MULTILINE)
            for sub_idx, sub in enumerate(sub_sections):
                sub = sub.strip()
                if not sub or len(sub) < MIN_CHUNK_LENGTH:
                    continue

                # Extract aesthetic label from --- NAME --- marker
                aesthetic_match = re.match(r'^--- (.+?) ---', sub)
                aesthetic = aesthetic_match.group(1).strip() if aesthetic_match else "GENERAL"
                # Remove the marker line from the text
                chunk_text = re.sub(r'^--- .+? ---\n?', '', sub).strip()

                if len(chunk_text) < MIN_CHUNK_LENGTH:
                    continue

                chunk_id = f"{source_filename}__s{section_idx}__sub{sub_idx}"
                chunks.append({
                    "text": chunk_text,
                    "source": source_filename,
                    "section": section_title,
                    "aesthetic": aesthetic,
                    "chunk_id": chunk_id,
                })
        else:
            # Use the whole section as one chunk
            chunk_id = f"{source_filename}__s{section_idx}"
            chunks.append({
                "text": section,
                "source": source_filename,
                "section": section_title,
                "aesthetic": "GENERAL",
                "chunk_id": chunk_id,
            })

    return chunks


# ── Ingest ────────────────────────────────────────────────────────────────────

def ingest(reset: bool = False):
    """
    Main ingest function. Loads all .txt files from knowledge_base/,
    chunks them, embeds with sentence-transformers, stores in ChromaDB.

    Args:
        reset: If True, deletes and recreates the collection first.
    """
    # Validate knowledge base exists and has files
    if not KB_DIR.exists():
        print(f"[ERROR] Knowledge base directory not found: {KB_DIR}")
        sys.exit(1)

    txt_files = list(KB_DIR.glob("*.txt"))
    if not txt_files:
        print(f"[ERROR] No .txt files found in {KB_DIR}")
        sys.exit(1)

    print(f"[INFO] Found {len(txt_files)} document(s) to ingest:")
    for f in txt_files:
        print(f"       - {f.name}")

    # Set up ChromaDB
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    embedding_fn = ONNXMiniLM_L6_V2(
        preferred_providers=["CPUExecutionProvider"]
    )

    # Handle reset
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"[INFO] Deleted existing collection '{COLLECTION_NAME}'")
        except Exception:
            pass  # collection didn't exist yet

    # Get or create collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},  # cosine similarity for text
    )

    existing_count = collection.count()
    if existing_count > 0 and not reset:
        print(f"[WARN] Collection already has {existing_count} chunks.")
        print("       Run with --reset to rebuild from scratch.")
        print("       Skipping ingest to avoid duplicates.")
        return

    # Process all documents
    all_chunks = []
    for filepath in txt_files:
        text = filepath.read_text(encoding="utf-8")
        chunks = parse_chunks(text, filepath.name)
        all_chunks.extend(chunks)
        print(f"[INFO] {filepath.name}: {len(chunks)} chunks")

    if not all_chunks:
        print("[ERROR] No usable chunks found after parsing.")
        sys.exit(1)

    print(f"\n[INFO] Total chunks to embed and store: {len(all_chunks)}")
    print("[INFO] Embedding with ONNX MiniLM (first run downloads ~80MB model)...")

    # Add to ChromaDB in batches (avoids memory issues on large collections)
    batch_size = 50
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        collection.add(
            ids=[c["chunk_id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{
                "source": c["source"],
                "section": c["section"],
                "aesthetic": c["aesthetic"],
            } for c in batch],
        )
        print(f"[INFO] Stored chunks {i+1}–{min(i+batch_size, len(all_chunks))}")

    final_count = collection.count()
    print(f"\n[DONE] Ingest complete. {final_count} chunks stored in ChromaDB.")
    print(f"       Location: {CHROMA_DIR}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest knowledge base into ChromaDB")
    parser.add_argument("--reset", action="store_true",
                        help="Delete and recreate the collection before ingesting")
    args = parser.parse_args()
    ingest(reset=args.reset)
