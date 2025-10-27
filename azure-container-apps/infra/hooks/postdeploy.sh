#!/usr/bin/env bash
set -euo pipefail
[[ ${DEBUG-} =~ ^1|yes|true$ ]] && set -o xtrace

# Learn more here: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/azd-extensibility

if [ "${SERVICE_APERTUS_EXISTS:-false}" = "true" ]; then
    printf "  \033[32m➜\033[0m Backend service already exists, skipping container app update...\n"
else 
    printf "  \033[32m➜\033[0m Backend service does not exist, updating container app images...\n"
    az containerapp update --name "${AZURE_CONTAINER_APP_NAME}" --resource-group ${AZURE_RESOURCE_GROUP} \
        --container-name apertus-vllm \
        --image "${AZURE_CONTAINER_REGISTRY_ENDPOINT}/azure-samples/apertus-vllm:latest" \
        --query "properties.provisioningState"
    az containerapp update --name "${AZURE_CONTAINER_APP_NAME}" --resource-group ${AZURE_RESOURCE_GROUP} \
        --container-name apertus-ingress \
        --image "${AZURE_CONTAINER_REGISTRY_ENDPOINT}/azure-samples/swiss-llm-quickstart-ingress:latest" \
        --query "properties.provisioningState"

    azd env set SERVICE_APERTUS_EXISTS true
fi