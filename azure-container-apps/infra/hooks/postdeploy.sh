#!/usr/bin/env bash
set -euo pipefail
[[ ${DEBUG-} =~ ^1|yes|true$ ]] && set -o xtrace

# Learn more here: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/azd-extensibility

if [ "${SERVICE_BACKEND_EXISTS:-false}" = "true" ]; then
    printf "  \033[32m➜\033[0m Backend service already exists, skipping container app update...\n"
else 
    printf "  \033[32m➜\033[0m Backend service does not exist, updating container app images...\n"
    az containerapp update --name apertus-vllm --resource-group ${AZURE_RESOURCE_GROUP} \
        --container-name apertus-vllm \
        --image "${AZURE_CONTAINER_REGISTRY_ENDPOINT}/azure-samples/swiss-llm-quickstart:latest"

    az containerapp update --name apertus-ingress --resource-group ${AZURE_RESOURCE_GROUP} \
        --container-name apertus-ingress \
        --image "${AZURE_CONTAINER_REGISTRY_ENDPOINT}/azure-samples/swiss-llm-quickstart-ingress:latest"

    azd env set SERVICE_BACKEND_EXISTS true
fi