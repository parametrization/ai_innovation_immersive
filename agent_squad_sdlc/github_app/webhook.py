"""
GitHub webhook handling.

Handles webhook signature verification and event processing.
"""

import hashlib
import hmac
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel

from agent_squad_sdlc.config import Settings, get_settings


class WebhookEventType(str, Enum):
    """Supported webhook event types."""

    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    PUSH = "push"
    CHECK_RUN = "check_run"
    CHECK_SUITE = "check_suite"


class WebhookAction(str, Enum):
    """Common webhook actions."""

    OPENED = "opened"
    EDITED = "edited"
    CLOSED = "closed"
    REOPENED = "reopened"
    CREATED = "created"
    DELETED = "deleted"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    REQUESTED = "requested"
    SYNCHRONIZE = "synchronize"


class WebhookEvent(BaseModel):
    """Parsed webhook event."""

    event_type: str
    action: Optional[str] = None
    delivery_id: str
    payload: dict[str, Any]

    @property
    def repository(self) -> dict[str, Any]:
        """Get repository info from payload."""
        return self.payload.get("repository", {})

    @property
    def sender(self) -> dict[str, Any]:
        """Get sender info from payload."""
        return self.payload.get("sender", {})

    @property
    def issue(self) -> Optional[dict[str, Any]]:
        """Get issue from payload if present."""
        return self.payload.get("issue")

    @property
    def pull_request(self) -> Optional[dict[str, Any]]:
        """Get pull request from payload if present."""
        return self.payload.get("pull_request")

    @property
    def comment(self) -> Optional[dict[str, Any]]:
        """Get comment from payload if present."""
        return self.payload.get("comment")


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> bool:
    """
    Verify GitHub webhook signature.

    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret (optional, uses settings if not provided)
        settings: Settings instance (optional)

    Returns:
        True if signature is valid, False otherwise
    """
    if settings is None:
        settings = get_settings()

    if secret is None:
        secret = settings.github_webhook_secret.get_secret_value()

    if not signature.startswith("sha256="):
        return False

    expected_signature = signature[7:]  # Remove "sha256=" prefix

    computed = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, expected_signature)


class WebhookHandler:
    """
    GitHub webhook event handler.

    Routes webhook events to appropriate handlers based on event type and action.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the webhook handler.

        Args:
            settings: Optional settings override
        """
        self.settings = settings or get_settings()
        self._handlers: dict[str, list[Callable]] = {}

    def on(
        self,
        event_type: str,
        action: Optional[str] = None,
    ) -> Callable:
        """
        Decorator to register an event handler.

        Args:
            event_type: GitHub event type (e.g., "issues", "pull_request")
            action: Optional action filter (e.g., "opened", "closed")

        Returns:
            Decorator function
        """
        key = f"{event_type}:{action}" if action else event_type

        def decorator(func: Callable) -> Callable:
            if key not in self._handlers:
                self._handlers[key] = []
            self._handlers[key].append(func)
            return func

        return decorator

    def register(
        self,
        event_type: str,
        handler: Callable,
        action: Optional[str] = None,
    ) -> None:
        """
        Register an event handler programmatically.

        Args:
            event_type: GitHub event type
            handler: Handler function
            action: Optional action filter
        """
        key = f"{event_type}:{action}" if action else event_type
        if key not in self._handlers:
            self._handlers[key] = []
        self._handlers[key].append(handler)

    async def handle(self, event: WebhookEvent) -> list[Any]:
        """
        Handle a webhook event.

        Args:
            event: Parsed webhook event

        Returns:
            List of handler results
        """
        results = []

        # Try specific handler first (event:action)
        if event.action:
            specific_key = f"{event.event_type}:{event.action}"
            if specific_key in self._handlers:
                for handler in self._handlers[specific_key]:
                    result = await self._call_handler(handler, event)
                    results.append(result)

        # Then try general handler (event only)
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                result = await self._call_handler(handler, event)
                results.append(result)

        return results

    async def _call_handler(
        self,
        handler: Callable,
        event: WebhookEvent,
    ) -> Any:
        """
        Call a handler function.

        Args:
            handler: Handler function
            event: Webhook event

        Returns:
            Handler result
        """
        import asyncio

        if asyncio.iscoroutinefunction(handler):
            return await handler(event)
        return handler(event)

    def parse_event(
        self,
        event_type: str,
        delivery_id: str,
        payload: dict[str, Any],
    ) -> WebhookEvent:
        """
        Parse raw webhook data into a WebhookEvent.

        Args:
            event_type: X-GitHub-Event header value
            delivery_id: X-GitHub-Delivery header value
            payload: Parsed JSON payload

        Returns:
            WebhookEvent instance
        """
        return WebhookEvent(
            event_type=event_type,
            action=payload.get("action"),
            delivery_id=delivery_id,
            payload=payload,
        )
