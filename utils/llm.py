"""
utils/llm.py
One place that decides how every agent's LLM is built — with an optional NVIDIA NIM
fallback.

Why this exists:
  Mid eval-run the Anthropic API hit a credit-balance error and the last case died.
  This makes the pipeline resilient: if an Anthropic call fails (credits, 5xx,
  overload, network), LiteLLM transparently retries the SAME request on a free
  NVIDIA NIM model instead of crashing the run.

How it works (no monkey-patching, version-safe for crewai 0.80.0):
  crewai's LLM.call() forwards **kwargs into litellm.completion(). LiteLLM's
  completion() natively accepts `fallbacks=[...]` and retries the same messages on
  the next model when the primary raises. So we just hand crewai an LLM built with
  that one extra kwarg.

Zero-change guarantee:
  If NO NVIDIA key is set, build_llm() returns the plain model STRING — byte-for-byte
  the previous behaviour. The fallback only activates when a key is present, so the
  demo path is untouched unless you opt in.

HONEST CAVEAT — fallback is for AVAILABILITY, not quality parity:
  The NVIDIA fallback models (open Llama/Qwen-class) are NOT Claude. If a fallback
  fires, that agent's output quality will differ from the Claude-validated eval
  scores. The point is "the run completes" rather than "the run crashes" — not
  "identical quality". Agent 04's JSON schema + retry guardrail still validate
  whatever the fallback produces. For a graded eval, run on Anthropic; treat the
  fallback as insurance for a live demo.

Setup:
  Put a free NVIDIA key in .env:  NVIDIA_API_KEY=nvapi-xxxx   (or NVIDIA_NIM_API_KEY)
  Optionally override the fallback models:
    NVIDIA_FALLBACK_FAST   (default nvidia_nim/meta/llama-3.3-70b-instruct)
    NVIDIA_FALLBACK_STRONG (default nvidia_nim/meta/llama-3.3-70b-instruct)

FREE-PRIMARY MODE (run with NO Anthropic credit spend):
  Set FREE_PRIMARY in .env to flip a free provider to PRIMARY so `anthropic/` is
  never called. The other free provider becomes the fallback (only if its key is set).
    FREE_PRIMARY=nvidia   -> primary = the validated NVIDIA NIM 70B (reuses NVIDIA_API_KEY)
    FREE_PRIMARY=groq     -> primary = Groq 70B (needs GROQ_API_KEY; daily-reset free tier)
  Unset (default) -> original Anthropic-primary behaviour, untouched. Use that for
  graded evals; use FREE_PRIMARY for the no-top-up demo path. Agent 04's JSON schema
  guardrail still validates whatever the free model produces, so keep Agent 04 on a
  70B-class model (both defaults are 70B).
  Optional Groq model overrides: GROQ_FAST, GROQ_STRONG.
"""

import os
from typing import Union

# Tier → default NVIDIA NIM fallback model. Haiku-class agents (research/retrieval/
# prompt-craft) fall back to a fast 70B; Sonnet-class agents (synthesis/report) fall
# back to a stronger model. Both overridable via env.
_FAST_FALLBACK = os.getenv("NVIDIA_FALLBACK_FAST", "nvidia_nim/meta/llama-3.3-70b-instruct")
# NOTE: meta/llama-3.1-405b-instruct was retired from NVIDIA NIM and now 404s, which
# silently killed strong-tier failover (Agents 03/04). Default to the 70B that is
# verified working in live runs. Override via NVIDIA_FALLBACK_STRONG if you have a
# larger model enabled on your NVIDIA account.
_STRONG_FALLBACK = os.getenv("NVIDIA_FALLBACK_STRONG", "nvidia_nim/meta/llama-3.3-70b-instruct")

# Free-primary mode: opt-in via FREE_PRIMARY ("nvidia" | "groq"). Empty => Anthropic
# primary (unchanged default). Groq is a separate free provider (daily-reset tier);
# its keys are read by litellm from GROQ_API_KEY. Both default models are 70B so
# Agent 04's schema guardrail has enough model to hold the JSON.
_FREE_PRIMARY = os.getenv("FREE_PRIMARY", "").strip().lower()
_GROQ_FAST = os.getenv("GROQ_FAST", "groq/llama-3.3-70b-versatile")
_GROQ_STRONG = os.getenv("GROQ_STRONG", "groq/llama-3.3-70b-versatile")


