import type { Status } from "./status";

// "same-origin" = the deployed build, served by the API itself (relative URLs). Unset = local dev API.
const RAW_API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API = RAW_API === "same-origin" ? "" : RAW_API;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Can't reach the QuarantineShock API on " + API + ". Is `npm run dev` running?");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = j.detail || msg;
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------- types
export type CallMeta = {
  provider: string;
  model?: string | null;
  cached: boolean;
  calls?: number;
  latency_ms: number;
  input_tokens?: number | null;
  output_tokens?: number | null;
  notes?: string[];
};

export type NoticeSummary = {
  id: string;
  title: string;
  effective_date: string;
  quarantine: string;
  stated_area_sq_mi: number | null;
  publisher: string;
  url: string;
  source_quality: string;
  processed: boolean;
  run_id: string | null;
  generated_area_sq_mi: number | null;
  counts: Counts | null;
  sources: { title: string; url: string; published: string }[];
};

export type Counts = {
  REVIEW: number;
  UNCLEAR: number;
  NOT_HOST: number;
  OUTSIDE: number;
  newly_flagged: number;
  newly_flagged_ids: string[];
  changed: number;
};

export type Reason = { code: string; text: string; rule_id?: string };

export type ShipmentRow = {
  id: string;
  pickup_date: string;
  origin_name: string;
  lat: number | null;
  lon: number | null;
  product_raw: string;
  quantity: string;
  destination: string;
  carrier: string;
  notes: string;
  status: Status;
  previous_status: Status | null;
  changed: boolean;
  reasons: Reason[];
  distance_mi: number | null;
  canonical_commodity: string | null;
  form: string | null;
  confidence: number | null;
  host_status: string | null;
  has_pack: boolean;
  decision: { decision: string; note: string; created_at: string } | null;
};

export type Detection = {
  place: string;
  detail: string;
  date: string | null;
  sex_status: string | null;
  quote: string;
  lat: number;
  lon: number;
  quarantine: string;
  new_in_notice: string;
  in_current_zone: boolean;
  approximate: boolean;
  geocode_source: string;
};

export type Verification = { verified: boolean; score: number; judge: "supports" | "partial" | "no" | null };

export type AppState = {
  notice_id: string;
  processed: boolean;
  run_id?: string;
  notice?: { id: string; title: string; effective_date: string; quarantine: string; url: string; publisher: string };
  zones?: GeoJSON.FeatureCollection;
  previous_zones?: GeoJSON.FeatureCollection;
  zone?: { quarantine: string; area_sq_mi: number; official_sq_mi: number | null; error_pct: number | null; n_detections: number };
  radius?: { miles: number; source: string; quote: string | null; chunk_id: string | null; verification?: Verification };
  detections?: Detection[];
  shipments?: ShipmentRow[];
  counts?: Counts;
  summary?: string;
  grounding?: { total: number; verified: number; supports: number; judged: number; unverified: string[] };
  warnings?: string[];
  provider_mode?: string;
};

export type RunEvent = {
  run_id: string;
  seq: number;
  node: string;
  status: "started" | "progress" | "done" | "error";
  message: string;
  meta: CallMeta | null;
  ts: string;
  output?: unknown;
  elapsed_ms?: number;
  toast?: string;
  prompt?: string | null;
  counts?: Counts;
  grounding?: AppState["grounding"];
  warnings?: string[];
  provider_mode?: string;
};

export type Evidence = {
  kind: "rule" | "ambiguity" | "host_list";
  id: string;
  claim: string;
  topic?: string;
  quote: string;
  chunk_id: string | null;
  verification: Verification | null;
  source: { title: string; url?: string; doc_id: string; chunk_id?: string } | null;
};

export type ActionPack = {
  shipment_id: string;
  explanation: string;
  rule_ids: string[];
  checklist: string[];
  email_subject: string;
  email_body: string;
  driver_hold_note: string;
  wording_warning?: string;
};

export type ShipmentDetail = {
  shipment: ShipmentRow;
  status: { status: Status; reasons: Reason[]; distance_mi: number | null; previous_status: Status | null; changed_since_previous_notice: boolean };
  normalized: {
    canonical_commodity: string;
    form: string;
    host_status: string;
    llm_host_status: string;
    confidence: number;
    reasoning: string;
    federal_host: boolean | null;
    state_host: boolean | null;
    host_source: string;
    candidates: { canonical: string; matched_label: string; score: number }[];
  } | null;
  pack: ActionPack | null;
  evidence: Evidence[];
  zones: GeoJSON.FeatureCollection;
  decisions: { decision: string; note: string; notice_id: string; created_at: string }[];
  notice_id: string;
};

export type NoticeDetail = {
  notice: { id: string; title: string; effective_date: string; url: string; publisher: string; excerpt_of: { title: string; url: string; published: string; retrieved: string }[]; source_quality: string };
  text: string;
  extract: {
    notice_date: string;
    effective_date: string | null;
    quarantine_name: string;
    action: string;
    detections: (Detection & { verification?: Verification; place_is_inferred?: boolean })[];
    stated_area_sq_mi: number | null;
    stated_commercial_acres: number | null;
    crops_mentioned: string[];
    ambiguities: string[];
  } | null;
  classification: { is_quarantine_change: boolean; pest: string; county: string; action: string; confidence: number } | null;
  highlights: { field: string; label: string; start: number; end: number; verified: boolean | null }[];
  processed: boolean;
};

