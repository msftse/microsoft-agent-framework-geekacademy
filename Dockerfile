# ---- Build stage: install Python deps ----
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build tools for any native extensions
RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .


# ---- Runtime stage ----
FROM python:3.13-slim

# Install Node.js (required for GitHub MCP stdio server via npx)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY pipeline/ pipeline/
COPY api/ api/
COPY a2a_demo/ a2a_demo/
COPY evaluation/ evaluation/
COPY frontend/ frontend/
COPY run.py .

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "-m", "api.server"]