# ── Served-model capture (provenance stamp) ─────────────────────────────────
# A litellm success callback records which model ACTUALLY answered each call —
# including after a fallback fires. This is the only reliable answer to "which
# provider ran this", because the CONFIGURED model != the SERVED model when a
# fallback kicks in. crew.py resets this per run and stamps it into the report.
# (Note: LangSmith does not capture these litellm calls, so this is the source
# of truth for provenance.)
_SERVED_MODELS: list[str] = []
# Deterministic provenance: the primary model build_llm() hands each agent. In this
# sync-CrewAI setup the litellm success callback does not reliably fire (it logged
# "unknown"), so this is the source of truth when _SERVED_MODELS stays empty. It is
# the CONFIGURED primary, so it won't reflect a post-fallback swap — served_models()
# tags it "(configured)" to make that explicit. Callback wins when it does fire.
_CONFIGURED_MODELS: list[str] = []
_CALLBACK_REGISTERED = False


def _record_served_model(response_obj, kwargs) -> None:
    """Append the actually-served model (deduped, in order). Sync + async safe."""
    try:
        model = getattr(response_obj, "model", None)
        if model is None and isinstance(response_obj, dict):
            model = response_obj.get("model")
        provider = (kwargs or {}).get("custom_llm_provider")
        # litellm sometimes drops the provider prefix on the response model
        # (e.g. groq returns "llama-3.3-70b-versatile"). Re-attach it for clarity.
        if model and provider and "/" not in model:
            model = f"{provider}/{model}"
        if model and model not in _SERVED_MODELS:
            _SERVED_MODELS.append(model)
    except Exception:
        pass  # observability must NEVER break a run


def _record_configured(model: str) -> None:
    """
    Record the primary model string build_llm() handed an agent (deduped, in order).
    Deterministic — no litellm dependency — so provenance is never "unknown" even when
    the success callback doesn't fire. served_models() prefers callback-confirmed
    models and falls back to these (tagged "(configured)") when the callback is silent.
    """
    if model and model not in _CONFIGURED_MODELS:
        _CONFIGURED_MODELS.append(model)


def _ensure_callback_registered() -> None:
    """
    Register a litellm CustomLogger that captures the served model on BOTH the sync
    and async success paths. CrewAI's fallback path uses litellm.acompletion (async),
    so a plain sync success_callback function is not reliably invoked — a CustomLogger
    with async_log_success_event is. (The first version registered only a sync fn and
    logged 'Served by: unknown' for exactly this reason.) CustomLogger.__init__ does no
    event-loop work, so it is safe inside CrewAI's sync threads.
    """
    global _CALLBACK_REGISTERED
    if _CALLBACK_REGISTERED:
        return
    try:
        import litellm
        from litellm.integrations.custom_logger import CustomLogger

        class _ServedModelLogger(CustomLogger):
            def log_success_event(self, kwargs, response_obj, start_time, end_time):
                _record_served_model(response_obj, kwargs)

            async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
                _record_served_model(response_obj, kwargs)

        if not any(type(c).__name__ == "_ServedModelLogger" for c in (litellm.callbacks or [])):
            litellm.callbacks = list(litellm.callbacks or []) + [_ServedModelLogger()]
        _CALLBACK_REGISTERED = True
    except Exception:
        pass  # litellm not importable in some tooling contexts — stamp stays empty


def served_models() -> list[str]:
    """
    Models that ran this pipeline, in call order.

    Prefers litellm-callback-confirmed served models (accurate even after a fallback
    fires). When the callback didn't fire — the common case in CrewAI's sync threads —
    falls back to the configured primaries captured in build_llm(), each tagged
    "(configured)" so a confirmed serve is never confused with a configured intent.
    Empty only if no agent LLM was built this run (e.g. every agent was a cache hit).
    """
    if _SERVED_MODELS:
        return list(_SERVED_MODELS)
    return [f"{m} (configured)" for m in _CONFIGURED_MODELS]


def reset_served_models() -> None:
    """Clear captured + configured models — call at pipeline start so each run is isolated."""
    _SERVED_MODELS.clear()
    _CONFIGURED_MODELS.clear()


def _nvidia_key() -> str | None:
    """Accept either env name; mirror into NVIDIA_NIM_API_KEY so litellm resolves it."""
    key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
    if key and not os.getenv("NVIDIA_NIM_API_KEY"):
        # litellm's nvidia_nim provider reads NVIDIA_NIM_API_KEY specifically.
        os.environ["NVIDIA_NIM_API_KEY"] = key
    return key


