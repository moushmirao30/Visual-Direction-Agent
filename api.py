"""
api.py
FastAPI layer for the Visual Direction Research Agent.

Endpoints:
  POST /generate              — kick off pipeline, return job_id immediately
  GET  /status/{job_id}       — poll for progress and final result
  GET  /moodboard/{filename}  — serve generated PNG images
  GET  /health                — liveness check

Why background task + polling (not synchronous)?
  The full pipeline takes ~275s. A synchronous POST would hold the HTTP
  connection open the entire time, which browsers and proxies will kill
  before the response arrives. Background task + job store lets Streamlit
  poll every few seconds and show per-agent progress while the pipeline runs.

Why serve moodboard images here?
  Agent 05 saves PNGs to moodboard_cache/ as local Windows paths. Streamlit
  can't display local file:// paths directly — it needs HTTP URLs. This
  endpoint converts file paths → HTTP URLs transparently.
"""

import os
import uuid
import asyncio
import traceback
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Visual Direction Research Agent",
    description=(
        "5-agent pipeline: trend research + design theory RAG "
        "→ visual direction report + moodboard"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Streamlit runs on a different port
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool — crew.py is synchronous (blocking), run it in a thread
# to avoid blocking FastAPI's async event loop
_executor = ThreadPoolExecutor(max_workers=2)

# In-memory job store  {job_id: dict}
# Sufficient for a single-user demo; no persistence needed
_jobs: dict[str, dict] = {}

# Moodboard cache directory (resolved relative to this file)
MOODBOARD_DIR = Path(__file__).parent / "moodboard_cache"


# ── Request / response models ─────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    keyword: str
    use_cache: bool = True
    skip_moodboard: bool = False


class GenerateResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: str           # queued | running | complete | error
    current_step: str
    started_at: str | None
    finished_at: str | None
    result: dict | None   # populated when status == "complete"
    error: str | None     # populated when status == "error"


# ── Job store helpers ─────────────────────────────────────────────────────────

def _new_job(keyword: str) -> str:
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "job_id":       job_id,
        "keyword":      keyword,
        "status":       "queued",
        "current_step": "Queued",
        "started_at":   None,
        "finished_at":  None,
        "result":       None,
        "error":        None,
    }
    return job_id


def _update_job(job_id: str, **kwargs) -> None:
    if job_id in _jobs:
        _jobs[job_id].update(kwargs)


def _serialise_result(raw: dict) -> dict:
    """
    Convert the pipeline result dict into a JSON-serialisable form.

    - VisualDirectionReport (Pydantic) → dict via model_dump()
    - moodboard_panels: replace local file paths with /moodboard/{filename} URLs
    """
    report = raw.get("report")
    panels = raw.get("moodboard_panels", [])

    api_panels = []
    for p in panels:
        url = p.get("url", "")
        # Normalise Windows backslashes before extracting filename
        # (Path() on Linux doesn't recognise \ as a separator)
        filename = Path(url.replace("\\", "/")).name if url else ""
        api_panels.append({
            "panel":    p.get("panel", ""),
            "prompt":   p.get("prompt", ""),
            "url":      f"/moodboard/{filename}" if filename else "",
            "filename": filename,
        })

    return {
        "keyword":          raw.get("keyword", ""),
        "report":           report.model_dump() if report else None,
        "formatted_report": raw.get("formatted_report", ""),
        "moodboard_panels": api_panels,
        "langsmith_url":    raw.get("langsmith_url"),
        "served_models":    raw.get("served_models", []),
        "timings":          raw.get("timings", {}),
    }


# ── Pipeline runner (runs in thread pool) ─────────────────────────────────────

