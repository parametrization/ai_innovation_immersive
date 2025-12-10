"""
GitHub webhook handler for SDLC Agent Squad.

Provides a FastAPI application that handles GitHub webhook events
and routes them to appropriate agents.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from agent_squad_sdlc.config import Settings, get_settings
from agent_squad_sdlc.github_app import WebhookHandler, verify_webhook_signature
from agent_squad_sdlc.main import create_sdlc_squad, process_request

logger = logging.getLogger(__name__)


class WebhookResponse(BaseModel):
    """Webhook processing response."""

    status: str
    message: str
    event_type: Optional[str] = None
    action: Optional[str] = None


# Global state for the squad
_squad = None
_webhook_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _squad, _webhook_handler

    logger.info("Starting SDLC Agent Squad webhook server...")

    # Initialize the squad
    settings = get_settings()
    _squad = await create_sdlc_squad(settings)
    _webhook_handler = WebhookHandler(settings)

    # Register event handlers
    register_event_handlers(_webhook_handler)

    logger.info("Webhook server ready!")
    yield

    # Cleanup
    logger.info("Shutting down webhook server...")


def create_webhook_app(settings: Optional[Settings] = None) -> FastAPI:
    """
    Create the webhook FastAPI application.

    Args:
        settings: Optional settings override

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="SDLC Agent Squad Webhook",
        description="GitHub webhook handler for SDLC automation",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "squad_ready": _squad is not None}

    @app.post("/webhook", response_model=WebhookResponse)
    async def handle_webhook(
        request: Request,
        x_github_event: str = Header(..., alias="X-GitHub-Event"),
        x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
        x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
    ):
        """
        Handle incoming GitHub webhooks.

        Verifies signature and routes to appropriate agent.
        """
        # Get raw body for signature verification
        body = await request.body()

        # Verify signature
        if not verify_webhook_signature(body, x_hub_signature_256):
            logger.warning(f"Invalid webhook signature for delivery {x_github_delivery}")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse payload
        payload = await request.json()

        # Parse event
        event = _webhook_handler.parse_event(
            event_type=x_github_event,
            delivery_id=x_github_delivery,
            payload=payload,
        )

        logger.info(
            f"Received webhook: {event.event_type}:{event.action} "
            f"(delivery: {x_github_delivery})"
        )

        # Process event
        try:
            results = await _webhook_handler.handle(event)

            return WebhookResponse(
                status="processed",
                message=f"Processed {len(results)} handler(s)",
                event_type=event.event_type,
                action=event.action,
            )

        except Exception as e:
            logger.exception(f"Error processing webhook: {e}")
            return WebhookResponse(
                status="error",
                message=str(e),
                event_type=event.event_type,
                action=event.action,
            )

    return app


def register_event_handlers(handler: WebhookHandler) -> None:
    """
    Register webhook event handlers.

    Args:
        handler: WebhookHandler instance
    """

    @handler.on("issues", "opened")
    async def handle_issue_opened(event):
        """Handle new issue created."""
        issue = event.issue
        if not issue:
            return

        logger.info(f"New issue opened: #{issue['number']} - {issue['title']}")

        # Route to requirements agent
        prompt = f"""A new GitHub issue has been created:

**Issue #{issue['number']}**: {issue['title']}

**Body**:
{issue.get('body', 'No description provided.')}

**Labels**: {', '.join(l['name'] for l in issue.get('labels', [])) or 'None'}

Please analyze this issue and determine next steps:
1. Is this a feature request, bug report, or something else?
2. What clarifying questions should be asked?
3. What labels should be applied?
"""

        return await process_request(
            _squad,
            prompt,
            user_id=f"github:{event.sender.get('login', 'unknown')}",
            session_id=f"issue:{issue['number']}",
        )

    @handler.on("issues", "labeled")
    async def handle_issue_labeled(event):
        """Handle issue labeled - check if ready for stories."""
        issue = event.issue
        if not issue:
            return

        labels = [l["name"] for l in issue.get("labels", [])]

        if "ready-for-stories" in labels:
            logger.info(f"Issue #{issue['number']} marked ready for stories")

            prompt = f"""Issue #{issue['number']} has been marked as ready for user stories.

**Issue**: {issue['title']}

**Body**:
{issue.get('body', '')}

Please create well-structured user stories from this requirement.
"""

            return await process_request(
                _squad,
                prompt,
                user_id=f"github:{event.sender.get('login', 'unknown')}",
                session_id=f"issue:{issue['number']}",
            )

    @handler.on("pull_request", "opened")
    async def handle_pr_opened(event):
        """Handle new PR opened."""
        pr = event.pull_request
        if not pr:
            return

        logger.info(f"New PR opened: #{pr['number']} - {pr['title']}")

        prompt = f"""A new pull request has been opened:

**PR #{pr['number']}**: {pr['title']}

**Description**:
{pr.get('body', 'No description provided.')}

**Branch**: {pr['head']['ref']} -> {pr['base']['ref']}
**Changed Files**: {pr.get('changed_files', 'unknown')}

Please review this PR:
1. Check if it's linked to an issue with acceptance criteria
2. Create a QA test checklist
3. Identify any concerns or suggestions
"""

        return await process_request(
            _squad,
            prompt,
            user_id=f"github:{event.sender.get('login', 'unknown')}",
            session_id=f"pr:{pr['number']}",
        )

    @handler.on("pull_request", "synchronize")
    async def handle_pr_updated(event):
        """Handle PR updated with new commits."""
        pr = event.pull_request
        if not pr:
            return

        logger.info(f"PR #{pr['number']} updated with new commits")

        # Could trigger re-review here
        return None

    @handler.on("issue_comment", "created")
    async def handle_issue_comment(event):
        """Handle new comment on issue or PR."""
        comment = event.comment
        issue = event.issue
        if not comment or not issue:
            return

        # Check if comment mentions the bot or requests action
        body = comment.get("body", "").lower()
        triggers = ["@sdlc-agent", "@sdlc-bot", "/sdlc"]

        if not any(trigger in body for trigger in triggers):
            return

        logger.info(f"Agent mentioned in comment on #{issue['number']}")

        prompt = f"""You were mentioned in a comment on issue #{issue['number']}:

**Issue**: {issue['title']}

**Comment by {comment.get('user', {}).get('login', 'unknown')}**:
{comment.get('body', '')}

Please respond appropriately to this request.
"""

        return await process_request(
            _squad,
            prompt,
            user_id=f"github:{comment.get('user', {}).get('login', 'unknown')}",
            session_id=f"issue:{issue['number']}",
        )

    @handler.on("check_suite", "completed")
    async def handle_check_suite_completed(event):
        """Handle CI check suite completed."""
        payload = event.payload
        check_suite = payload.get("check_suite", {})

        if check_suite.get("conclusion") == "failure":
            # Find associated PRs
            prs = check_suite.get("pull_requests", [])
            if prs:
                pr = prs[0]
                logger.info(f"CI failed for PR #{pr['number']}")

                prompt = f"""CI checks have failed for PR #{pr['number']}.

Please analyze the check runs and provide guidance on fixing the failures.
"""

                return await process_request(
                    _squad,
                    prompt,
                    user_id="github:ci",
                    session_id=f"pr:{pr['number']}",
                )

        return None


# Create default app instance
app = create_webhook_app()
