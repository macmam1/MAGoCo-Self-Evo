#!/usr/bin/env bash
# E2E test: BYOM Provider System (local Ollama + custom OpenAI-compatible endpoint)
# Requires: backend running, node + python3 + curl.
# Env:
#   BASE_URL (default http://localhost:8000)
#   TEST_BASE_URL + TEST_API_KEY + TEST_MODEL (optional: custom endpoint leg)
# Usage: BASE_URL=... TEST_BASE_URL=... TEST_API_KEY=... bash tests/e2e_providers.sh
set -u
BASE_URL="${BASE_URL:-http://localhost:8000}"
PASS=0; FAIL=0
check() { if [ "$2" = "0" ]; then echo "PASS: $1"; PASS=$((PASS+1)); else echo "FAIL: $1"; FAIL=$((FAIL+1)); fi; }
jget() { node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{const j=JSON.parse(d);const v='$1'.split('.').reduce((a,k)=>a?.[k],j);console.log(typeof v==='object'?JSON.stringify(v):v??'')}catch(e){console.log('')}})"; }

echo "== 1. health =="
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
check "health 200 (got $CODE)" "$([ "$CODE" = "200" ] && echo 0 || echo 1)"

echo "== 2. providers list (empty ok) =="
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/providers/")
check "list 200 (got $CODE)" "$([ "$CODE" = "200" ] && echo 0 || echo 1)"

echo "== 3. autodetect Ollama =="
AUTO=$(curl -s -X POST "$BASE_URL/api/v1/providers/autodetect-ollama")
echo "$AUTO" | head -c 200; echo
OLLAMA_ID=$(echo "$AUTO" | jget "provider.id")

echo "== 4. ensure ollama-local provider =="
if [ -z "$OLLAMA_ID" ]; then
  CREATED=$(curl -s -X POST "$BASE_URL/api/v1/providers/" -H 'Content-Type: application/json' \
    -d '{"name":"Ollama (local)","kind":"ollama-local","base_url":"http://localhost:11434"}')
  OLLAMA_ID=$(echo "$CREATED" | jget "id")
fi
check "ollama provider id=$OLLAMA_ID" "$([ -n "$OLLAMA_ID" ] && echo 0 || echo 1)"

echo "== 5. fetch Ollama models =="
MODELS=$(curl -s -X POST "$BASE_URL/api/v1/providers/$OLLAMA_ID/fetch-models")
echo "$MODELS" | head -c 300; echo
HAS_MODEL=$(echo "$MODELS" | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{const j=JSON.parse(d);console.log(j.models&&j.models.length>0?'yes':'no')}catch(e){console.log('no')}})")
check "ollama models fetched" "$([ "$HAS_MODEL" = "yes" ] && echo 0 || echo 1)"
OMODEL=$(echo "$MODELS" | jget "models.0")

echo "== 6. test Ollama connection =="
T1=$(curl -s -X POST "$BASE_URL/api/v1/providers/$OLLAMA_ID/test")
echo "$T1" | head -c 200; echo
check "ollama test ok" "$(echo "$T1" | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{console.log(JSON.parse(d).ok?'0':'1')}catch(e){console.log('1')}})")"

echo "== 7. chat via Ollama (must NOT be rule-based fallback) =="
pip install -q websocket-client 2>/dev/null
CHAT_OUT=$(BASE_URL="$BASE_URL" OLLAMA_ID="$OLLAMA_ID" OMODEL="$OMODEL" python3 - <<'EOF'
import json, os, sys
try:
    import websocket
except ImportError:
    print("NO_WS_LIB"); sys.exit(0)
base = os.environ["BASE_URL"].replace("http", "ws", 1)
ws = websocket.create_connection(f"{base}/ws/chat", timeout=120)
ws.send(json.dumps({"message": "Reply with exactly: PROVIDER_SMOKE_OK", "provider_id": os.environ["OLLAMA_ID"], "model": os.environ.get("OMODEL") or None}))
out = ""
import time
deadline = time.time() + 110
while time.time() < deadline:
    try:
        ws.settimeout(10)
        msg = json.loads(ws.recv())
    except Exception:
        break
    if msg.get("type") == "message":
        out = msg.get("content", ""); break
ws.close()
print(out)
EOF
)
echo "$CHAT_OUT" | head -c 300; echo
if [ "$CHAT_OUT" = "NO_WS_LIB" ]; then echo "SKIP: websocket-client unavailable"; else
  check "ollama chat real (not fallback)" "$(echo "$CHAT_OUT" | grep -q "I received the input" && echo 1 || echo 0)"
fi

if [ -n "${TEST_BASE_URL:-}" ] && [ -n "${TEST_API_KEY:-}" ]; then
  echo "== 8. create custom provider =="
  MODELS_JSON=$([ -n "${TEST_MODEL:-}" ] && echo "[\"$TEST_MODEL\"]" || echo "[]")
  CREATED2=$(curl -s -X POST "$BASE_URL/api/v1/providers/" -H 'Content-Type: application/json' \
    -d "{\"name\":\"Test Gateway\",\"kind\":\"openai-compatible\",\"base_url\":\"$TEST_BASE_URL\",\"api_key\":\"$TEST_API_KEY\",\"models\":$MODELS_JSON,\"default_model\":\"${TEST_MODEL:-}\"}")
  PID2=$(echo "$CREATED2" | jget "id")
  check "custom provider id=$PID2" "$([ -n "$PID2" ] && echo 0 || echo 1)"

  echo "== 9. fetch + test custom =="
  F2=$(curl -s -X POST "$BASE_URL/api/v1/providers/$PID2/fetch-models"); echo "$F2" | head -c 200; echo
  T2=$(curl -s -X POST "$BASE_URL/api/v1/providers/$PID2/test"); echo "$T2" | head -c 200; echo
  check "custom test ok" "$(echo "$T2" | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{console.log(JSON.parse(d).ok?'0':'1')}catch(e){console.log('1')}})")"

  echo "== 10. chat via custom (must NOT be fallback) =="
  CMODEL="${TEST_MODEL:-$(echo "$F2" | jget "models.0")}"
  CHAT2=$(BASE_URL="$BASE_URL" PID2="$PID2" CMODEL="$CMODEL" python3 - <<'EOF'
import json, os, sys
import websocket
base = os.environ["BASE_URL"].replace("http", "ws", 1)
ws = websocket.create_connection(f"{base}/ws/chat", timeout=120)
ws.send(json.dumps({"message": "Reply with exactly: PROVIDER_SMOKE_OK", "provider_id": os.environ["PID2"], "model": os.environ.get("CMODEL") or None}))
out = ""
import time
deadline = time.time() + 110
while time.time() < deadline:
    try:
        ws.settimeout(10)
        msg = json.loads(ws.recv())
    except Exception:
        break
    if msg.get("type") == "message":
        out = msg.get("content", ""); break
ws.close()
print(out)
EOF
)
  echo "$CHAT2" | head -c 300; echo
  check "custom chat real (not fallback)" "$(echo "$CHAT2" | grep -q "I received the input" && echo 1 || echo 0)"
else
  echo "SKIP steps 8-10 (no TEST_BASE_URL/TEST_API_KEY)"
fi

echo ""
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" = "0" ]
