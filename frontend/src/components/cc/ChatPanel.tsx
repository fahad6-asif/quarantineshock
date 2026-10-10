"use client";

import { AlertTriangle, BookOpen, Loader2, MessageSquareText, Send } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";
import { api, streamChat, type ChatEvent } from "@/lib/api";
import { ProviderBadge, VerifiedBadge } from "./bits";

type Msg = {
  role: "user" | "assistant";
  text: string;
  done?: Extract<ChatEvent, { type: "done" }>;
  error?: string;
};

const CITE = /\[?([A-Za-z0-9_.\-]+#\d{3})\]?/g;

/** Render answer text with chunk-id citations turned into numbered clickable chips. */
function Answer({ text, ids, onSource }: { text: string; ids: string[]; onSource: (id: string) => void }) {
  const parts: React.ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(CITE)) {
    const id = m[1];
    const idx = ids.indexOf(id);
    parts.push(text.slice(last, m.index));
    parts.push(
      idx >= 0 ? (
        <button
          key={`${m.index}`}
          data-testid="cite-chip"
          onClick={() => onSource(id)}
          className="mx-0.5 inline-flex -translate-y-px items-center rounded-md border border-brand/40 bg-brand/10 px-1 text-[10px] font-semibold text-brand hover:bg-brand/20"
          title={id}
        >
          {idx + 1}
        </button>
      ) : (
        <span key={`${m.index}`} className="mono text-[10px] text-muted-foreground">[{id}]</span>
      ),
    );
    last = (m.index ?? 0) + m[0].length;
  }
  parts.push(text.slice(last));
  return <p className="text-sm leading-relaxed whitespace-pre-wrap">{parts.map((p, i) => <Fragment key={i}>{p}</Fragment>)}</p>;
}

export function ChatPanel({ onSource }: { onSource: (chunkId: string, quote?: string) => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.suggestions().then(setSuggestions).catch(() => {});
  }, []);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [msgs]);

  const ask = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setMsgs((m) => [...m, { role: "user", text: question }, { role: "assistant", text: "" }]);
    const patch = (f: (m: Msg) => Msg) => setMsgs((all) => [...all.slice(0, -1), f(all[all.length - 1])]);
    await streamChat(question, (ev) => {
      if (ev.type === "token") patch((m) => ({ ...m, text: m.text + ev.text }));
      if (ev.type === "done") patch((m) => ({ ...m, text: ev.answer, done: ev }));
      if (ev.type === "error") patch((m) => ({ ...m, error: ev.message }));
    });
    setBusy(false);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="scroll-thin flex-1 space-y-3 overflow-y-auto p-3">
        {!msgs.length && (
          <div className="space-y-3 p-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <MessageSquareText className="size-4 text-brand" /> Ask the Rules
            </div>
            <p className="text-sm text-muted-foreground">Answers come only from the real rules, with sources. Try a question below.</p>
          </div>
        )}
        {msgs.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="ml-8 rounded-2xl rounded-tr-sm bg-brand/15 px-3 py-2 text-sm">{m.text}</div>
          ) : (
            <div key={i} data-testid="chat-answer" data-done={m.done ? "true" : "false"} className="mr-2 space-y-2 rounded-2xl rounded-tl-sm border border-border bg-card/40 p-3">
              {m.error ? (
                <p className="text-sm text-red-400">{m.error}</p>
              ) : m.text ? (
                <Answer text={m.text} ids={m.done?.citations.map((c) => c.chunk_id) ?? []} onSource={(id) => onSource(id, m.done?.quotes.find((q) => q.chunk_id === id)?.quote)} />
              ) : (
                <Loader2 className="size-4 animate-spin text-muted-foreground" />
              )}
              {m.done && (
                <div className="space-y-2 border-t border-border pt-2">
                  {m.done.certainty_warning && (
                    <p className="flex items-center gap-1 text-[11px] text-amber-400">
                      <AlertTriangle className="size-3" /> This answer uses certainty language; treat with care.
                    </p>
                  )}
                  {m.done.citations.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {m.done.citations.map((c, k) => (
                        <button
                          key={c.chunk_id}
                          onClick={() => onSource(c.chunk_id, m.done?.quotes.find((q) => q.chunk_id === c.chunk_id)?.quote)}
                          className="inline-flex max-w-full items-center gap-1 rounded-lg border border-border px-2 py-1 text-[11px] hover:border-brand/60"
                          title={c.chunk_id}
                        >
                          <BookOpen className="size-3 shrink-0 text-brand" />
                          <span className="font-semibold text-brand">{k + 1}</span>
                          <span className="max-w-[200px] truncate">{c.title}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {m.done.quotes.length > 0 && (
                    <details className="group">
                      <summary className="cursor-pointer list-none text-[11px] text-muted-foreground select-none hover:text-foreground [&::-webkit-details-marker]:hidden">
                        ▸ {m.done.quotes.filter((q) => q.verified).length}/{m.done.quotes.length} quotes verified word-for-word · show
                      </summary>
                      <div className="mt-2 space-y-2">
                        {m.done.quotes.map((q, k) => (
                          <div key={k} className="space-y-1">
                            <blockquote className="mono border-l-2 border-brand/60 pl-2 text-[11px] leading-relaxed text-muted-foreground">&ldquo;{q.quote}&rdquo;</blockquote>
                            <VerifiedBadge v={{ verified: q.verified, score: q.score, judge: null }} />
                          </div>
                        ))}
                        <ProviderBadge meta={m.done.meta} />
                      </div>
                    </details>
                  )}
                </div>
              )}
            </div>
          ),
        )}
        <div ref={end} />
      </div>
      <div className="space-y-2 border-t border-border p-3">
        <div className="flex flex-wrap gap-1.5">
          {(msgs.length ? suggestions.slice(0, 2) : suggestions).map((s) => (
            <button
              key={s}
              disabled={busy}
              onClick={() => ask(s)}
              className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground transition hover:border-brand/60 hover:text-foreground disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            placeholder="Ask about the rules…"
            className="h-9 flex-1 rounded-xl border border-input bg-transparent px-3 text-sm outline-none focus:border-ring"
            aria-label="Question"
          />
          <button disabled={busy || !input.trim()} className="grid size-9 place-items-center rounded-xl bg-brand text-slate-950 disabled:opacity-40" aria-label="Send">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
          </button>
        </form>
      </div>
    </div>
  );
}
