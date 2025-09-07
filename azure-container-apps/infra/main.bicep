metadata name = 'swiss-llm-aca'
metadata description = 'Deploys the Apertus - the Swiss LLM - in an Azure Container App'
metadata author = '<dobroegl@microsoft.com>; <frsodano@microsoft.com>'

/* -------------------------------------------------------------------------- */
/*                                 PARAMETERS                                 */
/* -------------------------------------------------------------------------- */

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@description('Principal ID of the user running the deployment')
param azurePrincipalId string

@description('Location for all resources')
param location string

@description('Extra tags to be applied to provisioned resources')
param extraTags object = {}

@description('If true, use and setup authentication with Azure Entra ID')
param useAuthentication bool = false


/* ---------------------------- Shared Resources ---------------------------- */

@maxLength(63)
@description('Name of the log analytics workspace to deploy. If not specified, a name will be generated. The maximum length is 63 characters.')
param logAnalyticsWorkspaceName string = ''

@maxLength(255)
@description('Name of the application insights to deploy. If not specified, a name will be generated. The maximum length is 255 characters.')
param applicationInsightsName string = ''

@description('Application Insights Location')
param appInsightsLocation string = location

@description('The auth tenant id for the app (leave blank in AZD to use your current tenant)')
param authTenantId string = '' // Make sure authTenantId is set if not using AZD

@description('Name of the authentication client secret in the key vault')
param authClientSecretName string = 'AZURE-AUTH-CLIENT-SECRET'

@description('The auth client id for the frontend and backend app')
param authClientAppId string = ''

@description('Client secret of the authentication client')
@secure()
param authClientSecret string = ''

@maxLength(50)
@description('Name of the container registry to deploy. If not specified, a name will be generated. The name is global and must be unique within Azure. The maximum length is 50 characters.')
param containerRegistryName string = ''

@maxLength(60)
@description('Name of the container apps environment to deploy. If not specified, a name will be generated. The maximum length is 60 characters.')
param containerAppsEnvironmentName string = ''

/* -------------------------------- Frontend -------------------------------- */

@maxLength(32)
@description('Name of the frontend container app to deploy. If not specified, a name will be generated. The maximum length is 32 characters.')
param frontendContainerAppName string = ''


@description('Set if the frontend container app already exists.')
param backendExists bool = false

@description('Hugging Face Hub Token to access private models')
@secure()
param huggingFaceHubToken string = ''

/* -------------------------------------------------------------------------- */
/*                                  VARIABLES                                 */
/* -------------------------------------------------------------------------- */

// Load abbreviations from JSON file
var abbreviations = loadJsonContent('./abbreviations.json')

@description('Generate a unique token to make global resource names unique')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

@description('Name of the environment with only alphanumeric characters. Used for resource names that require alphanumeric characters only')
var alphaNumericEnvironmentName = replace(replace(environmentName, '-', ''), ' ', '')

@description('Tags to be applied to all provisioned resources')
var tags = union(
  {
    'azd-env-name': environmentName
    solution: 'swiss-llm-aca'
  },
  extraTags
)

/* --------------------- Globally Unique Resource Names --------------------- */

var _applicationInsightsName = !empty(applicationInsightsName)
  ? applicationInsightsName
  : take('${abbreviations.insightsComponents}${environmentName}', 255)
var _logAnalyticsWorkspaceName = !empty(logAnalyticsWorkspaceName)
  ? logAnalyticsWorkspaceName
  : take('${abbreviations.operationalInsightsWorkspaces}${environmentName}', 63)

var _storageAccountName = take(
  '${abbreviations.storageStorageAccounts}${alphaNumericEnvironmentName}${resourceToken}',
  24
)

var _containerRegistryName = !empty(containerRegistryName)
  ? containerRegistryName
  : take('${abbreviations.containerRegistryRegistries}${alphaNumericEnvironmentName}${resourceToken}', 50)
var _keyVaultName = take('${abbreviations.keyVaultVaults}${alphaNumericEnvironmentName}-${resourceToken}', 24)
var _containerAppsEnvironmentName = !empty(containerAppsEnvironmentName)
  ? containerAppsEnvironmentName
  : take('${abbreviations.appManagedEnvironments}${environmentName}', 60)


/* ----------------------------- Resource Names ----------------------------- */

