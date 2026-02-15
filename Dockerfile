FROM python:3.13-slim AS builder
WORKDIR /app
COPY pyproject.toml .
# Stub packages so pip can resolve the project
RUN mkdir -p pipeline api a2a_demo evaluation prompts && \
    touch pipeline/__init__.py api/__init__.py a2a_demo/__init__.py evaluation/__init__.py prompts/__init__.py
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --pre --prefix=/install .

FROM python:3.13-slim
# Node.js only needed if GITHUB_PERSONAL_ACCESS_TOKEN is set (GitHub MCP stdio).
# Install it to keep the image self-contained — adds ~60 MB.
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
WORKDIR /app
COPY pipeline/ pipeline/
COPY api/ api/
COPY a2a_demo/ a2a_demo/
COPY evaluation/ evaluation/
COPY prompts/ prompts/
COPY frontend/ frontend/
COPY run.py .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
CMD ["python", "-m", "api.server"]
