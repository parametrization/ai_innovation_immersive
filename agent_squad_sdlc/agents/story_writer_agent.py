"""
Story Writer Agent

Transforms requirements into actionable user stories.
Responsible for:
- Creating well-formed user stories (As a... I want... So that...)
- Defining acceptance criteria
- Breaking down epics into smaller stories
- Adding story point estimates and labels
"""

from typing import Any, Optional

from agent_squad.agents import AnthropicAgent

from agent_squad_sdlc.agents.base import create_anthropic_agent, format_tool_schema
from agent_squad_sdlc.config import Settings
from agent_squad_sdlc.prompts.story_prompt import STORY_WRITER_AGENT_PROMPT
from agent_squad_sdlc.tools.github_tools import GitHubTools


def get_story_writer_tools() -> list[dict[str, Any]]:
    """Get tool definitions for the Story Writer Agent."""
    return [
        format_tool_schema(
            name="create_issue",
            description="Create a new GitHub issue (user story)",
            parameters={
                "title": {
                    "type": "string",
                    "description": "Issue title",
                },
                "body": {
                    "type": "string",
                    "description": "Issue body with user story details (markdown)",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels to apply (e.g., 'user-story', 'enhancement')",
                },
                "milestone": {
                    "type": "string",
                    "description": "Milestone name to assign",
                },
            },
            required=["title", "body"],
        ),
        format_tool_schema(
            name="update_issue",
            description="Update an existing GitHub issue",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number to update",
                },
                "title": {
                    "type": "string",
                    "description": "New title (optional)",
                },
                "body": {
                    "type": "string",
                    "description": "New body content (optional)",
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed"],
                    "description": "New state (optional)",
                },
            },
            required=["issue_number"],
        ),
        format_tool_schema(
            name="get_issue",
            description="Retrieve details of a GitHub issue",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number to retrieve",
                },
            },
            required=["issue_number"],
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
        format_tool_schema(
            name="create_milestone",
            description="Create a new milestone for grouping stories",
            parameters={
                "title": {
                    "type": "string",
                    "description": "Milestone title",
                },
                "description": {
                    "type": "string",
                    "description": "Milestone description",
                },
                "due_on": {
                    "type": "string",
                    "description": "Due date in ISO 8601 format (optional)",
                },
            },
            required=["title"],
        ),
        format_tool_schema(
            name="link_issues",
            description="Add a reference link between issues",
            parameters={
                "source_issue": {
                    "type": "integer",
                    "description": "The issue to add the link from",
                },
                "target_issue": {
                    "type": "integer",
                    "description": "The issue to link to",
                },
                "link_type": {
                    "type": "string",
                    "enum": ["relates_to", "blocks", "is_blocked_by", "parent_of", "child_of"],
                    "description": "Type of relationship",
                },
            },
            required=["source_issue", "target_issue", "link_type"],
        ),
    ]


async def story_writer_tool_handler(
    response: Any,
    conversation: list[dict[str, Any]],
    github_tools: GitHubTools,
) -> Any:
    """
    Handle tool calls from the Story Writer Agent.

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
        "create_issue": lambda: github_tools.create_issue(
            title=tool_input["title"],
            body=tool_input["body"],
            labels=tool_input.get("labels"),
            milestone=tool_input.get("milestone"),
        ),
        "update_issue": lambda: github_tools.update_issue(
            issue_number=tool_input["issue_number"],
            title=tool_input.get("title"),
            body=tool_input.get("body"),
            state=tool_input.get("state"),
        ),
        "get_issue": lambda: github_tools.get_issue(tool_input["issue_number"]),
        "add_labels": lambda: github_tools.add_labels(
            tool_input["issue_number"],
            tool_input["labels"],
        ),
        "create_milestone": lambda: github_tools.create_milestone(
            title=tool_input["title"],
            description=tool_input.get("description"),
            due_on=tool_input.get("due_on"),
        ),
        "link_issues": lambda: github_tools.link_issues(
            source_issue=tool_input["source_issue"],
            target_issue=tool_input["target_issue"],
            link_type=tool_input["link_type"],
        ),
    }

    handler = handlers.get(tool_name)
    if handler:
        return await handler()

    return {"error": f"Unknown tool: {tool_name}"}


def create_story_writer_agent(
    github_tools: GitHubTools,
    settings: Optional[Settings] = None,
) -> AnthropicAgent:
    """
    Create the Story Writer Agent.

    Args:
        github_tools: GitHub tools instance for API operations
        settings: Optional settings override

    Returns:
        Configured Story Writer Agent
    """

    async def tool_handler(response: Any, conversation: list[dict[str, Any]]) -> Any:
        return await story_writer_tool_handler(response, conversation, github_tools)

    return create_anthropic_agent(
        name="StoryWriterAgent",
        description=(
            "Transforms requirements into well-structured user stories. "
            "Specializes in creating user stories with proper format "
            "(As a... I want... So that...), defining acceptance criteria, "
            "breaking down epics, and organizing work with labels and milestones. "
            "Use this agent when: requirements are clarified and need to be "
            "converted into actionable user stories."
        ),
        system_prompt=STORY_WRITER_AGENT_PROMPT,
        tools=get_story_writer_tools(),
        tool_handler=tool_handler,
        settings=settings,
    )
