"""
Base agent utilities and factory functions.

Provides common functionality for creating and configuring SDLC agents.
"""

from typing import Any, Callable, Optional

from agent_squad.agents import AnthropicAgent, AnthropicAgentOptions

from agent_squad_sdlc.config import Settings, get_settings


def create_anthropic_agent(
    name: str,
    description: str,
    system_prompt: str,
    tools: Optional[list[dict[str, Any]]] = None,
    tool_handler: Optional[Callable] = None,
    settings: Optional[Settings] = None,
    streaming: bool = True,
    save_chat: bool = True,
) -> AnthropicAgent:
    """
    Factory function to create an AnthropicAgent with standard configuration.

    Args:
        name: Agent name identifier
        description: Agent description for classifier routing
        system_prompt: Custom system prompt for the agent
        tools: Optional list of tool definitions
        tool_handler: Optional handler for tool calls
        settings: Optional settings override
        streaming: Enable streaming responses
        save_chat: Save conversation history

    Returns:
        Configured AnthropicAgent instance
    """
    if settings is None:
        settings = get_settings()

    options = AnthropicAgentOptions(
        name=name,
        description=description,
        api_key=settings.anthropic_api_key.get_secret_value(),
        model_id=settings.claude_model_id,
        streaming=streaming,
        save_chat=save_chat,
        custom_system_prompt={
            "template": system_prompt,
            "variables": {
                "REPO_OWNER": settings.github_owner,
                "REPO_NAME": settings.github_repo,
                "REPO_FULL_NAME": settings.github_repo_full_name,
            },
        },
        inference_config={
            "temperature": 0.7,
            "maxTokens": 4096,
        },
    )

    # Add tools if provided
    if tools:
        options.tool_config = {
            "tool": tools,
            "toolMaxRecursions": 10,
            "useToolHandler": tool_handler,
        }

    return AnthropicAgent(options)


def format_tool_schema(
    name: str,
    description: str,
    parameters: dict[str, Any],
    required: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Format a tool definition for Agent Squad.

    Args:
        name: Tool name
        description: Tool description
        parameters: Parameter definitions
        required: List of required parameter names

    Returns:
        Formatted tool schema dict
    """
    schema = {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": parameters,
        },
    }

    if required:
        schema["input_schema"]["required"] = required

    return schema
