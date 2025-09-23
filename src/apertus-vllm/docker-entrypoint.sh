#!/usr/bin/env bash
set -euo pipefail

# Authenticate with Hugging Face if token is provided
if [[ -n "${HF_TOKEN:-}" ]]; then
    echo "Authenticating with Hugging Face..."
    hf auth login --token "${HF_TOKEN}"
fi

echo "Starting vLLM server for model: ${MODEL_ID}"

ARGS=(
  "serve" "${MODEL_ID}"
  "--load-format" "${LOAD_FORMAT:-"safetensors"}"
  "--safetensors-load-strategy" "eager"
  "--ignore-patterns" "original/*/"
  "--enforce-eager"
  "--gpu-memory-utilization" "${GPU_MEMORY_UTILIZATION:-0.95}"
  "--max-model-len" "${MAX_MODEL_LEN:-4096}"
  "--max-num-seqs" "${MAX_NUM_SEQS:-64}"
  "--dtype" "auto"
  "--enable-auto-tool-choice"
  "--tool-parser" "${TOOL_PARSER:-"/home/appuser/tool-parser/apertus_tool_parser.py"}"
  "--chat-template" "${CHAT_TEMPLATE:-"/home/appuser/tool-parser/apertus_chat_template.jinja"}"
)

# Append optional tensor parallel size if provided
if [[ -n "${TENSOR_PARALLEL_SIZE:-}" ]]; then
  ARGS+=("--tensor-parallel-size" "${TENSOR_PARALLEL_SIZE}")
fi

# Append optional KV cache dtype if provided (e.g., fp8)
if [[ -n "${KV_CACHE_DTYPE:-}" ]]; then
  ARGS+=("--kv-cache-dtype" "${KV_CACHE_DTYPE}")
fi

# Append optional Swap Space if provided (e.g., 32)
if [[ -n "${SWAP_SPACE:-}" ]]; then
  ARGS+=("--swap-space" "${SWAP_SPACE}")
fi

# Append optional GPU Memory Offload if provided (e.g., 32)
if [[ -n "${CPU_OFFLOAD_GB:-}" ]]; then
  ARGS+=("--cpu-offload-gb" "${CPU_OFFLOAD_GB}")
fi

if [[ -n "${TOOL_CALL_PARSER:-}" ]]; then
  ARGS+=(
    "--enable-auto-tool-choice"
    "--tool-call-parser" "${TOOL_CALL_PARSER}"
  )
fi

echo "Launching: vllm ${ARGS[*]}"
exec vllm "${ARGS[@]}"