export type SourcePassage = {
  chunk_id: string;
  text: string;
  title: string;
  url: string;
  doc_id: string;
  before: string | null;
  after: string | null;
  doc: { title: string; url: string; publisher: string; date: string | null; retrieved?: string };
};

export type ProviderHealth = {
  mode: string;
  gemini: { status: string; model?: string | null; latency_ms?: number; message?: string };
  openrouter: { status: string; model?: string | null; latency_ms?: number; message?: string };
};

export type SettingsInfo = {
  provider_mode: string;
  modes: string[];
  gemini: { configured: boolean; model_fast: string; model_strong: string };
  openrouter: { configured: boolean; model: string | null };
  radius_config_miles: number;
  health: Record<string, { unhealthy: boolean; last_error: string | null }>;
};

// ---------------------------------------------------------------- calls
export const api = {
  notices: () => req<NoticeSummary[]>("/api/notices"),
  notice: (id: string) => req<NoticeDetail>(`/api/notices/${encodeURIComponent(id)}`),
  state: (id: string) => req<AppState>(`/api/state?notice_id=${encodeURIComponent(id)}`),
  startRun: (notice_id: string) => req<{ run_id: string }>("/api/runs", { method: "POST", body: JSON.stringify({ notice_id }) }),
  run: (id: string) => req<{ run_id: string; status: string; events: RunEvent[]; error: string | null }>(`/api/runs/${id}`),
  shipment: (id: string, notice_id: string) =>
    req<ShipmentDetail>(`/api/shipments/${id}?notice_id=${encodeURIComponent(notice_id)}`),
  decide: (id: string, body: { decision: string; notice_id: string; note: string }) =>
    req<{ id: number; decision: string; created_at: string }>(`/api/shipments/${id}/decision`, { method: "POST", body: JSON.stringify(body) }),
  source: (chunk_id: string) => req<SourcePassage>(`/api/sources/${encodeURIComponent(chunk_id)}`),
  settings: () => req<SettingsInfo>("/api/settings"),
  setProvider: (mode: string) => req<SettingsInfo>("/api/settings/provider", { method: "POST", body: JSON.stringify({ mode }) }),
  providers: () => req<ProviderHealth>("/api/health/providers"),
  reset: (fast_forward_to?: string) =>
    req<{ ok: boolean }>("/api/demo/reset", { method: "POST", body: JSON.stringify({ fast_forward_to: fast_forward_to ?? null }) }),
  demoStatus: () => req<{ running: boolean; error: string | null; done: string | null; processed: string[] }>("/api/demo/status"),
  evals: () => req<Evals>("/api/evals"),
  runEvals: () => req<Evals>("/api/evals/run", { method: "POST" }),
  suggestions: () => req<string[]>("/api/chat/suggestions"),
};

export type Evals = {
  computed_at: string;
  runs_evaluated: number;
  normalizer: {
    n: number;
    canonical_accuracy: number | null;
    host_status_accuracy: number | null;
    confusion: Record<string, Record<string, number>>;
    rows: { id: string; label: string; predicted: string; label_status: string; predicted_status: string; form: string; confidence: number; canonical_ok: boolean; status_ok: boolean }[];
    reviewed_by_human: boolean;
    method: string;
  };
  rules: { gold_count: number; matched: number; extracted_count: number; method: string; rows: { id: string; description: string; keywords: string[]; matched_rule: string | null }[] };
  grounding: { total: number; verified: number; supports: number; judged: number; verified_pct: number | null; supports_pct: number | null; per_run: { notice_id: string; total: number; verified: number; supports: number; judged: number }[] };
  zones: { notice_id: string; title: string; effective_date: string; generated: number; official: number | null; error_pct: number | null }[];
  radius: AppState["radius"];
};

// ---------------------------------------------------------------- streaming
/** Subscribe to a run's SSE stream. Returns an unsubscribe function. */
export function subscribeRun(runId: string, onEvent: (e: RunEvent) => void, onEnd: () => void): () => void {
  const es = new EventSource(`${API}/api/runs/${runId}/events`);
  es.addEventListener("step", (m) => onEvent(JSON.parse((m as MessageEvent).data)));
  es.addEventListener("end", () => {
    es.close();
    onEnd();
  });
  es.onerror = () => {
    // the server closes the stream after "end"; a real drop also ends here
    if (es.readyState === EventSource.CLOSED) onEnd();
  };
  return () => es.close();
}

export type ChatEvent =
  | { type: "token"; text: string }
  | {
      type: "done";
      answer: string;
      citations: { chunk_id: string; title: string; url?: string; doc_id: string }[];
      quotes: { chunk_id: string; quote: string; verified: boolean; score: number }[];
      certainty_warning: boolean;
      meta: CallMeta | null;
    }
  | { type: "error"; message: string };

/** POST /api/chat and parse the SSE response body incrementally. */
export async function streamChat(question: string, onEvent: (e: ChatEvent) => void, signal?: AbortSignal) {
  let res: Response;
  try {
    res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch {
    onEvent({ type: "error", message: "Can't reach the API." });
    return;
  }
  if (!res.ok || !res.body) {
    onEvent({ type: "error", message: `Chat failed (${res.status})` });
    return;
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const frames = buf.split(/\r?\n\r?\n/);
    buf = frames.pop() ?? "";
    for (const f of frames) {
      const data = f
        .split(/\r?\n/)
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).replace(/^ /, ""))
        .join("\n");
      if (data) onEvent(JSON.parse(data) as ChatEvent);
    }
  }
}
