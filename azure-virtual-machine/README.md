# How to Run APERTUS - The Swiss LLM Model - on Azure Virtual Machine

This quickstart provides the following support:

* Instructions on how to download the model from HuggingFace.
* Provision suitable _Spot instances_ in your Azure Subscription.
* Guidance on how to deploy and serve the model for **local inference**. 

Find other deployment options [here](../README.md)

## Demo

![Demo](../assets/images/azure-virtual-machine-8b-instruct-run.gif)

## Getting Started

For the **APERTUS 8B**, we will use the `Standard_NC24ads_A100_v4` SKU in Azure.

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


For the **APERTUS 70B**, we will use the `Standard_NC48ads_A100_v4` SKU in Azure.

| Component | Specification |
|---|---|
| Series | NC_A100_v4 |
| vCPUs | 48 |
| CPU | AMD EPYC 7V13 (Milan) [x86-64] |
| System memory (RAM) | 440 GiB |
| GPUs | 2 × NVIDIA A100 PCIe |
| GPU memory | 2 x 80 GB |
| Local temporary disk | 64 GiB (per-size; series range: 64–256 GiB) |
| NVMe local storage | Up to 1920 GiB (series) |
| Network bandwidth | Nominal: ~20,000 Mbps (20 Gbps); series supports up to 80,000 Mbps (80 Gbps) |
| NICs | 2 (series range: 2–8) |

These SKUs are available only on a subset of Azure Regions. 

Please check the availability on the [**Product Availability by Region**](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/table) page.

### Setup your environment

#### Environment Variables

Add the following environment variables:

- `LABEL` is a name that will be re-used for various Azure resources, such as resource groups and virtual machines.
- `LOCATION` is the Azure region to which your resources will be deployed. Be sure that you choose an Azure region where the SKU is available and you have quota for it.

in this example we used **Switzerland North** Datacenter.

```bash
export LABEL=swiss-llm-001
export LOCATION=switzerlandnorth
```
#### Check CPU Quota for the VM

Based on the location you choose, you can check the current quota with the following:

```bash
az vm list-usage --location "${LOCATION}" --query "[?name.value=='StandardNCADSA100v4Family']" -o table
```

![Azure VM Quota Result](../assets/images/azure-virtual-machine-quota.png)

Check that the `Limit` value is at least **24** for `Standard_NC24ads_A100_v4` for APERTUS 8B and at least **48** for APERTUS 70B

#### Clone the repository

```bash
git clone https://github.com/Azure-Samples/swiss-llm-quickstart
cd swiss-llm-quickstart/azure-virtual-machine
```

#### Deploy the Virtual Machine in Azure

Based on the model you would like to install, you can run **one** of the following scripts

for [Apertus-8B-Instruct-2509](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509)

```bash
./deploy.sh
```

for [Apertus-70B-Instruct-2509](https://huggingface.co/swiss-ai/Apertus-70B-Instruct-2509)

```bash
./deploy_NC48.sh
```


## Virtual Machine Installation

You should now be able to access the virtual machine with the SSH command 
displayed after executing the deploy script:

```bash
ssh azureuser@__public_ip_address__
```
When connected, you need to install the correct NVIDIA Drivers.

Ubuntu packages NVIDIA proprietary drivers. Those drivers come directly from NVIDIA and are simply packaged by Ubuntu so that they can be automatically managed by the system.

The following script will:

1) Install ubuntu-drivers utility
2) Install the latest NVIDIA drivers
3) Download and install the CUDA toolkit from NVIDIA
4) Update PATH
5) Reboot the VM

```bash
sudo apt update && sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers install
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo apt install -y ./cuda-keyring_1.1-1_all.deb
rm -f ./cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-8
sudo apt install -y libpython3.10-dev

cat >> ~/.bashrc <<'EOF'
export PATH=/usr/local/cuda/bin${PATH:+:${PATH}}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64\${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
export CUDA_HOME=/usr/local/cuda/
export HF_HUB_ENABLE_HF_TRANSFER=1
export TORCHDYNAMO_DISABLE=1
export TORCH_LOGS="+dynamo"
export TORCH_CUDA_ARCH_LIST="8.0;8.6"
EOF

sudo reboot
```

### Prepare the Python Environment

