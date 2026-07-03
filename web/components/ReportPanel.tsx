"use client";

import type { PipelineResult } from "@/lib/types";
import { downloadReportHtml } from "@/lib/exportHtml";
import PaletteSwatch from "./PaletteSwatch";

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="mb-1.5 font-bold text-heading">{children}</p>;
}

function Divider() {
  return <hr className="my-5 border-card-border" />;
}

export default function ReportPanel({ result }: { result: PipelineResult }) {
  const report = result.report;

  if (!report) {
    return (
      <div className="whitespace-pre-wrap text-text">
        {result.formatted_report}
      </div>
    );
  }

  return (
    <div>
      <h3 className="mb-4 text-lg font-bold text-heading">
        Visual Direction Report
      </h3>

      <blockquote className="rounded-r border-l-[3px] border-blockquote-border bg-card px-4 py-3 italic text-text">
        {report.positioning_statement}
      </blockquote>
      <Divider />

      <SectionTitle>Palette</SectionTitle>
      <div className="flex flex-wrap gap-3">
        {report.palette.map((sw) => (
          <PaletteSwatch key={sw.hex_code} color={sw} />
        ))}
      </div>
      <Divider />

      {report.typography && (
        <>
          <SectionTitle>Typography</SectionTitle>
          <p className="my-0.5 text-text">Display: {report.typography.display_typeface}</p>
          <p className="my-0.5 text-text">Body: {report.typography.body_typeface}</p>
          <p className="my-0.5 text-text">Tracking: {report.typography.display_tracking}</p>
          <Divider />
        </>
      )}

      <SectionTitle>Spatial</SectionTitle>
      <p className="text-text">{report.layout_approach}</p>
      <p className="mt-1 text-sm text-secondary">{report.negative_space_rule}</p>
      <Divider />

      <SectionTitle>Photography</SectionTitle>
      {report.photography_direction.map((d, i) => (
        <p key={i} className="my-1 text-text">
          {i + 1}. {d}
        </p>
      ))}
      <Divider />

      <div className="grid grid-cols-2 gap-6">
        <div>
          <SectionTitle>Do</SectionTitle>
          {report.do_rules.map((r, i) => (
            <p key={i} className="my-1 text-sm text-text">
              ✓ {r}
            </p>
          ))}
        </div>
        <div>
          <SectionTitle>Don&apos;t</SectionTitle>
          {report.dont_rules.map((r, i) => (
            <p key={i} className="my-1 text-sm text-text">
              ✕ {r}
            </p>
          ))}
        </div>
      </div>
      <Divider />

      <SectionTitle>Benchmark Brands</SectionTitle>
      {report.benchmark_brands.map((b) => (
        <div key={b.name} className="mb-2">
          <p className="font-semibold text-heading">{b.name}</p>
          <p className="text-sm text-text">{b.reference_note}</p>
        </div>
      ))}
      <Divider />

      <SectionTitle>Visual Narrative</SectionTitle>
      <p className="italic leading-loose text-text">{report.visual_narrative}</p>

      {report.conflicts_resolved && (
        <details className="mt-4">
          <summary className="cursor-pointer text-secondary select-none">
            Conflicts resolved
          </summary>
          <p className="mt-2 text-text">{report.conflicts_resolved}</p>
        </details>
      )}

      <Divider />
      <button
        onClick={() =>
          downloadReportHtml(
            report,
            result.keyword,
            result.langsmith_url,
            result.served_models
          )
        }
        className="w-full rounded-md border border-card-border bg-input px-4 py-2.5 text-sm font-medium text-text transition-colors hover:bg-card"
        title="Standalone HTML file — open in any browser."
      >
        ⬇ Download Report (HTML)
      </button>
    </div>
  );
}
