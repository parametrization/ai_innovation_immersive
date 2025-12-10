"""
Tests for SDLC agents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_squad_sdlc.agents.base import create_anthropic_agent, format_tool_schema
from agent_squad_sdlc.config import Settings


class TestFormatToolSchema:
    """Tests for format_tool_schema utility."""

    def test_basic_tool_schema(self):
        """Test basic tool schema generation."""
        schema = format_tool_schema(
            name="test_tool",
            description="A test tool",
            parameters={
                "param1": {"type": "string", "description": "First parameter"},
            },
        )

        assert schema["name"] == "test_tool"
        assert schema["description"] == "A test tool"
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "param1" in schema["input_schema"]["properties"]

    def test_tool_schema_with_required(self):
        """Test tool schema with required parameters."""
        schema = format_tool_schema(
            name="required_tool",
            description="Tool with required params",
            parameters={
                "required_param": {"type": "string"},
                "optional_param": {"type": "integer"},
            },
            required=["required_param"],
        )

        assert schema["input_schema"]["required"] == ["required_param"]

    def test_tool_schema_without_required(self):
        """Test tool schema without required parameters."""
        schema = format_tool_schema(
            name="optional_tool",
            description="Tool without required params",
            parameters={
                "param": {"type": "string"},
            },
        )

        assert "required" not in schema["input_schema"]


class TestCreateAnthropicAgent:
    """Tests for create_anthropic_agent factory."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return MagicMock(
            spec=Settings,
            anthropic_api_key=MagicMock(get_secret_value=lambda: "test-key"),
            claude_model_id="claude-sonnet-4-20250514",
            github_owner="test-owner",
            github_repo="test-repo",
            github_repo_full_name="test-owner/test-repo",
        )

    @patch("agent_squad_sdlc.agents.base.AnthropicAgent")
    def test_create_agent_basic(self, mock_agent_class, mock_settings):
        """Test basic agent creation."""
        agent = create_anthropic_agent(
            name="TestAgent",
            description="A test agent",
            system_prompt="Test prompt",
            settings=mock_settings,
        )

        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        options = call_args[0][0]

        assert options.name == "TestAgent"
        assert options.description == "A test agent"

    @patch("agent_squad_sdlc.agents.base.AnthropicAgent")
    def test_create_agent_with_tools(self, mock_agent_class, mock_settings):
        """Test agent creation with tools."""
        tools = [
            {"name": "tool1", "description": "Test tool"},
        ]
        tool_handler = MagicMock()

        agent = create_anthropic_agent(
            name="ToolAgent",
            description="Agent with tools",
            system_prompt="Test prompt",
            tools=tools,
            tool_handler=tool_handler,
            settings=mock_settings,
        )

        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        options = call_args[0][0]

        assert options.tool_config is not None


class TestRequirementsAgent:
    """Tests for Requirements Agent."""

    @pytest.fixture
    def mock_github_tools(self):
        """Create mock GitHub tools."""
        mock = AsyncMock()
        mock.get_issue = AsyncMock(return_value={
            "number": 1,
            "title": "Test Issue",
            "body": "Test body",
        })
        mock.get_issue_comments = AsyncMock(return_value=[])
        mock.add_issue_comment = AsyncMock(return_value={"id": 1})
        mock.search_issues = AsyncMock(return_value=[])
        mock.add_labels = AsyncMock(return_value=[])
        return mock

    def test_requirements_tools_defined(self):
        """Test that requirements tools are properly defined."""
        from agent_squad_sdlc.agents.requirements_agent import get_requirements_tools

        tools = get_requirements_tools()

        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "get_issue" in tool_names
        assert "add_issue_comment" in tool_names
        assert "search_issues" in tool_names


class TestStoryWriterAgent:
    """Tests for Story Writer Agent."""

    def test_story_writer_tools_defined(self):
        """Test that story writer tools are properly defined."""
        from agent_squad_sdlc.agents.story_writer_agent import get_story_writer_tools

        tools = get_story_writer_tools()

        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "create_issue" in tool_names
        assert "update_issue" in tool_names
        assert "create_milestone" in tool_names


class TestImplementationAgent:
    """Tests for Implementation Agent."""

    def test_implementation_tools_defined(self):
        """Test that implementation tools are properly defined."""
        from agent_squad_sdlc.agents.implementation_agent import get_implementation_tools

        tools = get_implementation_tools()

        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "get_file_contents" in tool_names
        assert "create_pull_request" in tool_names
        assert "suggest_code_change" in tool_names


class TestQAAgent:
    """Tests for QA Agent."""

    def test_qa_tools_defined(self):
        """Test that QA tools are properly defined."""
        from agent_squad_sdlc.agents.qa_agent import get_qa_tools

        tools = get_qa_tools()

        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "get_pull_request" in tool_names
        assert "add_pr_review" in tool_names
        assert "create_test_checklist" in tool_names


class TestIssueResolverAgent:
    """Tests for Issue Resolver Agent."""

    def test_issue_resolver_tools_defined(self):
        """Test that issue resolver tools are properly defined."""
        from agent_squad_sdlc.agents.issue_resolver_agent import get_issue_resolver_tools

        tools = get_issue_resolver_tools()

        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "get_issue" in tool_names
        assert "search_code" in tool_names
        assert "link_issues" in tool_names
