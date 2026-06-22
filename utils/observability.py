"""
utils/observability.py
LangSmith observability setup for the Visual Direction Agent pipeline.

Call setup_langsmith() once at the start of crew.py before any agent runs.
LangSmith auto-traces all LLM calls when LANGCHAIN_TRACING_V2=true and
LANGCHAIN_API_KEY are set in the environment.

What gets traced:
  - Every LLM call across all 5 agents (inputs, outputs, token counts, latency)
  - Tool calls (Tavily searches, RAG retrievals, image generation)
  - The full crew execution graph

View traces at: https://smith.langchain.com
"""

import os
from dotenv import load_dotenv

load_dotenv()


def setup_langsmith() -> bool:
    """
    Activates LangSmith tracing if credentials are configured.
    Returns True if tracing is active, False otherwise.

    Safe to call even if LangSmith is not configured — will silently skip.
    """
    api_key = os.getenv("LANGCHAIN_API_KEY")
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "false").lower()
    project = os.getenv("LANGCHAIN_PROJECT", "visual-direction-agent")

    if not api_key:
        print("[OBSERVABILITY] LangSmith not configured — LANGCHAIN_API_KEY not set")
        return False

    if tracing != "true":
        print("[OBSERVABILITY] LangSmith tracing disabled — set LANGCHAIN_TRACING_V2=true to enable")
        return False

    # Set explicitly in case load_dotenv hasn't propagated to os.environ yet
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project

    # NOTE: We do NOT add litellm's "langsmith" success_callback here. litellm's
    # LangsmithLogger.__init__ calls asyncio.create_task(), which needs a running
    # event loop — but CrewAI runs litellm in sync threads, so it raises
    # "no running event loop" on every call and never actually traces (litellm
    # issue #6862). The result was traceback spam with zero traces. LLM-level
    # LangSmith tracing through litellm is not viable in this sync CrewAI setup;
    # tool spans still trace, and provenance is covered by utils/llm.served_models().

    try:
        # Verify the key is valid by initialising the client
        from langsmith import Client
        client = Client(api_key=api_key)
        # Light check — list projects (quick, no heavy data pull)
        _ = client.read_project(project_name=project, include_stats=False)
        print(f"[OBSERVABILITY] LangSmith active → project: '{project}'")
        print(f"                View traces: https://smith.langchain.com/projects/{project}")
        return True
    except Exception:
        # Project may not exist yet — that's fine, it auto-creates on first trace
        print(f"[OBSERVABILITY] LangSmith active → project: '{project}' (will be created on first run)")
        return True


def get_langsmith_run_url() -> str | None:
    """
    Returns the LangSmith URL for the most recent run in the project.

    Queries the LangSmith API after a short delay to account for async
    trace ingestion. Falls back to the project-level URL on any failure.
    """
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "visual-direction-agent")
    fallback = f"https://smith.langchain.com"

    if not api_key:
        return None

    try:
        import time as _time
        _time.sleep(3)  # allow async trace ingestion to complete

        from langsmith import Client
        client = Client(api_key=api_key)

        runs = list(client.list_runs(
            project_name=project,
            limit=1,
            run_type="chain",
            order="desc",
        ))

        if runs:
            run_id = str(runs[0].id)
            url = f"https://smith.langchain.com/public/{run_id}/r"
            print(f"[OBSERVABILITY] Run trace URL: {url}")
            return url

    except Exception as e:
        print(f"[OBSERVABILITY] Could not fetch run URL ({e}) — using project fallback")

    return fallback
