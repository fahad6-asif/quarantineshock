"use client";

import { BarChart3, Moon, Settings, Sun } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { api, type ProviderHealth } from "@/lib/api";
import { cn } from "cn";

export function useTheme() {
  const [dark, setDark] = useState(true);
  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);
  const toggle = () => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("qs-theme", next ? "dark" : "light");
    } catch {}
    setDark(next);
    window.dispatchEvent(new Event("qs-theme"));
  };
  return { dark, toggle };
}

/** One dot: green when the AI provider (or offline replay) is ready, amber/red otherwise. Details on hover. */
export function ProviderPill({ mode, refreshKey }: { mode: string; refreshKey: number }) {
  const [h, setH] = useState<ProviderHealth | null>(null);
  useEffect(() => {
    let alive = true;
    if (mode === "replay") return;
    api.providers().then((x) => alive && setH(x)).catch(() => alive && setH(null));
    return () => {
      alive = false;
    };
  }, [mode, refreshKey]);
  const g = h?.gemini.status;
  // no keys at all (e.g. the public demo): everything is served from the saved answers, which is fine
  const savedOnly = g === "not_configured" && h?.openrouter.status === "not_configured";
  const ok = mode === "replay" || savedOnly || g === "ok" || h?.openrouter.status === "ok";
  const label =
    mode === "replay" ? "Offline replay" : savedOnly ? "Saved answers" : ok ? "AI ready" : g ? "AI issue" : "Checking AI…";
  const title =
    mode === "replay" ? "Replay mode: saved answers only, no internet needed" : `Mode: ${mode} · Gemini: ${g ?? "?"} · OpenRouter: ${h?.openrouter.status ?? "?"}`;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground" title={title}>
      <span className={cn("size-2 rounded-full", !h && mode !== "replay" ? "animate-pulse bg-slate-400" : ok ? "bg-emerald-400" : "bg-amber-400")} />
      {label}
    </span>
  );
}

export function Header({ mode, onSettings, refreshKey }: { mode: string; onSettings: () => void; refreshKey: number }) {
  const { dark, toggle } = useTheme();
  const icon = "inline-flex size-9 items-center justify-center rounded-xl text-muted-foreground hover:bg-muted hover:text-foreground";
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 px-4">
      <Link href="/" className="flex items-center gap-2" title="Back to the story">
        <Logo className="size-7" />
        <span className="font-semibold tracking-tight">QuarantineShock</span>
      </Link>
      <div className="flex items-center gap-1">
        <ProviderPill mode={mode} refreshKey={refreshKey} />
        <span className="mx-2 h-5 w-px bg-border" />
        <Link href="/app/evals" className={cn(icon, "w-auto gap-1.5 px-3 text-sm")} aria-label="Evals">
          <BarChart3 className="size-4" /> Evals
        </Link>
        <button onClick={toggle} className={icon} aria-label="Toggle theme">
          {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </button>
        <button onClick={onSettings} className={icon} aria-label="Settings">
          <Settings className="size-4" />
        </button>
      </div>
    </header>
  );
}
