# Image to serve APERTUS models with vLLM using VLLM/VLLM-OPENAI base image

FROM vllm/vllm-openai:v0.10.2

LABEL org.opencontainers.image.source=https://github.com/Azure-Samples/swiss-llm-quickstart
LABEL org.opencontainers.image.description="Apertus vLLM backend for Swiss LLM Quickstart"
LABEL org.opencontainers.image.licenses=MIT

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/workspace/hf-home \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    TORCHDYNAMO_DISABLE=1 \
    TORCH_LOGS=+dynamo \
    # H100, A100, A10, L4 common SMs
    TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"

RUN set -eux; \
    apt-get update; \
    # Install Python so the copied venv's python symlinks resolve correctly
    apt-get install -y --no-install-recommends \
        tini \
        python-is-python3; \
    # Create a non-root user to run the app
    useradd -m -u 10001 appuser; \
    # Create necessary directories and set permissions
    mkdir -p /workspace/hf-home; \
    mkdir -p /workspace/tool-parser; \
    chown -R appuser:appuser /workspace; \
    chmod -R 775 /workspace; \
    # Clean up
    rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/uv \
    # Install fastsafetensors, XIELU for quantization support (must be installed after vllm and transformers)
    set -eux; \
    uv pip install --system fastsafetensors git+https://github.com/nickjbrowning/XIELU;

# Default server configuration via env vars
ENV MODEL_ID=swiss-ai/Apertus-8B-Instruct-2509 \
    # Model file format: 'safetensors' (for no GDS support - Default) or 'fastsafetensor' (for GDS support)
    LOAD_FORMAT="safetensors" \
    GPU_MEMORY_UTILIZATION=0.94 \
    MAX_MODEL_LEN=4096 \
    MAX_NUM_SEQS=64 \
    # Multi-GPU sharding; 1 for single GPU (default) or >1 for multi-GPU
    TENSOR_PARALLEL_SIZE="" \
    # Optional Features
    KV_CACHE_DTYPE="" \
    SWAP_SPACE="" \
    CPU_OFFLOAD_GB=""
    TOOL_CALL_PARSER=""


COPY --chmod=0755 src/apertus-vllm/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

WORKDIR /workspace

USER appuser

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]