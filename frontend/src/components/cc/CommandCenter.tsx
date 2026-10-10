"use client";

import { FastForward, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError, subscribeRun, type AppState, type NoticeSummary, type RunEvent } from "@/lib/api";
import { isFlagged } from "@/lib/status";
import { AgentActivity } from "./AgentActivity";
import { fmtDate } from "./bits";
import { ChatPanel } from "./ChatPanel";
import { Counter } from "./Counter";
import { Header } from "./Header";
import { MapView } from "./MapView";
import { NoticePanel } from "./NoticePanel";
import { Overview } from "./Overview";
import { SettingsDialog } from "./SettingsDialog";
import { ShipmentDrawer } from "./ShipmentDrawer";
import { ShipmentsTable } from "./ShipmentsTable";
import { SourceSheet } from "./SourceSheet";
import { Timeline } from "./Timeline";

const FF_DATE = "2026-06-16";

export function CommandCenter() {
  const [notices, setNotices] = useState<NoticeSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [state, setState] = useState<AppState | null>(null);
  const [animateKey, setAnimateKey] = useState(0);
  const [tab, setTab] = useState("overview");
  const [running, setRunning] = useState<string | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [drawer, setDrawer] = useState<string | null>(null);
  const [source, setSource] = useState<{ id: string; quote?: string } | null>(null);
  const [noticeOpen, setNoticeOpen] = useState(false);
  const [hoverShip, setHoverShip] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mode, setMode] = useState("auto");
  const [pillKey, setPillKey] = useState(0);
  const [ffBusy, setFfBusy] = useState(false);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const unsub = useRef<(() => void) | null>(null);

  const processed = notices.filter((n) => n.processed);
  const ffTarget = notices.find((n) => n.effective_date === FF_DATE)?.id ?? null;

  const refreshNotices = useCallback(async () => {
    const ns = await api.notices();
    setNotices(ns);
    setLoadErr(null);
    return ns;
  }, []);

  const loadState = useCallback(async (id: string, animate = false) => {
    const s = await api.state(id);
    setState(s);
    if (animate) setAnimateKey((k) => k + 1);
    return s;
  }, []);

  // initial load: latest processed notice
  useEffect(() => {
    refreshNotices()
      .then((ns) => {
        const last = [...ns].reverse().find((n) => n.processed);
        if (last) setSelected(last.id);
      })
      .catch((e) => setLoadErr(e.message));
    api.settings().then((s) => setMode(s.provider_mode)).catch(() => {});
  }, [refreshNotices]);

  // when the selection changes (and no run is streaming), load state + stored agent steps
  useEffect(() => {
    if (!selected) return;
    loadState(selected).catch((e) => toast.error(e.message));
    if (running) return;
    const n = notices.find((x) => x.id === selected);
    if (n?.run_id) api.run(n.run_id).then((r) => setEvents(r.events)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const processNext = useCallback(async () => {
    if (running) return;
    const next = notices.find((n) => !n.processed);
    if (!next) {
      toast.info("All notices are processed. Use ← → to move between them.");
      return;
    }
    let runId: string;
    try {
      ({ run_id: runId } = await api.startRun(next.id));
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Could not start the run");
      return;
    }
    setRunning(next.id);
    setEvents([]);
    setTab("activity");
    unsub.current?.();
    unsub.current = subscribeRun(
      runId,
      (ev) => {
        setEvents((all) => [...all, ev]);
        if (ev.toast) (ev.status === "error" ? toast.error : toast.warning)(ev.toast);
      },
      async () => {
        setRunning(null);
        const r = await api.run(runId).catch(() => null);
        await refreshNotices();
        if (r?.status === "done") {
          setSelected(next.id);
          await loadState(next.id, true);
          setTab("overview");
          setPillKey((k) => k + 1);
        } else if (r?.error) {
          toast.error(r.error);
        }
      },
    );
  }, [notices, running, refreshNotices, loadState]);

  useEffect(() => () => unsub.current?.(), []);

  const scrub = useCallback(
    (dir: -1 | 1) => {
      if (!processed.length || running) return;
      const i = processed.findIndex((n) => n.id === selected);
      const j = Math.max(0, Math.min(processed.length - 1, (i < 0 ? processed.length - 1 : i) + dir));
      setSelected(processed[j].id);
    },
    [processed, selected, running],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t.closest("input, textarea, select, [contenteditable=true]") || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "n" || e.key === "N") processNext();
      if (e.key === "ArrowLeft") scrub(-1);
      if (e.key === "ArrowRight") scrub(1);
      if (e.key === "Escape") {
        setDrawer(null);
        setSource(null);
        setNoticeOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [processNext, scrub]);

  // Clears runs + decisions, then the backend re-processes the notices up to June 16 (from cache when warm).
  const fastForward = useCallback(async () => {
    if (!ffTarget) return;
    setFfBusy(true);
    setEvents([]);
    try {
      await api.reset(ffTarget);
      for (;;) {
        await new Promise((r) => setTimeout(r, 700));
        const st = await api.demoStatus();
        await refreshNotices();
        if (!st.running) {
          if (st.error) toast.error(st.error);
          break;
        }
      }
      setSelected(ffTarget);
      await loadState(ffTarget, true);
      setTab("overview");
      toast.success("Ready at June 16. Press N for the next notice.");
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setFfBusy(false);
    }
  }, [ffTarget, refreshNotices, loadState]);

  const onReset = async (ff: boolean) => {
    if (ff) {
      await fastForward();
    } else {
      await api.reset();
      setState(null);
      setSelected(null);
      setEvents([]);
      await refreshNotices();
      toast.success("Demo reset.");
    }
    setSettingsOpen(false);
  };

  const selIdx = processed.findIndex((n) => n.id === selected);
  const flaggedNow = state?.shipments?.filter((s) => isFlagged(s.status)).length ?? 0;
  const hasPrev = selIdx > 0;
  const counterValue = hasPrev ? (state?.counts?.newly_flagged ?? 0) : flaggedNow;
  const shown = state?.processed ? state : null;

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Header mode={mode} onSettings={() => setSettingsOpen(true)} refreshKey={pillKey} />
      <main className="grid min-h-0 flex-1 grid-cols-[220px_minmax(0,1fr)_380px] gap-3 px-3 pb-3 xl:grid-cols-[250px_minmax(0,1fr)_420px]">
        <aside className="glass min-h-0 overflow-hidden">
          <Timeline notices={notices} selected={selected} running={running} onSelect={setSelected} onProcessNext={processNext} />
        </aside>

        <section className="relative min-h-0 min-w-0">
          <MapView state={shown} animateKey={animateKey} onShipment={setDrawer} highlight={hoverShip} />
          {shown && (
            <div className="pointer-events-none absolute top-3 left-1/2 -translate-x-1/2">
              <Counter value={counterValue} hasPrevious={hasPrev} />
            </div>
          )}
          {!processed.length && !running && (
            <div className="absolute inset-0 grid place-items-center bg-background/40 backdrop-blur-[2px]">
              <div className="glass max-w-sm space-y-3 p-6 text-center">
                {loadErr ? (
                  <p className="text-sm text-red-400">{loadErr}</p>
                ) : (
                  <>
                    <h2 className="text-lg font-semibold">Start the demo</h2>
                    <p className="text-sm text-muted-foreground">Jump to June 16, then press N for the June 18 notice.</p>
                    <button
                      onClick={() => fastForward()}
                      disabled={ffBusy || !ffTarget}
                      className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-2 font-semibold text-slate-950 disabled:opacity-60"
                    >
                      {ffBusy ? <Loader2 className="size-4 animate-spin" /> : <FastForward className="size-4" />}
                      {ffBusy ? "Getting ready…" : "Jump to June 16"}
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </section>

        <aside className="glass flex min-h-0 flex-col overflow-hidden">
          <Tabs value={tab} onValueChange={(v) => setTab(String(v))} className="flex min-h-0 flex-1 flex-col gap-0">
            <TabsList className="m-2 grid h-9 w-[calc(100%-1rem)] grid-cols-4">
              <TabsTrigger value="overview" className="text-xs">Overview</TabsTrigger>
              <TabsTrigger value="activity" className="text-xs">Agent</TabsTrigger>
              <TabsTrigger value="shipments" className="text-xs">Loads</TabsTrigger>
              <TabsTrigger value="chat" className="text-xs">Ask</TabsTrigger>
            </TabsList>
            <TabsContent value="overview" className="min-h-0 flex-1">
              <Overview
                state={shown}
                hasPrevious={hasPrev}
                onShipment={setDrawer}
                onNotice={() => setNoticeOpen(true)}
                onSteps={() => setTab("activity")}
              />
            </TabsContent>
            <TabsContent value="activity" className="min-h-0 flex-1">
              <AgentActivity events={events} running={!!running} grounding={state?.grounding} />
            </TabsContent>
            <TabsContent value="shipments" className="min-h-0 flex-1">
              {state?.shipments ? (
                <ShipmentsTable rows={state.shipments} onOpen={setDrawer} onHover={setHoverShip} />
              ) : (
                <p className="p-6 text-sm text-muted-foreground">Process a notice to see the loads.</p>
              )}
            </TabsContent>
            <TabsContent value="chat" className="min-h-0 flex-1" keepMounted>
              <ChatPanel onSource={(id, quote) => setSource({ id, quote })} />
            </TabsContent>
          </Tabs>
          <p className="border-t border-border px-4 py-1.5 text-[10px] text-muted-foreground">
            Decision support only · fictional loads · approximate zones
            {state?.notice ? ` · viewing ${fmtDate(state.notice.effective_date)}` : ""}
          </p>
        </aside>
      </main>

      <ShipmentDrawer
        shipmentId={drawer}
        noticeId={selected}
        onClose={() => setDrawer(null)}
        onDecided={() => selected && loadState(selected)}
        onSource={(id, quote) => setSource({ id, quote })}
      />
      <Sheet open={noticeOpen} onOpenChange={setNoticeOpen}>
        <SheetContent side="right" className="w-full gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-lg">
          <SheetHeader className="pb-0">
            <SheetTitle>The notice</SheetTitle>
          </SheetHeader>
          <div className="min-h-0 flex-1">
            <NoticePanel noticeId={running ?? selected} />
          </div>
        </SheetContent>
      </Sheet>
      <SourceSheet chunkId={source?.id ?? null} quote={source?.quote} onClose={() => setSource(null)} />
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        radius={state?.radius}
        onModeChange={(m) => {
          setMode(m);
          setPillKey((k) => k + 1);
        }}
        onReset={onReset}
        fastForwardTarget={ffTarget}
      />
    </div>
  );
}
