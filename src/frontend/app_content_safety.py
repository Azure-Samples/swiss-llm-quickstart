import os
import logging
import aiohttp
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentThread

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
                logging.error(f"Prompt Shield - Content Safety API error: {resp.status} {await resp.text()}")
                return False
            # Parse the JSON response
            data = await resp.json()

    # Return the boolean promptAttackResult field directly (True = attack detected, False = safe)
    return bool(data.get("userPromptAnalysis").get("attackDetected", False))

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
                logging.error(f"Harmful Content - Content Safety API error: {resp.status} {await resp.text()}")
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


async def is_grounded(text: str, domain: str = "Generic", query: str = None) -> bool:
    """
    Calls the Agent in AI Foundry (PROJECT_ENDPOINT, AGENT_ID) to get the grounding source for the query,
    then checks if the provided text is grounded in that source using Azure AI Content Safety Groundedness Detection.
    Always uses QnA task and NonReasoning mode for speed.
    Returns True if grounded, False otherwise.
    """
    PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT")
    AGENT_ID = os.environ.get("AGENT_ID")
    if not PROJECT_ENDPOINT or not AGENT_ID:
        raise RuntimeError("PROJECT_ENDPOINT and AGENT_ID must be set.")
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
    # Extract the grounding source (first text response)
    grounding_source = None
    for item in response.items:
        if getattr(item, "content_type", None) == "text" and getattr(item, "text", None):
            grounding_source = item.text
            break
    if not grounding_source:
        logging.error(f"No grounding source returned by agent: {response.dict() if hasattr(response, 'dict') else response}")
        return False

    # 2. Call the Azure Content Safety groundedness detection API with the user text and the grounding source
    ground_url = f"{CONTENT_SAFETY_ENDPOINT.rstrip('/')}/contentsafety/text:detectGroundedness?api-version=2024-09-15-preview"
    ground_headers = {
        "Ocp-Apim-Subscription-Key": CONTENT_SAFETY_KEY,
        "Content-Type": "application/json",
    }
    # The payload for Summarization task does NOT use a 'summarization' field, only the required fields
    ground_payload = {
        "domain": domain,
        "task": "Summarization",
        "text": text,
        "groundingSources": [grounding_source],
        "reasoning": False
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(ground_url, headers=ground_headers, json=ground_payload, timeout=15) as resp:
            if resp.status != 200:
                logging.error(f"Groundedness API error: {resp.status} {await resp.text()}")
                return False
            data = await resp.json()

    # The API returns 'ungroundedDetected': True if ungrounded, False if grounded
    return not data.get("ungroundedDetected", False)