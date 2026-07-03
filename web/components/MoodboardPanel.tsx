import type { MoodboardPanel as PanelData } from "@/lib/types";
import { moodboardImageUrl } from "@/lib/api";

function Panel({ panel, index }: { panel: PanelData; index: number }) {
  const label = panel.panel || `Panel ${index + 1}`;
  return (
    <div className="flex flex-col">
      {panel.filename ? (
        // eslint-disable-next-line @next/next/no-img-element -- cross-origin PNG from the API backend
        <img
          src={moodboardImageUrl(panel.url)}
          alt={label}
          className="w-full rounded-md border border-card-border"
        />
      ) : (
        <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          ⚠ Image generation unavailable (backend failed) — prompt below.
        </p>
      )}
      <p className="mt-1.5 text-xs font-medium uppercase tracking-wider text-sage">
        {label}
      </p>
      <details className="mt-0.5">
        <summary className="cursor-pointer text-xs text-secondary select-none">
          Prompt
        </summary>
        <p className="mt-1 text-xs leading-relaxed text-secondary">{panel.prompt}</p>
      </details>
    </div>
  );
}

export default function MoodboardPanel({ panels }: { panels: PanelData[] }) {
  if (!panels.length) {
    return (
      <div>
        <h3 className="mb-4 text-lg font-bold text-heading">Moodboard</h3>
        <p className="rounded-md border border-card-border bg-card px-4 py-3 text-sm text-secondary">
          No moodboard panels generated. Re-run with skip_moodboard unchecked.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="mb-4 text-lg font-bold text-heading">Moodboard</h3>
      <div className="grid grid-cols-2 gap-4">
        {panels.slice(0, 4).map((p, i) => (
          <Panel key={i} panel={p} index={i} />
        ))}
      </div>
      {panels[4] && (
        <div className="mt-4 px-[15%]">
          <Panel panel={panels[4]} index={4} />
        </div>
      )}
    </div>
  );
}
