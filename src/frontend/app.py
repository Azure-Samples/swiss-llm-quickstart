import os
import re
import json
from typing import Any, Callable, Dict, Optional, Set, Tuple
import chainlit as cl
import semantic_kernel as sk
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.azure_ai_inference import (
    AzureAIInferenceChatCompletion,
    AzureAIInferenceChatPromptExecutionSettings,
)
from semantic_kernel.contents import ChatHistory
from app_tools import register_plugins, tools_system_message


# Environment variables for model configuration
MODEL_ENDPOINT = os.getenv("MODEL_ENDPOINT")
MODEL_ID = os.getenv("MODEL_ID")
if not MODEL_ENDPOINT:
    raise RuntimeError("Environment variable MODEL_ENDPOINT must be set.")
if not MODEL_ID:
    raise RuntimeError("Environment variable MODEL_ID must be set.")

CALL_TOOL_PATTERN = re.compile(r"CALL_TOOL\s*(\{.*\})", re.DOTALL)
MAX_TOOL_ITERATIONS = 3



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
    request_settings.top_p = 0.2
    request_settings.max_tokens = 1024  # Set a reasonable maximum length
    request_settings.frequency_penalty = 0.0  # No penalty for repeating tokens
    request_settings.presence_penalty = 0.0   # No penalty for topic repetition


    chat_history = ChatHistory()
    
    chat_history.add_system_message(tools_system_message())

    # Instantiate and add the Chainlit filter to the kernel
    # This will automatically capture function calls as Steps
    sk_filter = cl.SemanticKernelFilter(kernel=kernel)

    cl.user_session.set("sk_filter", sk_filter)
    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_history", chat_history)
    cl.user_session.set("tool_registry", tool_registry)
    cl.user_session.set("request_settings", request_settings)

@cl.on_message
async def on_message(message: cl.Message):
    kernel = cl.user_session.get("kernel")
    ai_service = cl.user_session.get("ai_service")
    chat_history = cl.user_session.get("chat_history")
    tool_registry = cl.user_session.get("tool_registry")
    request_settings = cl.user_session.get("request_settings")

    # Add user message to history
    chat_history.add_user_message(message.content)

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="")
    # Send the initial empty message to start the stream

    # First AI response
    full_response = ""
    
    async for msg in ai_service.get_streaming_chat_message_content(
        chat_history=chat_history,
        user_input=message.content,
        settings=request_settings,
        kernel=kernel,
    ):
        if msg.content:
            full_response += msg.content
    print("First AI response:", full_response)
    # Check if the response contains a tool call
    match = CALL_TOOL_PATTERN.search(full_response)
    # if no tool call, just stream the response
    if not match:
        # await answer.send()
        await answer.stream_token(full_response)
        # Add the full assistant response to history
        chat_history.add_assistant_message(full_response)
        cl.user_session.set("chat_history", chat_history)
        return
    # If there is a tool call, we start with an empty answer and process tool calls
    else:
        interactions = 0
        while match and interactions < MAX_TOOL_ITERATIONS:
            try:
                # Extract tool call details
                tool_call_json = match.group(1)
                tool_call = json.loads(tool_call_json)
                # Execture the tool call
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("arguments", {})

                if tool_name in tool_registry:
                    # Create a Chainlit Step for the tool execution
                    with cl.Step(name=tool_name, type="tool") as step:
                        #await answer.send()
                        # Execute the tool and get the result
                        tool_function = tool_registry[tool_name]
                        tool_result = tool_function(**tool_args)

                        # Update chat history with the tool result
                        tool_message = f"CALL_TOOL_ANSWER {tool_name}: {tool_result}"
                        chat_history.add_assistant_message(tool_message)
                        cl.user_session.set("chat_history", chat_history)
                        
                        # Get a new AI response based on the tool result
                        next_response = ""
                        async for msg in ai_service.get_streaming_chat_message_content(
                            chat_history=chat_history,
                            user_input="", # No new user input, just continuing from tool result
                            settings=request_settings,
                            kernel=kernel,
                        ):
                            if msg.content:
                                next_response += msg.content
                                print("Next AI response:", next_response)
                        if next_response:
                            await answer.stream_token(next_response)
                        # Update the full response for further tool call checks
                        full_response = next_response
                        match = CALL_TOOL_PATTERN.search(full_response)

                else:
                    # Handle tool not found with step visualization
                    with cl.Step(name=f"Tool Error: {tool_name} not found", type="tool_error") as error_step:
                        await answer.send()
                        error_step.input = json.dumps(tool_call, indent=2)
                        error_step.output = f"Error: Tool {tool_name} not found."
                    
                    # Exit if tool not found
                    await answer.stream_token(f"\nError: Tool {tool_name} not found.")
                    break

            except Exception as e:
                # Handle execution errors with step visualization
                error_input = tool_call_json if 'tool_call_json' in locals() else ""
                with cl.Step(name="Tool Execution Error", type="tool_error") as error_step:
                    await answer.send()
                    error_step.input = error_input
                    error_step.output = f"Error executing tool: {str(e)}"
                
                # Exit if tool not found
                await answer.send()
                await answer.stream_token(f"\nError executing tool: {str(e)}")
                break
            
            interactions += 1

        # Add the full assistant response to history
        chat_history.add_assistant_message(answer.content)
        cl.user_session.set("chat_history", chat_history)
