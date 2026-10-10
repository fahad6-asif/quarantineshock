"use client";

import { AlertTriangle, ArrowUpRight, Check, ChevronRight, Copy, Gavel, Hand, Loader2, MapPin } from "lucide-react";
import { useEffect, useState } from "react";
import { Layer, Map, Marker, Source } from "react-map-gl/maplibre";
import { toast } from "sonner";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { api, type ShipmentDetail } from "@/lib/api";
import { STATUS } from "@/lib/status";
import { fmtDate, NewBadge, StatusChip, VerifiedBadge } from "./bits";
import { STYLE, useIsDark } from "./MapView";

/** Collapsible section: closed by default so the drawer stays short. */
function Fold({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  return (
    <details open={defaultOpen} className="group rounded-xl border border-border">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-sm font-medium select-none [&::-webkit-details-marker]:hidden">
        <ChevronRight className="size-4 text-muted-foreground transition group-open:rotate-90" />
        {title}
      </summary>
      <div className="space-y-3 px-3 pb-3">{children}</div>
    </details>
  );
}

function CopyArea({ label, value, onChange, rows }: { label: string; value: string; onChange: (v: string) => void; rows: number }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <button
          className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground"
          onClick={() => navigator.clipboard.writeText(value).then(() => toast.success(`${label} copied`))}
        >
          <Copy className="size-3" /> Copy
        </button>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        className="scroll-thin w-full resize-y rounded-lg border border-input bg-transparent p-2 text-[13px] leading-relaxed outline-none focus:border-ring"
      />
    </div>
  );
}

function MiniMap({ d }: { d: ShipmentDetail }) {
  const dark = useIsDark();
  const s = d.shipment;
  if (s.lat == null || s.lon == null) {
    return <p className="text-sm text-muted-foreground">No coordinates in the schedule, so the zone check could not run.</p>;
  }
  const dist = d.status.distance_mi;
  return (
    <div className="space-y-1.5">
      <div className="h-44 overflow-hidden rounded-xl">
        <Map
          initialViewState={{ longitude: s.lon, latitude: s.lat, zoom: 10.3 }}
          mapStyle={dark ? STYLE.dark : STYLE.light}
          interactive={false}
          attributionControl={false}
          style={{ width: "100%", height: "100%" }}
        >
          <Source id="mz" type="geojson" data={d.zones}>
            <Layer id="mz-fill" type="fill" paint={{ "fill-color": "#f59e0b", "fill-opacity": 0.18 }} />
            <Layer id="mz-line" type="line" paint={{ "line-color": "#f59e0b", "line-width": 2 }} />
          </Source>
          <Marker longitude={s.lon} latitude={s.lat}>
            <span className="block size-4 rounded-full border-2 border-white shadow-lg" style={{ background: STATUS[d.status.status].color }} />
          </Marker>
        </Map>
      </div>
      <p className="text-xs text-muted-foreground">
        <MapPin className="mr-1 inline size-3" />
        {dist == null ? "No active zone on the pickup date." : dist >= 0 ? `${dist.toFixed(1)} mi inside the zone edge.` : `${Math.abs(dist).toFixed(1)} mi outside the zone edge.`}{" "}
        Zone edges are approximate.
      </p>
    </div>
  );
}

const DECISION_LABEL: Record<string, string> = { approve: "Review plan approved", hold: "On hold", escalate: "Escalated" };

