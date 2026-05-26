#!/usr/bin/env python3
"""Mint a scoped JWT for Qdrant 1.18 JWT-RBAC.

The signing material is the master api-key string. Keep the master key
server-side and only mint tokens from it.

Usage:
  python3 issue_jwt.py docs r            # read-only on 'docs'
  python3 issue_jwt.py docs rw 3600      # rw on 'docs', expires in 1 hour
"""
import os
import sys
import time

import jwt

API_KEY_PATH = "/etc/qdrant/api-key.secret"


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: issue_jwt.py <collection> <r|w|rw> [exp_seconds]")
        sys.exit(1)
    collection, access = sys.argv[1], sys.argv[2]
    exp = int(sys.argv[3]) if len(sys.argv) > 3 else None

    if access not in ("r", "w", "rw"):
        print(f"bad access flag: {access!r} (must be r, w, or rw)")
        sys.exit(2)

    api_key = (
        os.environ.get("QDRANT_API_KEY")
        or open(API_KEY_PATH).read().strip()
    )

    claims = {"access": [{"collection": collection, "access": access}]}
    if exp is not None:
        claims["exp"] = int(time.time()) + exp

    token = jwt.encode(claims, api_key, algorithm="HS256")
    print(token)


if __name__ == "__main__":
    main()
