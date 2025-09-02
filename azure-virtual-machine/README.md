# Swiss LLM on Azure Container Apps with Serverless GPU

## Features
This quickstart provides the following support:

* Instructions on how to download the model from HuggingFace
* Provision suitable _Spot instances_ in your Azure Subscription
* Guidance on how to deploy and serve the model for local inference

Find other deployment options [here](../README.md)

## Architecture Overview

TODO

## Getting Started

### Prerequisites

There are some pre-requirements for the installation to be executed.

We will use the `Standard_NC24ads_A100_v4` SKU in Azure.

| Component | Specification |
|---|---|
| Series | NC_A100_v4 |
| vCPUs | 24 |
| CPU | AMD EPYC 7V13 (Milan) [x86-64] |
| System memory (RAM) | 220 GiB |
| GPUs | 1 × NVIDIA A100 PCIe |
| GPU memory | 80 GB |
| Local temporary disk | 64 GiB (per-size; series range: 64–256 GiB) |
| NVMe local storage | Up to 960 GiB (series) |
| Network bandwidth | Nominal: ~20,000 Mbps (20 Gbps); series supports up to 80,000 Mbps (80 Gbps) |
| NICs | 2 (series range: 2–8) |
| Typical workloads | Training and batch inference for large AI models, GPU-accelerated analytics, HPC |


This SKU is available only on a subset of Azure Regions. PLease check the Availablity on the [**Product Availability by Region**](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/table) page.

### Clone the repository

```bash
git clone https://github.com/Azure-Samples/swiss-llm-quickstart
cd swiss-llm-quickstart/azure-virtual-machine
```

### Deploy the virtual machine

```bash
./deploy.sh
```

### Installation

You should now be able to access the virtual machine with the SSH command 
displayed after executing `./deploy.sh`:

```bash
ssh azureuser@[public-ip-address from the result of ./deploy.sh]
```


```bash
sudo apt update && sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers install
sudo reboot

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo apt install -y ./cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt -y install cuda-toolkit-12-9

cat >> ~/.bashrc <<'EOF'
export PATH=/usr/local/cuda/bin${PATH:+:${PATH}}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64\${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
export CUDA_HOME=/usr/local/cuda/
EOF

sudo reboot
```

See [Azure N-series GPU driver setup for Linux - Azure Virtual Machines | Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/n-series-driver-setup#ubuntu) for additional information.

Login in again and execute the following commands:

```bash
sudo apt install python3-venv
python3 -m venv .venv
. .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129
pip install -U transformers
pip install -U "huggingface_hub[cli]"

# Optionally (including PR #13 to avoid build failure)
pip install git+https://github.com/nickjbrowning/XIELU.git@197811b8f6fb427d7aaede78665ceeb00c2f5e4c

uv run hf auth login
uv run hf download swiss-ai/Apertus-8B-Instruct-2509
```

See [swiss-ai/Apertus-8B-Instruct-2509 · Hugging Face](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509): 
and [PyTorch Get Started](https://pytorch.org/get-started/locally/#windows-pip) for additional information.


### Quickstart

TODO

(Add steps to get up and running quickly)

1. git clone [repository clone url]
2. cd [repository name]
3. ...


## Demo

TODO

A demo video is included to show the steps mentioned above.
(Add steps to start up the demo)

1.
2.
3.


## Cost

TODO