import os
import chainlit as cl
import semantic_kernel as sk
from semantic_kernel.connectors.ai.azure_ai_inference import (
    AzureAIInferenceChatCompletion,
    AzureAIInferenceChatPromptExecutionSettings,
)
from semantic_kernel.contents import ChatHistory
from app_tools import register_plugins, router_system_message, execute_tool_call


# Environment variables for model configuration
MODEL_ENDPOINT = os.getenv("MODEL_ENDPOINT")
MODEL_ID = os.getenv("MODEL_ID")
if not MODEL_ENDPOINT:
    raise RuntimeError("Environment variable MODEL_ENDPOINT must be set.")
if not MODEL_ID:
    raise RuntimeError("Environment variable MODEL_ID must be set.")

# System message for the assistant agent
def assistant_system_message() -> str:
    return (
        "You are a helpful assistant that answer user questions politely and concisely.\n"
        "if you have in the user message a reference TOOL ANSWER, you must use that information to create a friendly answer in natural language.\n"
        " Never call a tool directly, only use the information provided in the TOOL ANSWER.\n" \
        " Never use the tool name in your answer, or the information that the answer is coming from a tool.\n"
    )

# Chainlit Chat Starter Setup
@cl.set_starters
async def set_starters():
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

    ai_service = AzureAIInferenceChatCompletion(
        api_key="vLLM",  # vLLM usually ignores this
        endpoint=MODEL_ENDPOINT,
        ai_model_id=MODEL_ID,
    )
    
    kernel.add_service(ai_service)
    tool_registry = register_plugins(kernel)
    request_settings = AzureAIInferenceChatPromptExecutionSettings()
    request_settings.temperature = 0.2

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
    ai_service = cl.user_session.get("ai_service")
    chat_history = cl.user_session.get("chat_history")
    tool_registry = cl.user_session.get("tool_registry")
    request_settings = cl.user_session.get("request_settings")
    router_chat_history = cl.user_session.get("router_chat_history")

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="Thinking...")
    answer.send()

    # STEP1: Use the Router agent to determine if we need to call a tool
    router_chat_history.add_user_message(message.content)
    router_response = ""
    async for msg in ai_service.get_streaming_chat_message_content(
        chat_history=router_chat_history,
        user_input=message.content,
        settings=request_settings,
        kernel=kernel,
    ):
        if msg.content:
            router_response += msg.content
    print("Router response:", router_response)
    
    # STEP 2A: if the router decides that no tool is needed (ANSWER_AI), 
    # we forward the original user message to the assistant agent
    if "ANSWER_AI" in router_response:
        print("Router decided to ANSWER_AI")
        full_response = ""
        async for msg in ai_service.get_streaming_chat_message_content(
            chat_history=chat_history,
            user_input=message.content,
            settings=request_settings,
            kernel=kernel,
        ):
            if msg.content:
                full_response += msg.content
        print("Assistant response:", full_response)
        await answer.stream_token(full_response).update()
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
        async for msg in ai_service.get_streaming_chat_message_content(
            chat_history=chat_history,
            user_input=message.content + "\n" + tool_response[0],
            settings=request_settings,
            kernel=kernel,
            ):
                if msg.content:
                    response_with_tool += msg.content
        print("Assistant response after tool call:", response_with_tool)
        await answer.stream_token(response_with_tool).update()
        chat_history.add_assistant_message(response_with_tool)
        return