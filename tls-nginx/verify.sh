#!/usr/bin/env bash
# Verify the secured Qdrant deployment end-to-end.
#
# Run after every config change to catch regressions:
#   ./verify.sh qdrant.example.com $API_KEY
#
# Exits non-zero on any failed check so it can run in CI.
set -u

HOST="${1:?usage: ./verify.sh <host> <api_key>}"
API_KEY="${2:?usage: ./verify.sh <host> <api_key>}"

fail=0
ok()   { echo "  OK   $*"; }
bad()  { echo "  FAIL $*"; fail=$((fail + 1)); }

echo "=== TLS chain ==="
CHAIN=$(echo | openssl s_client -connect "${HOST}:443" \
    -servername "${HOST}" 2>/dev/null \
    | grep -E 'Protocol|Cipher|Verify return code')
echo "$CHAIN"
echo "$CHAIN" | grep -q 'Verify return code: 0' && ok "cert verified" || bad "cert NOT verified"
echo "$CHAIN" | grep -q 'TLSv1.3'              && ok "TLSv1.3 negotiated" || bad "not TLSv1.3"

echo
echo "=== Plain HTTP redirects ==="
code=$(curl -sS -o /dev/null -w '%{http_code}' "http://${HOST}/")
[ "$code" = "301" ] && ok "HTTP 301" || bad "got HTTP $code"

echo
echo "=== HTTPS REST no api-key (must 401) ==="
code=$(curl -sS -o /dev/null -w '%{http_code}' "https://${HOST}/collections")
[ "$code" = "401" ] && ok "HTTP 401" || bad "got HTTP $code"

echo
echo "=== HTTPS REST with api-key (must 200) ==="
code=$(curl -sS -o /dev/null -w '%{http_code}' "https://${HOST}/collections" \
    -H "api-key: ${API_KEY}")
[ "$code" = "200" ] && ok "HTTP 200" || bad "got HTTP $code"

echo
echo "=== Public cleartext 6333 must be unreachable ==="
code=$(curl -m 3 -sS -o /dev/null -w '%{http_code}' "http://${HOST}:6333/" 2>/dev/null || echo "000")
[ "$code" = "000" ] && ok "no listener on 6333" || bad "port 6333 reachable: HTTP $code"

echo
echo "=== Security headers ==="
HEADERS=$(curl -sS -I "https://${HOST}/collections" -H "api-key: ${API_KEY}")
echo "$HEADERS" | grep -qi 'strict-transport-security'  && ok "HSTS"               || bad "missing HSTS"
echo "$HEADERS" | grep -qi 'x-content-type-options'     && ok "X-Content-Type"     || bad "missing X-Content-Type"
echo "$HEADERS" | grep -qi 'x-frame-options'            && ok "X-Frame-Options"    || bad "missing X-Frame-Options"

echo
if [ "$fail" -eq 0 ]; then
    echo "All checks PASS"
    exit 0
else
    echo "FAILED: $fail check(s)"
    exit 1
fi
