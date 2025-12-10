"""
Tests for GitHub tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_squad_sdlc.tools.github_tools import GitHubTools
from agent_squad_sdlc.config import Settings


class TestGitHubTools:
    """Tests for GitHubTools class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return MagicMock(
            spec=Settings,
            github_owner="test-owner",
            github_repo="test-repo",
            github_repo_full_name="test-owner/test-repo",
        )

    @pytest.fixture
    def mock_github_app(self):
        """Create mock GitHub App."""
        app = AsyncMock()
        app.get_authenticated_client = AsyncMock()
        app.close = AsyncMock()
        return app

    @pytest.fixture
    def github_tools(self, mock_github_app, mock_settings):
        """Create GitHubTools instance with mocks."""
        return GitHubTools(
            github_app=mock_github_app,
            settings=mock_settings,
        )

    def test_repo_path(self, github_tools):
        """Test repo_path property."""
        assert github_tools.repo_path == "/repos/test-owner/test-repo"

    @pytest.mark.asyncio
    async def test_get_issue(self, github_tools, mock_github_app):
        """Test get_issue method."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "number": 1,
            "title": "Test Issue",
            "body": "Test body",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_github_app.get_authenticated_client.return_value = mock_client

        result = await github_tools.get_issue(1)

        assert result["number"] == 1
        assert result["title"] == "Test Issue"
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_issue(self, github_tools, mock_github_app):
        """Test create_issue method."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "number": 2,
            "title": "New Issue",
            "body": "New body",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_github_app.get_authenticated_client.return_value = mock_client

        result = await github_tools.create_issue(
            title="New Issue",
            body="New body",
            labels=["bug"],
        )

        assert result["number"] == 2
        assert result["title"] == "New Issue"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_issue_comment(self, github_tools, mock_github_app):
        """Test add_issue_comment method."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 123,
            "body": "Test comment",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_github_app.get_authenticated_client.return_value = mock_client

        result = await github_tools.add_issue_comment(1, "Test comment")

        assert result["id"] == 123
        assert result["body"] == "Test comment"

    @pytest.mark.asyncio
    async def test_search_issues(self, github_tools, mock_github_app):
        """Test search_issues method."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"number": 1, "title": "Found Issue"},
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_github_app.get_authenticated_client.return_value = mock_client

        result = await github_tools.search_issues("test query")

        assert len(result) == 1
        assert result[0]["title"] == "Found Issue"

    @pytest.mark.asyncio
    async def test_create_pull_request(self, github_tools, mock_github_app):
        """Test create_pull_request method."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "number": 10,
            "title": "New PR",
            "draft": True,
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_github_app.get_authenticated_client.return_value = mock_client

        result = await github_tools.create_pull_request(
            title="New PR",
            body="PR body",
            head_branch="feature-branch",
        )

        assert result["number"] == 10
        assert result["draft"] is True

    @pytest.mark.asyncio
    async def test_add_pr_review(self, github_tools, mock_github_app):
        """Test add_pr_review method."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 456,
            "state": "APPROVED",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_github_app.get_authenticated_client.return_value = mock_client

        result = await github_tools.add_pr_review(
            pr_number=10,
            body="LGTM!",
            event="APPROVE",
        )

        assert result["id"] == 456
        assert result["state"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_get_file_contents(self, github_tools, mock_github_app):
        """Test get_file_contents method."""
        import base64

        content = "print('hello')"
        encoded = base64.b64encode(content.encode()).decode()

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "path": "test.py",
            "content": encoded,
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_github_app.get_authenticated_client.return_value = mock_client

        result = await github_tools.get_file_contents("test.py")

        assert result["path"] == "test.py"
        assert result["decoded_content"] == content

    @pytest.mark.asyncio
    async def test_create_branch(self, github_tools, mock_github_app):
        """Test create_branch method."""
        mock_client = AsyncMock()

        # Mock get ref response
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "object": {"sha": "abc123"},
        }
        mock_get_response.raise_for_status = MagicMock()

        # Mock create ref response
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {
            "ref": "refs/heads/new-branch",
            "object": {"sha": "abc123"},
        }
        mock_post_response.raise_for_status = MagicMock()

        mock_client.get = AsyncMock(return_value=mock_get_response)
        mock_client.post = AsyncMock(return_value=mock_post_response)
        mock_github_app.get_authenticated_client.return_value = mock_client

        result = await github_tools.create_branch("new-branch")

        assert result["ref"] == "refs/heads/new-branch"

    @pytest.mark.asyncio
    async def test_link_issues(self, github_tools, mock_github_app):
        """Test link_issues method."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 789,
            "body": "Related to #2",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_github_app.get_authenticated_client.return_value = mock_client

        result = await github_tools.link_issues(
            source_issue=1,
            target_issue=2,
            link_type="relates_to",
        )

        assert "Related to #2" in result["body"]

    @pytest.mark.asyncio
    async def test_close(self, github_tools, mock_github_app):
        """Test close method cleans up resources."""
        # Create a mock client first
        mock_client = AsyncMock()
        mock_github_app.get_authenticated_client.return_value = mock_client

        # Get the client to set it
        await github_tools._get_client()

        # Now close
        await github_tools.close()

        mock_client.aclose.assert_called_once()
        mock_github_app.close.assert_called_once()
