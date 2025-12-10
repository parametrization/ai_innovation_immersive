"""
Main entry point for Agent Squad SDLC automation.

Sets up the supervisor agent and team for SDLC workflow orchestration.
"""

import asyncio
import logging
from typing import Optional

from agent_squad import SupervisorAgent
from agent_squad.agents import AnthropicAgent, AnthropicAgentOptions
from agent_squad.storage import InMemoryStorage

from agent_squad_sdlc.agents import (
    create_implementation_agent,
    create_issue_resolver_agent,
    create_qa_agent,
    create_requirements_agent,
    create_story_writer_agent,
)
from agent_squad_sdlc.config import Settings, StorageType, get_settings
from agent_squad_sdlc.github_app import GitHubApp
from agent_squad_sdlc.tools import GitHubTools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


SUPERVISOR_PROMPT = """You are the SDLC Supervisor Agent coordinating a team of specialized agents for software development lifecycle automation.

## Your Team
You have access to these specialized agents:

1. **RequirementsAgent** - Handles requirements intake from GitHub issues
   - Use when: New issues are created, requirements need clarification

2. **StoryWriterAgent** - Creates user stories from requirements
   - Use when: Requirements are clear, need to create actionable stories

3. **ImplementationAgent** - Suggests code implementations
   - Use when: Stories need implementation guidance, code suggestions needed

4. **QAAgent** - Handles testing and quality assurance
   - Use when: PRs need testing, acceptance criteria verification needed

5. **IssueResolverAgent** - Triages and resolves bugs
   - Use when: Bug reports need analysis, issues need root cause investigation

## Workflow
For typical SDLC tasks, follow this flow:

1. **New Feature Request**:
   Requirements → Story Writing → Implementation → QA

2. **Bug Report**:
   Issue Resolver → (if fix needed) Implementation → QA

3. **PR Review**:
   QA → (if issues found) Implementation suggestions

## Guidelines
- Route tasks to the most appropriate agent
- Maintain context across the workflow
- Escalate blockers or unclear situations
- Keep stakeholders informed via GitHub comments
- Prioritize based on labels and urgency

## Response Format
When coordinating, explain:
1. Which agent you're engaging and why
2. What you're asking them to do
3. Expected next steps
"""


def create_supervisor_agent(
    settings: Optional[Settings] = None,
) -> AnthropicAgent:
    """
    Create the SDLC supervisor agent.

    Args:
        settings: Optional settings override

    Returns:
        Configured supervisor AnthropicAgent
    """
    if settings is None:
        settings = get_settings()

    return AnthropicAgent(
        AnthropicAgentOptions(
            name="SDLCSupervisor",
            description=(
                "SDLC workflow supervisor that coordinates specialized agents "
                "for requirements, story writing, implementation, QA, and issue resolution."
            ),
            api_key=settings.anthropic_api_key.get_secret_value(),
            model_id=settings.claude_model_id,
            streaming=True,
            save_chat=True,
            custom_system_prompt={
                "template": SUPERVISOR_PROMPT,
                "variables": {
                    "REPO_OWNER": settings.github_owner,
                    "REPO_NAME": settings.github_repo,
                },
            },
        )
    )


def get_storage(settings: Optional[Settings] = None):
    """
    Get storage instance based on configuration.

    Args:
        settings: Optional settings override

    Returns:
        Storage instance
    """
    if settings is None:
        settings = get_settings()

    if settings.storage_type == StorageType.MEMORY:
        return InMemoryStorage()

    # DynamoDB storage would be configured here
    # from agent_squad.storage import DynamoDBStorage
    # return DynamoDBStorage(table_name=settings.dynamodb_table_name)

    return InMemoryStorage()


async def create_sdlc_squad(
    settings: Optional[Settings] = None,
) -> SupervisorAgent:
    """
    Create the full SDLC agent squad with supervisor.

    Args:
        settings: Optional settings override

    Returns:
        Configured SupervisorAgent with team
    """
    if settings is None:
        settings = get_settings()

    logger.info("Initializing SDLC Agent Squad...")

    # Initialize GitHub App and tools
    github_app = GitHubApp(settings)
    github_tools = GitHubTools(github_app, settings)

    # Verify GitHub App installation
    try:
        installation = await github_app.verify_app_installation()
        logger.info(f"GitHub App installed on: {installation.get('account', {}).get('login')}")
    except Exception as e:
        logger.warning(f"Could not verify GitHub App installation: {e}")

    # Create team agents
    logger.info("Creating team agents...")

    requirements_agent = create_requirements_agent(github_tools, settings)
    story_writer_agent = create_story_writer_agent(github_tools, settings)
    implementation_agent = create_implementation_agent(github_tools, settings)
    qa_agent = create_qa_agent(github_tools, settings)
    issue_resolver_agent = create_issue_resolver_agent(github_tools, settings)

    # Create supervisor
    supervisor_lead = create_supervisor_agent(settings)

    # Create the squad
    storage = get_storage(settings)

    supervisor = SupervisorAgent(
        lead_agent=supervisor_lead,
        team=[
            requirements_agent,
            story_writer_agent,
            implementation_agent,
            qa_agent,
            issue_resolver_agent,
        ],
        storage=storage,
        trace=settings.debug,
    )

    logger.info("SDLC Agent Squad initialized successfully!")
    return supervisor


async def process_request(
    supervisor: SupervisorAgent,
    user_input: str,
    user_id: str = "default_user",
    session_id: str = "default_session",
) -> str:
    """
    Process a request through the SDLC squad.

    Args:
        supervisor: The supervisor agent
        user_input: User's request
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Response text
    """
    logger.info(f"Processing request from {user_id}: {user_input[:100]}...")

    response = await supervisor.process_request(
        user_input=user_input,
        user_id=user_id,
        session_id=session_id,
    )

    if hasattr(response, "content"):
        return response.content

    return str(response)


async def main():
    """Main entry point for CLI usage."""
    import sys

    settings = get_settings()

    # Create the squad
    supervisor = await create_sdlc_squad(settings)

    print("SDLC Agent Squad is ready!")
    print("Type your requests (Ctrl+C to exit):\n")

    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            response = await process_request(supervisor, user_input)
            print(f"\nAgent: {response}\n")

    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
