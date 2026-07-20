"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getStatus, startGeneration } from "@/lib/api";
import type { PipelineResult, JobStatus } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;
// Transient poll failures tolerated before giving up (network blips,
// free-tier instance briefly unreachable). A 404 is never transient.
const MAX_CONSECUTIVE_FAILURES = 3;

export type UiStatus = "idle" | JobStatus;

interface JobState {
  status: UiStatus;
  jobId: string | null;
  keyword: string;
  currentStep: string;
  result: PipelineResult | null;
  error: string | null;
  startedAt: string | null;
  finishedAt: string | null;
}

const initialState: JobState = {
  status: "idle",
  jobId: null,
  keyword: "",
  currentStep: "",
  result: null,
  error: null,
  startedAt: null,
  finishedAt: null,
};

export function useJobPolling() {
  const [state, setState] = useState<JobState>(initialState);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const failuresRef = useRef(0);

  const stopPolling = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const poll = useCallback(
    async (jobId: string) => {
      try {
        const s = await getStatus(jobId);
        failuresRef.current = 0;
        setState((prev) => ({
          ...prev,
          status: s.status,
          currentStep: s.current_step,
          result: s.result,
          error: s.error,
          startedAt: s.started_at,
          finishedAt: s.finished_at,
        }));
        if (s.status === "complete" || s.status === "error") {
          stopPolling();
        }
      } catch (e) {
        // 404 → the backend restarted and its in-memory job store was wiped
        // (common on the free-tier host). The job is gone; say so plainly.
        if (e instanceof ApiError && e.httpStatus === 404) {
          stopPolling();
          setState((prev) => ({
            ...prev,
            status: "error",
            error:
              "The backend restarted mid-run and lost this job (free-tier instance was recycled). Please run the pipeline again.",
          }));
          return;
        }
        // Transient failure — keep polling up to the limit.
        failuresRef.current += 1;
        if (failuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
          stopPolling();
          setState((prev) => ({
            ...prev,
            status: "error",
            error: e instanceof Error ? e.message : String(e),
          }));
        }
      }
    },
    [stopPolling]
  );

  const start = useCallback(
    async (keyword: string, useCache: boolean, skipMoodboard: boolean) => {
      stopPolling();
      failuresRef.current = 0;
      setState({ ...initialState, status: "queued", keyword });
      try {
        const res = await startGeneration({
          keyword,
          use_cache: useCache,
          skip_moodboard: skipMoodboard,
        });
        setState((prev) => ({ ...prev, jobId: res.job_id }));
        void poll(res.job_id);
        timerRef.current = setInterval(() => void poll(res.job_id), POLL_INTERVAL_MS);
      } catch (e) {
        setState((prev) => ({
          ...prev,
          status: "error",
          error: e instanceof Error ? e.message : String(e),
        }));
      }
    },
    [poll, stopPolling]
  );

  const reset = useCallback(() => {
    stopPolling();
    setState(initialState);
  }, [stopPolling]);

  return { ...state, start, reset };
}
