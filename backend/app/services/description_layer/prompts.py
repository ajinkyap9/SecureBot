from langchain_core.prompts import ChatPromptTemplate

# Sample prompt template used for SOC-grade description generation.
ANALYST_DESCRIPTION_SYSTEM_PROMPT = """You are a senior SOC analyst assistant.
Use ONLY the evidence in the provided context.
Never invent IOC details, malware family names, CVEs, threat actor names, or infrastructure.
Do not change numeric scores or labels from the payload.
Write exactly 4 to 6 sentences in professional SOC tone.
The description must include:
1) why the case is risky,
2) strongest risk drivers,
3) reducing/moderating signals if present,
4) likely attack type and stage,
5) clear analyst next step.
"""

ANALYST_DESCRIPTION_HUMAN_PROMPT = """Incident evidence (JSON):
{prompt_context_json}

Return a structured response with one field: generated_description.
"""


def build_description_prompt() -> ChatPromptTemplate:
    """Create the chat prompt used for structured LLM invocation."""

    return ChatPromptTemplate.from_messages(
        [
            ("system", ANALYST_DESCRIPTION_SYSTEM_PROMPT),
            ("human", ANALYST_DESCRIPTION_HUMAN_PROMPT),
        ]
    )
