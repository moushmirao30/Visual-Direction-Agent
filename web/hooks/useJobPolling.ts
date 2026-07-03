"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getStatus, startGeneration } from "@/lib/api";
import type { PipelineResult, JobStatus } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;

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
        stopPolling();
        setState((prev) => ({
          ...prev,
          status: "error",
          error: e instanceof Error ? e.message : String(e),
        }));
      }
    },
    [stopPolling]
  );

  const start = useCallback(
    async (keyword: string, useCache: boolean, skipMoodboard: boolean) => {
      stopPolling();
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
