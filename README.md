# How to Run APERTUS - The Swiss LLM Model - on Microsoft Azure


<img src="https://cdn-uploads.huggingface.co/production/uploads/6639f08490b7db8dcbf1a2aa/YKux3SpTciL4O60L3Ol-6.jpeg" alt="swiss flag" width="500"/>


## What is APERTUS

[**Swiss National AI Initiative  (SNAI)**](https://swiss-ai.org) has released [**Apertus**](https://www.swiss-ai.org/apertus), Switzerland’s first large-scale open, multilingual language model — a milestone in generative AI for transparency and diversity. Trained on 15 trillion tokens across more than 1,000 languages – 40% of the data is non-English – Apertus includes many languages that have so far been underrepresented in LLMs, such as Swiss German, Romansh, and many others. Apertus serves as a building block for developers and organizations for future applications such as chatbots, translation systems, or educational tools.

The model is named Apertus – Latin for “open” – highlighting its distinctive feature: the entire development process, including its architecture, model weights, and training data and recipes, is openly accessible and fully documented.


## Run APERTUS on Microsoft Azure

This quickstart will help you get up & running with the Swiss LLM models built by the [**Swiss National AI Initiative  (SNAI)**](https://swiss-ai.org), on Azure.

**Note:** As the models are very new, this is a living documentation and will be updated frequently as more information gets publicly available about the models. If you find any errors or inconsistencies, please open a pull request.

## Deployment Instructions

We provide several ways of host the model on Azure:

| Azure Host Service                                                           | Model version | Status      |
| ---------------------------------------------------------------------------  | ------------- | ----------- |
| [Azure Container Apps with Serverless GPUs](azure-container-apps/README.md)  | 8b            | ⚠️ Preview  |   
| [Azure Virtual Machine with GPUs](azure-virtual-machine/README.md)           | 8b, 70b       | ⚠️ Preview  |
| [Azure Kubernetes Service with GPUs](azure-kubernetes-service/README.md)     | 8b, 70b       | 🚧 Work in Progress |

## Resources

TODO

- Getting Started on Azure
- Azure Pricing / cost estimator
- Create a Spot instance
- Deoloy a GPU-powered VM
- Azure AI Foundy
- Blog: [Deploying Language Models on Azure Kubernetes: A Complete Beginner's Guide](https://huggingface.co/blog/vpkprasanna/deploying-language-models-on-azure)
- https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks-gpu/gpu-aks

## Citation

```bibtex
@misc{swissai2025apertus,
  title={{Apertus: Democratizing Open and Compliant LLMs for Global Language Environments}},
  author={Apertus Team},
  year={2025},
  howpublished={\url{https://huggingface.co/swiss-ai/Apertus-70B-2509}}
}
```