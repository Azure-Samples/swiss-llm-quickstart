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
module storageAccount 'br/public:avm/res/storage/storage-account:0.26.0' = {
  name: '${deployment().name}-storageAccount'
  scope: resourceGroup()
  params: {
    location: location
    tags: tags
    name: _storageAccountName
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

module app 'modules/app.bicep' = {
  name: '${deployment().name}-app'
  params: {
    location: location
    tags: tags
    appIdentityName: _appIdentityName
    appInsightsConnectionString: appInsightsComponent.outputs.connectionString
    authClientAppId: authClientAppId
    authClientSecret: authClientSecret
    authClientSecretName: authClientSecretName
    authTenantId: authTenantId

    containerAppsEnvironmentName: _containerAppsEnvironmentName
    containerRegistryName: _containerRegistryName
    frontendContainerAppName: _frontendContainerAppName
    keyVaultName: _keyVaultName
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspace.outputs.resourceId
    useAuthentication: useAuthentication
    azurePrincipalId: azurePrincipalId
  }
}

/* ------------------------------ CosmosDB  --------------------------------- */

/* module cosmosDbAccount 'br/public:avm/res/document-db/database-account:0.12.0' = {
  name: '${deployment().name}-cosmosDbAccount'
  params: {
    name: _cosmosDbAccountName
    location: location
    sqlRoleAssignmentsPrincipalIds: [
      azurePrincipalId
      appIdentity.outputs.principalId
    ]
  }
} */

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
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = app.outputs.containerRegistryLoginServer

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

