"""
Configuration management for Agent Squad SDLC.

Handles environment variables, settings, and configuration validation.
"""

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageType(str, Enum):
    """Supported storage backends."""
    MEMORY = "memory"
    DYNAMODB = "dynamodb"


class Environment(str, Enum):
    """Deployment environments."""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Environment = Field(
        default=Environment.LOCAL,
        description="Deployment environment"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )

    # Anthropic / Claude
    anthropic_api_key: SecretStr = Field(
        description="Anthropic API key for Claude"
    )
    claude_model_id: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model to use for agents"
    )

    # GitHub App
    github_app_id: str = Field(
        description="GitHub App ID"
    )
    github_app_private_key: SecretStr = Field(
        description="GitHub App private key (PEM format)"
    )
    github_webhook_secret: SecretStr = Field(
        description="GitHub webhook secret for signature verification"
    )
    github_installation_id: Optional[str] = Field(
        default=None,
        description="GitHub App installation ID (optional, can be derived)"
    )

    # Repository
    github_owner: str = Field(
        description="GitHub repository owner"
    )
    github_repo: str = Field(
        description="GitHub repository name"
    )

    # Storage
    storage_type: StorageType = Field(
        default=StorageType.MEMORY,
        description="Storage backend type"
    )

    # AWS (for DynamoDB storage and Lambda deployment)
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region"
    )
    aws_endpoint_url: Optional[str] = Field(
        default=None,
        description="AWS endpoint URL (for LocalStack)"
    )
    dynamodb_table_name: str = Field(
        default="sdlc-agent-conversations",
        description="DynamoDB table name for conversation storage"
    )

    # Server
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    port: int = Field(
        default=8080,
        description="Server port"
    )

    @property
    def github_repo_full_name(self) -> str:
        """Return full repository name (owner/repo)."""
        return f"{self.github_owner}/{self.github_repo}"

    @property
    def is_local(self) -> bool:
        """Check if running in local environment."""
        return self.environment == Environment.LOCAL

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance loaded from environment.
    """
    return Settings()


# Convenience function for testing
def get_settings_override(**kwargs) -> Settings:
    """
    Create settings instance with overrides (for testing).

    Args:
        **kwargs: Setting overrides

    Returns:
        Settings instance with overrides applied.
    """
    return Settings(**kwargs)
