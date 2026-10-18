#!/usr/bin/env bash
set -eo pipefail

LOG_DIR="${LOG_DIR:-/logs}"
mkdir -p "$LOG_DIR"
mkdir -p /workspace

# Ensure log files exist so live-log-viewer doesn't fail on missing files
touch "$LOG_DIR/claude-cli-gateway.stdout.log" "$LOG_DIR/claude-cli-gateway.stderr.log"
touch "$LOG_DIR/antigravity-cli-gateway.stdout.log" "$LOG_DIR/antigravity-cli-gateway.stderr.log"
touch "$LOG_DIR/antigravity-websearch.stdout.log" "$LOG_DIR/antigravity-websearch.stderr.log"
touch "$LOG_DIR/muse-cli-gateway.stdout.log" "$LOG_DIR/muse-cli-gateway.stderr.log"

# Setup mcp.json for claude-cli-gateway if not present
if [ ! -f /app/claude-cli-gateway/mcp.json ]; then
  cat <<'EOF' > /app/claude-cli-gateway/mcp.json
{
  "mcpServers": {
    "openclaw": {
      "type": "stdio",
      "command": "node",
      "args": ["/app/openclaw-mcp-proxy/server.js"]
    }
  }
}
EOF
fi

# Configure agy bridge to host if USE_HOST_AGY is enabled
if [ "${USE_HOST_AGY:-0}" = "1" ]; then
  echo "[entrypoint] USE_HOST_AGY=1 detected. Routing agy CLI calls to host daemon via /app/scripts/agy_remote_client.py"
  export AGY_CLI_BIN="/app/scripts/agy_remote_client.py"
  chmod +x "$AGY_CLI_BIN" 2>/dev/null || true
fi

SERVICE="${1:-all}"

run_claude() {
  echo "[claude-gateway] Starting Claude CLI Gateway on ${CLAUDE_CLI_GATEWAY_HOST:-0.0.0.0}:${CLAUDE_CLI_GATEWAY_PORT:-4568}..."
  exec node /app/claude-cli-gateway/server.mjs \
    > >(tee -a "$LOG_DIR/claude-cli-gateway.stdout.log") \
    2> >(tee -a "$LOG_DIR/claude-cli-gateway.stderr.log" >&2)
}

run_antigravity() {
  echo "[antigravity-gateway] Starting Antigravity CLI Gateway on ${AGY_CLI_GATEWAY_HOST:-0.0.0.0}:${AGY_CLI_GATEWAY_PORT:-4569}..."
  exec node /app/antigravity-cli-gateway/server.mjs \
    > >(tee -a "$LOG_DIR/antigravity-cli-gateway.stdout.log") \
    2> >(tee -a "$LOG_DIR/antigravity-cli-gateway.stderr.log" >&2)
}

run_websearch() {
  echo "[antigravity-websearch] Starting Antigravity Websearch on ${AGY_SEARCH_HOST:-0.0.0.0}:${AGY_SEARCH_PORT:-4570}..."
  exec node /app/antigravity-cli-gateway/websearch-service.mjs \
    > >(tee -a "$LOG_DIR/antigravity-websearch.stdout.log") \
    2> >(tee -a "$LOG_DIR/antigravity-websearch.stderr.log" >&2)
}

run_muse() {
  echo "[muse-gateway] Starting Muse CLI Gateway on ${MUSE_CLI_GATEWAY_HOST:-0.0.0.0}:${MUSE_CLI_GATEWAY_PORT:-4571}..."
  exec node /app/muse-cli-gateway/server.mjs \
    > >(tee -a "$LOG_DIR/muse-cli-gateway.stdout.log") \
    2> >(tee -a "$LOG_DIR/muse-cli-gateway.stderr.log" >&2)
}

