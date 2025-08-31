# Swiss LLM on Azure Cloud

<img src="https://upload.wikimedia.org/wikipedia/commons/f/f3/Flag_of_Switzerland.svg" alt="swiss flag" width="100"/>

This quickstart will help you get up & running with the Swiss LLM models built by the [**Swiss National AI Initiative  (SNAI)**](https://swiss-ai.org), on Azure.

**Note:** As the models are very new, this is a living documentation and will be updated frequently as more information gets publicly available about the models. If you find any errors or inconsistencies, please open a pull request.

## Documentation

We provide several ways of deployming the model

| Documentation                                                                | Model version | Status      |
| ---------------------------------------------------------------------------  | ------------- | ----------- |
| [Azure Container Apps with Serverless GPUs](azure-container-apps/README.md)  | 8b            | ⚠️ Preview  |   
| [Azure Virtual Machine with GPUs](azure-virtual-machine/README.md)           | 8b, 70b       | ⚠️ Preview  |
| [Azure Kubernetes Service with GPUs](azure-kubernetes-service/README.md)     | 8b, 70b       | 🚧 Work in Progress |

## Resources

TODO

- Getting Started on Azure
- Azure Pricing / cost estimator
- Create a Spot instance
- Deoploy a GPU-powered VM
- Azure AI Foundy
- Blog: [Deploying Language Models on Azure Kubernetes: A Complete Beginner's Guide](https://huggingface.co/blog/vpkprasanna/deploying-language-models-on-azure)
- https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks-gpu/gpu-aks