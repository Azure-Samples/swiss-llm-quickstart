import os
import logging
import aiohttp
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentThread

#------------------------------------------------------
# LOGGING
#------------------------------------------------------
logging.basicConfig(
    format="[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S", level=logging.WARNING
)

#------------------------------------------------------

async def is_prompt_attack(text: str) -> bool:
    """
    Returns True if a prompt attack (jailbreak/prompt injection) is detected by Azure Content Safety Prompt Shield.
    This function sends the input text to the Azure Content Safety REST API and analyzes the response
    to determine if a prompt attack is present.
    """
    # Get the Content Safety endpoint and key from environment variables
    CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
    CONTENT_SAFETY_KEY = os.environ.get("CONTENT_SAFETY_KEY")
    # Raise an error if either variable is missing
    if not CONTENT_SAFETY_ENDPOINT or not CONTENT_SAFETY_KEY:
        raise RuntimeError("CONTENT_SAFETY_ENDPOINT and CONTENT_SAFETY_KEY must be set.")

    # Construct the REST API URL for Prompt Shields (jailbreak/prompt injection detection)
    url = f"{CONTENT_SAFETY_ENDPOINT.rstrip('/')}/contentsafety/text:shieldPrompt?api-version=2024-09-01"

    # Prepare the HTTP headers with the subscription key and content type
    headers = {
        "Ocp-Apim-Subscription-Key": CONTENT_SAFETY_KEY,
        "Content-Type": "application/json",
    }

    # Build the payload for Prompt Shields
    payload = {
        "userPrompt": text  # The user input to check for prompt attacks
    }

    # Create an aiohttp session to make the HTTP request
    async with aiohttp.ClientSession() as session:
        # Send a POST request to the Prompt Shields API
        async with session.post(url, headers=headers, json=payload, timeout=10) as resp:
            # If the response is not successful, log the error and return False
            if resp.status != 200:
                logging.error(f"PROMPT SHIELD - Content Safety API error: {resp.status} {await resp.text()}")
                return False
            # Parse the JSON response
            data = await resp.json()

    # Return the boolean promptAttackResult field directly (True = attack detected, False = safe)
    return bool(data.get("userPromptAnalysis").get("attackDetected", False))

#------------------------------------------------------

async def is_harmful_content(text: str) -> dict:
    """
    Returns a JSON with the highest severity detected (>2) and the corresponding harm category using Azure Content Safety.
    If multiple categories have the same highest severity, the first one detected is returned.
    Example return:
        {"category": "Hate", "severity": 4}
    If no harmful category is found, returns {"category": None, "severity": 0}
    """
    CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
    CONTENT_SAFETY_KEY = os.environ.get("CONTENT_SAFETY_KEY")
    if not CONTENT_SAFETY_ENDPOINT or not CONTENT_SAFETY_KEY:
        raise RuntimeError("CONTENT_SAFETY_ENDPOINT and CONTENT_SAFETY_KEY must be set.")

    url = f"{CONTENT_SAFETY_ENDPOINT.rstrip('/')}/contentsafety/text:analyze?api-version=2024-09-01"
    headers = {
        "Ocp-Apim-Subscription-Key": CONTENT_SAFETY_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "outputType": "FourSeverityLevels"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=10) as resp:
            if resp.status != 200:
                logging.error(f"HARMFUL CONTENT - Content Safety API error: {resp.status} {await resp.text()}")
                return {"category": None, "severity": 0}
            data = await resp.json()

    # Find the highest severity and its category.
    # If multiple categories have the same highest severity, the first one detected is returned.
    max_severity = -1
    max_category = None
    for cat in data.get("categoriesAnalysis", []):
        severity = cat.get("severity", 0)
        if severity > max_severity:
            max_severity = severity
            max_category = cat.get("category")
    # Only consider harmful if severity > 2
    if max_severity > 2:
        return {"category": max_category, "severity": max_severity}
    else:
        return {"category": None, "severity": 0}

#------------------------------------------------------

