"use client";

import { useState } from "react";
import type { PipelineResult } from "@/lib/types";
import type { UiStatus } from "@/hooks/useJobPolling";

interface SidebarProps {
  status: UiStatus;
  currentStep: string;
  result: PipelineResult | null;
  onGenerate: (keyword: string, useCache: boolean, skipMoodboard: boolean) => void;
  onReset: () => void;
}

export default function Sidebar({
  status,
  currentStep,
  result,
  onGenerate,
  onReset,
}: SidebarProps) {
  const [keyword, setKeyword] = useState("");
  const [useCache, setUseCache] = useState(true);
  const [skipMoodboard, setSkipMoodboard] = useState(false);
  const [inputError, setInputError] = useState("");

  const polling = status === "queued" || status === "running";

  const handleGenerate = () => {
    if (!keyword.trim()) {
      setInputError("Enter an aesthetic keyword first.");
      return;
    }
    setInputError("");
    onGenerate(keyword.trim(), useCache, skipMoodboard);
  };

  const timings = result?.timings ?? {};

  return (
    <aside className="w-72 shrink-0 bg-sidebar min-h-screen p-6 flex flex-col gap-4">
      <h1 className="text-xl font-bold text-heading leading-snug">
        Visual Direction
        <br />
        Research Agent
      </h1>
      <hr className="border-card-border" />

      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-text">Aesthetic keyword</span>
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !polling) handleGenerate();
          }}
          placeholder="e.g. quiet luxury wellness"
          disabled={polling}
          className="rounded-md border border-card-border bg-input px-3 py-2 text-sm text-text placeholder:text-placeholder focus:outline-none focus:ring-2 focus:ring-sage/40 disabled:opacity-60"
        />
      </label>

      <label className="flex items-center gap-2 text-sm text-text cursor-pointer">
        <input
          type="checkbox"
          checked={useCache}
          onChange={(e) => setUseCache(e.target.checked)}
          disabled={polling}
          className="accent-[#6A6460]"
        />
        Use cached outputs
      </label>

      <details className="text-sm text-text">
        <summary className="cursor-pointer text-secondary select-none">
          Advanced options
        </summary>
        <label className="mt-2 flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={skipMoodboard}
            onChange={(e) => setSkipMoodboard(e.target.checked)}
            disabled={polling}
            className="accent-[#6A6460]"
          />
          Skip moodboard generation
        </label>
      </details>

      <hr className="border-card-border" />

      <button
        onClick={handleGenerate}
        disabled={polling}
        className="w-full rounded-md bg-heading px-4 py-2.5 text-sm font-semibold text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Generate
      </button>
      {inputError && <p className="text-sm text-red-800">{inputError}</p>}

      {polling && (
        <div className="rounded-md border border-card-border bg-card p-3 text-sm">
          <p className="font-semibold text-heading">{currentStep || "Queued"}</p>
          <p className="mt-1 text-xs text-secondary">
            Fresh run can take 15–30 min on free-tier hosting. Repeat keywords
            finish faster. Leave this tab open — progress updates live.
          </p>
        </div>
      )}

      {status === "complete" && result && (
        <div className="flex flex-col gap-2 text-sm">
          <p className="rounded-md border border-blockquote-border bg-card px-3 py-2 font-medium text-heading">
            Done in {timings.total ?? "?"}s
          </p>
          <details>
            <summary className="cursor-pointer text-secondary select-none">
              Agent timings
            </summary>
            <ul className="mt-1 pl-1 text-xs text-secondary">
              {Object.entries(timings)
                .filter(([k]) => k !== "total")
                .map(([k, v]) => (
                  <li key={k}>
                    {k}: {v}s
                  </li>
                ))}
            </ul>
          </details>
          {result.langsmith_url && (
            <a
              href={result.langsmith_url}
              target="_blank"
              rel="noreferrer"
              className="text-sage underline underline-offset-2"
            >
              LangSmith trace
            </a>
          )}
          {result.served_models?.length > 0 && (
            <p className="text-xs text-secondary">
              Served by: {result.served_models.join(", ")}
            </p>
          )}
        </div>
      )}

      {status === "error" && (
        <p className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          Pipeline failed. See error details.
        </p>
      )}

      <hr className="border-card-border" />
      <button
        onClick={() => {
          setInputError("");
          onReset();
        }}
        className="w-full rounded-md border border-card-border bg-input px-4 py-2 text-sm text-text transition-colors hover:bg-card"
      >
        Reset
      </button>
    </aside>
  );
}
