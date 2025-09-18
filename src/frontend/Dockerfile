# Image for Frontend using ChainLit with OpenAI-compatible APIs, Semantic Kernel and Azure Content Safety. 

FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/Azure-Samples/swiss-llm-quickstart
LABEL org.opencontainers.image.description="Apertus vLLM Frontend for Swiss LLM Quickstart"
LABEL org.opencontainers.image.licenses=MIT

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/appuser/.local/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && curl -LsSf https://astral.sh/uv/install.sh | sh \
 && groupadd --system appuser \
 && useradd --system --create-home --gid appuser appuser \
 && chown -R appuser:appuser /app \
 && rm -rf /var/lib/apt/lists/*

USER appuser





