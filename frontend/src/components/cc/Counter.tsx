"use client";

import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { cn } from "cn";

export function Counter({ value, hasPrevious }: { value: number; hasPrevious: boolean }) {
  const mv = useMotionValue(0);
  const text = useTransform(mv, (x) => Math.round(x).toString());
  const prev = useRef(0);
  const [shake, setShake] = useState(0);
  useEffect(() => {
    const c = animate(mv, value, { duration: 1.1, ease: "easeOut" });
    if (value > prev.current) setShake((s) => s + 1);
    prev.current = value;
    return () => c.stop();
  }, [value, mv]);
  return (
    <div
      key={shake}
      className={cn(
        "glass flex items-baseline gap-2 rounded-2xl px-4 py-1.5",
        shake > 0 && value > 0 && "qs-shake",
        value > 0 && "border-review/50 shadow-[0_0_30px_-8px_#f59e0b]",
      )}
      role="status"
      aria-live="polite"
    >
      <motion.span
        data-testid="flag-counter"
        data-value={value}
        className={cn("text-2xl font-bold tabular-nums", value > 0 ? "text-review" : "text-muted-foreground")}
      >
        {text}
      </motion.span>
      <span className="text-sm text-muted-foreground">{hasPrevious ? "newly flagged" : "flagged"}</span>
    </div>
  );
}
