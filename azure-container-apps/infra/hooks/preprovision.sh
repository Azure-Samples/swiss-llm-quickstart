#!/usr/bin/env bash
set -euo pipefail
[[ ${DEBUG-} =~ ^1|yes|true$ ]] && set -o xtrace

# Learn more here: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/azd-extensibility


if [ -z "${HUGGING_FACE_HUB_TOKEN-}" ]; then
  echo "HUGGING_FACE_HUB_TOKEN is not set. Please set it to your Hugging Face token."
  echo "Example: azd env set HUGGING_FACE_HUB_TOKEN hf_your_token_here"
  exit 1
fi

