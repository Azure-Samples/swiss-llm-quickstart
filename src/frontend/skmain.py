import asyncio

from semantic_kernel import Kernel
from semantic_kernel.utils.logging import setup_logging
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIPromptExecutionSettings, OpenAIChatCompletion
)
from openai import AsyncOpenAI
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

import os
import logging

from typing import Annotated
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import (
    AzureAIAgent,
    AzureAIAgentThread,
)

MODEL_ENDPOINT = os.environ["MODEL_ENDPOINT"]
MODEL_ID = os.environ["MODEL_ID"]
if not MODEL_ENDPOINT:
    raise RuntimeError("Environment variable MODEL_ENDPOINT must be set.")
if not MODEL_ID:
    raise RuntimeError("Environment variable MODEL_ID must be set.")

PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT")
if not PROJECT_ENDPOINT:
    raise RuntimeError("Environment variable PROJECT_ENDPOINT must be set.")


agent_client = AzureAIAgent.create_client(
    credential=DefaultAzureCredential(),
    endpoint=os.environ["PROJECT_ENDPOINT"],
)

class BingPlugin:
    @kernel_function(
        name="query_bing",
        description="Queries bing for the given query and returns the results.",
    )
    async def query_bing(
        self,
        query: Annotated[str, "The search query"],
    ) -> str:
        agent_definition = await agent_client.agents.get_agent(agent_id="asst_ij7O8Ivql5WcoTbcNPdtd5i3")
        agent = AzureAIAgent(
            client=agent_client,
            definition=agent_definition,
            # plugins=[MenuPlugin()],  # add the sample plugin to the agent
        )
        thread: AzureAIAgentThread = AzureAIAgentThread(client=agent_client)
        response = await agent.get_response(messages=query, thread=thread)
        return response.content.content
    
async def main():
    # Initialize the kernel
    kernel = Kernel()

    chat_completion = OpenAIChatCompletion(
        async_client=AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "vLLM"),  # or None if vLLM ignores it
            base_url=MODEL_ENDPOINT),
        ai_model_id=MODEL_ID,
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