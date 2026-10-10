"use client";

import { Check, Loader2, Mail } from "lucide-react";
import { cn } from "cn";
import type { NoticeSummary } from "@/lib/api";
import { fmtDate } from "./bits";

export function Timeline({
  notices,
  selected,
  running,
  onSelect,
  onProcessNext,
}: {
  notices: NoticeSummary[];
  selected: string | null;
  running: string | null;
  onSelect: (id: string) => void;
  onProcessNext: () => void;
}) {
  const nextId = notices.find((n) => !n.processed)?.id;
  return (
    <div className="flex h-full flex-col">
      <h2 className="px-4 pt-4 pb-3 text-xs font-medium text-muted-foreground">Notices</h2>
      <ol className="scroll-thin flex-1 space-y-1 overflow-y-auto px-2 pb-3">
        {notices.map((n) => {
          const isSel = n.id === selected;
          const isRunning = running === n.id;
          const isNext = n.id === nextId && !running;
          const flagged = n.counts?.newly_flagged ?? 0;
          if (isNext) {
            return (
              <li key={n.id}>
                <button
                  onClick={onProcessNext}
                  className="relative w-full overflow-hidden rounded-xl bg-brand px-3 py-2.5 text-left text-slate-950"
                >
                  <span className="qs-ping absolute inset-0 rounded-xl bg-brand/40" aria-hidden />
                  <span className="relative flex items-center gap-2 text-sm font-semibold">
                    <Mail className="size-4" /> New notice received
                    <kbd className="ml-auto rounded bg-slate-950/15 px-1.5 text-[10px]">N</kbd>
                  </span>
                  <span className="relative mt-0.5 block text-xs opacity-80">
                    {fmtDate(n.effective_date)} · {n.title}
                  </span>
                </button>
              </li>
            );
          }
          return (
            <li key={n.id}>
              <button
                onClick={() => n.processed && onSelect(n.id)}
                disabled={!n.processed}
                className={cn(
                  "flex w-full items-start gap-2.5 rounded-xl px-3 py-2 text-left transition",
                  isSel ? "bg-brand/12 ring-1 ring-brand/50" : "hover:bg-muted/50",
                  !n.processed && !isRunning && "opacity-40",
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 grid size-4 shrink-0 place-items-center rounded-full",
                    n.processed ? "bg-brand text-slate-950" : "border border-muted-foreground/50",
                  )}
                >
                  {n.processed && <Check className="size-2.5" strokeWidth={3} />}
                  {isRunning && <Loader2 className="size-3 animate-spin text-brand" />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[11px] text-muted-foreground">{fmtDate(n.effective_date)}</span>
                  <span className="block text-sm leading-snug">{n.title}</span>
                </span>
                {flagged > 0 && (
                  <span className="mt-0.5 rounded-full bg-review/15 px-1.5 text-[11px] font-semibold text-review" title={`${flagged} newly flagged`}>
                    +{flagged}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
