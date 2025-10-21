import os
import http.client
import json

CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
CONTENT_SAFETY_KEY = os.environ.get("CONTENT_SAFETY_KEY")
OPEN_AI_ENDPOINT = os.environ.get("OPEN_AI_ENDPOINT")
OPEN_AI_DEPLOYMENT_NAME = os.environ.get("OPEN_AI_DEPLOYMENT_NAME")

endpoint = CONTENT_SAFETY_ENDPOINT.removeprefix("https://").rstrip("/")
conn = http.client.HTTPSConnection(endpoint)
headers = {
  "Ocp-Apim-Subscription-Key": CONTENT_SAFETY_KEY,
  "Content-Type": "application/json",
}
payload = json.dumps({
  "domain": "Generic",
  "task": "QnA",
  "qna": {
    "query": "When the Artemis II mission is planned to be launched?"
  },
  "text": "Sorry I cannot answer that.",
  "groundingSources": [
    "NASA is currently targeting a launch no earlier than February 5, 2026 for Artemis II, with monthly windows that run into April 2026 while final safety work wraps up."
  ],
  "correction": True,
  "llmResource": {
   "resourceType": "AzureOpenAI",
   "azureOpenAIEndpoint": OPEN_AI_ENDPOINT,
   "azureOpenAIDeploymentName": OPEN_AI_DEPLOYMENT_NAME
  }
})
conn.request("POST", "/contentsafety/text:detectGroundedness?api-version=2024-09-15-preview", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))