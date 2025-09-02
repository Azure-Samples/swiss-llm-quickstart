#!/usr/bin/env bash
set -euo pipefail
[[ ${DEBUG-} =~ ^1|yes|true$ ]] && set -o xtrace


LABEL=${LABEL:-swiss-llm-001}

LOCATION="${AZURE_RG:-swedencentral}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-${LABEL}}"
ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-cae-${LABEL}}"
CONTAINER_APP_NAME="${CONTAINER_APP_NAME:-ca-${LABEL}}"
CONTAINER_IMAGE="${CONTAINER_IMAGE:-mcr.microsoft.com/k8se/gpu-quickstart:latest}"
#CONTAINER_IMAGE="llama-3.1-8b-instruct:latest"
#WORKLOAD_PROFILE_NAME="NC8as-T4"
#WORKLOAD_PROFILE_TYPE="Consumption-GPU-NC8as-T4"
WORKLOAD_PROFILE_NAME="${WORKLOAD_PROFILE_NAME:-NC24-A100}"
WORKLOAD_PROFILE_TYPE="${WORKLOAD_PROFILE_TYPE:-Consumption-GPU-NC24-A100}"

AZURE_VM_NAME="${AZURE_VM_NAME:-vmswissllma100}"
# TODO: Canonical:ubuntu-24_04-lts:server:latest ?
IMAGE="${AZURE_IMAGE:-Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest}"

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" 1>/dev/null

az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AZURE_VM_NAME" \
    --admin-username "${AZURE_ADMIN_USER:-azureuser}" \
    --public-ip-sku Standard \
    --os-disk-size-gb 128 \
    --generate-ssh-keys \
    --image "$IMAGE" \
    --priority Spot \
    --size Standard_NC24ads_A100_v4