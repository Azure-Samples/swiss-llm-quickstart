"""Semantic Kernel plugin wrappers and registry helpers for Chainlit tools.

This module keeps tool implementations separate from the chat application so
they can be maintained and extended independently. Each plugin is registered
with Semantic Kernel and exposed through a simple registry map that the app can
use when it needs to manually dispatch tool calls.
"""
import os
import re
import json
from typing import Any, Callable, Dict
import semantic_kernel as sk
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.azure_ai_inference import (
    AzureAIInferenceChatCompletion,
    AzureAIInferenceChatPromptExecutionSettings,
)


# Environment variables for model configuration
MODEL_ENDPOINT = os.getenv("MODEL_ENDPOINT")
MODEL_ID = os.getenv("MODEL_ID")
if not MODEL_ENDPOINT:
    raise RuntimeError("Environment variable MODEL_ENDPOINT must be set.")
if not MODEL_ID:
    raise RuntimeError("Environment variable MODEL_ID must be set.")

CALL_TOOL_PATTERN = re.compile(r"CALL_TOOL\s*(\{.*\})", re.DOTALL)

class WeatherPlugin:
    """Simple demo plugin that returns canned weather summaries."""

    @kernel_function(name="get_weather", description="Gets the weather for a city")
    def get_weather(self, city: str) -> str:
        """Return a fake weather report for a limited set of cities."""
        if "paris" in city.lower():
            return f"The weather in {city} is 20°C and sunny."
        if "london" in city.lower():
            return f"The weather in {city} is 15°C and cloudy."
        return f"Sorry, I don't have the weather for {city}."


class MathPlugin:
    """Example math plugin used to demonstrate multiple tools."""

    @kernel_function(name="sum_numbers", description="Adds two numbers together")
    def sum_numbers(self, a: str, b: str) -> str:
        """Return the arithmetic sum of two numbers."""
        result = float(a) + float(b)
        return str(result)


def register_plugins(kernel: sk.Kernel) -> Dict[str, Callable[..., Any]]:
    """Attach plugins to the kernel and return the tool lookup table."""
    weather_plugin = WeatherPlugin()
    math_plugin = MathPlugin()

    kernel.add_plugin(weather_plugin, plugin_name="Weather")
    kernel.add_plugin(math_plugin, plugin_name="Math")

    tools: Dict[str, Callable[..., Any]] = {
        "Weather.get_weather": weather_plugin.get_weather,
        "Math.sum_numbers": math_plugin.sum_numbers,
    }
    return tools

def router_system_message() -> str:
    return (
        "You are a router that decides if the user message should be handled by the AI or by a tool.\n"
        "These rules apply on every turn, even after multiple tool calls:\n"
        "- You have ONE single task: decide if the user question can be answered by the AI directly or if requires a tool to answer\n"
        "- If the user question can be answered by the AI directly, answer exactly with on a single line, with no extra commentary: ANSWER_AI\n"
        "- If the user question requires a tool to answer, answer with exactly one line:\n"
        "  CALL_TOOL {\"name\": \"<Plugin.Function>\", \"arguments\": {...}}\n"
        "  The JSON must be valid, on a single line, and contain no extra commentary.\n"
        "You have access to a list of structured tools that you can use to answer user questions.\n"
        "- Available tools are only the following:\n"
        "  • Weather.get_weather(city: str) - Gets the weather for a city\n"
        "  • Math.sum_numbers(a: float, b: float) - Add two numbers\n"
    )

def execute_tool_call(message: str, tool_registry: Dict[str, Callable[..., Any]]) -> str:
    """Execute a tool call based on the provided message."""
    match = CALL_TOOL_PATTERN.search(message)
    tool_call_json = match.group(1)
    tool_call = json.loads(tool_call_json)
    # Execture the tool call
    tool_name = tool_call.get("name")
    tool_args = tool_call.get("arguments", {})
    if tool_name in tool_registry:
        tool_function = tool_registry[tool_name]
        tool_result = tool_function(**tool_args)
        print(f"Tool response -  {tool_name}:{tool_result}")
        return (f"TOOL ANSWER: {tool_name} {tool_result}", {tool_name})
    else:
        return "CALL_TOOL_ERROR: Tool not found."
