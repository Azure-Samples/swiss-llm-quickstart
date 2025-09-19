#!/usr/bin/env bash
set -euo pipefail
[[ ${DEBUG-} =~ ^1|yes|true$ ]] && set -o xtrace

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  -s, --sku SKU                 VM size to create (default: Standard_NC24ads_A100_v4, alternative: Standard_NC48ads_A100_v4)
      --label LABEL             Resource label (default: swiss-llm-001)
  -l, --location LOCATION       Azure location (default: switzerlandnorth)
  -g, --resource-group RG       Resource group name (default: rg-<label>)
  -n, --name VM_NAME            Azure VM name (default: vmswissllma100)
  -u, --user ADMIN_USER         Admin username (default: azureuser)
      --image IMAGE             VM image identifier
  -h, --help                    Show this help and exit

Examples:
  # Create a NC24 VM (default):
  ./deploy.sh

  # Create a different SKU in a different region:
  ./deploy.sh --sku Standard_NC6ads_A100_v4 --location swedencentral
EOF
  exit 0
}

# Defaults (can be overridden via environment variables)
LABEL="${LABEL:-swiss-llm-001}"
# Sanitize label: remove all underscores and dashes
ALPHA="${LABEL//[-_]/}"
LOCATION="${LOCATION:-switzerlandnorth}"
VM_NAME="${VM_NAME:-vm-swiss-llm-001}"
IMAGE="${AZURE_IMAGE:-Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest}"
VM_SKU="${VM_SKU:-Standard_NC24ads_A100_v4}"
AZURE_OS_DISK_SIZE_GB="${AZURE_OS_DISK_SIZE_GB:-512}"
AZURE_ADMIN_USER="${AZURE_ADMIN_USER:-azureuser}"

# Parse CLI args (override env vars)
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--sku)
      VM_SKU="$2"; shift 2;;
    --label)
      LABEL="$2"; shift 2;;
    -l|--location|--region)
      LOCATION="$2"; shift 2;;
    -g|--resource-group)
      RESOURCE_GROUP="$2"; shift 2;;
    -n|--name)
      VM_NAME="$2"; shift 2;;
    -u|--user)
      AZURE_ADMIN_USER="$2"; shift 2;;
    --image)
      IMAGE="$2"; shift 2;;
    -h|--help)
      usage;;
    *)
      echo "Unknown option: $1" >&2
      usage;;
  esac
done

# Compute resource group default if not provided explicitly
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-${LABEL}}"

# Summary of chosen values
cat <<EOF
Deploying VM with the following configuration:
  Label:          ${LABEL}
  Location:       ${LOCATION}
  Resource Group: ${RESOURCE_GROUP}
  VM Name:        ${VM_NAME}
  Image:          ${IMAGE}
  VM SKU:         ${VM_SKU}
  Admin User:     ${AZURE_ADMIN_USER}
EOF

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" 1>/dev/null

az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --admin-username "${AZURE_ADMIN_USER}" \
    --public-ip-sku Standard \
    --os-disk-size-gb "${AZURE_OS_DISK_SIZE_GB}" \
    --storage-sku Premium_LRS \
    --generate-ssh-keys \
    --image "$IMAGE" \
    --priority Spot \
    --size "$VM_SKU" \
    --custom-data ./init.sh

VM_IP=$(az vm show --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --show-details --query publicIps -o tsv)

if [ -n "$VM_IP" ]; then
cat <<EOF
Virtual Machine created successfully! 🎉
You can connect to it using the following command:
ssh ${AZURE_ADMIN_USER}@${VM_IP}
EOF

else
  echo "Failed to retrieve the public IP address of the VM." >&2
  exit 1
fi
