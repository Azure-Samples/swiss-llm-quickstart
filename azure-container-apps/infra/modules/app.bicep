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


/* -------------------------------------------------------------------------- */
/*                                   OUTPUTS                                  */
/* -------------------------------------------------------------------------- */

@description('Name of the created container app')
output name string = frontendApp.outputs.name

@description('Endpoint URL of the Frontend service')
output frontendAppUrl string = frontendApp.outputs.URL

@description('Resource ID of the Key Vault')
output keyVaultResourceId string = keyVault.outputs.resourceId

@description('Resource ID of the Container Registry')
output containerRegistryResourceId string = containerRegistry.outputs.resourceId

@description('Container registry login server URL')
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer

