"""
Issue Resolver Agent

Triages and resolves issues and bugs.
Responsible for:
- Analyzing bug reports and error logs
- Identifying root causes
- Proposing fixes via PR comments
- Linking related issues
"""

from typing import Any, Optional

from agent_squad.agents import AnthropicAgent

from agent_squad_sdlc.agents.base import create_anthropic_agent, format_tool_schema
from agent_squad_sdlc.config import Settings
from agent_squad_sdlc.prompts.issue_resolver_prompt import ISSUE_RESOLVER_AGENT_PROMPT
from agent_squad_sdlc.tools.github_tools import GitHubTools


def get_issue_resolver_tools() -> list[dict[str, Any]]:
    """Get tool definitions for the Issue Resolver Agent."""
    return [
        format_tool_schema(
            name="get_issue",
            description="Get details of a GitHub issue (bug report)",
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
            description="Get all comments on an issue for context",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number",
                },
            },
            required=["issue_number"],
        ),
        format_tool_schema(
            name="search_issues",
            description="Search for related issues",
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
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by labels",
                },
            },
            required=["query"],
        ),
        format_tool_schema(
            name="search_code",
            description="Search codebase for relevant code",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Code search query",
                },
            },
            required=["query"],
        ),
        format_tool_schema(
            name="get_file_contents",
            description="Read file contents to analyze code",
            parameters={
                "path": {
                    "type": "string",
                    "description": "File path relative to repository root",
                },
                "ref": {
                    "type": "string",
                    "description": "Branch or commit ref",
                },
            },
            required=["path"],
        ),
        format_tool_schema(
            name="add_issue_comment",
            description="Add analysis or fix suggestion to an issue",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number",
                },
                "body": {
                    "type": "string",
                    "description": "Comment with analysis/fix suggestion (markdown)",
                },
            },
            required=["issue_number", "body"],
        ),
        format_tool_schema(
            name="add_labels",
            description="Add labels to categorize issues",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels to add (e.g., 'bug', 'priority:high')",
                },
            },
            required=["issue_number", "labels"],
        ),
        format_tool_schema(
            name="link_issues",
            description="Link related issues together",
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
                    "enum": ["relates_to", "duplicates", "blocks", "is_blocked_by"],
                    "description": "Type of relationship",
                },
            },
            required=["source_issue", "target_issue", "link_type"],
        ),
        format_tool_schema(
            name="update_issue",
            description="Update issue details (title, body, state)",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number",
                },
                "title": {
                    "type": "string",
                    "description": "New title (optional)",
                },
                "body": {
                    "type": "string",
                    "description": "New body (optional)",
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
            name="get_recent_commits",
            description="Get recent commits to identify potential causes",
            parameters={
                "path": {
                    "type": "string",
                    "description": "File path to filter commits (optional)",
                },
                "since": {
                    "type": "string",
                    "description": "Start date (ISO format)",
                },
            },
            required=[],
        ),
        format_tool_schema(
            name="create_fix_branch",
            description="Create a branch for the fix",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number to reference in branch name",
                },
                "description": {
                    "type": "string",
                    "description": "Short description for branch name",
                },
            },
            required=["issue_number", "description"],
        ),
    ]


async def issue_resolver_tool_handler(
    response: Any,
    conversation: list[dict[str, Any]],
    github_tools: GitHubTools,
) -> Any:
    """
    Handle tool calls from the Issue Resolver Agent.

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
        "search_issues": lambda: github_tools.search_issues(
            query=tool_input["query"],
            state=tool_input.get("state", "all"),
            labels=tool_input.get("labels"),
        ),
        "search_code": lambda: github_tools.search_code(tool_input["query"]),
        "get_file_contents": lambda: github_tools.get_file_contents(
            path=tool_input["path"],
            ref=tool_input.get("ref"),
        ),
        "add_issue_comment": lambda: github_tools.add_issue_comment(
            issue_number=tool_input["issue_number"],
            body=tool_input["body"],
        ),
        "add_labels": lambda: github_tools.add_labels(
            issue_number=tool_input["issue_number"],
            labels=tool_input["labels"],
        ),
        "link_issues": lambda: github_tools.link_issues(
            source_issue=tool_input["source_issue"],
            target_issue=tool_input["target_issue"],
            link_type=tool_input["link_type"],
        ),
        "update_issue": lambda: github_tools.update_issue(
            issue_number=tool_input["issue_number"],
            title=tool_input.get("title"),
            body=tool_input.get("body"),
            state=tool_input.get("state"),
        ),
        "get_recent_commits": lambda: github_tools.get_recent_commits(
            path=tool_input.get("path"),
            since=tool_input.get("since"),
        ),
        "create_fix_branch": lambda: github_tools.create_fix_branch(
            issue_number=tool_input["issue_number"],
            description=tool_input["description"],
        ),
    }

    handler = handlers.get(tool_name)
    if handler:
        return await handler()

    return {"error": f"Unknown tool: {tool_name}"}


def create_issue_resolver_agent(
    github_tools: GitHubTools,
    settings: Optional[Settings] = None,
) -> AnthropicAgent:
    """
    Create the Issue Resolver Agent.

    Args:
        github_tools: GitHub tools instance for API operations
        settings: Optional settings override

    Returns:
        Configured Issue Resolver Agent
    """

    async def tool_handler(response: Any, conversation: list[dict[str, Any]]) -> Any:
        return await issue_resolver_tool_handler(response, conversation, github_tools)

    return create_anthropic_agent(
        name="IssueResolverAgent",
        description=(
            "Triages and helps resolve bugs and issues. "
            "Specializes in analyzing bug reports, identifying root causes, "
            "searching for related issues, and proposing fixes. "
            "Use this agent when: bug reports need triage, root cause analysis "
            "is needed, or issues need to be linked and categorized."
        ),
        system_prompt=ISSUE_RESOLVER_AGENT_PROMPT,
        tools=get_issue_resolver_tools(),
        tool_handler=tool_handler,
        settings=settings,
    )
