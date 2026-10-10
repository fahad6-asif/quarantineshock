"use client";

import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, Check, ChevronDown, Circle, Cpu, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { cn } from "cn";
import type { AppState, RunEvent } from "@/lib/api";
import { NODES, ProviderBadge } from "./bits";

type NodeState = { status: "pending" | "started" | "done" | "error"; message?: string; progress: string[]; ev?: RunEvent };

export function AgentActivity({
  events,
  running,
  grounding,
}: {
  events: RunEvent[];
  running: boolean;
  grounding?: AppState["grounding"];
}) {
  const [open, setOpen] = useState<string | null>(null);
  const nodes = useMemo(() => {
    const m: Record<string, NodeState> = Object.fromEntries(NODES.map((n) => [n.id, { status: "pending", progress: [] }]));
    for (const e of events) {
      const s = m[e.node];
      if (!s) continue;
      if (e.status === "progress") s.progress.push(e.message);
      else {
        s.status = e.status as NodeState["status"];
        s.message = e.message;
        if (e.status !== "started") s.ev = e;
      }
    }
    return m;
  }, [events]);
  const runEnd = events.find((e) => e.node === "run" && (e.status === "done" || e.status === "error"));
  const doneCount = NODES.filter((n) => nodes[n.id].status === "done").length;
  const g = runEnd?.grounding ?? grounding;

  if (!events.length) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-sm text-muted-foreground">
        <Cpu className="size-8 opacity-50" />
        Press <kbd className="rounded bg-muted px-1.5">N</kbd> to process the next notice.
      </div>
    );
  }

  return (
    <div className="scroll-thin h-full overflow-y-auto p-3">
      <div className="mb-3 flex items-center justify-between px-1 text-sm">
        <span className="font-medium">
          {running ? (
            <span className="inline-flex items-center gap-1.5 text-brand">
              <Loader2 className="size-4 animate-spin" /> Working… {doneCount}/10
            </span>
          ) : (
            `${doneCount}/10 steps done`
          )}
        </span>
        {g && !running && (
          <span className="text-xs text-muted-foreground" title="Quotes checked word-for-word against the source documents">
            {g.verified}/{g.total} quotes verified
          </span>
        )}
      </div>
      {runEnd?.status === "error" && (
        <div className="mb-3 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{runEnd.message}</div>
      )}
      <ol className="space-y-0.5">
        {NODES.map((n) => {
          const s = nodes[n.id];
          const isOpen = open === n.id;
          const showMsg = isOpen || s.status === "started" || s.status === "error";
          return (
            <li key={n.id} className={cn("rounded-xl px-2 py-1.5", s.status === "started" && "bg-brand/8", isOpen && "bg-muted/40")}>
              <button className="flex w-full items-center gap-2.5 text-left" onClick={() => setOpen(isOpen ? null : n.id)} disabled={!s.ev}>
                <span
                  className={cn(
                    "grid size-5 shrink-0 place-items-center rounded-full",
                    s.status === "done" && "bg-brand text-slate-950",
                    s.status === "started" && "text-brand",
                    s.status === "error" && "bg-red-500 text-white",
                    s.status === "pending" && "text-muted-foreground/50",
                  )}
                >
                  {s.status === "done" ? (
                    <Check className="size-3" strokeWidth={3} />
                  ) : s.status === "started" ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : s.status === "error" ? (
                    <AlertCircle className="size-3.5" />
                  ) : (
                    <Circle className="size-2" />
                  )}
                </span>
                <span className={cn("flex-1 text-sm", s.status === "pending" && "text-muted-foreground")}>{n.label}</span>
                {s.ev && <ProviderBadge meta={s.ev.meta} />}
                {s.ev && <ChevronDown className={cn("size-3.5 text-muted-foreground transition", isOpen && "rotate-180")} />}
              </button>
              {showMsg && s.message && <p className="mt-1 ml-[30px] text-xs leading-snug text-muted-foreground">{s.message}</p>}
              <AnimatePresence>
                {isOpen && s.ev && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                    <div className="mt-2 ml-[30px] space-y-1">
                      {s.progress.map((p, k) => (
                        <p key={k} className="text-[11px] text-sky-400/90">↳ {p}</p>
                      ))}
                      <p className="mono text-[10px] text-muted-foreground">
                        {n.ai ? `prompt: backend/app/prompts/${n.id === "verify_citations" ? "judge_citations" : n.id}.md` : "plain Python, no AI"}
                        {s.ev.meta?.model ? ` · ${s.ev.meta.model}` : ""}
                        {s.ev.elapsed_ms != null ? ` · ${s.ev.elapsed_ms} ms` : ""}
                      </p>
                      <pre className="mono scroll-thin max-h-56 overflow-auto rounded-lg bg-muted/60 p-2 text-[10.5px] leading-snug">
                        {JSON.stringify(s.ev.output, null, 2)}
                      </pre>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </li>
          );
        })}
      </ol>
      {!running && <p className="mt-3 px-1 text-[11px] text-muted-foreground">Click a step to see its output.</p>}
    </div>
  );
}
