# How to Run APERTUS - The Swiss LLM Model - with a Docker Container in Docker or Kubernetes

This quickstart provides the following support:

* Instructions on how to build the vLLM containers to use APERTUS 8B and 70B.
* You can build and use this container on your local machine or on a cloud VM with capable GPU support (e.g. Azure, AWS, GCP).
* You can use the container for any architecture in Azure (Azure Container Instances, Azure Kubernetes Service, Azure Virtual Machines, Azure Contianer Apps) or other providers (Local, AWS, GCP, etc). 

Find other deployment options [here](../README.md)

## Getting Started

these instructions are helping you to build and run the docker image for APERTUS with vLLM.
If you would like just to run the container, you can pull the image directly from GitHub Container Registry:

```bash
TBD
```

### Prerequisites

Before you begin:

- Docker installed on your local machine or cloud VM. Follow the instructions for your platform:
  - [Install Docker on Ubuntu | Docker Documentation](https://docs.docker.com/engine/install/ubuntu/)
  - [Install Docker on Windows | Docker Documentation](https://docs.docker.com/desktop/install/windows-install/)
  - [Install Docker on macOS | Docker Documentation](https://docs.docker.com/desktop/install/mac-install/)
- An NVIDIA GPU with the appropriate drivers installed.
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed to enable GPU support in Docker.
- A HuggingFace account and an access token with permission to download the APERTUS models. You can create a token in your HuggingFace account settings under "Access Tokens".
- (Optional) If you are using an Azure VM, ensure that the VM is an N-series instance with GPU support. Follow the instructions to set up the NVIDIA drivers on your Azure VM: [Azure N-series GPU driver setup for Linux - Azure Virtual Machines | Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/n-series-driver-setup#ubuntu)


### Build the Docker Image

From **the root of this repository**, build the docker image:

```bash
docker build -f src/apertus-vllm/Dockerfile -t swiss-llm-vllm .
```

### Run the Docker Image

The docker image in configured to run vLLM with the **APERTUS 8B model** by default in chatbot optimization with the following defualt parameters.

| Parameters | Default Value |
|---|---|
| MODEL_ID | swiss-ai/Apertus-8B-Instruct-2509 |
| LOAD_FORMAT | safetensors |
| SAFETENSORS_LOAD_STRATEGY | eager |
| GPU_MEMORY_UTILIZATION | 0.95 |
| MAX_MODEL_LEN | 4096 |
| MAX_NUM_SEQS | 512 |
| ENFORCE_EAGER | True |
| IGNORE-PATTERNS | "original/*/" |
| TENSOR_PARALLEL_SIZE | 1 |
| KV_CACHE_DTYPE | auto |
| SWAP_SPACE | 0 |
| CPU_OFFLOAD_GB | 0 |

For the meaning of the parameters, see the [vLLM Serve Parameters](https://docs.vllm.ai/en/latest/cli/serve.html).

To run the container with the default parameters, use the following command:

```bash
docker run --gpus all -p 8000:8000 -e HF_TOKEN=your_token_here -v ~/.cache/huggingface:/home/appuser/workspace/hf-home apertus-vllm
```
the additional parameters for docker run are the following:

- `-e HF_TOKEN` gives the contianer the capability to donwload the model from HuggingFace.
- `-v ~/.cache/huggingface:/home/appuser/workspace/hf-home` is the mapping of the HuggingFace cache from the host to the container. the HuggingFace cache is using the `HF_HOME` environment variable, which is set to `/home/appuser/workspace/hf-home` in the container.

To run the container with the **APERTUS 70B model**, you need to override some of the default parameters. this is an example command to run the container with the 70B model based on a 2xA100 40GB GPU VM (NC48NC48ads_A100_v4 in Azure):

```bash
docker run --gpus all -p 8000:8000 -e HF_TOKEN=your_token_here -e MODEL_ID=swiss-ai/Apertus-70B-Instruct-2509 -e MAX_MODEL_LEN=32768 -e SWAP_SPACE=128 -e KV_CACHE_DTYPE=fp8 -e TENSOR_PARALLEL_SIZE=2 -v ~/.cache/huggingface:/home/appuser/workspace/hf-home apertus-vllm
```

 docker run --gpus all -it --rm --user root --entrypoint bash apertus-vllm

 ### Run the Docker Image interactively

To run the container interactively, use the following command:

```bash
docker run --gpus all -it --rm --user root --entrypoint bash apertus-vllm
```

This will give you a bash shell inside the container. You can then run the vLLM serve command manually with your desired parameters.

 ## References

- [Azure N-series GPU driver setup for Linux - Azure Virtual Machines | Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/n-series-driver-setup#ubuntu)
- [vLLM](https://docs.vllm.ai/en/v0.7.3/index.html)
- [vLLM Serve Parameters](https://docs.vllm.ai/en/latest/cli/serve.html)
- [Swiss-ai/Apertus-8B-Instruct-2509 · Hugging Face](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509)
- [Swiss-ai/Apertus-70B-Instruct-2509 · Hugging Face](https://huggingface.co/swiss-ai/Apertus-70B-Instruct-2509)