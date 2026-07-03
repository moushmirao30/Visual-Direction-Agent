export interface AgentInfo {
  num: string;
  name: string;
  detail: string;
}

export const AGENTS: AgentInfo[] = [
  { num: "01", name: "Trend Researcher", detail: "Live web search via Tavily" },
  { num: "02", name: "Design Theory Analyst", detail: "RAG over curated design knowledge" },
  { num: "03", name: "Direction Synthesiser", detail: "Merges trend + theory outputs" },
  { num: "04", name: "Report Writer", detail: "Validated Pydantic schema output" },
  { num: "05", name: "Moodboard Generator", detail: "AI image generation" },
];

/** True when the given agent has already finished, judged from the current-step string. */
export function isAgentDone(agentNum: string, currentStep: string): boolean {
  const digits = currentStep.split(" ").find((c) => /^\d+$/.test(c));
  if (!digits) return false;
  return parseInt(agentNum, 10) < parseInt(digits, 10);
}
