"use client";

import { ArrowLeft, CheckCircle2, Loader2, RefreshCw, ShieldAlert, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";
import { Logo } from "@/components/Logo";
import { api, type Evals } from "@/lib/api";
import { fmtDate } from "@/components/cc/bits";

function Card({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`glass p-5 ${className}`}>
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-muted-foreground uppercase">{title}</h2>
      {children}
    </section>
  );
}

function Big({ value, label, tone = "brand" }: { value: string; label: string; tone?: "brand" | "review" | "muted" }) {
  const cls = tone === "brand" ? "text-brand" : tone === "review" ? "text-review" : "text-muted-foreground";
  return (
    <div>
      <div className={`text-4xl font-semibold tabular-nums ${cls}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

const pct = (x: number | null | undefined) => (x == null ? "-" : `${Math.round(x * 100)}%`);

export default function EvalsPage() {
  const [e, setE] = useState<Evals | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api.evals().then(setE).catch((x) => toast.error(x.message));
  }, []);
  const rerun = async () => {
    setBusy(true);
    try {
      setE(await api.runEvals());
      toast.success("Evals recomputed from the stored runs");
    } catch (x) {
      toast.error((x as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const classes = ["host", "not_host", "unclear"];
  return (
    <main className="mx-auto max-w-6xl space-y-4 p-4 md:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link href="/app" className="glass inline-flex size-9 items-center justify-center rounded-xl" aria-label="Back">
            <ArrowLeft className="size-4" />
          </Link>
          <Logo className="size-8" />
          <div>
            <h1 className="text-xl font-semibold">Evals: the honesty panel</h1>
            <p className="text-xs text-muted-foreground">
              Computed from stored runs{e ? ` · ${e.runs_evaluated} notices · ${new Date(e.computed_at).toLocaleString()}` : ""}
            </p>
          </div>
        </div>
        <button onClick={rerun} disabled={busy} className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60">
          {busy ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />} Re-run evals
        </button>
      </header>

      {!e ? (
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="Commodity normalizer vs answer key">
            <div className="flex flex-wrap gap-8">
              <Big value={pct(e.normalizer.canonical_accuracy)} label={`commodity name correct (n=${e.normalizer.n})`} />
              <Big value={pct(e.normalizer.host_status_accuracy)} label="host status correct" />
            </div>
            <p className={`mt-3 inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs ${e.normalizer.reviewed_by_human ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"}`}>
              {e.normalizer.reviewed_by_human ? <CheckCircle2 className="size-3.5" /> : <TriangleAlert className="size-3.5" />}
              Answer key reviewed by a human: {e.normalizer.reviewed_by_human ? "yes" : "no (draft)"}
            </p>
            <table className="mt-3 w-full text-xs">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="p-1 text-left">label ↓ / predicted →</th>
                  {classes.map((c) => (
                    <th key={c} className="p-1 text-right">{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {classes.map((r) => (
                  <tr key={r} className="border-t border-border">
                    <td className="p-1">{r}</td>
                    {classes.map((c) => (
                      <td key={c} className={`mono p-1 text-right ${r === c ? "font-semibold text-brand" : e.normalizer.confusion[r][c] ? "text-review" : "text-muted-foreground"}`}>
                        {e.normalizer.confusion[r][c]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {e.normalizer.rows.some((r) => !r.canonical_ok || !r.status_ok) && (
              <div className="mt-3 space-y-0.5 text-[11px] text-muted-foreground">
                {e.normalizer.rows
                  .filter((r) => !r.canonical_ok || !r.status_ok)
                  .map((r) => (
                    <p key={r.id}>
                      <span className="mono">{r.id}</span>: expected {r.label} ({r.label_status}), got {r.predicted} ({r.predicted_status})
                    </p>
                  ))}
              </div>
            )}
            <p className="mt-3 text-[11px] text-muted-foreground">Method: {e.normalizer.method}.</p>
          </Card>

          <Card title="Citation grounding">
            <div className="flex flex-wrap gap-8">
              <Big value={e.grounding.verified_pct == null ? "-" : `${e.grounding.verified_pct}%`} label={`quotes verified verbatim (${e.grounding.verified}/${e.grounding.total})`} />
              <Big value={e.grounding.supports_pct == null ? "-" : `${e.grounding.supports_pct}%`} label={`judged to support the claim (${e.grounding.supports}/${e.grounding.judged})`} tone="review" />
            </div>
            <div className="mt-4 h-44">
              <ResponsiveContainer>
                <BarChart data={e.grounding.per_run.map((r) => ({ name: r.notice_id.slice(5, 10), verified: r.verified, unverified: r.total - r.verified, supports: r.supports }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} />
                  <Tooltip contentStyle={{ background: "#0b1222", border: "1px solid #334155", borderRadius: 12, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="verified" stackId="a" fill="#a3e635" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="unverified" stackId="a" fill="#ef4444" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="supports" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Unverified quotes are shown in red in the UI and never used in drafts. Example: a rule quote whose second half was not in CCR 3417 was caught here.
            </p>
          </Card>

          <Card title="Zone accuracy: generated vs official area">
            <div className="h-56">
              <ResponsiveContainer>
                <BarChart data={e.zones.map((z) => ({ name: fmtDate(z.effective_date), generated: z.generated, official: z.official }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} unit=" mi²" width={56} />
                  <Tooltip contentStyle={{ background: "#0b1222", border: "1px solid #334155", borderRadius: 12, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="official" fill="#64748b" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="generated" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
              {e.zones.map((z) => (
                <span key={z.notice_id} className={`mono rounded-md px-1.5 py-0.5 ${Math.abs(z.error_pct ?? 0) > 25 ? "bg-red-500/10 text-red-400" : "bg-muted text-muted-foreground"}`}>
                  {fmtDate(z.effective_date)}: {z.error_pct != null && z.error_pct > 0 ? "+" : ""}{z.error_pct}%
                </span>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Generated zones are {e.radius?.miles ?? 4.5}-mile circles around town centers (notices don&apos;t give trap addresses). Official
              boundaries follow roads and are widened so commercial host properties aren&apos;t split (CCR 3417(b)(3)), so ours run smaller.
            </p>
          </Card>

          <Card title="Rule extraction vs gold rules">
            {e.rules.gold_count === 0 ? (
              <p className="text-sm text-amber-400">
                No gold rules written yet. Fahad writes 6–8 rules by hand in <span className="mono">data/gold_rules.json</span>; this card then scores the
                extractor against them.
              </p>
            ) : (
              <>
                <Big value={`${e.rules.matched}/${e.rules.gold_count}`} label="gold rules found by the extractor" />
                <ul className="mt-3 space-y-1 text-xs">
                  {e.rules.rows.map((r) => (
                    <li key={r.id} className="flex gap-2">
                      {r.matched_rule ? <CheckCircle2 className="size-3.5 shrink-0 text-emerald-400" /> : <ShieldAlert className="size-3.5 shrink-0 text-red-400" />}
                      <span>
                        <span className="mono">{r.id}</span> {r.description} {r.matched_rule && <span className="text-muted-foreground">→ {r.matched_rule}</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p className="mt-3 text-[11px] text-muted-foreground">
              {e.rules.extracted_count} rules extracted in the latest run. Method: {e.rules.method}.
            </p>
          </Card>

          <section className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-5 md:col-span-2">
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-400">
              <TriangleAlert className="size-4" /> Limits (always read these)
            </h2>
            <ul className="grid gap-1.5 text-sm md:grid-cols-2">
              <li>• Zones are approximate: town-center detections plus the official 4.5-mile radius, not the legal boundary text.</li>
              <li>• Ambiguous clauses (frozen, processed, mixed products) always go to a human.</li>
              <li>• Shipments, origins and carriers are fictional. Notices and regulations are real and quoted verbatim.</li>
              <li>• Decision support, not legal advice: the tool flags loads for review and never clears them.</li>
            </ul>
          </section>
        </div>
      )}
    </main>
  );
}
