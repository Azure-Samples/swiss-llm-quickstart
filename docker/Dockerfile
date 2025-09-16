# Image to serve APERTUS models with vLLM using VLLM/VLLM-OPENAI base image

FROM vllm/vllm-openai:v0.10.2

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
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
    mkdir -p /workspace; \
    chown appuser:appuser /workspace; \
    rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/uv \
    # Install fastsafetensors, XIELU for quantization support (must be installed after vllm and transformers)
    set -eux; \
    uv pip install --system fastsafetensors git+https://github.com/nickjbrowning/XIELU;

# Default server configuration via env vars
ENV MODEL_ID=swiss-ai/Apertus-8B-Instruct-2509 \
    HOST=0.0.0.0 \
    PORT=8000 \
    GPU_MEMORY_UTILIZATION=0.95 \
    MAX_MODEL_LEN=4096 \
    MAX_NUM_SEQS=512 \
    SWAP_SPACE=32 \
    # Optional: set for multi-GPU sharding; e.g., 2 for 70B on 2x A100 80GB
    TENSOR_PARALLEL_SIZE="" \
    # Optional KV cache dtype (e.g., fp8 for large models)
    KV_CACHE_DTYPE="" \
    # Hugging Face token
    HF_TOKEN=""

COPY --chmod=0755 docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

WORKDIR /workspace

USER appuser

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]