"use client";

import { ExternalLink, FileText, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { api, type SourcePassage } from "@/lib/api";

/** Shows the exact source passage behind a citation, with neighbours for context and a highlighted quote. */
export function SourceSheet({ chunkId, quote, onClose }: { chunkId: string | null; quote?: string | null; onClose: () => void }) {
  const [p, setP] = useState<SourcePassage | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    setP(null);
    setErr(null);
    if (chunkId) api.source(chunkId).then(setP).catch((e) => setErr(e.message));
  }, [chunkId]);

  const mark = (text: string) => {
    if (!quote) return text;
    const norm = (s: string) => s.replace(/\s+/g, " ").toLowerCase();
    const i = norm(text).indexOf(norm(quote).slice(0, 80));
    if (i < 0) return text;
    // map back approximately: text already whitespace-normalized by the backend chunker
    const end = Math.min(text.length, i + quote.length);
    return (
      <>
        {text.slice(0, i)}
        <mark className="rounded bg-brand/30 px-0.5 text-foreground">{text.slice(i, end)}</mark>
        {text.slice(end)}
      </>
    );
  };

  return (
    <Sheet open={!!chunkId} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full data-[side=right]:w-full data-[side=right]:sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <FileText className="size-4" /> Source passage
          </SheetTitle>
          <SheetDescription className="mono text-xs">{chunkId}</SheetDescription>
        </SheetHeader>
        <div className="scroll-thin flex-1 space-y-3 overflow-y-auto px-4 pb-6">
          {err && <p className="text-sm text-red-400">{err}</p>}
          {!p && !err && <Loader2 className="size-5 animate-spin text-muted-foreground" />}
          {p && (
            <>
              <div className="rounded-xl border border-border p-3">
                <p className="text-sm font-medium">{p.doc.title}</p>
                <p className="text-xs text-muted-foreground">
                  {p.doc.publisher}
                  {p.doc.date ? ` · ${p.doc.date}` : ""}
                </p>
                {p.doc.url && (
                  <a href={p.doc.url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs text-brand hover:underline">
                    Open original <ExternalLink className="size-3" />
                  </a>
                )}
              </div>
              {p.before && <p className="mono text-[11.5px] leading-relaxed text-muted-foreground/60">…{p.before.slice(-280)}</p>}
              <blockquote className="mono rounded-xl border-l-2 border-brand bg-muted/40 p-3 text-[12px] leading-relaxed">{mark(p.text)}</blockquote>
              {p.after && <p className="mono text-[11.5px] leading-relaxed text-muted-foreground/60">{p.after.slice(0, 280)}…</p>}
              <p className="text-[11px] text-muted-foreground">Text extracted verbatim from the downloaded original and stored in sources/.</p>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
