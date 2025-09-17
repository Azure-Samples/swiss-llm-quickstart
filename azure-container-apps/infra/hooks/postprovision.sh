#!/usr/bin/env bash
set -euo pipefail
[[ ${DEBUG-} =~ ^1|yes|true$ ]] && set -o xtrace

# Learn more here: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/azd-extensibility

# Delete the Hugging Face token from environment for security reasons
azd env set HUGGING_FACE_HUB_TOKEN ""

printf "  \033[32m➜\033[0m Import vLLM container image to ${AZURE_CONTAINER_REGISTRY_ENDPOINT}...\n"
az acr import --force --name ${AZURE_CONTAINER_REGISTRY_ENDPOINT/.*/} \
    --source ghcr.io/azure-samples/apertus-vllm:latest \
    --image azure-samples/apertus-vllm:latest

printf "  \033[32m➜\033[0m Import Nginx Ingress container image to ${AZURE_CONTAINER_REGISTRY_ENDPOINT}...\n"
az acr import --force --name ${AZURE_CONTAINER_REGISTRY_ENDPOINT/.*/} \
    --source ghcr.io/azure-samples/swiss-llm-quickstart-ingress:latest \
    --image azure-samples/swiss-llm-quickstart-ingress:latest

printf "  \033[32m➜\033[0m Activating artifact streaming...\n"
az acr artifact-streaming create --name ${AZURE_CONTAINER_REGISTRY_ENDPOINT/.*/} \
    --image azure-samples/apertus-vllm:latest
az acr artifact-streaming create --name ${AZURE_CONTAINER_REGISTRY_ENDPOINT/.*/} \
    --image azure-samples/swiss-llm-quickstart-ingress:latest
