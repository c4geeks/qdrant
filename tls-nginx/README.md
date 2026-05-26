# Secure Qdrant with API Key, TLS, and Nginx Reverse Proxy

Companion to: https://computingforgeeks.com/secure-qdrant-tls-nginx/

A hardened Qdrant 1.18.1 deployment: loopback bind, API key + JWT RBAC,
Nginx TLS termination for REST and gRPC, Let's Encrypt cert, and Nginx
rate limiting.

## Files

| File | Purpose |
|---|---|
| `qdrant.nginx` | Nginx vhost for HTTPS REST (443) + gRPC over TLS (6334) + rate limit |
| `issue_jwt.py` | Mint scoped JWT tokens for per-collection access |
| `verify.sh` | End-to-end check: TLS chain, redirect, auth, headers, port 6333 closed |

## Setup

```bash
# 1. Strong API key (32 bytes random) outside the container
openssl rand -base64 32 | tr -d '=+/' | cut -c1-40 \
  | sudo tee /etc/qdrant/api-key.secret > /dev/null
sudo chmod 600 /etc/qdrant/api-key.secret

# 2. Qdrant bound to loopback ONLY (gRPC on internal 16334)
API_KEY=$(sudo cat /etc/qdrant/api-key.secret)
sudo docker run -d --name qdrant --restart=always \
  -p 127.0.0.1:6333:6333 -p 127.0.0.1:16334:6334 \
  -e QDRANT__SERVICE__API_KEY="$API_KEY" \
  -e QDRANT__SERVICE__JWT_RBAC=true \
  -v /opt/qdrant/storage:/qdrant/storage \
  -v /opt/qdrant/snapshots:/qdrant/snapshots \
  qdrant/qdrant:v1.18.1

# 3. Nginx + Let's Encrypt
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp qdrant.nginx /etc/nginx/sites-available/qdrant
sudo ln -sf /etc/nginx/sites-available/qdrant /etc/nginx/sites-enabled/qdrant
# Update the server_name and cert paths to your domain
sudo certbot --nginx -d qdrant.example.com --non-interactive --agree-tos \
  --redirect -m admin@example.com
sudo nginx -t && sudo systemctl restart nginx

# 4. Verify
./verify.sh qdrant.example.com "$API_KEY"
```

## JWT RBAC

```bash
pip install pyjwt
# Read-only on 'docs' collection
RO=$(python3 issue_jwt.py docs r 3600)
curl -sS https://qdrant.example.com/collections/docs -H "api-key: $RO"

# Read-write on 'docs' collection
RW=$(python3 issue_jwt.py docs rw 3600)
```

## Public surface area

- **443/tcp**  Nginx, HTTPS REST
- **6334/tcp** Nginx, gRPC over TLS
- **80/tcp**   Nginx, HTTP-to-HTTPS redirect only (also for Let's Encrypt renewal)
- **22/tcp**   SSH from admin CIDR only

Cleartext 6333 is bound only on `127.0.0.1` so the public NIC never sees it.

## Gotchas this catches

- **`-p 127.0.0.1:6333:6333` is the actual loopback bind.** `-p 6333:6333`
  publishes on every interface.
- **Nginx and Qdrant cannot both own 6334.** Move Qdrant's loopback gRPC
  to 16334 so Nginx can bind 0.0.0.0:6334 for TLS termination.
- **`grpc_pass` needs HTTP/2 end-to-end.** Use `listen 6334 ssl http2;`
  AND `grpc_pass`, not `proxy_pass`.
- **JWT-RBAC needs the env flag plus the JWT.** Setting the flag without
  minting tokens leaves the master api-key as the only credential.
- **Certbot's HTTP-01 needs port 80 open at the cloud firewall**, every
  90 days. Either keep 80 open or switch to a DNS-01 plugin.

Tested 2026-05 on Ubuntu 24.04 with Qdrant 1.18.1, Nginx 1.24.0,
certbot 2.9.0, qdrant-client 1.18.0.
