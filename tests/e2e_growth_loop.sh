#!/usr/bin/env bash
# E2E test: Growth closed loop (record -> mine -> suggest -> approve -> apply -> skill)
# Requires: backend running (uvicorn app.main), node for JSON parsing.
# Usage: BASE_URL=http://localhost:8000 bash tests/e2e_growth_loop.sh
set -u
BASE_URL="${BASE_URL:-http://localhost:8000}"
PASS=0; FAIL=0

jget() { node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{const j=JSON.parse(d);const v='$1'.split('.').reduce((a,k)=>a?.[k],j);console.log(typeof v==='object'?JSON.stringify(v):v??'')}catch(e){console.log('')}})"; }
jlen() { node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{console.log(JSON.parse(d).length)}catch(e){console.log(0)}})"; }

check() { # check <name> <condition: 0/1>
  if [ "$2" = "0" ]; then echo "PASS: $1"; PASS=$((PASS+1)); else echo "FAIL: $1"; FAIL=$((FAIL+1)); fi
}

echo "== 1. health =="
CODE=$(curl -s -o /tmp/h.json -w "%{http_code}" "$BASE_URL/health")
check "health 200" "$([ "$CODE" = "200" ] && echo 0 || echo 1)"

echo "== 2. record demo pattern x4 =="
for i in 1 2 3 4; do
  for act_tgt in "chat:send" "browser:navigate" "browser:click"; do
    a="${act_tgt%%:*}"; t="${act_tgt##*:}"
    curl -s -X POST "$BASE_URL/api/v1/growth/record" -H 'Content-Type: application/json' \
      -d "{\"agent_id\":\"e2e\",\"action\":\"$a\",\"target\":\"$t\",\"session_id\":\"e2e-run\"}" > /dev/null
  done
done
echo "recorded."

echo "== 3. mine =="
MINE=$(curl -s -X POST "$BASE_URL/api/v1/growth/mine?min_count=3&seq_len=3")
echo "$MINE" | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const a=JSON.parse(d);console.log('patterns:',a.length)})"

echo "== 4. suggest =="
SUGG=$(curl -s -X POST "$BASE_URL/api/v1/growth/suggest")
SID=$(echo "$SUGG" | jget "0.id")
[ -z "$SID" ] && SID=$(echo "$SUGG" | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const a=JSON.parse(d);console.log(a.length?a[0].id:'')})")
check "suggestion created (id=$SID)" "$([ -n "$SID" ] && echo 0 || echo 1)"

echo "== 5. approval auto-created =="
APPR=$(curl -s "$BASE_URL/api/v1/approvals/")
AID=$(echo "$APPR" | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const a=JSON.parse(d);const f=a.find(x=>x.proposed_input&&x.proposed_input.suggestion_id==='$SID');console.log(f?f.request_id:'')})")
check "approval exists for suggestion" "$([ -n "$AID" ] && echo 0 || echo 1)"

echo "== 6. apply BEFORE approval must 409 =="
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/growth/suggestions/$SID/apply")
check "apply gated (409, got $CODE)" "$([ "$CODE" = "409" ] && echo 0 || echo 1)"

echo "== 7. approve via Approvals tab API =="
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/approvals/$AID/resolve" -H 'Content-Type: application/json' -d '{"status":"approved"}')
check "resolve approved (got $CODE)" "$([ "$CODE" = "200" ] && echo 0 || echo 1)"

echo "== 8. apply AFTER approval =="
OUT=$(curl -s -X POST "$BASE_URL/api/v1/growth/suggestions/$SID/apply")
SKILL=$(echo "$OUT" | jget "skill_id")
check "draft skill created ($SKILL)" "$([ -n "$SKILL" ] && echo 0 || echo 1)"

echo "== 9. skill exists in registry =="
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/skills/$SKILL")
check "skill fetch 200 (got $CODE)" "$([ "$CODE" = "200" ] && echo 0 || echo 1)"

echo "== 10. dedup: suggest again must NOT duplicate =="
N1=$(curl -s "$BASE_URL/api/v1/growth/suggestions" | jlen)
curl -s -X POST "$BASE_URL/api/v1/growth/suggest" > /dev/null
N2=$(curl -s "$BASE_URL/api/v1/growth/suggestions" | jlen)
check "no duplicate suggestions ($N1 -> $N2)" "$([ "$N1" = "$N2" ] && echo 0 || echo 1)"

echo ""
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" = "0" ]
