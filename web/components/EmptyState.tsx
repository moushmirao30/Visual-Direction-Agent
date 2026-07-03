import { AGENTS } from "@/lib/agents";

export default function EmptyState() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-heading">
        Visual Direction Research Agent
      </h2>
      <p className="mt-4 max-w-3xl text-[1.05rem] leading-relaxed text-text">
        Enter an aesthetic keyword in the sidebar — e.g.{" "}
        <strong>quiet luxury wellness</strong>, <strong>bold brutalist tech</strong>,{" "}
        <strong>coastal minimal resort</strong> — and click <strong>Generate</strong>.
        <br />
        <br />
        The 5-agent pipeline runs live web search, retrieves design theory from a
        curated knowledge base, synthesises a unified visual direction, validates it
        against a Pydantic schema, and generates a 5-panel AI moodboard.
      </p>
      <hr className="my-6 border-card-border" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {AGENTS.map((a) => (
          <div
            key={a.num}
            className="rounded-md border border-card-border bg-card p-4"
          >
            <strong className="text-heading">
              {a.num} — {a.name}
            </strong>
            <br />
            <span className="text-sm text-secondary">{a.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
