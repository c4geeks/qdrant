#!/usr/bin/env python3
"""Chunk and embed the markdown corpus into Qdrant.

Pipeline:
    Markdown files
      -> MarkdownHeaderTextSplitter (preserve H1/H2/H3 metadata)
      -> RecursiveCharacterTextSplitter (768-char chunks, 96 overlap)
      -> Ollama nomic-embed-text (768-dim)
      -> Qdrant upsert (named dense vector + payload incl. source path)

Run timing and counts are printed at the end so the article can quote
real numbers.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from tqdm import tqdm

CORPUS_DIR = Path(os.environ.get("CORPUS_DIR", "/opt/rag/corpus"))
COLLECTION = os.environ.get("COLLECTION", "k8s_docs")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
EMBED_DIM = 768

HEADER_SPLIT = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
    strip_headers=False,
)
CHAR_SPLIT = RecursiveCharacterTextSplitter(
    chunk_size=768,
    chunk_overlap=96,
    separators=["\n\n", "\n", " ", ""],
)


def strip_frontmatter(text: str) -> str:
    """Remove Hugo front-matter so embeddings see the body, not YAML."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    return text


def load_chunks() -> list[dict]:
    chunks: list[dict] = []
    files = sorted(CORPUS_DIR.rglob("*.md"))
    print(f"Loading {len(files)} markdown files from {CORPUS_DIR}", flush=True)

    for f in tqdm(files, desc="chunking"):
        try:
            raw = f.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:  # noqa: BLE001
            print(f"skip {f}: {e}", flush=True)
            continue

        body = strip_frontmatter(raw)
        if len(body.strip()) < 80:
            continue

        # MarkdownHeaderTextSplitter does not always return docs; fall back
        try:
            header_docs = HEADER_SPLIT.split_text(body)
        except Exception:
            header_docs = []

        if not header_docs:
            header_docs = [type("D", (), {"page_content": body, "metadata": {}})()]

        for hd in header_docs:
            for sub in CHAR_SPLIT.split_text(hd.page_content):
                if len(sub.strip()) < 60:
                    continue
                chunks.append(
                    {
                        "text": sub,
                        "source": str(f.relative_to(CORPUS_DIR)),
                        "h1": hd.metadata.get("h1", ""),
                        "h2": hd.metadata.get("h2", ""),
                        "h3": hd.metadata.get("h3", ""),
                    }
                )

    print(f"Produced {len(chunks)} chunks", flush=True)
    return chunks


def main() -> int:
    chunks = load_chunks()
    if not chunks:
        print("No chunks produced - nothing to ingest", flush=True)
        return 1

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=120)

    if client.collection_exists(COLLECTION):
        print(f"Dropping existing collection {COLLECTION}", flush=True)
        client.delete_collection(COLLECTION)

    print(f"Creating collection {COLLECTION} (dim={EMBED_DIM})", flush=True)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=qm.VectorParams(size=EMBED_DIM, distance=qm.Distance.COSINE),
    )

    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE)

    store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION,
        embedding=embeddings,
    )

    t0 = time.perf_counter()
    batch = 64
    for i in tqdm(range(0, len(chunks), batch), desc="embed+upsert"):
        slab = chunks[i : i + batch]
        store.add_texts(
            texts=[c["text"] for c in slab],
            metadatas=[
                {
                    "source": c["source"],
                    "h1": c["h1"],
                    "h2": c["h2"],
                    "h3": c["h3"],
                }
                for c in slab
            ],
        )
    elapsed = time.perf_counter() - t0

    info = client.get_collection(COLLECTION)
    print(
        f"\nIngest complete: {info.points_count} points, "
        f"{elapsed:.1f}s wall ({len(chunks) / elapsed:.1f} chunks/s)"
    )
    print(f"Indexed segments: {info.indexed_vectors_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
