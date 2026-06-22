"""
utils/run_logger.py
Tee all console output (stdout + stderr) for a pipeline run into a timestamped
file under logs/, so "check the latest log" actually works.

Why this exists:
  crew.py / the agents use print() and litellm logs to stderr — all of it went to
  the terminal and nowhere else. After a run finished (or the terminal scrolled
  away) there was no record: no served model, no timings, no traceback. This
  captures the EXACT terminal output to logs/run_<ts>_<slug>.log for every CLI and
  API/UI run, including the "Served by:" banner and any fallback/credit errors.

How it works:
  A tiny tee wraps sys.stdout/sys.stderr to write to BOTH the original stream and
  the log file. start() installs it; stop() always restores the originals (even on
  exception) and closes the file. Usable two ways:

    with run_log(keyword):
        run_visual_direction_pipeline(...)

  or, to drop into an existing try/except without re-indenting the body:

    _log = start_run_log(keyword)
    try:
        ...
    finally:
        stop_run_log(_log)

Notes:
  - Output is also still printed to the real terminal (it's a tee, not a redirect).
  - sys.stdout is process-global, so concurrent runs in the same process would
    interleave into whichever log is active. Fine for the single-user demo path
    (api.py runs pipelines sequentially in practice); not meant for parallel runs.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s[:40] or "run"


class _Tee:
    """Write to several streams at once; never let logging break the run."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass

    def flush(self):
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass


class run_log:
    """
    Context manager / handle that tees stdout+stderr to logs/run_<ts>_<slug>.log.
    `.path` is the log file path (available after start()).
    """

    def __init__(self, keyword: str):
        self.keyword = keyword
        self.path = None
        self._file = None
        self._orig_out = None
        self._orig_err = None
        self._t0 = None

    def start(self) -> "run_log":
        try:
            LOG_DIR.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.path = LOG_DIR / f"run_{ts}_{_slug(self.keyword)}.log"
            self._file = open(self.path, "w", encoding="utf-8")
            self._t0 = datetime.now()
            self._file.write(
                f"# Visual Direction Agent — run log\n"
                f"# keyword : {self.keyword!r}\n"
                f"# started : {self._t0.isoformat()}\n"
                f"{'=' * 60}\n\n"
            )
            self._file.flush()
            self._orig_out, self._orig_err = sys.stdout, sys.stderr
            sys.stdout = _Tee(self._orig_out, self._file)
            sys.stderr = _Tee(self._orig_err, self._file)
            print(f"[LOG] Writing this run to: {self.path}")
        except Exception as e:
            # Logging must never block a run — degrade to console-only.
            print(f"[LOG] Could not start file logging ({type(e).__name__}: {e}) — console only")
            self._restore_streams()
        return self

    def stop(self) -> None:
        # Restore streams FIRST so nothing can get stuck writing to a closed file.
        try:
            if self._file:
                elapsed = (datetime.now() - self._t0).total_seconds() if self._t0 else None
                self._file.write(
                    f"\n{'=' * 60}\n# finished: {datetime.now().isoformat()}"
                    f"{f' ({elapsed:.1f}s)' if elapsed is not None else ''}\n"
                )
        except Exception:
            pass
        self._restore_streams()
        try:
            if self._file:
                self._file.close()
        except Exception:
            pass
        self._file = None
        if self.path:
            print(f"[LOG] Run log saved: {self.path}")

    def _restore_streams(self) -> None:
        if self._orig_out is not None:
            sys.stdout = self._orig_out
        if self._orig_err is not None:
            sys.stderr = self._orig_err

    # Context-manager sugar
    def __enter__(self) -> "run_log":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.stop()
        return False  # never suppress exceptions


def start_run_log(keyword: str) -> run_log:
    """Start logging and return the handle. Pair with stop_run_log() in a finally."""
    return run_log(keyword).start()


def stop_run_log(handle: "run_log | None") -> None:
    """Stop a handle returned by start_run_log(); safe to call with None."""
    if handle is not None:
        handle.stop()
