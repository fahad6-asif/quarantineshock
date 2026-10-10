"use client";

import { ChevronRight, FileText, ListChecks } from "lucide-react";
import { useState } from "react";
import type { AppState } from "@/lib/api";
import { isFlagged, STATUS, STATUS_ORDER } from "@/lib/status";
import { fmtDate, StatusChip } from "./bits";

/** The need-to-know view: what changed, how many loads are flagged, and which ones to look at. */
export function Overview({
  state,
  hasPrevious,
  onShipment,
  onNotice,
  onSteps,
}: {
  state: AppState | null;
  hasPrevious: boolean;
  onShipment: (id: string) => void;
  onNotice: () => void;
  onSteps: () => void;
}) {
  const [more, setMore] = useState(false);
  if (!state?.processed || !state.shipments) {
    return <p className="p-6 text-sm text-muted-foreground">Process a notice to see the overview.</p>;
  }
  const ships = state.shipments;
  const count = (s: string) => ships.filter((x) => x.status === s).length;
  const changed = ships.filter((s) => s.changed && isFlagged(s.status));
  const toReview = hasPrevious ? changed : ships.filter((s) => isFlagged(s.status));
  const z = state.zone;

  return (
    <div className="scroll-thin h-full space-y-5 overflow-y-auto p-4">
      <div>
        <p className="text-xs text-muted-foreground">{fmtDate(state.notice?.effective_date, { month: "long", day: "numeric", year: "numeric" })}</p>
        <h2 className="text-lg leading-snug font-semibold">{state.notice?.title}</h2>
        {z && (
          <p className="mt-0.5 text-sm text-muted-foreground">
            Zone ≈ {z.official_sq_mi ?? z.area_sq_mi} sq mi
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        {STATUS_ORDER.map((s) => (
          <div key={s} className="rounded-xl border border-border px-3 py-2">
            <div className="text-2xl font-semibold tabular-nums" style={{ color: STATUS[s].color }}>
              {count(s)}
            </div>
            <div className="text-xs text-muted-foreground">{STATUS[s].label}</div>
          </div>
        ))}
      </div>

      <section>
        <h3 className="mb-2 text-sm font-medium">
          {hasPrevious ? "Newly flagged with this notice" : "Flagged loads"}{" "}
          <span className="text-muted-foreground">({toReview.length})</span>
        </h3>
        {toReview.length === 0 ? (
          <p className="rounded-xl bg-muted/40 px-3 py-3 text-sm text-muted-foreground">No new flags with this notice.</p>
        ) : (
          <ul className="space-y-1.5">
            {toReview.map((s) => (
              <li key={s.id}>
                <button
                  onClick={() => onShipment(s.id)}
                  className="flex w-full items-center gap-3 rounded-xl border border-border px-3 py-2 text-left transition hover:border-brand/60 hover:bg-muted/30"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{s.product_raw}</span>
                    <span className="block text-xs text-muted-foreground">
                      {s.id} · pickup {fmtDate(s.pickup_date)}
                    </span>
                  </span>
                  <StatusChip status={s.status} />
                  <ChevronRight className="size-4 text-muted-foreground" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {state.summary && (
        <section>
          <h3 className="mb-1 text-sm font-medium">Summary</h3>
          <p className={`text-sm leading-relaxed text-muted-foreground ${more ? "" : "line-clamp-3"}`}>{state.summary}</p>
          <button onClick={() => setMore(!more)} className="mt-1 text-xs text-brand hover:underline">
            {more ? "Show less" : "Read more"}
          </button>
        </section>
      )}

      <div className="flex gap-2">
        <button onClick={onNotice} className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-border py-2 text-sm hover:bg-muted/40">
          <FileText className="size-4" /> Read the notice
        </button>
        <button onClick={onSteps} className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-border py-2 text-sm hover:bg-muted/40">
          <ListChecks className="size-4" /> Agent steps
        </button>
      </div>
    </div>
  );
}
