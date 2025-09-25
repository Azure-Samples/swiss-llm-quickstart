import logging
import os
from textwrap import dedent
from typing import Annotated, List, Optional

import chainlit as cl
import semantic_kernel as sk
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI
from semantic_kernel.agents import (
    AzureAIAgent,
    AzureAIAgentThread,
)
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIPromptExecutionSettings,
)
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import kernel_function

logging.basicConfig(
    format="[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("kernel").setLevel(logging.DEBUG)
logging.getLogger("openai").setLevel(logging.DEBUG)


# Environment variables for model configuration

MODEL_ENDPOINT = os.environ["MODEL_ENDPOINT"]
MODEL_ID = os.environ["MODEL_ID"]
AGENT_ID = os.environ["AGENT_ID"]
if not MODEL_ENDPOINT:
    raise RuntimeError("Environment variable MODEL_ENDPOINT must be set.")
if not MODEL_ID:
    raise RuntimeError("Environment variable MODEL_ID must be set.")
if not AGENT_ID:
    raise RuntimeError("Environment variable AGENT_ID must be set.")

agent_client = AzureAIAgent.create_client(
    credential=DefaultAzureCredential(),
    endpoint=os.environ["PROJECT_ENDPOINT"],
)

class BingPlugin:
    @kernel_function(
        name="query_bing",
        description="Uses a search engine to find information with the query and returns the results.",
    )
    async def query_bing(
        self,
        query: Annotated[str, "The search query"],
    ) -> dict:
        agent_definition = await agent_client.agents.get_agent(agent_id=AGENT_ID)
        agent = AzureAIAgent(
            client=agent_client,
            definition=agent_definition,
            # plugins=[MenuPlugin()],  # add the sample plugin to the agent
        )
        thread: AzureAIAgentThread = AzureAIAgentThread(client=agent_client)
        response = await agent.get_response(messages=query, thread=thread)
        text = [item.text for item in response.items if item.content_type == 'text']
        citations = [{ "url": item.url, "title": item.title } for item in response.items if item.content_type == 'annotation']
        print("DATA:", response.dict())
        return {"text": text, "citations": citations}

SYSTEM_MESSAGE = dedent("""
    You are a helpful assistant that answer user questions politely and concisely.            
    Use the tools available to you to find information but do NOT answer questions 
    based on your training data.
    If you are unsure and the user question is not factual, you can ask the user
    for clarification.
    Always use the search tool when you need to find information about current events or
    anything that is not general knowledge.
    Never make up answers that are not based on the search results.
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
            message="Who are the members of the Swiss Bundesrat?",
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
    # Setup Semantic Kernel
    kernel = sk.Kernel()
    
    openai_client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "vLLM"),  # or None if vLLM ignores it
        base_url=MODEL_ENDPOINT,
    )
    ai_service = OpenAIChatCompletion(
        async_client=openai_client,
        ai_model_id=MODEL_ID,
    )
    execution_settings = OpenAIPromptExecutionSettings(
        temperature=0.2,
    )
    execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    kernel.add_service(ai_service)
    kernel.add_plugin(
        BingPlugin(),
        plugin_name="Bing",
    )

    # ASSISTANT AGENT: Initialize chat history and system prompt
    chat_history = ChatHistory()
    chat_history.add_system_message(SYSTEM_MESSAGE)

    #cl.user_session.set("sk_filter", sk_filter)
    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_history", chat_history)
    cl.user_session.set("execution_settings", execution_settings)


# Chainlit Message Event
@cl.on_message
async def on_message(message: cl.Message):
    kernel = cl.user_session.get("kernel")
    ai_service: OpenAIChatCompletion = cl.user_session.get("ai_service") # type: ignore
    chat_history: ChatHistory = cl.user_session.get("chat_history") # type: ignore #
    execution_settings: OpenAIPromptExecutionSettings = cl.user_session.get("execution_settings") # type: ignore

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="Thinking...")
    await answer.send()

    chat_history.add_user_message(message.content)
    await answer.send()
    msg = await ai_service.get_chat_message_content(
        chat_history=chat_history,
        settings=execution_settings,
        kernel=kernel,
        )
    if msg:
        answer.content = msg.content
        await answer.update()
        chat_history.add_assistant_message(msg.content)
    else:
        answer.content = "I'm sorry, but I couldn't find a response."
        await answer.update()
        chat_history.add_assistant_message("I'm sorry, but I couldn't find a response.")
