"use client";

import { useJobPolling } from "@/hooks/useJobPolling";
import Sidebar from "@/components/Sidebar";
import EmptyState from "@/components/EmptyState";
import RunningState from "@/components/RunningState";
import ErrorState from "@/components/ErrorState";
import ReportPanel from "@/components/ReportPanel";
import MoodboardPanel from "@/components/MoodboardPanel";

export default function Home() {
  const { status, keyword, currentStep, result, error, start, reset } =
    useJobPolling();

  return (
    <div className="flex min-h-screen">
      <Sidebar
        status={status}
        currentStep={currentStep}
        result={result}
        onGenerate={start}
        onReset={reset}
      />

      <main className="flex-1 p-8 lg:p-12">
        {status === "idle" && <EmptyState />}

        {(status === "queued" || status === "running") && (
          <RunningState keyword={keyword} currentStep={currentStep} />
        )}

        {status === "error" && <ErrorState error={error} />}

        {status === "complete" && result && (
          <div>
            <h2 className="mb-6 text-2xl font-bold tracking-[0.06em] text-heading">
              {result.keyword.toUpperCase()}
            </h2>
            <div className="grid grid-cols-1 gap-10 xl:grid-cols-2">
              <ReportPanel result={result} />
              <MoodboardPanel panels={result.moodboard_panels} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
