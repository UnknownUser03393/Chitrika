#!/usr/bin/env bash
# Smoke test for the PyInstaller-built backend.exe.
# Usage: bash packaging/smoke_test.sh [port]
set -u

ROOT="D:/Development/PythonProject/Chitrika"
PORT="${1:-8787}"
DATA="D:/Development/PythonProject/Chitrika/build_backend/smoke"
TOKEN="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# Kill any stray instance first.
taskkill //F //IM backend.exe >/dev/null 2>&1
rm -rf "$DATA"
mkdir -p "$DATA/plugins"

DATABASE_URL="sqlite:///$DATA/test.db" \
PLUGINS_DIR="$DATA/plugins" \
CHITRIKA_PORT="$PORT" \
CHITRIKA_LOG_DIR="$DATA" \
EMOTION_CLASSIFIER_MODEL_DIR="$ROOT/models/emotion" \
EMBEDDING_MODEL_DIR="$ROOT/models/embedding" \
CHITRIKA_SKILL_FILE="$ROOT/skill_0624.txt" \
CHITRIKA_API_TOKEN="$TOKEN" \
CORS_ORIGINS="null" \
"$ROOT/dist_backend/backend/backend.exe" &

EXE_PID=$!
echo "spawned backend.exe pid=$EXE_PID on port $PORT"

RESP=""
for i in $(seq 1 60); do
  sleep 1
  RESP=$(curl -s -m 2 -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:$PORT/api/health" 2>/dev/null || true)
  if [ -n "$RESP" ]; then
    echo "HEALTHY after ${i}s: $RESP"
    break
  fi
  # Early exit if the process died.
  kill -0 "$EXE_PID" 2>/dev/null || { echo "backend.exe died after ${i}s"; break; }
done

if [ -z "$RESP" ]; then
  echo "=== NOT HEALTHY — log tail ==="
  tail -40 "$DATA/backend.log" 2>/dev/null
else
  echo "--- /api/characters ---"
  curl -s -m 3 -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:$PORT/api/characters" | head -c 400
  echo ""
  CHAR_ID=$(curl -s -m 3 -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:$PORT/api/characters" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
  if [ -n "$CHAR_ID" ]; then
    echo "--- emotion endpoint (ONNX classifier live?) ---"
    curl -s -m 10 -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:$PORT/api/characters/$CHAR_ID/emotion" | head -c 300
    echo ""
  fi
fi

kill "$EXE_PID" 2>/dev/null
sleep 1
taskkill //F //IM backend.exe >/dev/null 2>&1
echo "=== smoke test done ==="
