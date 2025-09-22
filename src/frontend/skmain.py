import asyncio

from semantic_kernel import Kernel
from semantic_kernel.utils.logging import setup_logging
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions.kernel_arguments import KernelArguments

from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIPromptExecutionSettings, OpenAIChatCompletion
)
from openai import AsyncOpenAI

import os
import logging

from typing import Annotated
from semantic_kernel.functions import kernel_function

class BingPlugin:
    @kernel_function(
        name="query_bing",
        description="Queries bing for the given query and returns the results.",
    )
    def query_bing(
        self,
        query: Annotated[str, "The search query"],
    ) -> str:
        return f"Results for '{query}' from Bing"

async def main():
    # Initialize the kernel
    kernel = Kernel()


    chat_completion = OpenAIChatCompletion(
        async_client=AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "vLLM"),  # or None if vLLM ignores it
            base_url="http://localhost:18000/v1"),
        ai_model_id="swiss-ai/Apertus-8B-Instruct-2509",
    )
    kernel.add_service(chat_completion)

    # Set the logging level for  semantic_kernel.kernel to DEBUG.
    setup_logging()
    logging.getLogger("kernel").setLevel(logging.DEBUG)
    logging.getLogger("openai").setLevel(logging.DEBUG)    # OpenAI SDK logs

    # Add a plugin (the BingPlugin class is defined below)
    kernel.add_plugin(
        BingPlugin(),
        plugin_name="Bing",
    )

    # Enable planning
    execution_settings = OpenAIPromptExecutionSettings()
    execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    # Create a history of the conversation
    history = ChatHistory()

    # Initiate a back-and-forth chat
    userInput = None
    while True:
        # Collect user input
        userInput = input("User > ")

        # Terminate the loop if the user says "exit"
        if userInput == "exit":
            break

        # Add user input to the history
        history.add_user_message(userInput)

        # Get the response from the AI
        result = await chat_completion.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        # Print the results
        print("Assistant > " + str(result))

        # Add the message from the agent to the chat history
        history.add_message(result)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())