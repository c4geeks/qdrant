#!/usr/bin/env python3
"""Ask the docs: a working LCEL retrieval chain.

Usage:
    python query.py "How do I create a Service in Kubernetes?"
    python query.py --interactive

The chain is the textbook LCEL shape: retriever | prompt | llm | parser,
with a citation post-processor that lists the source files behind every
retrieved chunk so the article reader can see provenance, not just an
LLM hallucination.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from operator import itemgetter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

COLLECTION = os.environ.get("COLLECTION", "k8s_docs")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.1:8b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
TOP_K = int(os.environ.get("TOP_K", "5"))

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior Kubernetes engineer answering questions for a "
            "DevOps audience. Use ONLY the context below. If the context "
            "does not answer the question, say so plainly. Keep answers "
            "tight - 4 to 8 sentences - and prefer concrete commands or "
            "object shapes over abstract description.",
        ),
        (
            "human",
            "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:",
        ),
    ]
)


def format_docs(docs) -> str:
    return "\n\n".join(
        f"[{i + 1}] {d.metadata.get('source', '?')}\n{d.page_content}"
        for i, d in enumerate(docs)
    )


def build_chain():
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=120)
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE)
    store = QdrantVectorStore(
        client=client, collection_name=COLLECTION, embedding=embeddings
    )
    retriever = store.as_retriever(search_kwargs={"k": TOP_K})

    llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE, temperature=0.2)

    answer = (
        {
            "context": itemgetter("docs") | RunnableLambda(format_docs),
            "question": itemgetter("question"),
        }
        | PROMPT
        | llm
        | StrOutputParser()
    )

    chain = RunnableParallel(
        question=itemgetter("question"),
        docs=itemgetter("question") | retriever,
    ).assign(answer=answer)

    return chain


def ask(chain, question: str) -> None:
    t0 = time.perf_counter()
    out = chain.invoke({"question": question})
    elapsed = time.perf_counter() - t0

    print("\n" + "=" * 78)
    print(f"Q: {question}")
    print("=" * 78)
    print(out["answer"].strip())
    print("\n--- Sources ---")
    seen = set()
    for d in out["docs"]:
        src = d.metadata.get("source", "?")
        if src in seen:
            continue
        seen.add(src)
        h2 = d.metadata.get("h2") or d.metadata.get("h1") or ""
        print(f"  - {src}" + (f"  ({h2})" if h2 else ""))
    print(f"\n[{elapsed:.2f}s, {len(out['docs'])} chunks retrieved]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="*", help="Question text")
    ap.add_argument("--interactive", "-i", action="store_true")
    args = ap.parse_args()

    chain = build_chain()

    if args.interactive:
        print("Interactive mode. Empty line to quit.")
        while True:
            try:
                q = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q:
                break
            ask(chain, q)
        return 0

    if not args.question:
        print("usage: query.py 'your question' OR --interactive", file=sys.stderr)
        return 2

    ask(chain, " ".join(args.question))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
