"""
search_tool.py
Custom Tavily search tool for Agent 01 (Trend Researcher).

Why not crewai-tools.TavilySearchResults?
  crewai-tools 0.17.x imports from crewai.tools.structured_tool which was
  removed in crewai 0.80.0. Using tavily-python directly with crewai's native
  @tool decorator is cleaner and has no version conflicts.

Why @tool instead of BaseTool class?
  @tool is simpler for single-function tools. BaseTool is better when you need
  state (e.g. a client that opens a persistent connection). Tavily is stateless
  per-call, so @tool is the right choice here.
"""

import os
from crewai.tools import tool
from tavily import TavilyClient


@tool("web_search")
def web_search(query: str) -> str:
    """
    Search the web for brand aesthetic trends, visual identity examples,
    campaigns, and editorial references. Use specific, targeted queries.
    Returns a formatted summary of the top results.
    """
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    response = client.search(
        query=query,
        search_depth="advanced",  # full page content, not just snippets
        max_results=5,
        include_answer=True,      # Tavily's own AI summary — useful for synthesis
        include_raw_content=False, # saves tokens
    )

    # Format into a clean string the LLM can reason over
    parts = []

    if response.get("answer"):
        parts.append(f"SEARCH SUMMARY:\n{response['answer']}\n")

    parts.append("TOP RESULTS:")
    for i, result in enumerate(response.get("results", []), 1):
        title = result.get("title", "No title")
        url = result.get("url", "")
        content = result.get("content", "")[:400]  # cap per-result length
        parts.append(f"\n[{i}] {title}\n{url}\n{content}")

    return "\n".join(parts)


def get_search_tool():
    """Returns the web_search tool for use in agent definitions."""
    return web_search
