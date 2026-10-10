"use client";

import { transformScale } from "@turf/turf";
import { Bug } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Layer, Map, Marker, NavigationControl, Popup, Source, type MapRef } from "react-map-gl/maplibre";
import "@/lib/maplibre";
import type { AppState, Detection, ShipmentRow } from "@/lib/api";
import { STATUS, STATUS_ORDER } from "@/lib/status";
import { fmtDate, NewBadge, StatusChip } from "./bits";

export const STYLE = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
};
const VIEW = { longitude: -116.985, latitude: 32.775, zoom: 10.15 };
const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

export function useIsDark() {
  const [dark, setDark] = useState(true);
  useEffect(() => {
    const read = () => setDark(document.documentElement.classList.contains("dark"));
    read();
    window.addEventListener("qs-theme", read);
    return () => window.removeEventListener("qs-theme", read);
  }, []);
  return dark;
}

/** Scale the current zone from ~80% to 100% when a new run lands, so the growth is visible. */
function useGrowth(zones: GeoJSON.FeatureCollection | undefined, animateKey: number) {
  const [frame, setFrame] = useState<{ fc: GeoJSON.FeatureCollection; opacity: number }>({ fc: zones ?? EMPTY, opacity: 0.26 });
  const last = useRef(animateKey);
  useEffect(() => {
    const fc = zones ?? EMPTY;
    if (animateKey === last.current) {
      setFrame({ fc, opacity: 0.26 });
      return;
    }
    last.current = animateKey;
    let raf = 0;
    const t0 = performance.now();
    const dur = 1100;
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / dur);
      const e = 1 - Math.pow(1 - p, 3);
      const k = 0.8 + 0.2 * e;
      const scaled: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: fc.features.map((f) =>
          f.properties?.current ? (transformScale(f as GeoJSON.Feature<GeoJSON.Polygon>, k, { origin: "centroid" }) as GeoJSON.Feature) : f,
        ),
      };
      setFrame({ fc: scaled, opacity: 0.08 + 0.18 * e });
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [zones, animateKey]);
  return frame;
}

export function MapView({
  state,
  animateKey,
  onShipment,
  highlight,
}: {
  state: AppState | null;
  animateKey: number;
  onShipment: (id: string) => void;
  highlight: string | null;
}) {
  const dark = useIsDark();
  const mapRef = useRef<MapRef>(null);
  const [hover, setHover] = useState<ShipmentRow | null>(null);
  const [hoverDet, setHoverDet] = useState<Detection | null>(null);
  const growth = useGrowth(state?.zones, animateKey);
  const ships = useMemo(() => (state?.shipments ?? []).filter((s) => s.lat != null && s.lon != null), [state]);
  const zoneColor = "#f59e0b";

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-border">
      <Map
        ref={mapRef}
        initialViewState={VIEW}
        mapStyle={dark ? STYLE.dark : STYLE.light}
        attributionControl={{ compact: true }}
        style={{ width: "100%", height: "100%" }}
        minZoom={7}
        maxZoom={15}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <Source id="prev" type="geojson" data={state?.previous_zones ?? EMPTY}>
          <Layer id="prev-line" type="line" paint={{ "line-color": dark ? "#94a3b8" : "#475569", "line-width": 1.6, "line-dasharray": [3, 2], "line-opacity": 0.85 }} />
        </Source>
        <Source id="zones" type="geojson" data={growth.fc}>
          <Layer
            id="zones-fill"
            type="fill"
            paint={{ "fill-color": zoneColor, "fill-opacity": ["case", ["get", "current"], growth.opacity, growth.opacity * 0.55] }}
          />
          <Layer id="zones-line" type="line" paint={{ "line-color": zoneColor, "line-width": ["case", ["get", "current"], 2.2, 1.2], "line-opacity": 0.9 }} />
        </Source>

        {(state?.detections ?? []).map((d, i) => (
          <Marker key={`d${i}`} longitude={d.lon} latitude={d.lat} anchor="center">
            <div
              className="relative grid size-7 cursor-help place-items-center"
              onMouseEnter={() => setHoverDet(d)}
              onMouseLeave={() => setHoverDet(null)}
              aria-label={`Detection in ${d.place}`}
            >
              <span className="qs-ping absolute inset-0 rounded-full bg-red-500/60" />
              <span className="relative grid size-6 place-items-center rounded-full border-2 border-white/80 bg-red-600 shadow-lg">
                <Bug className="size-3.5 text-white" />
              </span>
            </div>
          </Marker>
        ))}

        {ships.map((s) => {
          const color = STATUS[s.status]?.color ?? "#94a3b8";
          const isNew = s.changed;
          const hl = highlight === s.id;
          return (
            <Marker key={s.id} longitude={s.lon!} latitude={s.lat!} anchor="center" onClick={(e) => { e.originalEvent.stopPropagation(); onShipment(s.id); }}>
              <button
                className="relative grid size-5 place-items-center"
                onMouseEnter={() => setHover(s)}
                onMouseLeave={() => setHover(null)}
                aria-label={`${s.id} ${STATUS[s.status]?.label}`}
              >
                {(isNew || hl) && <span className="qs-ping absolute inset-0 rounded-full" style={{ background: `${hl ? "#a3e635" : color}99` }} />}
                <span
                  className="relative size-3.5 rounded-full border-2 shadow-md transition-transform hover:scale-150"
                  style={{ background: color, borderColor: isNew ? "#a3e635" : dark ? "#0b1222" : "#fff", transform: hl ? "scale(1.5)" : undefined }}
                />
              </button>
            </Marker>
          );
        })}

        {hover && (
          <Popup longitude={hover.lon!} latitude={hover.lat!} closeButton={false} offset={14} anchor="bottom">
            <div className="glass w-60 p-3 text-foreground">
              <div className="flex items-center justify-between gap-2">
                <span className="mono text-xs text-muted-foreground">{hover.id}</span>
                {hover.changed && <NewBadge />}
              </div>
              <p className="mt-1 text-sm font-medium">{hover.product_raw}</p>
              <p className="text-xs text-muted-foreground">
                → {hover.canonical_commodity ?? "?"} · pickup {fmtDate(hover.pickup_date)}
              </p>
              <p className="truncate text-xs text-muted-foreground">{hover.origin_name}</p>
              <div className="mt-2">
                <StatusChip status={hover.status} />
              </div>
            </div>
          </Popup>
        )}
        {hoverDet && (
          <Popup longitude={hoverDet.lon} latitude={hoverDet.lat} closeButton={false} offset={16} anchor="bottom">
            <div className="glass w-64 p-3 text-foreground">
              <p className="text-sm font-semibold">Detection · {hoverDet.place}</p>
              <p className="text-xs text-muted-foreground">
                {fmtDate(hoverDet.date, { month: "short", day: "numeric", year: "numeric" })} · {hoverDet.sex_status ?? "fly"}
              </p>
              <p className="mt-1 text-xs">{hoverDet.detail}</p>
              <p className="mt-1.5 text-[10px] text-muted-foreground">Placed at the town center (approximate). {hoverDet.quarantine} quarantine.</p>
            </div>
          </Popup>
        )}
      </Map>


      <div className="glass absolute bottom-3 left-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl px-3 py-1.5 text-[11px]">
        {STATUS_ORDER.map((s) => (
          <span key={s} className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-full" style={{ background: STATUS[s].color }} /> {STATUS[s].short}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5 text-muted-foreground">
          <span className="h-0 w-3 border-t-2 border-dashed border-slate-400" /> before
        </span>
      </div>
    </div>
  );
}