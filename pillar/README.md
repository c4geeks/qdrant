# Pillar — Qdrant Vector Database

Companion artifacts for the pillar article on Computing for Geeks:

- **Article**: https://computingforgeeks.com/qdrant-vector-database-guide/
- **Series**: [Qdrant Mastery](https://computingforgeeks.com/series/qdrant-mastery/)

## What is here

- [`quick-try.sh`](./quick-try.sh) — the 60 second Docker run referenced in the article. Spins Qdrant, opens the Web UI, leaves the container running so you can poke at it.

## Quick try

```bash
./quick-try.sh
```

That gets you a Qdrant container on port 6333 with the Web UI at `http://localhost:6333/dashboard`. To clean up:

```bash
docker rm -f qdrant && rm -rf qdrant_storage
```
