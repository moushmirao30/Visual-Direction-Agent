import { AGENTS, isAgentDone } from "@/lib/agents";

interface RunningStateProps {
  keyword: string;
  currentStep: string;
}

export default function RunningState({ keyword, currentStep }: RunningStateProps) {
  return (
    <div>
      <h2 className="text-2xl font-bold text-heading">
        Running: <em>{keyword}</em>
      </h2>
      <div className="mt-6 flex flex-col gap-1.5">
        {AGENTS.map((a) => {
          const active = currentStep.includes(`Agent ${a.num}`);
          const done = !active && isAgentDone(a.num, currentStep);
          const marker = active ? "→" : done ? "✓" : "○";
          const markerColor = active
            ? "text-heading font-bold"
            : done
              ? "text-blockquote-border"
              : "text-placeholder";
          return (
            <div
              key={a.num}
              className="flex items-center gap-3 rounded-md border border-card-border bg-card px-4 py-3"
            >
              <span className={`text-base ${markerColor}`}>{marker}</span>
              <strong className="text-heading">
                {a.num} — {a.name}
              </strong>
              <span className="text-sm text-secondary">{a.detail}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
