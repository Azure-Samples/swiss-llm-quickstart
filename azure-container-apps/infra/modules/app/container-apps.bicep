metadata description = 'Creates an Azure Container App and deals with initial state when no container is deployed.'

@description('Name of the container app')
param name string

@description('The location to deploy the container app to')
param location string = resourceGroup().location

@description('The tags to apply to the container app')
param tags object = {}

@description('Environment variables for the container in key value pairs')
param env object = {}

@description('Resource ID of the identity to use for the container app')
param identityId string

@description('Name of the service the container app belongs to in azure.yaml')
param serviceName string

@description('Name of the container registry to use for the container app')
param containerRegistryName string

@description('Name of the container apps environment to build the app in')
param containerAppsEnvironmentName string

@description('The keyvault identities required for the container')
@secure()
param keyvaultIdentities object = {}

@description('The secrets required for the container')
@secure()
param secrets object = {}

@description('External Ingress Allowed?')
param externalIngressAllowed bool = true

@description('The auth config for the container app')
param authConfig object = {}

var keyvalueSecrets = [
  for secret in items(secrets): {
    name: secret.key
    value: secret.value
  }
]

var keyvaultIdentitySecrets = [
  for secret in items(keyvaultIdentities): {
    name: secret.key
    keyVaultUrl: secret.value.keyVaultUrl
    identity: secret.value.identity
  }
]

var environment = [
  for key in objectKeys(env): {
    name: key
    value: '${env[key]}'
  }
]

var secret_refs = [
  for key in objectKeys(secrets): {
    name: key
    secretRef: key
  }
]

var environmentVariables = union(environment, secret_refs)

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: containerAppsEnvironmentName
}

module app 'br/public:avm/res/app/container-app:0.16.0' = {
  name: name
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    managedIdentities: {
      userAssignedResourceIds: [ identityId ]
    }
    environmentResourceId: containerAppsEnvironment.id
    ingressExternal: externalIngressAllowed
    ingressTargetPort: 8000
    ingressTransport: 'auto'
    ingressAllowInsecure: false
    corsPolicy: {
      allowedOrigins: ['https://portal.azure.com', 'https://ms.portal.azure.com']
    }
    registries: [
      {
        server: '${containerRegistryName}.azurecr.io'
        identity: identityId
      }
    ]
    secrets: concat(keyvalueSecrets, keyvaultIdentitySecrets)
    containers: [
      {
        image: 'ghcr.io/azure-samples/swiss-llm-quickstart:latest'
        name: 'main'
        env: environmentVariables
        resources: {
          cpu: json('1.0')
          memory: '2.0Gi'
        }
      }
    ]
    scaleSettings: {
      minReplicas: 0
      maxReplicas: 1
    }
    authConfig: authConfig
  }
}

@description('The resource ID of the Container App.')
output resourceId string = app.outputs.resourceId

@description('The name of the Container App.')
output name string = app.name

output defaultDomain string = containerAppsEnvironment.properties.defaultDomain

output URL string = 'https://${app.outputs.fqdn}'

output internalUrl string = 'http://${app.name}'
