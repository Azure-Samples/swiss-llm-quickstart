docker build -f docker/Dockerfile -t swiss-llm-vllm .

docker run --gpus all -p 8000:8000 swiss-llm-vllm


- Build: docker build -f docker/Dockerfile -t swiss-llm-vllm .
- Run (8B defaults): docker run --gpus all -p 8000:8000 swiss-llm-vllm
- Run (70B example): add env vars:
 - -e MODEL_ID=swiss-ai/Apertus-70B-Instruct-2509 -e MAX_MODEL_LEN=32768 -e SWAP_SPACE=128 -e KV_CACHE_DTYPE=fp8 -e TENSOR_PARALLEL_SIZE=2



 docker run --gpus all -p 8000:8000 -e HF_TOKEN=your_token_here swiss-llm-vllm -v ~/.cache/huggingface:/home/appuser/.cache/huggingface swiss-llm-vllm