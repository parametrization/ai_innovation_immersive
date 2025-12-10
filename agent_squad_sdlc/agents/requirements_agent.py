"""
Requirements Agent

Handles intake and clarification of project requirements from GitHub issues.
Responsible for:
- Parsing incoming GitHub issues for feature requests
- Asking clarifying questions via issue comments
- Extracting acceptance criteria
- Identifying dependencies and constraints
"""

from typing import Any, Optional

from agent_squad.agents import AnthropicAgent

from agent_squad_sdlc.agents.base import create_anthropic_agent, format_tool_schema
from agent_squad_sdlc.config import Settings
from agent_squad_sdlc.prompts.requirements_prompt import REQUIREMENTS_AGENT_PROMPT
from agent_squad_sdlc.tools.github_tools import GitHubTools


def get_requirements_tools() -> list[dict[str, Any]]:
    """Get tool definitions for the Requirements Agent."""
    return [
        format_tool_schema(
            name="get_issue",
            description="Retrieve details of a GitHub issue by number",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number to retrieve",
                },
            },
            required=["issue_number"],
        ),
        format_tool_schema(
            name="get_issue_comments",
            description="Get all comments on a GitHub issue",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number to get comments for",
                },
            },
            required=["issue_number"],
        ),
        format_tool_schema(
            name="add_issue_comment",
            description="Add a comment to a GitHub issue",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number to comment on",
                },
                "body": {
                    "type": "string",
                    "description": "The comment text (supports markdown)",
                },
            },
            required=["issue_number", "body"],
        ),
        format_tool_schema(
            name="search_issues",
            description="Search for related issues in the repository",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by issue state",
                },
            },
            required=["query"],
        ),
        format_tool_schema(
            name="add_labels",
            description="Add labels to a GitHub issue",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number to label",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of label names to add",
                },
            },
            required=["issue_number", "labels"],
        ),
    ]


async def requirements_tool_handler(
    response: Any,
    conversation: list[dict[str, Any]],
    github_tools: GitHubTools,
) -> Any:
    """
    Handle tool calls from the Requirements Agent.

    Args:
        response: The tool call response from the agent
        conversation: Current conversation history
        github_tools: GitHub tools instance

    Returns:
        Tool execution result
    """
    tool_name = response.name
    tool_input = response.input

    handlers = {
        "get_issue": lambda: github_tools.get_issue(tool_input["issue_number"]),
        "get_issue_comments": lambda: github_tools.get_issue_comments(
            tool_input["issue_number"]
        ),
        "add_issue_comment": lambda: github_tools.add_issue_comment(
            tool_input["issue_number"],
            tool_input["body"],
        ),
        "search_issues": lambda: github_tools.search_issues(
            tool_input["query"],
            tool_input.get("state", "open"),
        ),
        "add_labels": lambda: github_tools.add_labels(
            tool_input["issue_number"],
            tool_input["labels"],
        ),
    }

    handler = handlers.get(tool_name)
    if handler:
        return await handler()

    return {"error": f"Unknown tool: {tool_name}"}


def create_requirements_agent(
    github_tools: GitHubTools,
    settings: Optional[Settings] = None,
) -> AnthropicAgent:
    """
    Create the Requirements Agent.

    Args:
        github_tools: GitHub tools instance for API operations
        settings: Optional settings override

    Returns:
        Configured Requirements Agent
    """

    async def tool_handler(response: Any, conversation: list[dict[str, Any]]) -> Any:
        return await requirements_tool_handler(response, conversation, github_tools)

    return create_anthropic_agent(
        name="RequirementsAgent",
        description=(
            "Handles requirements intake and clarification from GitHub issues. "
            "Specializes in parsing feature requests, asking clarifying questions, "
            "extracting acceptance criteria, and identifying dependencies. "
            "Use this agent when: a new issue is created, requirements need clarification, "
            "or acceptance criteria need to be documented."
        ),
        system_prompt=REQUIREMENTS_AGENT_PROMPT,
        tools=get_requirements_tools(),
        tool_handler=tool_handler,
        settings=settings,
    )
