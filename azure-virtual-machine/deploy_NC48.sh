#!/usr/bin/env bash
set -euo pipefail
[[ ${DEBUG-} =~ ^1|yes|true$ ]] && set -o xtrace

LABEL=${LABEL:-swiss-llm-001}
LOCATION="${AZURE_RG:-swedencentral}"

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-${LABEL}}"
AZURE_VM_NAME="${AZURE_VM_NAME:-vmswissllma100}"
IMAGE="${AZURE_IMAGE:-Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest}"
VM_SKU="${VM_SKU:-Standard_NC48ads_A100_v4}"
AZURE_OS_DISK_SIZE_GB="${AZURE_OS_DISK_SIZE_GB:-512}"
AZURE_ADMIN_USER="${AZURE_ADMIN_USER:-azureuser}"

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" 1>/dev/null

az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AZURE_VM_NAME" \
    --admin-username "${AZURE_ADMIN_USER:-azureuser}" \
    --public-ip-sku Standard \
    --os-disk-size-gb "${AZURE_OS_DISK_SIZE_GB}" \
    --storage-sku Premium_LRS \
    --generate-ssh-keys \
    --image "$IMAGE" \
    --priority Spot \
    --size "$VM_SKU"

VM_IP=$(az vm show --resource-group "$RESOURCE_GROUP" --name "$AZURE_VM_NAME" --show-details --query publicIps -o tsv)

if [ -n "$VM_IP" ]; then
cat <<EOF
Virtual Machine created successfully! 🎉
You can connect to it using the following command:
ssh ${AZURE_ADMIN_USER}@${VM_IP}
EOF

else
  echo "Failed to retrieve the public IP address of the VM."
  exit 1
fi