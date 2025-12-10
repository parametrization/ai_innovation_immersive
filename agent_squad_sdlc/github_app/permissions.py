"""
GitHub App permissions configuration.

Defines the required permissions for the SDLC automation app.
"""

# Required permissions for the GitHub App
REQUIRED_PERMISSIONS = {
    # Repository permissions
    "contents": "write",  # Read/write repository contents
    "issues": "write",  # Read/write issues
    "pull_requests": "write",  # Read/write pull requests
    "metadata": "read",  # Read repository metadata

    # Optional but recommended
    "checks": "read",  # Read check runs and suites
    "actions": "read",  # Read GitHub Actions workflows
}

# Webhook events to subscribe to
WEBHOOK_EVENTS = [
    "issues",  # Issue events
    "issue_comment",  # Issue comment events
    "pull_request",  # PR events
    "pull_request_review",  # PR review events
    "pull_request_review_comment",  # PR review comment events
    "check_run",  # CI check run events
    "check_suite",  # CI check suite events
]

# App manifest for creating the GitHub App
# Use this when setting up a new GitHub App
APP_MANIFEST = {
    "name": "SDLC Automation Agent",
    "url": "https://github.com/your-org/sdlc-automation",
    "hook_attributes": {
        "url": "https://your-webhook-url.com/webhook",
        "active": True,
    },
    "redirect_url": "https://your-app.com/callback",
    "callback_urls": [
        "https://your-app.com/callback",
    ],
    "public": False,
    "default_permissions": REQUIRED_PERMISSIONS,
    "default_events": WEBHOOK_EVENTS,
}


def validate_installation_permissions(permissions: dict[str, str]) -> list[str]:
    """
    Validate that an installation has required permissions.

    Args:
        permissions: Permissions dict from installation

    Returns:
        List of missing or insufficient permissions
    """
    issues = []

    for permission, required_level in REQUIRED_PERMISSIONS.items():
        granted = permissions.get(permission)

        if not granted:
            issues.append(f"Missing permission: {permission}")
        elif required_level == "write" and granted == "read":
            issues.append(f"Insufficient permission: {permission} (need write, have read)")

    return issues


def get_permission_markdown() -> str:
    """
    Generate markdown documentation for required permissions.

    Returns:
        Markdown string documenting permissions
    """
    lines = [
        "## Required GitHub App Permissions",
        "",
        "The SDLC Automation Agent requires the following permissions:",
        "",
        "### Repository Permissions",
        "",
        "| Permission | Access | Purpose |",
        "|------------|--------|---------|",
        "| Contents | Read & Write | Read repository files, create branches |",
        "| Issues | Read & Write | Create/update issues, add comments |",
        "| Pull Requests | Read & Write | Create PRs, add reviews and comments |",
        "| Metadata | Read | Access repository metadata |",
        "| Checks | Read | View CI/CD status |",
        "| Actions | Read | View workflow runs |",
        "",
        "### Webhook Events",
        "",
        "Subscribe to these events:",
        "",
    ]

    for event in WEBHOOK_EVENTS:
        lines.append(f"- `{event}`")

    return "\n".join(lines)
