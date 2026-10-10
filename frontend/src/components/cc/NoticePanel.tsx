"use client";

import { ExternalLink, Loader2 } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { cn } from "cn";
import { api, type NoticeDetail } from "@/lib/api";
import { fmtDate } from "./bits";

export function NoticePanel({ noticeId }: { noticeId: string | null }) {
  const [d, setD] = useState<NoticeDetail | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  useEffect(() => {
    setD(null);
    if (noticeId) api.notice(noticeId).then(setD).catch(() => setD(null));
  }, [noticeId]);

  if (!noticeId) return <p className="p-6 text-sm text-muted-foreground">Select a notice.</p>;
  if (!d) return <Loader2 className="m-6 size-5 animate-spin text-muted-foreground" />;

  // highlighted spans of the notice text (non-overlapping, in order)
  const spans = [...d.highlights].sort((a, b) => a.start - b.start).filter((s, i, arr) => i === 0 || s.start >= arr[i - 1].end);
  const pieces: React.ReactNode[] = [];
  let pos = 0;
  spans.forEach((s, i) => {
    pieces.push(<Fragment key={`t${i}`}>{d.text.slice(pos, s.start)}</Fragment>);
    pieces.push(
      <mark key={`m${i}`} className={cn("rounded px-0.5 text-foreground transition", hover === s.field ? "bg-brand/50" : "bg-brand/15")}>
        {d.text.slice(s.start, s.end)}
      </mark>,
    );
    pos = s.end;
  });
  pieces.push(<Fragment key="end">{d.text.slice(pos)}</Fragment>);

  const ex = d.extract;
  const Fact = ({ field, label, value }: { field: string; label: string; value: React.ReactNode }) => (
    <div onMouseEnter={() => setHover(field)} onMouseLeave={() => setHover(null)} className="flex justify-between gap-4 py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );

  return (
    <div className="scroll-thin h-full space-y-4 overflow-y-auto p-4">
      <div>
        <p className="text-xs text-muted-foreground">{fmtDate(d.notice.effective_date, { month: "long", day: "numeric", year: "numeric" })}</p>
        <h3 className="text-base font-semibold">{d.notice.title}</h3>
      </div>

      {ex && (
        <div className="divide-y divide-border rounded-xl border border-border px-3">
          <Fact field="stated_area_sq_mi" label="Zone size" value={ex.stated_area_sq_mi != null ? `${ex.stated_area_sq_mi} sq mi` : "not stated"} />
          <Fact
            field="stated_commercial_acres"
            label="Farm land inside"
            value={ex.stated_commercial_acres ? `${ex.stated_commercial_acres} acres` : ex.stated_commercial_acres === 0 ? "none" : "not stated"}
          />
          {ex.crops_mentioned.length > 0 && <Fact field="crops_mentioned" label="Crops" value={ex.crops_mentioned.join(", ")} />}
          {ex.detections.map((det, i) => (
            <Fact key={i} field={`detections[${i}]`} label={i === 0 ? "Fly found" : ""} value={`${det.place}, ${fmtDate(det.date)}`} />
          ))}
        </div>
      )}

      <div>
        <p className="mb-1.5 text-xs text-muted-foreground">Original text (highlights = what the AI pulled out)</p>
        <div className="rounded-xl bg-muted/40 p-3 text-[13px] leading-relaxed whitespace-pre-wrap">{pieces}</div>
      </div>

      <div className="space-y-1">
        {d.notice.excerpt_of.map((s) => (
          <a key={s.url} href={s.url} target="_blank" rel="noreferrer" className="flex items-start gap-1.5 text-[11px] text-muted-foreground hover:text-foreground">
            <ExternalLink className="mt-0.5 size-3 shrink-0" />
            <span>{s.title}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
