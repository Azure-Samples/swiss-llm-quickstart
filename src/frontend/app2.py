import os
import logging
from textwrap import dedent
from typing import Annotated, List, Optional

import chainlit as cl

from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI

from app_content_safety import is_prompt_attack, is_harmful_content, is_grounded

from agent_framework.azure import AzureAIAgentClient
from agent_framework.openai import OpenAIChatClient
from agent_framework import ChatAgent, ai_function

#------------------------------------------------------
# ENVIRONMENT VARIABLES AND VALIDATIONS
#------------------------------------------------------

# Environment variables for model configuration
MODEL_ENDPOINT = os.environ["MODEL_ENDPOINT"]
MODEL_ID = os.environ["MODEL_ID"]
# Environment variables for Bing Search Plugin
PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
AGENT_ID = os.environ["AGENT_ID"]

if not MODEL_ENDPOINT:
    raise RuntimeError("Environment variable MODEL_ENDPOINT must be set.")
if not MODEL_ID:
    raise RuntimeError("Environment variable MODEL_ID must be set.")
if not PROJECT_ENDPOINT:
    raise RuntimeError("Environment variable PROJECT_ENDPOINT must be set.")
if not AGENT_ID:
    raise RuntimeError("Environment variable AGENT_ID must be set.")

#------------------------------------------------------
# LOGGING
#------------------------------------------------------

# Setup logging
logging.basicConfig(
    format="[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("agent_framework").setLevel(logging.DEBUG)
logging.getLogger("openai").setLevel(logging.DEBUG)


#------------------------------------------------------
# TOOLS DEFINITIONS
#------------------------------------------------------

# Setup Azure AI Agent client for search functionality
search_agent_client = AzureAIAgentClient(
    async_credential=DefaultAzureCredential(),
    agent_id=AGENT_ID,
    project_endpoint=PROJECT_ENDPOINT,
)

# TOOL: Bing Search Plugin
@ai_function(name="search_engine", description="Find current information based on the user request and returns the results.")
async def search_engine(query: Annotated[str, "The search query"]) -> dict:
    search_agent = ChatAgent(client=search_agent_client)
    thread = search_agent.get_new_thread()
    response = await search_agent.run(query, thread=thread)
    text = [item.text for item in response.items if item.content_type == 'text']
    citations = [{ "url": item.url, "title": item.title } for item in response.items if item.content_type == 'annotation']
    print("DATA:", response.dict())
    return {"text": text, "citations": citations}

#------------------------------------------------------
# APPLICATION LOGIC
#------------------------------------------------------

# System Message for the AI
SYSTEM_MESSAGE = dedent("""
    You are a polite, concise assistant who always replies in the same language as the user.        
    - You **MUST ALWAYS** use the tools available to answer the user's questions.
    - NEVER rely on prior training memories, NEVER fabricate or guess, you ALWAYS, at every iteration, MUST retrieve current information through the tools instead.
    - If a user request lacks facts or clarity, ask the user for the needed clarification before proceeding.
""")


# Chainlit Starter Messages        
@cl.set_starters
async def set_starters(user: Optional["cl.User"] = None, project: Optional[str] = None) -> List[cl.Starter]:
    return [
        cl.Starter(
            label="Morning routine ideation",
            message="Can you help me create a personalized morning routine that would help increase my productivity throughout the day? Start by asking me about my current habits and what activities energize me in the morning.",
            icon="/public/idea.svg",
        ),
        cl.Starter(
            label="Explain Gravity at high school",
            message="Give a simple explanation of what gravity is for a high school level physics course with a few typical formulas. Use lots of emojis and do it in French, Swiss German, Italian and Romansh.",
            icon="/public/learn.svg",
        ),
        cl.Starter(
            label="Swiss Bundesrat Members",
            message="Who are the current members of the Swiss Bundesrat?",
            icon="/public/swiss-flag.svg",
        ),
        cl.Starter(
            label="Text inviting friend to wedding",
            message="Write a text asking a friend to be my plus-one at a wedding next month. I want to keep it super short and casual, and offer an out.",
            icon="/public/write.svg",
        )
    ]

# Chainlit Chat Start Event
@cl.on_chat_start
async def on_chat_start():
    # Setup Agent Framework OpenAI Chat Client and Plugins
    apertus_client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "vLLM"),  # or None if vLLM ignores it
        base_url=MODEL_ENDPOINT,   
    )
    ai_service = OpenAIChatClient(
        async_client=apertus_client,
        model_id=MODEL_ID,
    )
    apertus_agent = ai_service.create_agent(
        name="ApertusAI",
        instructions=SYSTEM_MESSAGE,
        tools=[search_engine],
        temperature=0.2,
        tool_choice="auto",
    )

    # Initialize chat history
    chat_history = apertus_agent.get_new_thread()

    # Store information in user session
    cl.user_session.set("apertus_agent", apertus_agent)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_history", chat_history)


# Chainlit Message Event
@cl.on_message
async def on_message(message: cl.Message):
    # Retrieve information from user session
    apertus_agent = cl.user_session.get("apertus_agent")
    chat_history = cl.user_session.get("chat_history") # type: ignore #

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="Thinking...")
    await answer.send()

    # Responsible AI Check - Prompt Shield
    prompt_attack = await is_prompt_attack(message.content)
    if prompt_attack:
        logging.warning(f"Prompt attack detected and filtered: {message.content}")
        answer.content = "Sorry, your prompt was filtered by the Responsible AI Service - Prompt Shield. Please rephrase your prompt and try again."
        await answer.update()
        return
    
    # Responsible AI Check - Harmful Content
    harm_result = await is_harmful_content(message.content)
    if harm_result.get("category") is not None and harm_result.get("severity", 0) > 2:
        logging.warning(f"Harmful content detected and filtered: {message.content} | Category: {harm_result.get('category')} | Severity: {harm_result.get('severity')}")
        answer.content = "Sorry, your prompt was filtered by the Responsible AI Service - Harmful Content. Please rephrase your prompt and try again."
        await answer.update()
        return
    
    # Get response from the Agent
    msg = await apertus_agent.run(message.content, thread=chat_history)

    # TODO: Grounding Check

    if msg:
        answer.content = msg.content
        await answer.update()
    else:
        answer.content = "I'm sorry, but I couldn't find a response."
        await answer.update()