async def groundedness_detection(text: str, domain: str = "Generic", query: str = None, threshold: float = 0.40) -> dict:
    """
    Calls the Agent in AI Foundry (PROJECT_ENDPOINT, AGENT_ID) to get the grounding source for the query,
    then checks if the provided text is grounded in that source using Azure AI Content Safety Groundedness Detection.
    Always uses QnA task and NonReasoning mode for speed.
    Returns True if grounded, False otherwise.
    """
    # ENVIRONMENT VARIABLES - Grounded Resources generation
    PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT")
    AGENT_ID = os.environ.get("AGENT_ID")
    if not PROJECT_ENDPOINT or not AGENT_ID:
        raise RuntimeError("PROJECT_ENDPOINT and AGENT_ID must be set.")
    
    # ENVIRONMENT VARIABLES - Correction LLM
    OPEN_AI_ENDPOINT = os.environ.get("OPEN_AI_ENDPOINT")
    OPEN_AI_DEPLOYMENT_NAME = os.environ.get("OPEN_AI_DEPLOYMENT_NAME")
    if not OPEN_AI_ENDPOINT or not OPEN_AI_DEPLOYMENT_NAME:
        raise RuntimeError("OPEN_AI_ENDPOINT and OPEN_AI_DEPLOYMENT_NAME must be set.")
    
    # ENVIRONMENT VARIABLES - Content Safety Groundedness Detection
    CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
    CONTENT_SAFETY_KEY = os.environ.get("CONTENT_SAFETY_KEY")
    if not CONTENT_SAFETY_ENDPOINT or not CONTENT_SAFETY_KEY:
        raise RuntimeError("CONTENT_SAFETY_ENDPOINT and CONTENT_SAFETY_KEY must be set.")

    # 1. Use AzureAIAgent client to get the grounding source
    agent_client = AzureAIAgent.create_client(
        credential=DefaultAzureCredential(),
        endpoint=PROJECT_ENDPOINT,
    )
    agent_definition = await agent_client.agents.get_agent(agent_id=AGENT_ID)
    agent = AzureAIAgent(
        client=agent_client,
        definition=agent_definition,
    )
    thread = AzureAIAgentThread(client=agent_client)
    if not query:
        raise ValueError("A query must be provided for groundedness detection.")
    response = await agent.get_response(messages=query, thread=thread)

    # 2. Extract the grounding source (first text response)
    grounding_source = None
    for item in response.items:
        if getattr(item, "content_type", None) == "text" and getattr(item, "text", None):
            grounding_source = item.text
            logging.info(f"GROUNDEDNESS DETECTION - Grounding source: {grounding_source}")
            break
    if not grounding_source:
        logging.error(f"GROUNDEDNESS DETECTION - No grounding source returned by agent")
        return False

    # 3. Call the Azure Content Safety groundedness detection API with the user text and the grounding sources
    ground_url = f"{CONTENT_SAFETY_ENDPOINT.rstrip('/')}/contentsafety/text:detectGroundedness?api-version=2024-09-15-preview"
    ground_headers = {
        "Ocp-Apim-Subscription-Key": CONTENT_SAFETY_KEY,
        "Content-Type": "application/json",
    }
    # Prepare the payload for QnA task and Generic domain
    ground_payload = {
        "domain": "Generic",
        "task": "QnA",
        "qna": {
            "query": query
        },
        "text": text,
        "groundingSources": [
            grounding_source
        ],
        "correction": True,
        "llmResource": {
        "resourceType": "AzureOpenAI",
        "azureOpenAIEndpoint": OPEN_AI_ENDPOINT,
        "azureOpenAIDeploymentName": OPEN_AI_DEPLOYMENT_NAME
        }
    }
    # Make the HTTP request to the groundedness detection API
    async with aiohttp.ClientSession() as session:
        async with session.post(ground_url, headers=ground_headers, json=ground_payload, timeout=15) as resp:
            if resp.status != 200:
                logging.error(f"GROUNDEDNESS DETECTION - Groundedness API error: {resp.status} {await resp.text()}")
                return False
            data = await resp.json()
    
    # 4. Anylyze the reponse, if ungrounded Detected is true and ungrondedPercentage > threshold, return correction text else return text
    ungrounded_detected = data.get("ungroundedDetected", False)
    ungrounded_percentage = data.get("ungroundedPercentage", 0.0)
    corrected_text = data.get("correctedText", text)
    
    # If ungrounded is detected and exceeds threshold, use corrected text
    if ungrounded_detected and ungrounded_percentage >= threshold:
        final_text = corrected_text
    else:
        final_text = text
    
    return {
        "correctedText": final_text,
        "isUngrounded": ungrounded_detected,
        "ungroundednessScore": ungrounded_percentage
    }
#------------------------------------------------------