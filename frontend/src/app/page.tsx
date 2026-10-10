"use client";

import { animate, AnimatePresence, motion, useMotionValue, useTransform } from "framer-motion";
import { ArrowLeft, ArrowRight, ExternalLink, Rocket } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Logo } from "@/components/Logo";

const DA16 = "https://www.aphis.usda.gov/news/program-update/aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-area-california";
const DA36 = "https://www.aphis.usda.gov/news/program-update/aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-san-diego-county";
const CDFA_NOTICE = "https://www.sandiegocounty.gov/content/dam/sdc/awm/docs/MXFF_PEP_SpringValley_SanDiegoCounty_Amd2_20260624_SoF.pdf";

function SourceTag({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="mono inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-3 py-1 text-xs text-muted-foreground transition hover:text-foreground"
    >
      Source: {children} <ExternalLink className="size-3" />
    </a>
  );
}

function CountUp({ to, decimals = 1, run }: { to: number; decimals?: number; run: boolean }) {
  const v = useMotionValue(0);
  const text = useTransform(v, (x) => x.toFixed(decimals));
  useEffect(() => {
    if (!run) return;
    v.set(0);
    const c = animate(v, to, { duration: 1.8, ease: [0.16, 1, 0.3, 1], delay: 0.35 });
    return () => c.stop();
  }, [run, to, v]);
  return <motion.span>{text}</motion.span>;
}

const CARDS = [
  {
    key: "april",
    render: () => (
      <>
        <p className="text-sm text-muted-foreground">April 2026 · San Diego County</p>
        <h1 className="mt-4 text-5xl leading-tight font-semibold text-balance md:text-7xl">
          A fruit fly quarantine with <span className="text-brand">no commercial agriculture</span>.
        </h1>
        <div className="mt-10">
          <SourceTag href={DA16}>USDA APHIS DA-2026-16</SourceTag>
        </div>
      </>
    ),
  },
  {
    key: "june",
    render: (active: boolean) => (
      <>
        <p className="text-sm text-muted-foreground">Two months later · June 18, 2026</p>
        <div className="mt-4 flex items-baseline gap-4">
          <span className="text-8xl font-semibold tabular-nums text-review md:text-[10rem] md:leading-none">
            <CountUp to={338.5} run={active} />
          </span>
          <span className="text-3xl text-muted-foreground">acres</span>
        </div>
        <h2 className="mt-6 text-3xl font-semibold text-balance md:text-5xl">of farms suddenly inside the zone.</h2>
        <div className="mt-10">
          <SourceTag href={DA36}>USDA APHIS DA-2026-36</SourceTag>
        </div>
      </>
    ),
  },
  {
    key: "risk",
    render: () => (
      <>
        <p className="text-sm text-muted-foreground">The problem</p>
        <h2 className="mt-4 text-5xl leading-tight font-semibold text-balance md:text-7xl">
          Every truck checked against legal text, <span className="text-unclear">read by hand</span>.
        </h2>
        <p className="mt-8 text-xl text-muted-foreground">
          <span className="font-semibold text-foreground">$3.3 billion</span> of California host crops at risk.
        </p>
        <div className="mt-6">
          <SourceTag href={CDFA_NOTICE}>CDFA, June 2026</SourceTag>
        </div>
      </>
    ),
  },
  {
    key: "product",
    render: () => (
      <>
        <Logo className="size-16" />
        <h2 className="mt-6 text-5xl font-semibold md:text-7xl">QuarantineShock</h2>
        <p className="mt-4 text-2xl text-muted-foreground md:text-3xl">
          Notice in. Rules out. <span className="text-brand">Shipments flagged.</span>
        </p>
        <Link
          href="/app"
          className="mt-12 inline-flex items-center gap-2 rounded-2xl bg-brand px-7 py-4 text-lg font-semibold text-slate-950 shadow-[0_0_40px_-8px_var(--brand)] transition hover:scale-[1.03]"
        >
          <Rocket className="size-5" /> Launch Command Center
        </Link>
      </>
    ),
  },
];

export default function Story() {
  const [i, setI] = useState(0);
  const router = useRouter();
  const next = useCallback(() => {
    if (i === CARDS.length - 1) router.push("/app");
    else setI((x) => Math.min(x + 1, CARDS.length - 1));
  }, [i, router]);
  const prev = useCallback(() => setI((x) => Math.max(x - 1, 0)), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "Enter") {
        e.preventDefault();
        next();
      }
      if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev]);

  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-brand/10 blur-3xl" />
      <header className="flex items-center justify-between px-6 py-5 md:px-12">
        <div className="flex items-center gap-2.5">
          <Logo className="size-8" />
          <span className="font-semibold tracking-tight">QuarantineShock</span>
        </div>
        <Link href="/app" className="text-sm text-muted-foreground hover:text-foreground">
          Skip intro →
        </Link>
      </header>

      <section className="flex flex-1 items-center px-6 md:px-12">
        <div className="mx-auto w-full max-w-5xl">
          <AnimatePresence mode="wait">
            <motion.div
              key={CARDS[i].key}
              initial={{ opacity: 0, y: 24, filter: "blur(6px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -16, filter: "blur(6px)" }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              {CARDS[i].render(true)}
            </motion.div>
          </AnimatePresence>
        </div>
      </section>

      <div className="flex items-center justify-between px-6 pb-4 md:px-12">
        <div className="flex gap-2">
          {CARDS.map((c, k) => (
            <button
              key={c.key}
              aria-label={`Go to card ${k + 1}`}
              onClick={() => setI(k)}
              className={`h-1.5 rounded-full transition-all ${k === i ? "w-10 bg-brand" : "w-4 bg-muted"}`}
            />
          ))}
        </div>
        <div className="flex gap-2">
          <button
            onClick={prev}
            disabled={i === 0}
            className="glass inline-flex size-11 items-center justify-center disabled:opacity-30"
            aria-label="Previous"
          >
            <ArrowLeft className="size-5" />
          </button>
          <button onClick={next} className="glass inline-flex h-11 items-center gap-2 px-5 font-medium" aria-label="Next">
            {i === CARDS.length - 1 ? "Launch" : "Next"} <ArrowRight className="size-5" />
          </button>
        </div>
      </div>
      <footer className="px-6 pb-5 text-center text-xs text-muted-foreground md:px-12">
        Real public notices · fictional shipments · decision support, not legal advice.
      </footer>
    </main>
  );
}