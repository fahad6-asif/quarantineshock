"use client";

import { Download, FastForward, HeartPulse, Loader2, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { API, api, type AppState, type ProviderHealth, type SettingsInfo } from "@/lib/api";

const MODES: { id: string; label: string; help: string }[] = [
  { id: "auto", label: "Auto", help: "Cache first, then Gemini, then OpenRouter, then closest cached answer" },
  { id: "gemini", label: "Gemini", help: "Live Gemini only" },
  { id: "openrouter", label: "OpenRouter", help: "Live OpenRouter only" },
  { id: "replay", label: "Replay", help: "Cache only, zero network (demo insurance)" },
];

export function SettingsDialog({
  open,
  onOpenChange,
  radius,
  onModeChange,
  onReset,
  fastForwardTarget,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  radius: AppState["radius"];
  onModeChange: (mode: string) => void;
  onReset: (fastForward: boolean) => Promise<void>;
  fastForwardTarget: string | null;
}) {
  const [info, setInfo] = useState<SettingsInfo | null>(null);
  const [health, setHealth] = useState<ProviderHealth | null>(null);
  const [checking, setChecking] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (open) api.settings().then(setInfo).catch((e) => toast.error(e.message));
  }, [open]);

  const setMode = async (mode: string) => {
    try {
      const s = await api.setProvider(mode);
      setInfo(s);
      onModeChange(mode);
      toast.success(`Provider for the next run: ${MODES.find((m) => m.id === mode)?.label}`);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const check = async () => {
    setChecking(true);
    try {
      setHealth(await api.providers());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setChecking(false);
    }
  };

  const reset = async (ff: boolean) => {
    setBusy(ff ? "ff" : "reset");
    try {
      await onReset(ff);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Changes apply to the next run. No restart needed.</DialogDescription>
        </DialogHeader>

        <section className="space-y-2">
          <h3 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">LLM provider</h3>
          <div className="grid grid-cols-2 gap-2">
            {MODES.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`rounded-xl border p-2.5 text-left transition ${info?.provider_mode === m.id ? "border-brand bg-brand/10" : "border-border hover:bg-muted/50"}`}
              >
                <div className="text-sm font-medium">{m.label}</div>
                <div className="text-[11px] leading-snug text-muted-foreground">{m.help}</div>
              </button>
            ))}
          </div>
          {info && (
            <p className="mono text-[11px] text-muted-foreground">
              Gemini: {info.gemini.configured ? `${info.gemini.model_fast} / ${info.gemini.model_strong}` : "not configured"} · OpenRouter:{" "}
              {info.openrouter.configured ? info.openrouter.model : "not configured"}
            </p>
          )}
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={check} disabled={checking}>
              {checking ? <Loader2 className="animate-spin" /> : <HeartPulse />} Check provider health
            </Button>
            {health && (
              <span className="text-xs text-muted-foreground">
                Gemini: <b>{health.gemini.status}</b> · OpenRouter: <b>{health.openrouter.status}</b>
              </span>
            )}
          </div>
        </section>

        <section className="space-y-1">
          <h3 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">Quarantine radius</h3>
          {radius ? (
            <p className="text-sm">
              <b>{radius.miles} miles</b>{" "}
              {radius.source === "sources" ? (
                <span className="text-muted-foreground">
                  quoted from the sources ({radius.chunk_id}):{" "}
                  <span className="mono text-xs">&ldquo;{radius.quote}&rdquo;</span>
                </span>
              ) : (
                <span className="text-amber-400">from config: verify</span>
              )}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">Process a notice to see where the radius came from.</p>
          )}
        </section>

        <section className="space-y-2">
          <h3 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">Demo</h3>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => reset(false)} disabled={!!busy}>
              {busy === "reset" ? <Loader2 className="animate-spin" /> : <RotateCcw />} Reset demo
            </Button>
            {fastForwardTarget && (
              <Button size="sm" onClick={() => reset(true)} disabled={!!busy}>
                {busy === "ff" ? <Loader2 className="animate-spin" /> : <FastForward />} Reset &amp; fast-forward to Jun 16
              </Button>
            )}
            <a href={`${API}/api/audit.csv`} className="inline-flex">
              <Button variant="outline" size="sm" render={<span />}>
                <Download /> Export audit log (CSV)
              </Button>
            </a>
          </div>
          <p className="text-[11px] text-muted-foreground">Reset clears runs and decisions; LLM caches are kept.</p>
        </section>
      </DialogContent>
    </Dialog>
  );
}
