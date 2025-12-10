"""
CLI handler for SDLC Agent Squad.

Provides a command-line interface for interacting with the agent squad.
"""

import asyncio
import logging
import sys
from typing import Optional

import click

from agent_squad_sdlc.config import Settings, get_settings
from agent_squad_sdlc.main import create_sdlc_squad, process_request

logger = logging.getLogger(__name__)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, debug: bool):
    """SDLC Agent Squad CLI - Automate your development workflow."""
    ctx.ensure_object(dict)

    # Configure logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    ctx.obj["debug"] = debug


@cli.command()
@click.pass_context
def interactive(ctx: click.Context):
    """Start an interactive session with the agent squad."""

    async def run_interactive():
        settings = get_settings()
        click.echo("Initializing SDLC Agent Squad...")

        try:
            supervisor = await create_sdlc_squad(settings)
        except Exception as e:
            click.echo(f"Error initializing squad: {e}", err=True)
            return

        click.echo("\nSDLC Agent Squad is ready!")
        click.echo("Type your requests (Ctrl+C to exit):\n")

        session_id = f"cli-{asyncio.get_event_loop().time()}"

        try:
            while True:
                try:
                    user_input = click.prompt("You", prompt_suffix=": ")
                except click.Abort:
                    break

                if not user_input.strip():
                    continue

                if user_input.lower() in ("exit", "quit", "q"):
                    break

                try:
                    response = await process_request(
                        supervisor,
                        user_input,
                        user_id="cli-user",
                        session_id=session_id,
                    )
                    click.echo(f"\nAgent: {response}\n")
                except Exception as e:
                    click.echo(f"\nError: {e}\n", err=True)

        except KeyboardInterrupt:
            pass

        click.echo("\nGoodbye!")

    asyncio.run(run_interactive())


@cli.command()
@click.argument("message")
@click.option("--user-id", default="cli-user", help="User identifier")
@click.option("--session-id", default=None, help="Session identifier")
@click.pass_context
def ask(ctx: click.Context, message: str, user_id: str, session_id: Optional[str]):
    """Send a single message to the agent squad."""

    async def run_ask():
        settings = get_settings()

        try:
            supervisor = await create_sdlc_squad(settings)
        except Exception as e:
            click.echo(f"Error initializing squad: {e}", err=True)
            return

        sid = session_id or f"cli-{asyncio.get_event_loop().time()}"

        try:
            response = await process_request(
                supervisor,
                message,
                user_id=user_id,
                session_id=sid,
            )
            click.echo(response)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)

    asyncio.run(run_ask())


@cli.command()
@click.argument("issue_number", type=int)
@click.pass_context
def analyze_issue(ctx: click.Context, issue_number: int):
    """Analyze a GitHub issue."""

    async def run_analyze():
        settings = get_settings()

        try:
            supervisor = await create_sdlc_squad(settings)
        except Exception as e:
            click.echo(f"Error initializing squad: {e}", err=True)
            return

        message = f"""Please analyze GitHub issue #{issue_number}.

1. Retrieve the issue details
2. Review any comments
3. Search for related issues
4. Provide analysis and recommended next steps
"""

        try:
            response = await process_request(
                supervisor,
                message,
                user_id="cli-user",
                session_id=f"issue-{issue_number}",
            )
            click.echo(response)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)

    asyncio.run(run_analyze())


@cli.command()
@click.argument("pr_number", type=int)
@click.pass_context
def review_pr(ctx: click.Context, pr_number: int):
    """Review a GitHub pull request."""

    async def run_review():
        settings = get_settings()

        try:
            supervisor = await create_sdlc_squad(settings)
        except Exception as e:
            click.echo(f"Error initializing squad: {e}", err=True)
            return

        message = f"""Please review GitHub PR #{pr_number}.

1. Get the PR details and changed files
2. Find the linked issue for acceptance criteria
3. Create a QA test checklist
4. Review the changes and provide feedback
"""

        try:
            response = await process_request(
                supervisor,
                message,
                user_id="cli-user",
                session_id=f"pr-{pr_number}",
            )
            click.echo(response)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)

    asyncio.run(run_review())


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8080, type=int, help="Server port")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int):
    """Start the webhook server."""
    import uvicorn

    from agent_squad_sdlc.handlers.webhook_handler import app

    click.echo(f"Starting webhook server on {host}:{port}...")
    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.pass_context
def verify(ctx: click.Context):
    """Verify configuration and GitHub App setup."""

    async def run_verify():
        click.echo("Verifying configuration...\n")

        try:
            settings = get_settings()
            click.echo(f"  Repository: {settings.github_repo_full_name}")
            click.echo(f"  Environment: {settings.environment.value}")
            click.echo(f"  Storage: {settings.storage_type.value}")
            click.echo(f"  Claude Model: {settings.claude_model_id}")
            click.echo("  Anthropic API Key: ***configured***")
            click.echo("  GitHub App ID: " + settings.github_app_id)
            click.echo("  GitHub Webhook Secret: ***configured***")
        except Exception as e:
            click.echo(f"\nConfiguration Error: {e}", err=True)
            return

        click.echo("\nVerifying GitHub App installation...")

        try:
            from agent_squad_sdlc.github_app import GitHubApp

            app = GitHubApp(settings)
            installation = await app.verify_app_installation()
            click.echo(f"  Installation ID: {installation.get('id')}")
            click.echo(f"  Account: {installation.get('account', {}).get('login')}")
            click.echo(f"  Permissions: {list(installation.get('permissions', {}).keys())}")
            await app.close()
            click.echo("\nGitHub App verification successful!")
        except Exception as e:
            click.echo(f"\nGitHub App Error: {e}", err=True)

    asyncio.run(run_verify())


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