// These resources only require uniqueness within resource group
var _appIdentityName = take('${abbreviations.managedIdentityUserAssignedIdentities}app-${environmentName}', 32)
var _frontendContainerAppName = empty(frontendContainerAppName)
  ? take('${abbreviations.appContainerApps}frontend-${environmentName}', 32)
  : frontendContainerAppName


/* -------------------------------------------------------------------------- */
/*                                  RESOURCES                                 */
/* -------------------------------------------------------------------------- */

// ------------------------------ Storage Account ------------------------------
module storageAccount 'br/public:avm/res/storage/storage-account:0.26.2' = {
  name: '${deployment().name}-storageAccount'
  scope: resourceGroup()
  params: {
    name: _storageAccountName
    location: location
    tags: tags
    kind: 'StorageV2'
    skuName: 'Standard_ZRS'
    publicNetworkAccess: 'Enabled' 
    networkAcls: {
      // Necessary for the user to work directly with the storage account
      defaultAction: 'Allow'
    }
    roleAssignments: [
      // TODO: review and make work for AI Foundry Evaluations
      {
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalId: azurePrincipalId
        principalType: 'User'
      }   
      {
        roleDefinitionIdOrName: 'Storage File Data Privileged Contributor'
        principalId: appIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Storage File Data Privileged Contributor'
        principalId: azurePrincipalId
        principalType: 'User'
      }
    ]
    blobServices: {
      corsRules: [
        {
          allowedOrigins: [
            'https://mlworkspace.azure.ai'
            'https://ml.azure.com'
            'https://*.ml.azure.com'
            'https://ai.azure.com'
            'https://*.ai.azure.com'
            'https://mlworkspacecanary.azure.ai'
            'https://mlworkspace.azureml-test.net'
          ]
          allowedMethods: [
            'GET'
            'HEAD'
            'POST'
            'PUT'
            'DELETE'
            'OPTIONS'
            'PATCH'
          ]
          maxAgeInSeconds: 1800
          exposedHeaders: [
            '*'
          ]
          allowedHeaders: [
            '*'
          ]
        }
      ]
      containers: [
        {
          name: 'default'
          roleAssignments: [
            {
              roleDefinitionIdOrName: 'Storage Blob Data Contributor'
              principalId: appIdentity.outputs.principalId
              principalType: 'ServicePrincipal'
            }
          ]
        }
      ]
      roleAssignments: [
      ]
      deleteRetentionPolicy: {
        allowPermanentDelete: false
        enabled: false
      }
      shareDeleteRetentionPolicy: {
        enabled: true
        days: 7
      }
    }
    fileServices: {
      shares: [
        {
          name: 'huggingfacecache'
          quotaInGB: 500
          enabledProtocols: 'SMB'
          roleAssignments: [
            {
              roleDefinitionIdOrName: 'Storage File Data SMB Share Contributor'
              principalId: appIdentity.outputs.principalId
              principalType: 'ServicePrincipal'
            }
          ]
        }
      ]
    }
  }
}

/* --------------------------------- App  ----------------------------------- */

module appIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: '${deployment().name}-appIdentity'
  scope: resourceGroup()
  params: {
    name: _appIdentityName
    location: location
    tags: tags
  }
}

module containerRegistry 'br/public:avm/res/container-registry/registry:0.9.3' = {
  name: '${deployment().name}-containerRegistry'
  params: {
    name: _containerRegistryName
    location: location
    tags: tags
    acrSku: 'Premium'
    acrAdminUserEnabled: true
    exportPolicyStatus: 'enabled'
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'AcrPull'
        principalId: appIdentity.outputs.principalId
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
    name: _keyVaultName
    location: location
    tags: tags
    enableRbacAuthorization: true
    enablePurgeProtection: false // Set to true to if you deploy in production and want to protect against accidental deletion
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Key Vault Secrets User'
        principalId: appIdentity.outputs.principalId
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
          {
            name: authClientSecretName
            value: authClientSecret
          }          
        ]
      : [
          {
            name: authClientSecretName
            value: authClientSecret
          }        
      ]
  }
}

module containerAppsEnvironment 'br/public:avm/res/app/managed-environment:0.10.2' = {
  name: '${deployment().name}-containerAppsEnvironment'
  params: {
    name: _containerAppsEnvironmentName
    location: location
    tags: tags
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspace.outputs.resourceId
    daprAIConnectionString: appInsightsComponent.outputs.connectionString
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
        storageAccountName: storageAccount.outputs.name 
        shareName: 'huggingfacecache'
      }
    ]
  }
}

