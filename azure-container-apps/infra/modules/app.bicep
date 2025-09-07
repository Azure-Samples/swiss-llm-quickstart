metadata description = 'Deploys the Apertus - the Swiss LLM - in an Azure Container App with a sample App'
metadata author = '<dobroegl@microsoft.com>; <frsodano@microsoft.com>'

/* -------------------------------------------------------------------------- */
/*                                 PARAMETERS                                 */
/* -------------------------------------------------------------------------- */

@description('The location to deploy the container app to')
param location string = resourceGroup().location

@description('The tags to apply to the container app')
param tags object = {}

@description('Principal ID of the user running the deployment')
param azurePrincipalId string

@description('If true, use and setup authentication with Azure Entra ID')
param useAuthentication bool = false

@description('Name of the Managed Identity to use for the container apps')
param appIdentityName string

@description('The name of the container registry')
param containerRegistryName string

@description('The name of the key vault')
param keyVaultName string

@description('The auth tenant id for the app (leave blank in AZD to use your current tenant)')
param authTenantId string = '' // Make sure authTenantId is set if not using AZD

@description('Name of the authentication client secret in the key vault')
param authClientSecretName string = 'AZURE-AUTH-CLIENT-SECRET'

@description('The auth client id for the frontend and backend app')
param authClientAppId string = ''

@description('Client secret of the authentication client')
@secure()
param authClientSecret string = ''

@description('The name of the container apps environment')
param containerAppsEnvironmentName string

@description('The ')
param logAnalyticsWorkspaceResourceId string

@description('Name of the storage account to use for the container apps environment')
param storageAccountName string

@description('True if the container app has already been deployed')
param exists bool

@description('Hugging Face Hub Token to access private models')
@secure()
param huggingFaceHubToken string = ''

/* -------------------------------- Frontend -------------------------------- */

@maxLength(32)
@description('Name of the frontend container app to deploy. If not specified, a name will be generated. The maximum length is 32 characters.')
param frontendContainerAppName string = ''

@description('Connection string for the Azure Application Insights component')
param appInsightsConnectionString string

/* ------------------------ Common App Resources  -------------------------- */


resource appIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: appIdentityName
}

module containerRegistry 'br/public:avm/res/container-registry/registry:0.9.3' = {
  name: '${deployment().name}-containerRegistry'
  params: {
    name: containerRegistryName
    location: location
    tags: tags
    acrSku: 'Premium'
    acrAdminUserEnabled: true
    exportPolicyStatus: 'enabled'
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'AcrPull'
        principalId: appIdentity.properties.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'AcrPull'
        principalId: azurePrincipalId
      }
    ]
  }
}

module keyVault 'br/public:avm/res/key-vault/vault:0.12.1' = {
  name: '${deployment().name}-keyVault'
  scope: resourceGroup()
  params: {
    name: keyVaultName
    location: location
    tags: tags
    enableRbacAuthorization: true
    enablePurgeProtection: false // Set to true to if you deploy in production and want to protect against accidental deletion
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Key Vault Secrets User'
        principalId: appIdentity.properties.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Key Vault Administrator'
        principalId: azurePrincipalId
      }
    ]
    secrets: huggingFaceHubToken != ''
      ? [
          {
            name: 'hugging-face-hub-token'
            value: huggingFaceHubToken
          }
        ]
      : []
  }
}

module containerAppsEnvironment 'br/public:avm/res/app/managed-environment:0.10.2' = {
  name: '${deployment().name}-containerAppsEnvironment'
  params: {
    name: containerAppsEnvironmentName
    location: location
    tags: tags
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
    daprAIConnectionString: appInsightsConnectionString
    zoneRedundant: false
    publicNetworkAccess: 'Enabled'
    workloadProfiles: [
      {
        workloadProfileType: 'Consumption'
        name: 'Consumption'
        enableFips: false
      }
      {
        workloadProfileType: 'Consumption-GPU-NC24-A100'
        name: 'GPU-NC24-A100'
        enableFips: false
      }
    ]
    storages: [
      {
        accessMode: 'ReadWrite'
        kind: 'SMB'
        storageAccountName: storageAccountName
        shareName: 'huggingfacecache'
      }
    ]
  }
}

/* ------------------------------ Frontend App ------------------------------ */

module frontendApp 'app/container-apps.bicep' = {
  name: '${deployment().name}-frontendContainerApp'
  scope: resourceGroup()
  params: {
    name: frontendContainerAppName
    exists: exists
    tags: tags
    identityId: appIdentity.id
    containerAppsEnvironmentName: containerAppsEnvironment.outputs.name
    containerRegistryName: containerRegistry.outputs.name
    serviceName: 'frontend' // Must match the service name in azure.yaml
    env: {
      // Required for container app daprAI
      APPLICATIONINSIGHTS_CONNECTION_STRING: appInsightsConnectionString
      AZURE_RESOURCE_GROUP: resourceGroup().name
      SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS: true
      SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS_SENSITIVE: true // OBS! You might want to remove this in production

      // Required for managed identity
      AZURE_CLIENT_ID: appIdentity.properties.clientId

      // Required for the frontend app to ask for a token for the backend app
      AZURE_CLIENT_APP_ID: authClientAppId
    }
    secrets: {
      'hugging-face-hub-token': 'keyvaultref:${keyVault.outputs.uri}secrets/hugging-face-hub-token'
    }
    keyvaultIdentities: useAuthentication
      ? {
          'microsoft-provider-authentication-secret': {
            keyVaultUrl: '${keyVault.outputs.uri}secrets/${authClientSecretName}'
            identity: appIdentity.id
          }
        }
      : {}
    authConfig: useAuthentication
      ? {
          platform: {
            enabled: true
          }
          globalValidation: {
            redirectToProvider: 'azureactivedirectory'
            unauthenticatedClientAction: 'RedirectToLoginPage'
          }
          identityProviders: {
            azureActiveDirectory: {
              registration: {
                clientId: authClientAppId
                clientSecretSettingName: 'microsoft-provider-authentication-secret'
                openIdIssuer: '${environment().authentication.loginEndpoint}${authTenantId}/v2.0' // Works only for Microsoft Entra
              }
              validation: {
                defaultAuthorizationPolicy: {
                  allowedApplications: [
                    appIdentity.properties.clientId
                    '04b07795-8ddb-461a-bbee-02f9e1bf7b46' // AZ CLI for testing purposes
                  ]
                }
                allowedAudiences: [
                  'api://${authClientAppId}'
                ]
              }
            }
          }
        }
      : {
          platform: {
            enabled: false
          }
        }
  }
}

/* -------------------------------------------------------------------------- */
/*                                   OUTPUTS                                  */
/* -------------------------------------------------------------------------- */

@description('Endpoint URL of the Frontend service')
output frontendAppUrl string = frontendApp.outputs.URL

@description('Resource ID of the Key Vault')
output keyVaultResourceId string = keyVault.outputs.resourceId

@description('Resource ID of the Container Registry')
output containerRegistryResourceId string = containerRegistry.outputs.resourceId

@description('Container registry login server URL')
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
