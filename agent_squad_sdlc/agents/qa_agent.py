"""
QA Agent

Handles functional testing and validation.
Responsible for:
- Designing test scenarios from acceptance criteria
- Executing functional tests
- Reporting test results on PRs
- Validating against requirements
"""

from typing import Any, Optional

from agent_squad.agents import AnthropicAgent

from agent_squad_sdlc.agents.base import create_anthropic_agent, format_tool_schema
from agent_squad_sdlc.config import Settings
from agent_squad_sdlc.prompts.qa_prompt import QA_AGENT_PROMPT
from agent_squad_sdlc.tools.github_tools import GitHubTools


def get_qa_tools() -> list[dict[str, Any]]:
    """Get tool definitions for the QA Agent."""
    return [
        format_tool_schema(
            name="get_pull_request",
            description="Get details of a pull request",
            parameters={
                "pr_number": {
                    "type": "integer",
                    "description": "The PR number to retrieve",
                },
            },
            required=["pr_number"],
        ),
        format_tool_schema(
            name="get_pr_files",
            description="Get list of files changed in a pull request",
            parameters={
                "pr_number": {
                    "type": "integer",
                    "description": "The PR number",
                },
            },
            required=["pr_number"],
        ),
        format_tool_schema(
            name="get_pr_diff",
            description="Get the diff/patch for a pull request",
            parameters={
                "pr_number": {
                    "type": "integer",
                    "description": "The PR number",
                },
            },
            required=["pr_number"],
        ),
        format_tool_schema(
            name="add_pr_review",
            description="Submit a review on a pull request",
            parameters={
                "pr_number": {
                    "type": "integer",
                    "description": "The PR number to review",
                },
                "body": {
                    "type": "string",
                    "description": "Review summary comment",
                },
                "event": {
                    "type": "string",
                    "enum": ["APPROVE", "REQUEST_CHANGES", "COMMENT"],
                    "description": "Review action",
                },
                "comments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "line": {"type": "integer"},
                            "body": {"type": "string"},
                        },
                    },
                    "description": "Line-specific review comments",
                },
            },
            required=["pr_number", "body", "event"],
        ),
        format_tool_schema(
            name="add_pr_comment",
            description="Add a general comment to a pull request",
            parameters={
                "pr_number": {
                    "type": "integer",
                    "description": "The PR number",
                },
                "body": {
                    "type": "string",
                    "description": "Comment text (markdown)",
                },
            },
            required=["pr_number", "body"],
        ),
        format_tool_schema(
            name="get_check_runs",
            description="Get CI/CD check run results for a PR",
            parameters={
                "pr_number": {
                    "type": "integer",
                    "description": "The PR number",
                },
            },
            required=["pr_number"],
        ),
        format_tool_schema(
            name="get_issue",
            description="Get linked issue for acceptance criteria",
            parameters={
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number",
                },
            },
            required=["issue_number"],
        ),
        format_tool_schema(
            name="create_test_checklist",
            description="Create a test checklist comment on a PR",
            parameters={
                "pr_number": {
                    "type": "integer",
                    "description": "The PR number",
                },
                "test_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "steps": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "expected_result": {"type": "string"},
                        },
                    },
                    "description": "List of test cases to include",
                },
            },
            required=["pr_number", "test_cases"],
        ),
        format_tool_schema(
            name="get_file_contents",
            description="Read file contents to review test coverage",
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
    ]


async def qa_tool_handler(
    response: Any,
    conversation: list[dict[str, Any]],
    github_tools: GitHubTools,
) -> Any:
    """
    Handle tool calls from the QA Agent.

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
        "get_pull_request": lambda: github_tools.get_pull_request(
            tool_input["pr_number"]
        ),
        "get_pr_files": lambda: github_tools.get_pr_files(tool_input["pr_number"]),
        "get_pr_diff": lambda: github_tools.get_pr_diff(tool_input["pr_number"]),
        "add_pr_review": lambda: github_tools.add_pr_review(
            pr_number=tool_input["pr_number"],
            body=tool_input["body"],
            event=tool_input["event"],
            comments=tool_input.get("comments"),
        ),
        "add_pr_comment": lambda: github_tools.add_pr_comment(
            pr_number=tool_input["pr_number"],
            body=tool_input["body"],
        ),
        "get_check_runs": lambda: github_tools.get_check_runs(tool_input["pr_number"]),
        "get_issue": lambda: github_tools.get_issue(tool_input["issue_number"]),
        "create_test_checklist": lambda: github_tools.create_test_checklist(
            pr_number=tool_input["pr_number"],
            test_cases=tool_input["test_cases"],
        ),
        "get_file_contents": lambda: github_tools.get_file_contents(
            path=tool_input["path"],
            ref=tool_input.get("ref"),
        ),
    }

    handler = handlers.get(tool_name)
    if handler:
        return await handler()

    return {"error": f"Unknown tool: {tool_name}"}


def create_qa_agent(
    github_tools: GitHubTools,
    settings: Optional[Settings] = None,
) -> AnthropicAgent:
    """
    Create the QA Agent.

    Args:
        github_tools: GitHub tools instance for API operations
        settings: Optional settings override

    Returns:
        Configured QA Agent
    """

    async def tool_handler(response: Any, conversation: list[dict[str, Any]]) -> Any:
        return await qa_tool_handler(response, conversation, github_tools)

    return create_anthropic_agent(
        name="QAAgent",
        description=(
            "Handles quality assurance and testing for pull requests. "
            "Specializes in reviewing PRs against acceptance criteria, "
            "creating test checklists, analyzing CI/CD results, and "
            "providing QA feedback. Use this agent when: PRs need testing "
            "validation, test scenarios need to be designed, or CI results "
            "need interpretation."
        ),
        system_prompt=QA_AGENT_PROMPT,
        tools=get_qa_tools(),
        tool_handler=tool_handler,
        settings=settings,
    )
