"""
Implementation Agent

Analyzes codebase and suggests implementation approaches.
Responsible for:
- Analyzing codebase structure
- Suggesting implementation code (via PR comments)
- Recommending unit test approaches
- Creating pull requests with suggested changes
"""

from typing import Any, Optional

from agent_squad.agents import AnthropicAgent

from agent_squad_sdlc.agents.base import create_anthropic_agent, format_tool_schema
from agent_squad_sdlc.config import Settings
from agent_squad_sdlc.prompts.implementation_prompt import IMPLEMENTATION_AGENT_PROMPT
from agent_squad_sdlc.tools.github_tools import GitHubTools


def get_implementation_tools() -> list[dict[str, Any]]:
    """Get tool definitions for the Implementation Agent."""
    return [
        format_tool_schema(
            name="get_file_contents",
            description="Read the contents of a file from the repository",
            parameters={
                "path": {
                    "type": "string",
                    "description": "File path relative to repository root",
                },
                "ref": {
                    "type": "string",
                    "description": "Branch or commit ref (defaults to main)",
                },
            },
            required=["path"],
        ),
        format_tool_schema(
            name="list_directory",
            description="List contents of a directory in the repository",
            parameters={
                "path": {
                    "type": "string",
                    "description": "Directory path relative to repository root",
                },
                "ref": {
                    "type": "string",
                    "description": "Branch or commit ref (defaults to main)",
                },
            },
            required=["path"],
        ),
        format_tool_schema(
            name="search_code",
            description="Search for code patterns in the repository",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query (supports GitHub code search syntax)",
                },
            },
            required=["query"],
        ),
        format_tool_schema(
            name="create_branch",
            description="Create a new branch from the default branch",
            parameters={
                "branch_name": {
                    "type": "string",
                    "description": "Name for the new branch",
                },
                "base_branch": {
                    "type": "string",
                    "description": "Base branch to create from (defaults to main)",
                },
            },
            required=["branch_name"],
        ),
        format_tool_schema(
            name="create_pull_request",
            description="Create a pull request with implementation suggestions",
            parameters={
                "title": {
                    "type": "string",
                    "description": "PR title",
                },
                "body": {
                    "type": "string",
                    "description": "PR description with implementation details",
                },
                "head_branch": {
                    "type": "string",
                    "description": "Source branch with changes",
                },
                "base_branch": {
                    "type": "string",
                    "description": "Target branch (defaults to main)",
                },
                "draft": {
                    "type": "boolean",
                    "description": "Create as draft PR",
                },
            },
            required=["title", "body", "head_branch"],
        ),
        format_tool_schema(
            name="add_pr_comment",
            description="Add a comment to a pull request with code suggestions",
            parameters={
                "pr_number": {
                    "type": "integer",
                    "description": "The PR number to comment on",
                },
                "body": {
                    "type": "string",
                    "description": "Comment text with code suggestions (markdown)",
                },
                "path": {
                    "type": "string",
                    "description": "File path for line-specific comment (optional)",
                },
                "line": {
                    "type": "integer",
                    "description": "Line number for the comment (optional)",
                },
            },
            required=["pr_number", "body"],
        ),
        format_tool_schema(
            name="suggest_code_change",
            description="Add a code suggestion to a PR using GitHub's suggestion format",
            parameters={
                "pr_number": {
                    "type": "integer",
                    "description": "The PR number",
                },
                "path": {
                    "type": "string",
                    "description": "File path for the suggestion",
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number",
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number",
                },
                "suggestion": {
                    "type": "string",
                    "description": "The suggested code replacement",
                },
                "comment": {
                    "type": "string",
                    "description": "Explanation of the suggestion",
                },
            },
            required=["pr_number", "path", "start_line", "suggestion", "comment"],
        ),
        format_tool_schema(
            name="get_issue",
            description="Get issue details for implementation context",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number",
                },
            },
            required=["issue_number"],
        ),
    ]


async def implementation_tool_handler(
    response: Any,
    conversation: list[dict[str, Any]],
    github_tools: GitHubTools,
) -> Any:
    """
    Handle tool calls from the Implementation Agent.

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
        "get_file_contents": lambda: github_tools.get_file_contents(
            path=tool_input["path"],
            ref=tool_input.get("ref"),
        ),
        "list_directory": lambda: github_tools.list_directory(
            path=tool_input["path"],
            ref=tool_input.get("ref"),
        ),
        "search_code": lambda: github_tools.search_code(tool_input["query"]),
        "create_branch": lambda: github_tools.create_branch(
            branch_name=tool_input["branch_name"],
            base_branch=tool_input.get("base_branch"),
        ),
        "create_pull_request": lambda: github_tools.create_pull_request(
            title=tool_input["title"],
            body=tool_input["body"],
            head_branch=tool_input["head_branch"],
            base_branch=tool_input.get("base_branch"),
            draft=tool_input.get("draft", True),
        ),
        "add_pr_comment": lambda: github_tools.add_pr_comment(
            pr_number=tool_input["pr_number"],
            body=tool_input["body"],
            path=tool_input.get("path"),
            line=tool_input.get("line"),
        ),
        "suggest_code_change": lambda: github_tools.suggest_code_change(
            pr_number=tool_input["pr_number"],
            path=tool_input["path"],
            start_line=tool_input["start_line"],
            end_line=tool_input.get("end_line"),
            suggestion=tool_input["suggestion"],
            comment=tool_input["comment"],
        ),
        "get_issue": lambda: github_tools.get_issue(tool_input["issue_number"]),
    }

    handler = handlers.get(tool_name)
    if handler:
        return await handler()

    return {"error": f"Unknown tool: {tool_name}"}


def create_implementation_agent(
    github_tools: GitHubTools,
    settings: Optional[Settings] = None,
) -> AnthropicAgent:
    """
    Create the Implementation Agent.

    Args:
        github_tools: GitHub tools instance for API operations
        settings: Optional settings override

    Returns:
        Configured Implementation Agent
    """

    async def tool_handler(response: Any, conversation: list[dict[str, Any]]) -> Any:
        return await implementation_tool_handler(response, conversation, github_tools)

    return create_anthropic_agent(
        name="ImplementationAgent",
        description=(
            "Analyzes codebase and suggests implementation approaches. "
            "Specializes in reviewing code structure, suggesting implementation "
            "patterns, and providing code suggestions via PR comments. "
            "Does NOT directly commit code - provides suggestions for human review. "
            "Use this agent when: user stories need implementation guidance, "
            "code suggestions are needed, or PRs need code review comments."
        ),
        system_prompt=IMPLEMENTATION_AGENT_PROMPT,
        tools=get_implementation_tools(),
        tool_handler=tool_handler,
        settings=settings,
    )