/* ------------------------------ Frontend App ------------------------------ */

module frontendApp 'modules/app/container-apps.bicep' = {
  name: '${deployment().name}-frontendApp'
  scope: resourceGroup()
  params: {
    name: _frontendContainerAppName
    exists: backendExists
    tags: tags
    identityId: appIdentity.outputs.resourceId
    containerAppsEnvironmentName: containerAppsEnvironment.outputs.name
    containerRegistryName: containerRegistry.outputs.name
    serviceName: 'frontend' // Must match the service name in azure.yaml
    env: {
      // Required for container app daprAI
      APPLICATIONINSIGHTS_CONNECTION_STRING:  appInsightsComponent.outputs.connectionString
      AZURE_RESOURCE_GROUP: resourceGroup().name
      SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS: true
      SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS_SENSITIVE: true // OBS! You might want to remove this in production

      // Required for managed identity
      AZURE_CLIENT_ID: appIdentity.outputs.clientId

      // Required for the frontend app to ask for a token for the backend app
      AZURE_CLIENT_APP_ID: authClientAppId
    }
    secrets: [
      {
        name: 'hugging-face-hub-token'
        keyVaultUrl: '${keyVault.outputs.uri}secrets/hugging-face-hub-token'
        identity: appIdentity.outputs.resourceId
      }
  ]
    keyvaultIdentities: useAuthentication
      ? {
          'microsoft-provider-authentication-secret': {
            keyVaultUrl: '${keyVault.outputs.uri}secrets/${authClientSecretName}'
            identity: appIdentity.outputs.resourceId
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
                    appIdentity.outputs.clientId
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

/* ---------------------------- Observability  ------------------------------ */

module logAnalyticsWorkspace 'br/public:avm/res/operational-insights/workspace:0.11.1' = {
  name: '${deployment().name}-workspaceDeployment'
  params: {
    name: _logAnalyticsWorkspaceName
    location: location
    tags: tags
    dataRetention: 30
  }
}

module appInsightsComponent 'br/public:avm/res/insights/component:0.6.0' = {
  name: '${deployment().name}-applicationInsights'
  params: {
    name: _applicationInsightsName
    location: appInsightsLocation
    workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId
  }
}

/* -------------------------------------------------------------------------- */
/*                                   OUTPUTS                                  */
/* -------------------------------------------------------------------------- */

// Outputs are automatically saved in the local azd environment .env file.
// To see these outputs, run `azd env get-values`,  or
// `azd env get-values --output json` for json output.
// To generate your own `.env` file run `azd env get-values > .env`

/* -------------------------- Feature flags ------------------------------- */

@description('If true, use and setup authentication with Azure Entra ID')
output USE_AUTHENTICATION bool = useAuthentication


/* --------------------------- Apps Deployment ----------------------------- */

/* -------------------------------- Frontend -------------------------------- */

// @description('Endpoint URL of the Frontend service')
// output SERVICE_FRONTEND_URL string = frontendApp.outputs.frontendAppUrl

// output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
@description('The endpoint of the container registry.') // necessary for azd deploy
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer

/* ------------------------ Authentication & RBAC ------------------------- */

@description('ID of the tenant we are deploying to')
output AZURE_AUTH_TENANT_ID string = authTenantId

@description('Principal ID of the user running the deployment')
output AZURE_PRINCIPAL_ID string = azurePrincipalId

@description('Application registration client ID')
output AZURE_CLIENT_APP_ID string = authClientAppId

/* -------------------------- Diagnostic Settings --------------------------- */

@description('Application Insights name')
output AZURE_APPLICATION_INSIGHTS_NAME string = appInsightsComponent.outputs.name

@description('Log Analytics Workspace name')
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = logAnalyticsWorkspace.outputs.name

@description('Application Insights connection string')
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appInsightsComponent.outputs.connectionString

@description('Semantic Kernel Diagnostics')
output SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS bool = true

@description('Semantic Kernel Diagnostics: if set, content of the messages is traced. Set to false in production')
output SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS_SENSITIVE bool = true

@description('Name of the created container app')
output AZURE_CONTAINER_APP_NAME string = frontendApp.outputs.name
