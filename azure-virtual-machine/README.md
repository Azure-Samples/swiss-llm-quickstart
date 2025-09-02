# How to Run APERTUS - The Swiss LLM Model - on Azure Virtual Machine

This quickstart provides the following support:

* Instructions on how to download the model from HuggingFace.
* Provision suitable _Spot instances_ in your Azure Subscription.
* Guidance on how to deploy and serve the model for **local inference**. 

Find other deployment options [here](../README.md)

## Demo

![Demo](../assets/images/azure-virtual-machine-8b-instruct-run.gif)

## Getting Started

We will use the `Standard_NC24ads_A100_v4` SKU in Azure to host the model.
This SKU is suitable for both APERTUS 8B and 70B.

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


This SKU is available only on a subset of Azure Regions. 

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

Check that the `Limit` value is at least **24** for `Standard_NC24ads_A100_v4`.

#### Clone the repository

```bash
git clone https://github.com/Azure-Samples/swiss-llm-quickstart
cd swiss-llm-quickstart/azure-virtual-machine
```

#### Deploy the virtual machine

```bash
./deploy.sh
```

## Virtual Machine Installation

You should now be able to access the virtual machine with the SSH command 
displayed after executing `./deploy.sh`:

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
sudo apt update
sudo apt install -y cuda-toolkit-12-9

cat >> ~/.bashrc <<'EOF'
export PATH=/usr/local/cuda/bin${PATH:+:${PATH}}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64\${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
export CUDA_HOME=/usr/local/cuda/
EOF

sudo reboot
```

Log in again into the VM and execute the following commands to prepare the python environment:

```bash
sudo apt install python3-venv
python3 -m venv .venv
. .venv/bin/activate
```

Install `PyTorch`:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129
```

Install `transformers` and HuggingFace CLI:

```bash
pip install -U transformers
pip install -U "huggingface_hub[cli]"
pip install -U rich
```

Log in into Hugging Face Hub and install the model.

In this example, we are using [Apertus-8B-Instruct-2509](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509)

```bash
hf auth login
hf download swiss-ai/Apertus-8B-Instruct-2509
```


## Test the Model

To test the model, use the provided `run.py`.

From the root of the cloned repository (from your local machine), you need to copy the `run.py` script on the Virtual Machine:

```bash
scp run.py azureuser@__public_ip_address__:
```

Now, Log in into the virtual machine again and run:

```bash
. .venv/bin/activate
python run.py
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
- [Swiss-ai/Apertus-8B-Instruct-2509 · Hugging Face](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509)
- [PyTorch Get Started](https://pytorch.org/get-started/locally/#windows-pip)