Log in again into the VM and execute the following commands to install UV and prepare a python environment:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv init
```

Install `PyTorch`:

```bash
cat >> pyproject.toml <<'EOF'
[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true

[tool.uv.sources]
torch = [
  { index = "pytorch-cu128", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
torchvision = [
  { index = "pytorch-cu128", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
EOF
uv add torch torchvision
uv add git+https://github.com/vllm-project/vllm.git@main
uv add git+https://github.com/huggingface/transformers.git@main
uv add git+https://github.com/nickjbrowning/XIELU
uv add "huggingface_hub[cli]"
uv add rich
uv add flashinfer-python
uv add huggingface_hub hf_transfer
uv add fastsafetensors
```

Activate
Log in into Hugging Face Hub and install the model.

for [Apertus-8B-Instruct-2509](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509)

```bash
uv run hf auth login
uv run hf download swiss-ai/Apertus-8B-Instruct-2509
```

for [Apertus-70B-Instruct-2509](https://huggingface.co/swiss-ai/Apertus-70B-Instruct-2509)

```bash
uv run hf auth login
uv run hf download swiss-ai/Apertus-70B-Instruct-2509
```

## Run the model using vLLM

We will use [vLLM](https://docs.vllm.ai/en/v0.7.3/index.html) to run the model.


for [Apertus-8B-Instruct-2509](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509)

```bash
uv run vllm serve swiss-ai/Apertus-8B-Instruct-2509 \
  --load-format fastsafetensors \
  --gpu-memory-utilization 0.95 \
  --max-model-len 4096 \
  --max-num-seqs 512 \
  --swap-space 32 \
  --dtype auto \
  --ignore-patterns "original/*/" \
  --safetensors-load-strategy eager \
  --enforce-eager 
```

for [Apertus-70B-Instruct-2509](https://huggingface.co/swiss-ai/Apertus-70B-Instruct-2509)

```bash
uv run vllm serve swiss-ai/Apertus-70B-Instruct-2509 \
  --load-format fastsafetensors \
  --max-model-len 32768 \
  --max-num-seqs 512 \
  --swap-space 128 \
  --kv-cache-dtype fp8 \
  --gpu-memory-utilization 0.95 \
  --tensor-parallel-size 2 \
  --dtype auto \
  --ignore-patterns "original/*/" \
  --enforce-eager
```

## Test the Model

To test the model, you need to open an additional SSH terminal on the VM (the first one is used to keep the FastAPI server up and running) and run the following command:

for [Apertus-8B-Instruct-2509](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509)

```bash
curl http://localhost:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-d '{
    "model": "swiss-ai/Apertus-8B-Instruct-2509",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Give a simple explanation of what gravity is for a high school level physics course with a few typical formulas. Use lots of emojis and do it in French, Swiss German, Italian and Romansh."}
    ]
}'
```

for [Apertus-70B-Instruct-2509](https://huggingface.co/swiss-ai/Apertus-70B-Instruct-2509)

```bash
curl http://localhost:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-d '{
    "model": "swiss-ai/Apertus-70B-Instruct-2509",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Give a simple explanation of what gravity is for a high school level physics course with a few typical formulas. Use lots of emojis and do it in French, Swiss German, Italian and Romansh."}
    ]
}'
```

```
If the installation if successfully completed, you should see something similar to this:

<img src="../assets/images/azure-virtual-machine-test.png" alt="Test Result" width="auto"/>

## Clean Up

To clean up all the resources created by this sample just delete the resource group.

```bash
az group delete --name MyResourceGroup --no-wait
```

## Cost Estimation

Pricing varies per region and usage, so it isn't possible to predict exact costs for your usage.
However, you can try the [Azure pricing calculator](https://azure.com/e/e3490de2372a4f9b909b0d032560e41b) for the resources below.

- [Azure Virtual Machine](https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/)

⚠️ To avoid unnecessary costs, remember to take down your resources if it's no longer in use.

## References

- [Azure N-series GPU driver setup for Linux - Azure Virtual Machines | Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/n-series-driver-setup#ubuntu)
- [vLLM](https://docs.vllm.ai/en/v0.7.3/index.html)
- [Swiss-ai/Apertus-8B-Instruct-2509 · Hugging Face](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509)
- [Swiss-ai/Apertus-70B-Instruct-2509 · Hugging Face](https://huggingface.co/swiss-ai/Apertus-70B-Instruct-2509)
- [PyTorch Get Started](https://pytorch.org/get-started/locally/#windows-pip)