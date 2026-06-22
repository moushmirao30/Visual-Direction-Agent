"""
eval/cost_tracker.py
Best-effort token + USD cost accounting for a pipeline run.

Why this exists:
  The first thing a senior reviewer asks after "is it good?" is "what does it
  cost?". The pipeline already returns wall-clock latency (crew.py timings). This
  adds the spend side. CrewAI runs every LLM call through LiteLLM, so a single
  global LiteLLM success-callback captures token usage and cost across ALL five
  agents without touching any agent code.

Why "best-effort":
  Callback signatures and cost tables drift between LiteLLM versions, and some
  providers do not return usage. Every access is defensive. If anything is
  missing the tracker degrades to what it could measure and never crashes a run —
  a missing cost number must not take down an eval.
"""

import threading


class CostTracker:
    """
    Accumulates token usage and USD cost from LiteLLM completion callbacks.
    Thread-safe because CrewAI may issue calls from worker threads.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock if hasattr(self, "_lock") else threading.Lock():
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.total_cost_usd = 0.0
            self.calls = 0
            self.cost_available = True  # flips False if we never manage to read a cost

    # LiteLLM calls this with (kwargs, completion_response, start_time, end_time)
    def _on_success(self, kwargs, completion_response, start_time, end_time) -> None:
        try:
            with self._lock:
                self.calls += 1

                usage = getattr(completion_response, "usage", None)
                if usage is not None:
                    self.prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
                    self.completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)

                # Prefer the cost LiteLLM attaches; fall back to computing it.
                cost = None
                hidden = getattr(completion_response, "_hidden_params", {}) or {}
                if isinstance(hidden, dict):
                    cost = hidden.get("response_cost")
                if cost is None:
                    try:
                        import litellm
                        cost = litellm.completion_cost(completion_response=completion_response)
                    except Exception:
                        cost = None

                if cost is None:
                    self.cost_available = False
                else:
                    self.total_cost_usd += float(cost)
        except Exception:
            # Never let accounting break a run.
            self.cost_available = False

    def register(self) -> bool:
        """
        Registers the success callback with LiteLLM.
        Returns True if registration succeeded, False otherwise (degrade gracefully).
        """
        try:
            import litellm
            if self._on_success not in litellm.success_callback:
                litellm.success_callback.append(self._on_success)
            return True
        except Exception:
            return False

    def unregister(self) -> None:
        try:
            import litellm
            if self._on_success in litellm.success_callback:
                litellm.success_callback.remove(self._on_success)
        except Exception:
            pass

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "llm_calls": self.calls,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.prompt_tokens + self.completion_tokens,
                "cost_usd": round(self.total_cost_usd, 4) if self.cost_available else None,
                "cost_available": self.cost_available,
            }
