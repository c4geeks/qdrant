#!/usr/bin/env python3
"""Download a real markdown corpus for RAG ingestion.

Pulls the Kubernetes documentation repo from GitHub (Apache-2.0 licensed)
and keeps only the English markdown files under content/en/docs. Produces
roughly 1,500 .md files totalling ~25-30 MB of real, production-grade
documentation - exactly the kind of corpus a SaaS would point an
internal RAG at.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/kubernetes/website.git"
DEST = Path("/opt/rag/corpus")
KEEP_UNDER = "content/en/docs"


def run(cmd: list[str]) -> None:
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        shutil.rmtree(DEST)

    tmp = Path("/tmp/k8s-website")
    if tmp.exists():
        shutil.rmtree(tmp)

    run(["git", "clone", "--depth", "1", "--filter=blob:none", REPO, str(tmp)])

    src = tmp / KEEP_UNDER
    if not src.exists():
        print(f"ERROR: {src} does not exist after clone", file=sys.stderr)
        return 1

    DEST.mkdir(parents=True, exist_ok=True)
    md_files = list(src.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files under {KEEP_UNDER}", flush=True)

    for f in md_files:
        rel = f.relative_to(src)
        target = DEST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)

    total_bytes = sum(p.stat().st_size for p in DEST.rglob("*.md"))
    print(f"Copied {len(md_files)} files, {total_bytes / 1024 / 1024:.1f} MB to {DEST}")

    shutil.rmtree(tmp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
