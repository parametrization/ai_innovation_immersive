"""
Integration tests for SDLC Agent Squad.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_squad_sdlc.config import Settings, StorageType, Environment
from agent_squad_sdlc.github_app.webhook import (
    WebhookHandler,
    WebhookEvent,
    verify_webhook_signature,
)


class TestWebhookSignatureVerification:
    """Tests for webhook signature verification."""

    def test_valid_signature(self):
        """Test valid webhook signature."""
        import hashlib
        import hmac

        secret = "test-secret"
        payload = b'{"action": "opened"}'

        signature = "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert verify_webhook_signature(payload, signature, secret) is True

    def test_invalid_signature(self):
        """Test invalid webhook signature."""
        payload = b'{"action": "opened"}'
        signature = "sha256=invalid"

        assert verify_webhook_signature(payload, signature, "secret") is False

    def test_missing_prefix(self):
        """Test signature without sha256= prefix."""
        payload = b'{"action": "opened"}'
        signature = "notsha256=abc123"

        assert verify_webhook_signature(payload, signature, "secret") is False


class TestWebhookHandler:
    """Tests for WebhookHandler."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return MagicMock(
            spec=Settings,
            github_webhook_secret=MagicMock(get_secret_value=lambda: "test-secret"),
        )

    @pytest.fixture
    def handler(self, mock_settings):
        """Create WebhookHandler instance."""
        return WebhookHandler(mock_settings)

    def test_parse_event(self, handler):
        """Test event parsing."""
        event = handler.parse_event(
            event_type="issues",
            delivery_id="abc-123",
            payload={
                "action": "opened",
                "issue": {"number": 1, "title": "Test"},
                "repository": {"full_name": "owner/repo"},
                "sender": {"login": "user"},
            },
        )

        assert event.event_type == "issues"
        assert event.action == "opened"
        assert event.delivery_id == "abc-123"
        assert event.issue["number"] == 1

    def test_register_handler(self, handler):
        """Test handler registration."""
        @handler.on("issues", "opened")
        def handle_issue_opened(event):
            return "handled"

        assert "issues:opened" in handler._handlers
        assert len(handler._handlers["issues:opened"]) == 1

    def test_register_handler_without_action(self, handler):
        """Test handler registration without action filter."""
        @handler.on("issues")
        def handle_all_issues(event):
            return "handled"

        assert "issues" in handler._handlers

    @pytest.mark.asyncio
    async def test_handle_event_with_matching_handler(self, handler):
        """Test event handling with matching handler."""
        handled = []

        @handler.on("issues", "opened")
        async def handle_issue_opened(event):
            handled.append(event)
            return "handled"

        event = WebhookEvent(
            event_type="issues",
            action="opened",
            delivery_id="123",
            payload={"issue": {"number": 1}},
        )

        results = await handler.handle(event)

        assert len(handled) == 1
        assert results == ["handled"]

    @pytest.mark.asyncio
    async def test_handle_event_no_matching_handler(self, handler):
        """Test event handling with no matching handler."""
        event = WebhookEvent(
            event_type="push",
            action=None,
            delivery_id="123",
            payload={},
        )

        results = await handler.handle(event)

        assert results == []

    @pytest.mark.asyncio
    async def test_handle_event_general_and_specific(self, handler):
        """Test event handling with both general and specific handlers."""
        results = []

        @handler.on("issues")
        async def handle_all(event):
            results.append("general")
            return "general"

        @handler.on("issues", "opened")
        async def handle_opened(event):
            results.append("specific")
            return "specific"

        event = WebhookEvent(
            event_type="issues",
            action="opened",
            delivery_id="123",
            payload={},
        )

        await handler.handle(event)

        assert "specific" in results
        assert "general" in results


class TestWebhookEvent:
    """Tests for WebhookEvent model."""

    def test_issue_property(self):
        """Test issue property."""
        event = WebhookEvent(
            event_type="issues",
            action="opened",
            delivery_id="123",
            payload={"issue": {"number": 1}},
        )

        assert event.issue["number"] == 1

    def test_pull_request_property(self):
        """Test pull_request property."""
        event = WebhookEvent(
            event_type="pull_request",
            action="opened",
            delivery_id="123",
            payload={"pull_request": {"number": 10}},
        )

        assert event.pull_request["number"] == 10

    def test_repository_property(self):
        """Test repository property."""
        event = WebhookEvent(
            event_type="issues",
            action="opened",
            delivery_id="123",
            payload={"repository": {"full_name": "owner/repo"}},
        )

        assert event.repository["full_name"] == "owner/repo"

    def test_sender_property(self):
        """Test sender property."""
        event = WebhookEvent(
            event_type="issues",
            action="opened",
            delivery_id="123",
            payload={"sender": {"login": "user"}},
        )

        assert event.sender["login"] == "user"


class TestConfigSettings:
    """Tests for configuration settings."""

    def test_storage_type_enum(self):
        """Test StorageType enum values."""
        assert StorageType.MEMORY.value == "memory"
        assert StorageType.DYNAMODB.value == "dynamodb"

    def test_environment_enum(self):
        """Test Environment enum values."""
        assert Environment.LOCAL.value == "local"
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"

    def test_settings_repo_full_name(self):
        """Test github_repo_full_name property."""
        with patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "test",
            "GITHUB_APP_ID": "123",
            "GITHUB_APP_PRIVATE_KEY": "key",
            "GITHUB_WEBHOOK_SECRET": "secret",
            "GITHUB_OWNER": "test-owner",
            "GITHUB_REPO": "test-repo",
        }):
            settings = Settings()
            assert settings.github_repo_full_name == "test-owner/test-repo"

    def test_settings_is_local(self):
        """Test is_local property."""
        with patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "test",
            "GITHUB_APP_ID": "123",
            "GITHUB_APP_PRIVATE_KEY": "key",
            "GITHUB_WEBHOOK_SECRET": "secret",
            "GITHUB_OWNER": "owner",
            "GITHUB_REPO": "repo",
            "ENVIRONMENT": "local",
        }):
            settings = Settings()
            assert settings.is_local is True
            assert settings.is_production is False

    def test_settings_is_production(self):
        """Test is_production property."""
        with patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "test",
            "GITHUB_APP_ID": "123",
            "GITHUB_APP_PRIVATE_KEY": "key",
            "GITHUB_WEBHOOK_SECRET": "secret",
            "GITHUB_OWNER": "owner",
            "GITHUB_REPO": "repo",
            "ENVIRONMENT": "production",
        }):
            settings = Settings()
            assert settings.is_production is True
            assert settings.is_local is False