def _run_pipeline(job_id: str, keyword: str, use_cache: bool, skip_moodboard: bool) -> None:
    """
    Runs the full pipeline synchronously in a background thread.
    Updates the job store at each stage.

    Uses a monkey-patch on crew._step to intercept per-agent progress
    without modifying crew.py itself.
    """
    _update_job(job_id,
        status="running",
        started_at=datetime.utcnow().isoformat(),
        current_step="Starting pipeline",
    )

    from utils.run_logger import start_run_log, stop_run_log
    _log = start_run_log(keyword)
    try:
        from crew import run_visual_direction_pipeline
        import crew as crew_module

        original_step = crew_module._step

        def _tracked_step(num: str, name: str, detail: str) -> None:
            original_step(num, name, detail)
            _update_job(job_id, current_step=f"Agent {num} — {name}")

        crew_module._step = _tracked_step

        try:
            raw_result = run_visual_direction_pipeline(
                keyword,
                use_cache=use_cache,
                skip_moodboard=skip_moodboard,
            )
        finally:
            crew_module._step = original_step  # always restore

        _update_job(job_id,
            status="complete",
            current_step="Complete",
            finished_at=datetime.utcnow().isoformat(),
            result=_serialise_result(raw_result),
        )

    except ValueError as e:
        _update_job(job_id,
            status="error",
            current_step="Failed — input validation",
            finished_at=datetime.utcnow().isoformat(),
            error=str(e),
        )
    except RuntimeError as e:
        _update_job(job_id,
            status="error",
            current_step="Failed — schema validation",
            finished_at=datetime.utcnow().isoformat(),
            error=str(e),
        )
    except Exception as e:
        _update_job(job_id,
            status="error",
            current_step="Failed — unexpected error",
            finished_at=datetime.utcnow().isoformat(),
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
        )
    finally:
        stop_run_log(_log)


# ── (Removed) FLUX warm-up ────────────────────────────────────────────────────
# The HuggingFace FLUX warm-up was removed Jun 23. Image generation moved to
# Cloudflare Workers AI (a hosted API with no cold start), and the HF endpoint now
# returns 402, so the warm-up was both useless and a 402-warning on every boot.
# See HANDOFF §6.


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/generate", response_model=GenerateResponse, status_code=202)
async def generate(request: GenerateRequest):
    """
    Starts the visual direction pipeline for the given aesthetic keyword.

    Returns immediately with a job_id. Poll GET /status/{job_id} for progress.

    Options:
    - use_cache=true  (default): reuses cached Agent 01 + 02 outputs (24hr TTL)
    - use_cache=false: forces fresh agent runs
    - skip_moodboard=true: skips Agent 05 image generation (~220s faster)
    """
    keyword = request.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=422, detail="keyword cannot be empty")

    job_id = _new_job(keyword)

    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _run_pipeline,
        job_id,
        keyword,
        request.use_cache,
        request.skip_moodboard,
    )

    return GenerateResponse(
        job_id=job_id,
        status="queued",
        message=f"Pipeline started for '{keyword}'. Poll GET /status/{job_id} for progress.",
    )


@app.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """
    Returns the current state of a pipeline job.

    status values:
      queued   — job is in the queue, not started yet
      running  — pipeline is running; current_step shows which agent is active
      complete — all agents finished; result contains the full report + panel URLs
      error    — pipeline failed; error contains the details
    """
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return StatusResponse(**job)


@app.get("/moodboard/{filename}")
async def serve_moodboard_image(filename: str):
    """
    Serves a generated moodboard PNG via HTTP.

    Agent 05 saves PNGs to moodboard_cache/ as local file paths.
    This endpoint exposes them as HTTP URLs so Streamlit can render
    them with st.image() — local file:// paths don't work in Streamlit.
    """
    # Sanitise — only allow simple filenames with .png extension
    if not filename.endswith(".png") or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = MOODBOARD_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Image '{filename}' not found")

    return FileResponse(path, media_type="image/png")


@app.get("/")
async def root():
    """Root route — uptime check target."""
    return {"status": "ok", "service": "visual-direction-agent"}


@app.get("/health")
async def health():
    """Liveness check."""
    active = sum(1 for j in _jobs.values() if j["status"] == "running")
    return {
        "status":     "ok",
        "active_jobs": active,
        "total_jobs":  len(_jobs),
    }


@app.get("/jobs")
async def list_jobs():
    """Lists all jobs in the current session (debugging / demo use)."""
    return [
        {
            "job_id":       j["job_id"],
            "keyword":      j["keyword"],
            "status":       j["status"],
            "current_step": j["current_step"],
            "started_at":   j["started_at"],
            "finished_at":  j["finished_at"],
        }
        for j in _jobs.values()
    ]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,   # reload=True breaks the thread pool
        log_level="info",
    )
