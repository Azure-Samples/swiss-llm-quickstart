#!/usr/bin/env bash
set -euo pipefail

set -o xtrace

sudo apt update && sudo apt install -y ubuntu-drivers-common
sudo env DEBIAN_FRONTEND=noninteractive ubuntu-drivers install

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo apt install -y ./cuda-keyring_1.1-1_all.deb
rm -f ./cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-8
sudo apt install -y libpython3.10-dev

cat >> /home/azureuser/.bashrc <<'EOF'
export PATH=/usr/local/cuda/bin${PATH:+:${PATH}}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64\${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
export CUDA_HOME=/usr/local/cuda/
export HF_HUB_ENABLE_HF_TRANSFER=1
export TORCHDYNAMO_DISABLE=1
export TORCH_LOGS="+dynamo"
export TORCH_CUDA_ARCH_LIST="8.0;8.6"
EOF

sudo reboot