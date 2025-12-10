"""
GitHub App authentication.

Handles JWT generation and installation access token management.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import jwt
from pydantic import BaseModel

from agent_squad_sdlc.config import Settings, get_settings


class InstallationToken(BaseModel):
    """Represents a GitHub App installation access token."""

    token: str
    expires_at: datetime
    permissions: dict[str, str]
    repository_selection: str


class GitHubApp:
    """
    GitHub App authentication manager.

    Handles JWT generation for app authentication and
    installation access token management.
    """

    GITHUB_API_URL = "https://api.github.com"

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the GitHub App.

        Args:
            settings: Optional settings override
        """
        self.settings = settings or get_settings()
        self._installation_token: Optional[InstallationToken] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def app_id(self) -> str:
        """Get the GitHub App ID."""
        return self.settings.github_app_id

    @property
    def private_key(self) -> str:
        """Get the GitHub App private key."""
        return self.settings.github_app_private_key.get_secret_value()

    def _generate_jwt(self) -> str:
        """
        Generate a JWT for GitHub App authentication.

        Returns:
            JWT token string
        """
        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued 60 seconds ago to handle clock skew
            "exp": now + (10 * 60),  # Expires in 10 minutes
            "iss": self.app_id,
        }

        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.GITHUB_API_URL,
                timeout=30.0,
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def get_installation_id(self) -> str:
        """
        Get the installation ID for the configured repository.

        Returns:
            Installation ID string

        Raises:
            ValueError: If installation cannot be found
        """
        if self.settings.github_installation_id:
            return self.settings.github_installation_id

        client = await self._get_http_client()
        jwt_token = self._generate_jwt()

        # Get installation for the repository
        response = await client.get(
            f"/repos/{self.settings.github_repo_full_name}/installation",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        if response.status_code != 200:
            raise ValueError(
                f"Failed to get installation: {response.status_code} - {response.text}"
            )

        data = response.json()
        return str(data["id"])

    async def get_installation_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid installation access token.

        Args:
            force_refresh: Force token refresh even if current token is valid

        Returns:
            Installation access token string
        """
        # Check if we have a valid cached token
        if (
            not force_refresh
            and self._installation_token
            and self._installation_token.expires_at > datetime.now(timezone.utc) + timedelta(minutes=5)
        ):
            return self._installation_token.token

        # Get new token
        client = await self._get_http_client()
        jwt_token = self._generate_jwt()
        installation_id = await self.get_installation_id()

        response = await client.post(
            f"/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        if response.status_code != 201:
            raise ValueError(
                f"Failed to get installation token: {response.status_code} - {response.text}"
            )

        data = response.json()
        self._installation_token = InstallationToken(
            token=data["token"],
            expires_at=datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")),
            permissions=data.get("permissions", {}),
            repository_selection=data.get("repository_selection", "selected"),
        )

        return self._installation_token.token

    async def get_authenticated_client(self) -> httpx.AsyncClient:
        """
        Get an HTTP client authenticated with the installation token.

        Returns:
            Authenticated httpx.AsyncClient
        """
        token = await self.get_installation_token()
        return httpx.AsyncClient(
            base_url=self.GITHUB_API_URL,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def verify_app_installation(self) -> dict:
        """
        Verify the app installation and return installation details.

        Returns:
            Installation details dict
        """
        client = await self._get_http_client()
        jwt_token = self._generate_jwt()
        installation_id = await self.get_installation_id()

        response = await client.get(
            f"/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        if response.status_code != 200:
            raise ValueError(
                f"Failed to verify installation: {response.status_code} - {response.text}"
            )

        return response.json()
