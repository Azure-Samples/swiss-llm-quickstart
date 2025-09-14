# Multi-stage image to serve APERTUS models with vLLM using NVIDIA CUDA base images
# - Builder stage creates a slim Python environment with CUDA-enabled PyTorch and vLLM
# - Runtime stage contains only what’s needed to serve

ARG CUDA_VERSION=12.8.0
ARG UBUNTU_VERSION=24.04

############################
# Builder
############################
FROM nvidia/cuda:${CUDA_VERSION}-cudnn-devel-ubuntu${UBUNTU_VERSION} AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    CUDA_HOME=/usr/local/cuda \
    TORCHDYNAMO_DISABLE=1 \
    TORCH_LOGS=+dynamo \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH} \
    # H100, A100, A10, L4 common SMs
    TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0" \
    PATH=/opt/venv/bin:${PATH}

# Choose versions via build args for easy overrides
ARG TORCH_CUDA_CHANNEL=https://download.pytorch.org/whl/cu128

# Base build layer: OS deps, venv, core wheels, utilities
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        cmake \
        ninja-build \
        python3 \
        python3-venv \
        python3-pip \
        python3-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*; \
    # Create a dedicated virtual environment to copy into runtime
    python3 -m venv /opt/venv; \
    pip install --upgrade pip setuptools wheel; \
    # Install torch first to satisfy downstream builds
    pip install --extra-index-url ${TORCH_CUDA_CHANNEL} torch torchvision; \
    # Additional utilities that rarely change
    pip install "huggingface_hub[cli]" hf_transfer fastsafetensors rich flashinfer-python; \
    rm -rf /root/.cache

# Late layer: fetch and build from source (vllm, transformers)
RUN set -eux; \
    # Install vLLM and Transformes
    pip install vllm transformers; \
    # Install XIELU for quantization support (must be installed after vllm and transformers)
    pip install git+https://github.com/nickjbrowning/XIELU; \
    rm -rf /root/.cache

############################
# Runtime
############################
FROM nvidia/cuda:${CUDA_VERSION}-cudnn-runtime-ubuntu${UBUNTU_VERSION} AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/venv/bin:${PATH} \
    PYTHONUNBUFFERED=1 \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    TORCHDYNAMO_DISABLE=1 \
    TORCH_LOGS=+dynamo \
    CUDA_HOME=/usr/local/cuda \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH} \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    # H100, A100, A10, L4 common SMs
    TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"

RUN set -eux; \
    apt-get update; \
    # Install Python so the copied venv's python symlinks resolve correctly
    apt-get install -y --no-install-recommends \
        ca-certificates \
        bash \
        tini \
        python3 \
        python-is-python3 \
        git; \
    # Create a non-root user to run the app
    useradd -m -u 10001 appuser; \
    mkdir -p /workspace; \
    chown appuser:appuser /workspace; \
    rm -rf /var/lib/apt/lists/*

# Copy the prebuilt Python environment
COPY --from=builder /opt/venv /opt/venv

RUN chown -R appuser:appuser /opt/venv

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
    # Hugging Face token for authentication
    HF_TOKEN=""

COPY --chmod=0755 docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

WORKDIR /workspace

USER appuser

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]
