import os
import chainlit as cl
import semantic_kernel as sk
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion , AzureAIInferenceChatPromptExecutionSettings
from semantic_kernel.functions import kernel_function
from semantic_kernel.contents import ChatHistory


request_settings = AzureAIInferenceChatPromptExecutionSettings(
    function_choice_behavior=FunctionChoiceBehavior.Auto(filters={"excluded_plugins": ["ChatBot"]})
)

# Example Native Plugin (Tool)
class WeatherPlugin:
    @kernel_function(name="get_weather", description="Gets the weather for a city")
    def get_weather(self, city: str) -> str:
        """Retrieves the weather for a given city."""
        if "paris" in city.lower():
            return f"The weather in {city} is 20°C and sunny."
        elif "london" in city.lower():
            return f"The weather in {city} is 15°C and cloudy."
        else:
            return f"Sorry, I don't have the weather for {city}."

@cl.on_chat_start
async def on_chat_start():
    # Setup Semantic Kernel
    kernel = sk.Kernel()

    ai_service = AzureAIInferenceChatCompletion(
        api_key="vLLM",  # vLLM usually ignores this
        endpoint="https://ca-apertus--0000001.proudbay-4a0bd09b.swedencentral.azurecontainerapps.io/v1",  # vLLM OpenAI API endpoint
        ai_model_id="swiss-ai/Apertus-8B-Instruct-2509",
    )
    
    kernel.add_service(ai_service)

    # Import the WeatherPlugin
    #kernel.add_plugin(WeatherPlugin(), plugin_name="Weather")
    
    # Instantiate and add the Chainlit filter to the kernel
    # This will automatically capture function calls as Steps
    sk_filter = cl.SemanticKernelFilter(kernel=kernel)

    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_history", ChatHistory())

@cl.on_message
async def on_message(message: cl.Message):
    kernel = cl.user_session.get("kernel") # type: sk.Kernel
    ai_service = cl.user_session.get("ai_service") # type: OpenAIChatCompletion
    chat_history = cl.user_session.get("chat_history") # type: ChatHistory

    # Add user message to history
    chat_history.add_user_message(message.content)

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="")

    async for msg in ai_service.get_streaming_chat_message_content(
        chat_history=chat_history,
        user_input=message.content,
        settings=request_settings,
        kernel=kernel,
    ):
        if msg.content:
            await answer.stream_token(msg.content)

    # Add the full assistant response to history
    chat_history.add_assistant_message(answer.content)

    # Send the final message
    await answer.send()