export function ShipmentDrawer({
  shipmentId,
  noticeId,
  onClose,
  onDecided,
  onSource,
}: {
  shipmentId: string | null;
  noticeId: string | null;
  onClose: () => void;
  onDecided: () => void;
  onSource: (chunkId: string, quote?: string) => void;
}) {
  const [d, setD] = useState<ShipmentDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [checks, setChecks] = useState<Record<number, boolean>>({});
  const [email, setEmail] = useState("");
  const [driver, setDriver] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    if (!shipmentId || !noticeId) return; // keep the last content visible while the sheet animates closed
    setD(null);
    setErr(null);
    setChecks({});
    setNote("");
    api
      .shipment(shipmentId, noticeId)
      .then((x) => {
        setD(x);
        setEmail(x.pack ? `Subject: ${x.pack.email_subject}\n\n${x.pack.email_body}` : "");
        setDriver(x.pack?.driver_hold_note ?? "");
      })
      .catch((e) => setErr(e.message));
  }, [shipmentId, noticeId]);

  const decide = async (decision: "approve" | "hold" | "escalate") => {
    if (!d || !noticeId) return;
    setSaving(decision);
    try {
      await api.decide(d.shipment.id, { decision, notice_id: noticeId, note });
      const label = { approve: "Review plan approved", hold: "Shipment on hold", escalate: "Escalated to compliance lead" }[decision];
      toast.success(`${d.shipment.id}: ${label}`, { description: "Saved to the audit log." });
      setD(await api.shipment(d.shipment.id, noticeId));
      onDecided();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setSaving(null);
    }
  };

  const flagged = d && (d.status.status === "REVIEW" || d.status.status === "UNCLEAR");
  const last = d?.decisions.at(-1);
  const n = d?.normalized;
  const verified = d?.evidence.filter((e) => e.verification?.verified).length ?? 0;

  return (
    <Sheet open={!!shipmentId} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-lg">
        <SheetHeader className="pb-2">
          <SheetDescription className="flex items-center gap-2 text-xs">
            {shipmentId} {d?.status.changed_since_previous_notice && <NewBadge />}
          </SheetDescription>
          <SheetTitle className="text-xl leading-snug">{d ? d.shipment.product_raw : "Loading…"}</SheetTitle>
          {d && (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <StatusChip status={d.status.status} size="md" />
                {last && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs">
                    <Gavel className="size-3" /> {DECISION_LABEL[last.decision]}
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                Pickup {fmtDate(d.shipment.pickup_date, { weekday: "short", month: "short", day: "numeric" })} ·{" "}
                {d.shipment.origin_name.replace(" (fictional)", "")}
              </p>
            </div>
          )}
        </SheetHeader>

        <div className="scroll-thin flex-1 space-y-4 overflow-y-auto px-4 pb-6">
          {err && <p className="text-sm text-red-400">{err}</p>}
          {!d && !err && <Loader2 className="size-5 animate-spin text-muted-foreground" />}
          {d && (
            <>
              <section className="space-y-1.5">
                <h3 className="text-sm font-medium">Why</h3>
                {d.pack ? (
                  <p className="text-[15px] leading-relaxed">{d.pack.explanation}</p>
                ) : (
                  <p className="text-[15px] leading-relaxed">{d.status.reasons.map((r) => r.text).join(" ")}</p>
                )}
                {d.status.changed_since_previous_notice && d.status.previous_status && (
                  <p className="text-xs text-muted-foreground">Was: {STATUS[d.status.previous_status].label}</p>
                )}
                {d.pack?.wording_warning && (
                  <p className="flex items-center gap-1 text-xs text-amber-400">
                    <AlertTriangle className="size-3" /> {d.pack.wording_warning}
                  </p>
                )}
              </section>

              {flagged && (
                <section className="space-y-2">
                  <div className="grid grid-cols-3 gap-2">
                    <button onClick={() => decide("approve")} disabled={!!saving} className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-emerald-500/12 px-2 py-2.5 text-sm font-medium text-emerald-500 hover:bg-emerald-500/20 disabled:opacity-50">
                      {saving === "approve" ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />} Approve plan
                    </button>
                    <button onClick={() => decide("hold")} disabled={!!saving} className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-review px-2 py-2.5 text-sm font-semibold text-slate-950 hover:opacity-90 disabled:opacity-50">
                      {saving === "hold" ? <Loader2 className="size-4 animate-spin" /> : <Hand className="size-4" />} Hold shipment
                    </button>
                    <button onClick={() => decide("escalate")} disabled={!!saving} className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-unclear/12 px-2 py-2.5 text-sm font-medium text-unclear hover:bg-unclear/20 disabled:opacity-50">
                      {saving === "escalate" ? <Loader2 className="size-4 animate-spin" /> : <ArrowUpRight className="size-4" />} Escalate
                    </button>
                  </div>
                  <input
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    onKeyDown={(e) => e.stopPropagation()}
                    placeholder="Add a note (optional)"
                    className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus:border-ring"
                  />
                </section>
              )}

              {d.pack && (
                <section className="space-y-1.5">
                  <h3 className="text-sm font-medium">To confirm</h3>
                  <ul className="space-y-1.5">
                    {d.pack.checklist.map((c, i) => (
                      <li key={i}>
                        <label className="flex cursor-pointer gap-2 text-sm leading-snug">
                          <input
                            type="checkbox"
                            className="mt-0.5 size-4 shrink-0 accent-[#a3e635]"
                            checked={!!checks[i]}
                            onChange={(e) => setChecks((s) => ({ ...s, [i]: e.target.checked }))}
                          />
                          <span className={checks[i] ? "text-muted-foreground line-through" : ""}>{c.replace(/^Confirm whether /, "")}</span>
                        </label>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <div className="space-y-2 pt-1">
                {d.evidence.length > 0 && (
                  <Fold title={`Rule evidence · ${verified}/${d.evidence.length} verified`}>
                    {d.evidence.map((e, i) => (
                      <div key={i} className="space-y-1.5 border-b border-border pb-3 last:border-0 last:pb-0">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-xs font-medium">
                            {e.kind === "rule" ? `Rule ${e.id}` : e.kind === "ambiguity" ? "Open question" : "Host list"}
                          </span>
                          <VerifiedBadge v={e.verification} />
                        </div>
                        <blockquote className="mono border-l-2 border-brand/70 pl-2.5 text-[12px] leading-relaxed">&ldquo;{e.quote}&rdquo;</blockquote>
                        {e.source && (
                          <button
                            onClick={() => (e.chunk_id ? onSource(e.chunk_id, e.quote) : e.source?.url && window.open(e.source.url, "_blank"))}
                            className="inline-flex items-center gap-1 text-[11px] text-brand hover:underline"
                          >
                            {e.source.title} <ArrowUpRight className="size-3" />
                          </button>
                        )}
                      </div>
                    ))}
                  </Fold>
                )}
                {d.pack && (
                  <Fold title="Draft email & driver note">
                    <CopyArea label="Email to compliance" value={email} onChange={setEmail} rows={6} />
                    <CopyArea label="Driver hold note" value={driver} onChange={setDriver} rows={2} />
                  </Fold>
                )}
                <Fold title="Map">
                  <MiniMap d={d} />
                </Fold>
                <Fold title="Details">
                  <ul className="space-y-1 text-xs text-muted-foreground">
                    {d.status.reasons.map((r, i) => (
                      <li key={i}>
                        <span className="mono mr-1.5 rounded bg-muted px-1 text-[10px]">{r.code}</span>
                        {r.text}
                      </li>
                    ))}
                  </ul>
                  {n && (
                    <p className="text-xs text-muted-foreground">
                      Label read as <b className="text-foreground">{n.canonical_commodity}</b> ({n.form}) · match {Math.round(n.confidence * 100)}% · host
                      status from {n.host_source}
                      {n.federal_host != null && ` (federal ${n.federal_host ? "yes" : "no"}, California ${n.state_host ? "yes" : "no"})`}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    {d.shipment.quantity} · to {d.shipment.destination} · {d.shipment.carrier}
                  </p>
                  {d.decisions.length > 0 && (
                    <ul className="space-y-0.5 text-[11px] text-muted-foreground">
                      {d.decisions.map((x, i) => (
                        <li key={i}>
                          {new Date(x.created_at).toLocaleString()} · {x.decision}
                          {x.note ? ` · ${x.note}` : ""}
                        </li>
                      ))}
                    </ul>
                  )}
                </Fold>
              </div>
              <p className="text-[11px] text-muted-foreground">Decision support only. A person decides; the tool never clears a load.</p>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
