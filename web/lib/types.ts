export type JobStatus = "queued" | "running" | "complete" | "error";

export interface GenerateRequest {
  keyword: string;
  use_cache?: boolean;
  skip_moodboard?: boolean;
}

export interface GenerateResponse {
  job_id: string;
  status: "queued";
  message: string;
}

export interface PaletteColor {
  hex_code: string;
  name: string;
  [key: string]: unknown;
}

export interface BenchmarkBrand {
  name: string;
  reference_note: string;
}

export interface Typography {
  display_typeface: string;
  body_typeface: string;
  display_tracking: string;
}

export interface Report {
  positioning_statement: string;
  palette: PaletteColor[];
  typography: Typography;
  layout_approach: string;
  negative_space_rule: string;
  photography_direction: string[];
  do_rules: string[];
  dont_rules: string[];
  benchmark_brands: BenchmarkBrand[];
  visual_narrative: string;
  conflicts_resolved: string | null;
}

export interface MoodboardPanel {
  panel: string;
  prompt: string;
  url: string;
  filename: string;
}

export interface PipelineResult {
  keyword: string;
  report: Report | null;
  formatted_report: string;
  moodboard_panels: MoodboardPanel[];
  langsmith_url: string | null;
  served_models: string[];
  timings: Record<string, number>;
}

export interface StatusResponse {
  job_id: string;
  status: JobStatus;
  current_step: string;
  started_at: string | null;
  finished_at: string | null;
  result: PipelineResult | null;
  error: string | null;
}
