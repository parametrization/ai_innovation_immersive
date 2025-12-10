"""
Agent system prompts.

Contains specialized prompts for each SDLC agent.
"""

from agent_squad_sdlc.prompts.implementation_prompt import IMPLEMENTATION_AGENT_PROMPT
from agent_squad_sdlc.prompts.issue_resolver_prompt import ISSUE_RESOLVER_AGENT_PROMPT
from agent_squad_sdlc.prompts.qa_prompt import QA_AGENT_PROMPT
from agent_squad_sdlc.prompts.requirements_prompt import REQUIREMENTS_AGENT_PROMPT
from agent_squad_sdlc.prompts.story_prompt import STORY_WRITER_AGENT_PROMPT

__all__ = [
    "REQUIREMENTS_AGENT_PROMPT",
    "STORY_WRITER_AGENT_PROMPT",
    "IMPLEMENTATION_AGENT_PROMPT",
    "QA_AGENT_PROMPT",
    "ISSUE_RESOLVER_AGENT_PROMPT",
]
