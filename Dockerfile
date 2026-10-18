# Multi-service runtime for OpenClaw CLI Gateway Stack
FROM node:22-bookworm-slim

LABEL maintainer="harisant" \
      description="Dockerized OpenClaw CLI Gateway Stack"

# Install system dependencies (Python 3 for log viewer, git for fetching repo, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    git \
    curl \
    ca-certificates \
    procps \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

ARG REPO_URL=https://github.com/everflowinv/openclaw-cli-gateway-stack.git
ARG REPO_REF=main

WORKDIR /app

# Clone upstream repo
RUN git clone --depth 1 --branch ${REPO_REF} ${REPO_URL} /app

# Patch hardcoded 127.0.0.1 bindings to allow container networking via environment variables
RUN sed -i 's/const HOST = "127.0.0.1";/const HOST = process.env.AGY_SEARCH_HOST || "0.0.0.0";/g' /app/antigravity-cli-gateway/websearch-service.mjs && \
    sed -i "s/server.listen(PORT, '127.0.0.1',/server.listen(PORT, process.env.MUSE_CLI_GATEWAY_HOST || '0.0.0.0',/g" /app/muse-cli-gateway/server.mjs && \
    sed -i "s/ThreadingHTTPServer(('127.0.0.1', PORT), Handler)/ThreadingHTTPServer((os.environ.get('LOG_VIEWER_HOST', '0.0.0.0'), PORT), Handler)/g" /app/live-log-viewer/server.py

# Create required runtime directories
RUN mkdir -p /logs /workspace /root/.openclaw/workspace /app/antigravity-cli-gateway/cwd

COPY entrypoint.sh /entrypoint.sh
COPY scripts /app/scripts
RUN chmod +x /entrypoint.sh /app/scripts/*.py

# Ports:
# 4568: Claude CLI Gateway
# 4569: Antigravity CLI Gateway
# 4570: Antigravity WebSearch Service
# 4571: Muse CLI Gateway
# 8765: Live Log Viewer
EXPOSE 4568 4569 4570 4571 8765

ENV OPENCLAW_WORKSPACE=/workspace \
    LOG_DIR=/logs \
    CLAUDE_CLI_GATEWAY_HOST=0.0.0.0 \
    AGY_CLI_GATEWAY_HOST=0.0.0.0 \
    AGY_SEARCH_HOST=0.0.0.0 \
    MUSE_CLI_GATEWAY_HOST=0.0.0.0 \
    LOG_VIEWER_HOST=0.0.0.0

ENTRYPOINT ["/entrypoint.sh"]
CMD ["all"]