def _groq_key() -> str | None:
    """litellm's groq provider reads GROQ_API_KEY directly — no mirroring needed."""
    return os.getenv("GROQ_API_KEY")


def _build_free_primary(tier: str, **overrides):
    """
    Build an LLM whose PRIMARY is a free provider, so no Anthropic call happens.
    The other free provider is attached as fallback ONLY when its key exists, so we
    never point a fallback at an unauthenticated provider.
    """
    strong = tier == "strong"
    nvidia_model = _STRONG_FALLBACK if strong else _FAST_FALLBACK
    groq_model = _GROQ_STRONG if strong else _GROQ_FAST

    if _FREE_PRIMARY == "groq":
        primary, primary_key = groq_model, _groq_key()
        alt, alt_key = nvidia_model, _nvidia_key()
    else:  # "nvidia" (or any other value) -> the already-validated NIM path
        primary, primary_key = nvidia_model, _nvidia_key()
        alt, alt_key = groq_model, _groq_key()

    _record_configured(primary)  # deterministic provenance, regardless of return path

    if not primary_key:
        print(f"[WARN] FREE_PRIMARY={_FREE_PRIMARY!r} but no API key found for it. "
              f"Set the provider key in .env. Returning '{primary}'; the call will "
              f"surface a clear auth error rather than silently using Anthropic.")
        return primary

    fallbacks = [alt] if alt_key else []

    from crewai import LLM
    try:
        return LLM(model=primary, fallbacks=fallbacks, **overrides)
    except Exception as e:
        print(f"[WARN] free-primary LLM build failed ({type(e).__name__}: {e}); "
              f"using plain '{primary}' with no fallback.")
        return primary


def build_llm(model: str, tier: str = "fast", **overrides) -> Union[str, "object"]:
    """
    Returns what an agent should pass to Agent(llm=...).

    Args:
        model:  primary Anthropic model string, e.g. "anthropic/claude-sonnet-4-6"
        tier:   "fast" (haiku-class agents) or "strong" (sonnet-class agents) —
                selects which NVIDIA fallback model to use.
        **overrides: extra crewai LLM kwargs (rarely needed).

    Behaviour:
        - No NVIDIA key  → returns `model` (plain string) → unchanged pipeline.
        - NVIDIA key set → returns a crewai LLM with litellm `fallbacks=[nvidia/...]`.

    NOTE on credentials: we intentionally do NOT pin api_key on the LLM, so litellm
    resolves each provider's key from the environment independently — Anthropic from
    ANTHROPIC_API_KEY, NVIDIA from NVIDIA_NIM_API_KEY. That is what lets the fallback
    authenticate against a different provider than the primary.
    """
    _ensure_callback_registered()  # capture the actually-served model for provenance

    # Free-primary mode wins when opted in: never touch Anthropic, run on a free
    # provider as primary. Default (unset) falls through to the original path below.
    if _FREE_PRIMARY:
        return _build_free_primary(tier, **overrides)

    # Anthropic-primary path: the configured primary IS `model` (any NVIDIA model is
    # only a fallback here). Record it before every return below.
    _record_configured(model)

    key = _nvidia_key()
    if not key:
        return model  # exact previous behaviour — no fallback, no LLM object

    fallback = _STRONG_FALLBACK if tier == "strong" else _FAST_FALLBACK

    # Imported here (not at module top) so this file is importable even in contexts
    # where crewai isn't installed (e.g. lightweight tooling/tests).
    from crewai import LLM

    # Defensive: a resilience feature must never REDUCE resilience. If the LLM object
    # can't be constructed (e.g. running outside the venv against a newer crewai that
    # needs the 'crewai[anthropic]' extra), do NOT crash every agent — warn and return
    # the plain Anthropic string so the pipeline still runs (just without NVIDIA
    # failover). Activate the venv (crewai 0.80.0) to get the fallback back.
    try:
        return LLM(model=model, fallbacks=[fallback], **overrides)
    except Exception as e:
        print(f"[WARN] utils/llm.build_llm: NVIDIA fallback unavailable "
              f"({type(e).__name__}: {e}). Using Anthropic-only for '{model}'. "
              f"If unexpected, run inside the venv (crewai 0.80.0).")
        return model
