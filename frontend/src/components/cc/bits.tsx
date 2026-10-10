"use client";

import { CheckCircle2, Cloud, Code2, Database, History, ShieldAlert, ShieldCheck, Sparkles, XCircle } from "lucide-react";
import { cn } from "cn";
import type { CallMeta, Verification } from "@/lib/api";
import { STATUS, type Status } from "@/lib/status";

export function StatusChip({ status, size = "sm" }: { status: Status | null | undefined; size?: "sm" | "md" }) {
  if (!status) return <span className="text-xs text-muted-foreground">-</span>;
  const s = STATUS[status];
  const Icon = s.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-medium whitespace-nowrap",
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-3 py-1 text-sm",
      )}
      style={{ color: s.color, borderColor: `${s.color}55`, background: `${s.color}14` }}
    >
      <Icon className={size === "sm" ? "size-3" : "size-4"} aria-hidden />
      {s.label}
    </span>
  );
}

export function NewBadge() {
  return (
    <span className="rounded-md bg-brand px-1.5 py-px text-[10px] font-bold tracking-wider text-slate-950 uppercase">New</span>
  );
}

const PROVIDER_STYLE: Record<string, { label: string; cls: string; icon: typeof Cloud }> = {
  gemini: { label: "Gemini", cls: "text-sky-400 border-sky-400/30 bg-sky-400/10", icon: Sparkles },
  openrouter: { label: "OpenRouter", cls: "text-fuchsia-400 border-fuchsia-400/30 bg-fuchsia-400/10", icon: Cloud },
  cache: { label: "saved", cls: "text-amber-300 border-amber-300/30 bg-amber-300/10", icon: Database },
  replay: { label: "offline", cls: "text-violet-300 border-violet-300/30 bg-violet-300/10", icon: History },
  code: { label: "code", cls: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10", icon: Code2 },
};

export function ProviderBadge({ meta }: { meta: CallMeta | null | undefined }) {
  let key = "code";
  if (meta) key = meta.provider.includes("+") ? (meta.cached ? "cache" : meta.provider.split("+").find((p) => p in PROVIDER_STYLE && p !== "cache") || "cache") : meta.provider;
  const st = PROVIDER_STYLE[key] || PROVIDER_STYLE.code;
  const Icon = st.icon;
  return (
    <span
      className={cn("mono inline-flex items-center gap-1 rounded-md border px-1.5 py-px text-[10px]", st.cls)}
      title={meta?.model ? `${meta.model}${meta.calls ? ` · ${meta.calls} call(s)` : ""}` : "deterministic code, no AI"}
    >
      <Icon className="size-3" />
      {st.label}
    </span>
  );
}

export function VerifiedBadge({ v }: { v: Verification | null | undefined }) {
  if (!v) return null;
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      {v.verified ? (
        <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-px text-[10px] font-medium text-emerald-400">
          <CheckCircle2 className="size-3" /> verified
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 rounded-md border border-red-500/40 bg-red-500/10 px-1.5 py-px text-[10px] font-medium text-red-400">
          <XCircle className="size-3" /> unverified
        </span>
      )}
      {v.judge && v.judge !== "supports" && (
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-md border px-1.5 py-px text-[10px] font-medium",
            v.judge === "partial" && "border-amber-400/30 text-amber-300",
            v.judge === "no" && "border-red-500/40 text-red-400",
          )}
          title="LLM judge: does the quote support the claim?"
        >
          {v.judge === "no" ? <ShieldAlert className="size-3" /> : <ShieldCheck className="size-3" />}
          {v.judge === "partial" ? "partly supports" : "does not support"}
        </span>
      )}
    </span>
  );
}

export const NODES: { id: string; label: string; ai: boolean }[] = [
  { id: "classify_notice", label: "Read the notice", ai: true },
  { id: "extract_notice", label: "Pull out the facts", ai: true },
  { id: "geocode_detections", label: "Locate the flies", ai: false },
  { id: "build_zone", label: "Draw the zone", ai: false },
  { id: "extract_rules", label: "Read the rules", ai: true },
  { id: "normalize_shipments", label: "Understand load labels", ai: true },
  { id: "match", label: "Check loads against zone", ai: false },
  { id: "verify_citations", label: "Verify every quote", ai: true },
  { id: "draft_actions", label: "Draft next steps", ai: true },
  { id: "summarize", label: "Summarize", ai: true },
];

export function fmtDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" }) {
  if (!iso) return "-";
  const d = new Date(iso.length === 10 ? `${iso}T12:00:00` : iso);
  return d.toLocaleDateString("en-US", opts);
}
