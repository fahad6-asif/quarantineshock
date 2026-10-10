"use client";

import { Gavel } from "lucide-react";
import { useMemo, useState } from "react";
import { cn } from "cn";
import type { ShipmentRow } from "@/lib/api";
import { isFlagged, type Status } from "@/lib/status";
import { fmtDate, NewBadge, StatusChip } from "./bits";

const RANK: Record<Status, number> = { REVIEW: 0, UNCLEAR: 1, NOT_HOST: 2, OUTSIDE: 3 };
const FILTERS = [
  { id: "flagged", label: "Flagged" },
  { id: "changed", label: "Changed" },
  { id: "all", label: "All" },
] as const;

export function ShipmentsTable({
  rows,
  onOpen,
  onHover,
}: {
  rows: ShipmentRow[];
  onOpen: (id: string) => void;
  onHover: (id: string | null) => void;
}) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("flagged");

  const counts = useMemo(
    () => ({ all: rows.length, flagged: rows.filter((r) => isFlagged(r.status)).length, changed: rows.filter((r) => r.changed).length }),
    [rows],
  );
  const shown = useMemo(
    () =>
      rows
        .filter((r) => filter === "all" || (filter === "flagged" ? isFlagged(r.status) : r.changed))
        .sort((a, b) => RANK[a.status] - RANK[b.status] || Number(b.changed) - Number(a.changed) || a.id.localeCompare(b.id)),
    [rows, filter],
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 p-3 pb-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={cn(
              "rounded-full px-3 py-1 text-xs transition",
              filter === f.id ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted",
            )}
          >
            {f.label} <span className="opacity-60">{counts[f.id]}</span>
          </button>
        ))}
      </div>
      <ul className="scroll-thin flex-1 space-y-1 overflow-y-auto px-2 pb-3">
        {shown.map((r) => (
          <li key={r.id}>
            <button
              data-testid={`row-${r.id}`}
              onClick={() => onOpen(r.id)}
              onMouseEnter={() => onHover(r.id)}
              onMouseLeave={() => onHover(null)}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-muted/50"
            >
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5">
                  <span className="truncate text-sm font-medium">{r.product_raw}</span>
                  {r.changed && <NewBadge />}
                </span>
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  {r.id} · {fmtDate(r.pickup_date)}
                  {r.decision && (
                    <span className="inline-flex items-center gap-0.5">
                      · <Gavel className="size-3" />
                      {r.decision.decision === "approve" ? "plan approved" : r.decision.decision === "hold" ? "on hold" : "escalated"}
                    </span>
                  )}
                </span>
              </span>
              <StatusChip status={r.status} />
            </button>
          </li>
        ))}
        {!shown.length && <li className="p-6 text-center text-sm text-muted-foreground">Nothing here.</li>}
      </ul>
      <p className="border-t border-border px-4 py-2 text-[11px] text-muted-foreground">Fictional demo loads</p>
    </div>
  );
}
