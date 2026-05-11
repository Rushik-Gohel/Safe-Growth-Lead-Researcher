"""Agent module for LangGraph workflow."""

from .workflow import LeadResearchAgent, AgentState, lead_research_agent
from .prompts import SYSTEM_PROMPT, RESEARCH_PROMPT, EMAIL_GENERATION_PROMPT

__all__ = [
    "LeadResearchAgent",
    "AgentState",
    "lead_research_agent",
    "SYSTEM_PROMPT",
    "RESEARCH_PROMPT",
    "EMAIL_GENERATION_PROMPT",
]


