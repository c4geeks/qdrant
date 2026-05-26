# Self-Hosted RAG with Qdrant + Ollama + LangChain

Companion to: https://computingforgeeks.com/qdrant-rag-ollama-langchain/

A working "ask the docs" pipeline that runs entirely on one Linux box with a
single NVIDIA GPU (RTX 4090 in the article). No external API calls, no
managed embedding service, no OpenAI key. The corpus is the official
Kubernetes documentation (~1,500 markdown files) and the LLM is
`llama3.1:8b` served by Ollama.

## Files

| File | Purpose |
|---|---|
| `setup.sh` | One-shot installer: Ollama + Qdrant binary + Python venv |
| `requirements.txt` | LangChain 0.3 / langchain-qdrant / langchain-ollama / ragas |
| `fetch_corpus.py` | Clone the upstream Kubernetes docs repo, keep only `content/en/docs` |
| `ingest.py` | Chunk + embed (`nomic-embed-text`) + upsert into Qdrant |
| `query.py` | LCEL retrieval chain with cited sources |
| `evaluate.py` | ragas faithfulness + relevancy + context precision |

## Quick start

```bash
# 1. Stack
sudo bash setup.sh

# 2. Corpus
sudo /opt/rag/venv/bin/python fetch_corpus.py

# 3. Ingest
sudo /opt/rag/venv/bin/python ingest.py

# 4. Query
/opt/rag/venv/bin/python query.py "How do I drain a node before maintenance?"

# 5. Evaluate
/opt/rag/venv/bin/python evaluate.py
```

## Measured results

(see article for the full table — the README is intentionally short)

## Notes

- `nomic-embed-text` outputs 768-dim vectors. If you swap models, change
  `EMBED_DIM` in `ingest.py` and recreate the collection.
- The chain uses LangChain Expression Language (LCEL). The shape is the
  textbook `retriever | prompt | llm | parser` with a small wrapper that
  also returns the retrieved chunks so the caller can render citations.
- ragas uses the *same* local Ollama LLM as the chain (no external grader),
  which makes the eval reproducible at zero marginal cost but slow — budget
  ~20 minutes for 12 questions × 3 metrics on an RTX 4090.

## License

MIT (same as parent repo).
