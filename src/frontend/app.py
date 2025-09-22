import os
from textwrap import dedent
from typing import Any, Callable, Dict
import chainlit as cl
from openai import AsyncOpenAI
import semantic_kernel as sk
from semantic_kernel.connectors.ai.azure_ai_inference import (
    AzureAIInferenceChatCompletion,
    AzureAIInferenceChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIPromptExecutionSettings, OpenAIChatCompletion
)
from semantic_kernel.contents import ChatHistory
from app_tools import register_plugins, router_system_message, execute_tool_call


import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment variables for model configuration
MODEL_ENDPOINT = os.environ["MODEL_ENDPOINT"]
MODEL_ID = os.environ["MODEL_ID"]
if not MODEL_ENDPOINT:
    raise RuntimeError("Environment variable MODEL_ENDPOINT must be set.")
if not MODEL_ID:
    raise RuntimeError("Environment variable MODEL_ID must be set.")

# System message for the assistant agent
def assistant_system_message() -> str:
    return (
        "You are a helpful assistant that answer user questions politely and concisely.\n"
        "Never call a tool directly, only use the information provided in the message.\n" \
        "Never hallucinate, if you don't know the answer or the tool does not provide one just say you don't know.\n"
    )

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
    request_settings = OpenAIPromptExecutionSettings(
        temperature=0.2,
    )

    kernel.add_service(ai_service)
    tool_registry = register_plugins(kernel)

    # ROUTER AGENT: Initialize chat hystory and system prompt
    router_chat_history = ChatHistory()
    router_chat_history.add_system_message(router_system_message())

    # ASSISTANT AGENT: Initialize chat history and system prompt
    chat_history = ChatHistory()
    chat_history.add_system_message(assistant_system_message())

    #cl.user_session.set("sk_filter", sk_filter)
    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_history", chat_history)
    cl.user_session.set("router_chat_history", router_chat_history)
    cl.user_session.set("tool_registry", tool_registry)
    cl.user_session.set("request_settings", request_settings)

# Chainlit Message Event
@cl.on_message
async def on_message(message: cl.Message):
    kernel = cl.user_session.get("kernel")
    ai_service: OpenAIChatCompletion = cl.user_session.get("ai_service") # type: ignore
    chat_history: ChatHistory = cl.user_session.get("chat_history") # type: ignore #
    tool_registry: Dict[str, Callable[..., Any]] = cl.user_session.get("tool_registry")  # type: ignore
    request_settings: OpenAIPromptExecutionSettings = cl.user_session.get("request_settings") # type: ignore
    router_chat_history: ChatHistory = cl.user_session.get("router_chat_history") # type: ignore

    # Create a Chainlit message for the response stream
    thinking_answer = cl.Message(content="Thinking...")
    await thinking_answer.send()


    # STEP1: Use the Router agent to determine if we need to call a tool
    router_chat_history.add_user_message(message.content)
    router_response = ""
    async for msg in ai_service.get_streaming_chat_message_content(
        chat_history=router_chat_history,
        settings=request_settings,
        kernel=kernel,
    ):
        if msg and msg.content:
            router_response += msg.content
    print("Router response:", router_response)
    answer = cl.Message(content="")
    await answer.send()
    # STEP 2A: if the router decides that no tool is needed (ANSWER_AI), 
    # we forward the original user message to the assistant agent
    if "ANSWER_AI" in router_response:
        print("Router decided to ANSWER_AI")
        full_response = ""
        async for msg in ai_service.get_streaming_chat_message_content(
            chat_history=chat_history,
            settings=request_settings,
            kernel=kernel,
        ):
            if msg and msg.content:
                full_response += msg.content
        print("Assistant response:", full_response)
        await answer.stream_token(full_response)
        # Add the full assistant response to history
        chat_history.add_assistant_message(full_response)
        return
    # STEP 2B: If the router decides that a tool is needed (CALL_TOOL), 
    # we forward the tool call to the assistant agent
    else:
        print("Router decided to CALL_TOOL")
        tool_response = execute_tool_call(router_response, tool_registry)
        # Updated the answer message with the tool name used
        answer.author = "Used Tool: " + tool_response[1]
        await answer.update()
        # Take the tool call result and send it to the Assistant agent to prepare the final answer
        response_with_tool = ""

        chat_history.add_user_message(dedent(f"""
            Information provided by the `{tool_response[1]}` tool:
            ```
            {tool_response[0]}
            ```
            Answer the user's question by using ONLY the information provided by the tool above DO NOT use multiple tool answers.
            ```
            {message.content}
            ```
            
        """))
        print("--- Chat history:", chat_history)
        async for msg in ai_service.get_streaming_chat_message_content(
            chat_history=chat_history,
            settings=request_settings,
            kernel=kernel,
            ):
                if msg and msg.content:
                    await thinking_answer.remove()
                    response_with_tool += msg.content
                    await answer.stream_token(msg.content)
        chat_history.add_assistant_message(response_with_tool)