run_log_viewer() {
  echo "[live-log-viewer] Starting Live Log Viewer on ${LOG_VIEWER_HOST:-0.0.0.0}:${LOG_VIEWER_PORT:-8765}..."
  exec python3 /app/live-log-viewer/server.py \
    --file "$LOG_DIR/claude-cli-gateway.stdout.log" \
    --file "$LOG_DIR/antigravity-cli-gateway.stdout.log" \
    --file "$LOG_DIR/muse-cli-gateway.stdout.log" \
    --port "${LOG_VIEWER_PORT:-8765}"
}

run_all() {
  echo "=========================================================="
  echo " Starting OpenClaw CLI Gateway Stack (All-In-One Mode)..."
  echo "=========================================================="

  pids=()

  cleanup() {
    echo "Stopping all services..."
    for pid in "${pids[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        kill -TERM "$pid" 2>/dev/null || true
      fi
    done
    wait
    exit 0
  }

  trap cleanup SIGINT SIGTERM

  # Start Claude gateway if enabled
  if [ "${ENABLE_CLAUDE:-1}" = "1" ]; then
    echo "-> Starting Claude Gateway (port ${CLAUDE_CLI_GATEWAY_PORT:-4568})"
    node /app/claude-cli-gateway/server.mjs \
      > >(tee -a "$LOG_DIR/claude-cli-gateway.stdout.log") \
      2> >(tee -a "$LOG_DIR/claude-cli-gateway.stderr.log" >&2) &
    pids+=($!)
  fi

  # Start Antigravity gateway if enabled
  if [ "${ENABLE_ANTIGRAVITY:-1}" = "1" ]; then
    echo "-> Starting Antigravity Gateway (port ${AGY_CLI_GATEWAY_PORT:-4569})"
    node /app/antigravity-cli-gateway/server.mjs \
      > >(tee -a "$LOG_DIR/antigravity-cli-gateway.stdout.log") \
      2> >(tee -a "$LOG_DIR/antigravity-cli-gateway.stderr.log" >&2) &
    pids+=($!)

    # Start WebSearch service
    if [ "${ENABLE_WEBSEARCH:-1}" = "1" ]; then
      echo "-> Starting Antigravity WebSearch (port ${AGY_SEARCH_PORT:-4570})"
      node /app/antigravity-cli-gateway/websearch-service.mjs \
        > >(tee -a "$LOG_DIR/antigravity-websearch.stdout.log") \
        2> >(tee -a "$LOG_DIR/antigravity-websearch.stderr.log" >&2) &
      pids+=($!)
    fi
  fi

  # Start Muse gateway if enabled
  if [ "${ENABLE_MUSE:-1}" = "1" ]; then
    echo "-> Starting Muse Gateway (port ${MUSE_CLI_GATEWAY_PORT:-4571})"
    node /app/muse-cli-gateway/server.mjs \
      > >(tee -a "$LOG_DIR/muse-cli-gateway.stdout.log") \
      2> >(tee -a "$LOG_DIR/muse-cli-gateway.stderr.log" >&2) &
    pids+=($!)
  fi

  # Start Log Viewer
  if [ "${ENABLE_LOG_VIEWER:-1}" = "1" ]; then
    echo "-> Starting Live Log Viewer (port ${LOG_VIEWER_PORT:-8765})"
    python3 /app/live-log-viewer/server.py \
      --file "$LOG_DIR/claude-cli-gateway.stdout.log" \
      --file "$LOG_DIR/antigravity-cli-gateway.stdout.log" \
      --file "$LOG_DIR/muse-cli-gateway.stdout.log" \
      --port "${LOG_VIEWER_PORT:-8765}" &
    pids+=($!)
  fi

  echo "All requested services are running. Waiting for process events..."
  wait -n "${pids[@]}"
  cleanup
}

case "$SERVICE" in
  claude)
    run_claude
    ;;
  antigravity)
    run_antigravity
    ;;
  websearch)
    run_websearch
    ;;
  muse)
    run_muse
    ;;
  log-viewer)
    run_log_viewer
    ;;
  all)
    run_all
    ;;
  *)
    exec "$@"
    ;;
esac
