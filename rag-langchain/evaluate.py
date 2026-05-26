#!/usr/bin/env python3
"""Score the RAG pipeline with ragas.

Uses local Ollama for both LLM and embeddings (no API key, no external
calls). Measures faithfulness, answer relevance, and context precision
on 12 hand-written Kubernetes questions whose ground truth is grounded
in the upstream documentation we ingested.
"""
from __future__ import annotations

import os
import time

import pandas as pd
from datasets import Dataset
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    LLMContextPrecisionWithoutReference,
)

from query import build_chain

QUESTIONS = [
    ("How do I expose a Deployment as a Service?",
     "Use kubectl expose deployment to create a ClusterIP, NodePort, or LoadBalancer Service that selects the deployment's pods."),
    ("What is a Kubernetes namespace used for?",
     "Namespaces partition cluster resources between multiple users or teams and scope names so identical resource names can exist in different namespaces."),
    ("How do I roll back a Deployment to a previous revision?",
     "Run kubectl rollout undo deployment/<name> which sets the deployment back to the previous ReplicaSet revision."),
    ("What does the kubelet do?",
     "The kubelet is the per-node agent that registers the node with the API server and ensures the containers described in the assigned PodSpecs are running and healthy."),
    ("How do I drain a node before maintenance?",
     "Use kubectl drain <node> --ignore-daemonsets which cordons the node and evicts its pods so it can be safely taken offline."),
    ("What is a StatefulSet?",
     "A StatefulSet manages a set of pods with stable, unique network identities and persistent storage, used for stateful workloads like databases."),
    ("How do I set resource limits on a container?",
     "Add resources.limits and resources.requests entries to the container spec with cpu and memory values."),
    ("How do I create a Secret from a literal value?",
     "Use kubectl create secret generic <name> --from-literal=key=value."),
    ("What is the difference between requests and limits?",
     "Requests are the resources guaranteed to a container at schedule time; limits are the hard ceiling the runtime will enforce."),
    ("How do I see logs from a previous container restart?",
     "Run kubectl logs <pod> --previous to read the stdout from the last terminated container instance."),
    ("How do I write a NetworkPolicy that denies all ingress to a namespace?",
     "Apply a NetworkPolicy with podSelector {} and policyTypes Ingress and no ingress rules, which blocks all incoming traffic to pods in the namespace."),
    ("What is a ConfigMap?",
     "A ConfigMap stores non-confidential key-value configuration data that pods can consume as environment variables, command-line args, or files in a volume."),
]


def main() -> int:
    chain = build_chain()
    rows = []

    print(f"Running {len(QUESTIONS)} eval queries through the chain")
    for i, (q, gt) in enumerate(QUESTIONS, 1):
        t0 = time.perf_counter()
        out = chain.invoke({"question": q})
        dt = time.perf_counter() - t0
        rows.append(
            {
                "question": q,
                "answer": out["answer"].strip(),
                "contexts": [d.page_content for d in out["docs"]],
                "ground_truth": gt,
                "elapsed_s": round(dt, 2),
            }
        )
        print(f"  {i:2d}/{len(QUESTIONS)}  {dt:5.2f}s  {q[:60]}")

    df = pd.DataFrame(rows)
    df[["question", "elapsed_s"]].to_csv("/tmp/latencies.csv", index=False)
    print(f"\nMean latency: {df.elapsed_s.mean():.2f}s  p95: {df.elapsed_s.quantile(0.95):.2f}s")

    ds = Dataset.from_pandas(df[["question", "answer", "contexts", "ground_truth"]])

    eval_llm = LangchainLLMWrapper(
        ChatOllama(
            model=os.environ.get("EVAL_MODEL", "llama3.1:8b"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            temperature=0,
        )
    )
    eval_emb = LangchainEmbeddingsWrapper(
        OllamaEmbeddings(
            model=os.environ.get("EMBED_MODEL", "nomic-embed-text"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        )
    )

    print("Scoring with ragas (faithfulness, answer_relevancy, context_precision)...")
    result = evaluate(
        ds,
        metrics=[
            Faithfulness(llm=eval_llm),
            ResponseRelevancy(llm=eval_llm, embeddings=eval_emb),
            LLMContextPrecisionWithoutReference(llm=eval_llm),
        ],
        llm=eval_llm,
        embeddings=eval_emb,
    )

    rdf = result.to_pandas()
    rdf.to_csv("/tmp/ragas-detail.csv", index=False)

    metric_cols = [c for c in rdf.columns if c not in ("question", "answer", "contexts", "ground_truth", "user_input", "response", "retrieved_contexts", "reference")]
    print("\n=== ragas summary ===")
    for c in metric_cols:
        vals = rdf[c].dropna()
        if len(vals):
            print(f"  {c:30s}  mean={vals.mean():.3f}  median={vals.median():.3f}  n={len(vals)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
