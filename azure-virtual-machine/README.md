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

#### GPU Quotas

Be sure to have quota for your virtual machine. You can check quota availability with the following command:

```bash
az vm list-usage --location "swedencentral" --query "[?name.value=='StandardNCADSA100v4Family']" -o table
```

TODO

### Installation

TODO

- Step 1
- Step 2 
- ...

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