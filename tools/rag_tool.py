"""
tools/rag_tool.py
CrewAI @tool wrapper around the RAG retriever.
Used by Agent 02 (Design Theory Analyst).

Why a separate wrapper?
  CrewAI tools are decorated functions with a docstring the LLM reads
  to decide when and how to call the tool. The docstring here is the
  "interface contract" between the tool and Agent 02's reasoning.
  Keeping this separate from retriever.py means the RAG logic stays
  clean and the agent interface stays explicit.
"""

from crewai.tools import tool
from rag.retriever import retrieve


@tool("design_knowledge_retrieval")
def design_knowledge_retrieval(query: str) -> str:
    """
    Retrieves relevant design theory from the curated knowledge base.
    Use this to find colour psychology principles, typography pairing rules,
    spatial design guidelines, brand positioning frameworks, and aesthetic
    references for any brand keyword or visual direction query.

    Input: A specific design question or aesthetic keyword.
    Examples:
      - "colour palette principles for quiet luxury wellness"
      - "typography pairing rules for premium editorial brand"
      - "negative space and layout for minimalist packaging"
      - "what visual codes signal heritage craft authenticity"
      - "streetwear brand typography and layout patterns"

    Returns: Relevant design theory excerpts with source references.
    """
    return retrieve(query, n_results=5)


def get_rag_tool():
    """Returns the design_knowledge_retrieval tool for use in agent definitions."""
    return design_knowledge_retrieval
