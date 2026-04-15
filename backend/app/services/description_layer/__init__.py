"""LangChain + LangGraph description enrichment layer.

This package consumes finalized risk pipeline JSON and enriches analyst-facing
narrative output without changing deterministic scoring fields.
"""

from .description_service import AnalystDescriptionService, LLMConfig, create_chat_model
from .schemas import DescriptionPipelineOutput, IncidentPayload

__all__ = [
    "AnalystDescriptionService",
    "LLMConfig",
    "create_chat_model",
    "DescriptionPipelineOutput",
    "IncidentPayload",
]
