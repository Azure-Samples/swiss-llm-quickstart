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

Setup your environment:
```bash
export LABEL=swiss-llm-001
export LOCATION=swedencentral
```

- `LABEL` is a name that will be re-used for various Azure resources, such as resource groups and virtual machines.
- `LOCATION` is the Azure region to which your resources will be deployed.

Be sure to have quota for your virtual machine. You can check quota availability with the following command:

```bash
az vm list-usage --location "${LOCATION}" --query "[?name.value=='StandardNCADSA100v4Family']" -o table
```

Check that the `Limit` value is at least 24.

TODO


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

From [Azure N-series GPU driver setup for Linux - Azure Virtual Machines | Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/n-series-driver-setup#ubuntu):
```bash
sudo apt update && sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers install
sudo reboot

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo apt install -y ./cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt -y install cuda-toolkit-12-9

cat >> .bashrc <<'EOF'
export PATH=/usr/local/cuda/bin${PATH:+:${PATH}}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64\${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
export CUDA_HOME=/usr/local/cuda/
EOF

sudo reboot
```

Then from [swiss-ai/Apertus-70B-Instruct-2509 · Hugging Face](https://huggingface.co/swiss-ai/Apertus-70B-Instruct-2509): 
and [PyTorch Get Started](https://pytorch.org/get-started/locally/#windows-pip)

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
uv run hf download swiss-ai/Apertus-70B-Instruct-2509
uv run hf download swiss-ai/Apertus-8B-Instruct-2509
```


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