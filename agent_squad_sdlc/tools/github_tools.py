"""
GitHub API tools for SDLC agents.

Provides async methods for interacting with GitHub Issues, PRs, and repository content.
Supports both Personal Access Token (PAT) and GitHub App authentication.
"""

import base64
from datetime import datetime
from typing import Any, Optional

import httpx

from agent_squad_sdlc.config import GitHubAuthType, Settings, get_settings


class GitHubTools:
    """
    GitHub API operations for SDLC automation.

    Provides methods for issues, PRs, code, and repository operations.
    Supports both PAT and GitHub App authentication.
    """

    GITHUB_API_URL = "https://api.github.com"

    def __init__(
        self,
        settings: Optional[Settings] = None,
    ):
        """
        Initialize GitHub tools.

        Args:
            settings: Optional settings override
        """
        self.settings = settings or get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._github_app = None  # Lazy-loaded if needed

    async def _get_client(self) -> httpx.AsyncClient:
        """Get authenticated HTTP client based on auth type."""
        if self._client is None:
            if self.settings.github_auth_type == GitHubAuthType.TOKEN:
                # Use Personal Access Token
                token = self.settings.github_token
                if not token:
                    raise ValueError(
                        "GITHUB_TOKEN is required when GITHUB_AUTH_TYPE=token"
                    )
                self._client = httpx.AsyncClient(
                    base_url=self.GITHUB_API_URL,
                    headers={
                        "Authorization": f"token {token.get_secret_value()}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
            else:
                # Use GitHub App
                from agent_squad_sdlc.github_app import GitHubApp
                if self._github_app is None:
                    self._github_app = GitHubApp(self.settings)
                self._client = await self._github_app.get_authenticated_client()

        return self._client

    async def close(self) -> None:
        """Close HTTP clients."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._github_app:
            await self._github_app.close()
            self._github_app = None

    @property
    def repo_path(self) -> str:
        """Get repository API path."""
        return f"/repos/{self.settings.github_repo_full_name}"

    # ==================== Issue Operations ====================

    async def get_issue(self, issue_number: int) -> dict[str, Any]:
        """
        Get issue details.

        Args:
            issue_number: Issue number

        Returns:
            Issue data dict
        """
        client = await self._get_client()
        response = await client.get(f"{self.repo_path}/issues/{issue_number}")
        response.raise_for_status()
        return response.json()

    async def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
        milestone: Optional[str] = None,
        assignees: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Create a new issue.

        Args:
            title: Issue title
            body: Issue body (markdown)
            labels: Labels to apply
            milestone: Milestone name
            assignees: Usernames to assign

        Returns:
            Created issue data
        """
        client = await self._get_client()

        data: dict[str, Any] = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        if milestone:
            # Need to get milestone number from name
            milestone_num = await self._get_milestone_number(milestone)
            if milestone_num:
                data["milestone"] = milestone_num

        response = await client.post(f"{self.repo_path}/issues", json=data)
        response.raise_for_status()
        return response.json()

    async def update_issue(
        self,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Update an issue.

        Args:
            issue_number: Issue number
            title: New title
            body: New body
            state: New state (open/closed)
            labels: New labels

        Returns:
            Updated issue data
        """
        client = await self._get_client()

        data: dict[str, Any] = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None:
            data["state"] = state
        if labels is not None:
            data["labels"] = labels

        response = await client.patch(
            f"{self.repo_path}/issues/{issue_number}",
            json=data,
        )
        response.raise_for_status()
        return response.json()

    async def get_issue_comments(self, issue_number: int) -> list[dict[str, Any]]:
        """
        Get all comments on an issue.

        Args:
            issue_number: Issue number

        Returns:
            List of comment data
        """
        client = await self._get_client()
        response = await client.get(
            f"{self.repo_path}/issues/{issue_number}/comments"
        )
        response.raise_for_status()
        return response.json()

    async def add_issue_comment(
        self,
        issue_number: int,
        body: str,
    ) -> dict[str, Any]:
        """
        Add a comment to an issue.

        Args:
            issue_number: Issue number
            body: Comment text

        Returns:
            Created comment data
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.repo_path}/issues/{issue_number}/comments",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()

    async def search_issues(
        self,
        query: str,
        state: str = "open",
        labels: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for issues.

        Args:
            query: Search query
            state: Issue state filter
            labels: Label filters

        Returns:
            List of matching issues
        """
        client = await self._get_client()

        # Build search query
        search_query = f"{query} repo:{self.settings.github_repo_full_name}"
        if state != "all":
            search_query += f" state:{state}"
        if labels:
            for label in labels:
                search_query += f' label:"{label}"'

        response = await client.get(
            "/search/issues",
            params={"q": search_query, "per_page": 20},
        )
        response.raise_for_status()
        return response.json().get("items", [])

    async def add_labels(
        self,
        issue_number: int,
        labels: list[str],
    ) -> list[dict[str, Any]]:
        """
        Add labels to an issue.

        Args:
            issue_number: Issue number
            labels: Labels to add

        Returns:
            Updated labels list
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.repo_path}/issues/{issue_number}/labels",
            json={"labels": labels},
        )
        response.raise_for_status()
        return response.json()

    async def link_issues(
        self,
        source_issue: int,
        target_issue: int,
        link_type: str,
    ) -> dict[str, Any]:
        """
        Link two issues via a comment.

        Args:
            source_issue: Source issue number
            target_issue: Target issue number
            link_type: Type of link (relates_to, blocks, etc.)

        Returns:
            Created comment data
        """
        link_texts = {
            "relates_to": "Related to",
            "blocks": "Blocks",
            "is_blocked_by": "Blocked by",
            "duplicates": "Duplicate of",
            "parent_of": "Parent of",
            "child_of": "Child of",
        }
        text = link_texts.get(link_type, "Related to")
        body = f"{text} #{target_issue}"
        return await self.add_issue_comment(source_issue, body)

    # ==================== Milestone Operations ====================

    async def _get_milestone_number(self, title: str) -> Optional[int]:
        """Get milestone number by title."""
        client = await self._get_client()
        response = await client.get(f"{self.repo_path}/milestones")
        response.raise_for_status()

        for milestone in response.json():
            if milestone["title"] == title:
                return milestone["number"]
        return None

    async def create_milestone(
        self,
        title: str,
        description: Optional[str] = None,
        due_on: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a milestone.

        Args:
            title: Milestone title
            description: Description
            due_on: Due date (ISO 8601)

        Returns:
            Created milestone data
        """
        client = await self._get_client()

        data: dict[str, Any] = {"title": title}
        if description:
            data["description"] = description
        if due_on:
            data["due_on"] = due_on

        response = await client.post(f"{self.repo_path}/milestones", json=data)
        response.raise_for_status()
        return response.json()

    # ==================== Pull Request Operations ====================

    async def get_pull_request(self, pr_number: int) -> dict[str, Any]:
        """
        Get PR details.

        Args:
            pr_number: PR number

        Returns:
            PR data dict
        """
        client = await self._get_client()
        response = await client.get(f"{self.repo_path}/pulls/{pr_number}")
        response.raise_for_status()
        return response.json()

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: Optional[str] = None,
        draft: bool = True,
    ) -> dict[str, Any]:
        """
        Create a pull request.

        Args:
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch (defaults to main)
            draft: Create as draft

        Returns:
            Created PR data
        """
        client = await self._get_client()

        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch or "main",
            "draft": draft,
        }

        response = await client.post(f"{self.repo_path}/pulls", json=data)
        response.raise_for_status()
        return response.json()

    async def get_pr_files(self, pr_number: int) -> list[dict[str, Any]]:
        """
        Get files changed in a PR.

        Args:
            pr_number: PR number

        Returns:
            List of file change data
        """
        client = await self._get_client()
        response = await client.get(f"{self.repo_path}/pulls/{pr_number}/files")
        response.raise_for_status()
        return response.json()

    async def get_pr_diff(self, pr_number: int) -> str:
        """
        Get PR diff.

        Args:
            pr_number: PR number

        Returns:
            Diff text
        """
        client = await self._get_client()
        response = await client.get(
            f"{self.repo_path}/pulls/{pr_number}",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        response.raise_for_status()
        return response.text

    async def add_pr_comment(
        self,
        pr_number: int,
        body: str,
        path: Optional[str] = None,
        line: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Add a comment to a PR.

        Args:
            pr_number: PR number
            body: Comment text
            path: File path for line comment
            line: Line number for line comment

        Returns:
            Created comment data
        """
        client = await self._get_client()

        if path and line:
            # Create review comment on specific line
            # First get the PR to get the commit SHA
            pr = await self.get_pull_request(pr_number)
            data = {
                "body": body,
                "path": path,
                "line": line,
                "commit_id": pr["head"]["sha"],
            }
            response = await client.post(
                f"{self.repo_path}/pulls/{pr_number}/comments",
                json=data,
            )
        else:
            # Create issue comment (general PR comment)
            response = await client.post(
                f"{self.repo_path}/issues/{pr_number}/comments",
                json={"body": body},
            )

        response.raise_for_status()
        return response.json()

    async def add_pr_review(
        self,
        pr_number: int,
        body: str,
        event: str,
        comments: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Submit a PR review.

        Args:
            pr_number: PR number
            body: Review summary
            event: APPROVE, REQUEST_CHANGES, or COMMENT
            comments: Line-specific comments

        Returns:
            Created review data
        """
        client = await self._get_client()

        data: dict[str, Any] = {"body": body, "event": event}
        if comments:
            data["comments"] = comments

        response = await client.post(
            f"{self.repo_path}/pulls/{pr_number}/reviews",
            json=data,
        )
        response.raise_for_status()
        return response.json()

    async def suggest_code_change(
        self,
        pr_number: int,
        path: str,
        start_line: int,
        suggestion: str,
        comment: str,
        end_line: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Add a code suggestion to a PR.

        Args:
            pr_number: PR number
            path: File path
            start_line: Start line
            suggestion: Suggested code
            comment: Explanation
            end_line: End line (for multi-line)

        Returns:
            Created comment data
        """
        # Format as GitHub suggestion
        body = f"{comment}\n\n```suggestion\n{suggestion}\n```"

        pr = await self.get_pull_request(pr_number)
        client = await self._get_client()

        data: dict[str, Any] = {
            "body": body,
            "path": path,
            "line": end_line or start_line,
            "commit_id": pr["head"]["sha"],
        }

        if end_line and end_line != start_line:
            data["start_line"] = start_line

        response = await client.post(
            f"{self.repo_path}/pulls/{pr_number}/comments",
            json=data,
        )
        response.raise_for_status()
        return response.json()

    async def get_check_runs(self, pr_number: int) -> list[dict[str, Any]]:
        """
        Get CI check runs for a PR.

        Args:
            pr_number: PR number

        Returns:
            List of check run data
        """
        pr = await self.get_pull_request(pr_number)
        client = await self._get_client()

        response = await client.get(
            f"{self.repo_path}/commits/{pr['head']['sha']}/check-runs"
        )
        response.raise_for_status()
        return response.json().get("check_runs", [])

    async def create_test_checklist(
        self,
        pr_number: int,
        test_cases: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Create a test checklist comment on a PR.

        Args:
            pr_number: PR number
            test_cases: List of test case definitions

        Returns:
            Created comment data
        """
        lines = ["## QA Test Checklist\n"]

        for i, tc in enumerate(test_cases, 1):
            lines.append(f"### Test Case {i}: {tc.get('description', 'Untitled')}")
            if tc.get("steps"):
                lines.append("\n**Steps:**")
                for step in tc["steps"]:
                    lines.append(f"1. {step}")
            if tc.get("expected_result"):
                lines.append(f"\n**Expected:** {tc['expected_result']}")
            lines.append("\n- [ ] Pass\n- [ ] Fail\n")

        body = "\n".join(lines)
        return await self.add_pr_comment(pr_number, body)

    # ==================== Repository Operations ====================

    async def get_file_contents(
        self,
        path: str,
        ref: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get file contents.

        Args:
            path: File path
            ref: Branch or commit ref

        Returns:
            File data including decoded content
        """
        client = await self._get_client()

        params = {}
        if ref:
            params["ref"] = ref

        response = await client.get(
            f"{self.repo_path}/contents/{path}",
            params=params,
        )
        response.raise_for_status()

        data = response.json()
        if data.get("content"):
            data["decoded_content"] = base64.b64decode(data["content"]).decode("utf-8")

        return data

    async def list_directory(
        self,
        path: str,
        ref: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        List directory contents.

        Args:
            path: Directory path
            ref: Branch or commit ref

        Returns:
            List of directory entries
        """
        client = await self._get_client()

        params = {}
        if ref:
            params["ref"] = ref

        response = await client.get(
            f"{self.repo_path}/contents/{path}",
            params=params,
        )
        response.raise_for_status()
        return response.json()

    async def search_code(self, query: str) -> list[dict[str, Any]]:
        """
        Search code in repository.

        Args:
            query: Search query

        Returns:
            List of matching code results
        """
        client = await self._get_client()

        search_query = f"{query} repo:{self.settings.github_repo_full_name}"
        response = await client.get(
            "/search/code",
            params={"q": search_query, "per_page": 20},
        )
        response.raise_for_status()
        return response.json().get("items", [])

    async def create_branch(
        self,
        branch_name: str,
        base_branch: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new branch.

        Args:
            branch_name: New branch name
            base_branch: Base branch (defaults to main)

        Returns:
            Created ref data
        """
        client = await self._get_client()

        # Get base branch SHA
        base = base_branch or "main"
        response = await client.get(f"{self.repo_path}/git/ref/heads/{base}")
        response.raise_for_status()
        sha = response.json()["object"]["sha"]

        # Create new branch
        response = await client.post(
            f"{self.repo_path}/git/refs",
            json={
                "ref": f"refs/heads/{branch_name}",
                "sha": sha,
            },
        )
        response.raise_for_status()
        return response.json()

    async def create_fix_branch(
        self,
        issue_number: int,
        description: str,
    ) -> dict[str, Any]:
        """
        Create a fix branch for an issue.

        Args:
            issue_number: Issue number
            description: Short description for branch name

        Returns:
            Created branch ref data
        """
        # Sanitize description for branch name
        safe_desc = description.lower().replace(" ", "-")[:30]
        branch_name = f"fix/{issue_number}-{safe_desc}"
        return await self.create_branch(branch_name)

    async def get_recent_commits(
        self,
        path: Optional[str] = None,
        since: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get recent commits.

        Args:
            path: Filter by file path
            since: Start date (ISO 8601)

        Returns:
            List of commit data
        """
        client = await self._get_client()

        params: dict[str, Any] = {"per_page": 20}
        if path:
            params["path"] = path
        if since:
            params["since"] = since

        response = await client.get(f"{self.repo_path}/commits", params=params)
        response.raise_for_status()
        return response.json()
