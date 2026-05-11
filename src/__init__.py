"""Safe-Growth Lead Researcher - AI-powered lead research and email generation."""

__version__ = "1.0.0"
__author__ = "Safe-Growth Team"
__description__ = "AI-powered lead research agent with LangGraph, Gemini, and production-grade features"

from .core import settings
from .agent import lead_research_agent
from .security import guardrails

__all__ = [
    "settings",
    "lead_research_agent",
    "guardrails",
]


