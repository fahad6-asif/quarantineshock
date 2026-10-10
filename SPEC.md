# QuarantineShock: Build Spec for Claude Code 🪰

> **One line:** When the government expands a pest quarantine, QuarantineShock's AI agent reads the new notice, redraws the quarantine zone from the text, checks every shipment a distributor has scheduled, and tells them in minutes which loads need a compliance review, with verified quotes from the actual rules.

**Owner:** Fahad (solo, hackathon). **Time budget:** ~10 hours total including slides and video.
**Builder:** Claude Code. Fahad is not deeply technical: explain what you're doing in simple words, show him progress at each checkpoint, and ask before any big deviation from this spec.

---

## 0. Rules for Claude Code (read first) ⚠️

1. **It must actually work end to end.** No fake buttons, no hardcoded "AI" text pretending to be live output, no TODO stubs in the demo path. If something is mocked (shipments are fictional), it is labelled as such in the UI.
2. **Never fabricate regulatory text, quotes, dates or numbers.** All notice text and rule text must come from real fetched or pasted sources in `sources/`. If you can't fetch a source, STOP and ask Fahad to paste or download it. Every quote shown in the UI must be a verbatim substring of a source document (the verifier enforces this).
3. **AI reads and writes. Plain code decides.** No LLM decides whether a shipment is flagged. The match/status logic is deterministic Python and is unit-tested.
4. **The demo must survive bad Wi-Fi and dead API keys.** Every LLM call is cached to disk, and there is a replay mode that runs the whole demo from cache with zero network.
5. **Work in phases** (Section 12). At the end of each phase: run the tests, run the app, tell Fahad in 3–5 plain sentences what now works, and wait for a "go" only where the phase says so.
6. **Windows-friendly.** Fahad is likely on Windows. No Makefile-only or bash-only workflows. Use Python scripts plus npm scripts that run on Windows, macOS and Linux.
7. **Secrets:** keys live only in `.env` (git-ignored). Commit a `.env.example` with placeholder values. Never print keys in logs.
8. **OpenRouter model choice requires Fahad's confirmation.** See Section 6.3. Do not pick the model yourself.

---

## 1. The story (used in the intro screen, README and pitch) 📖

**The pest:** the Mexican fruit fly (*Anastrepha ludens*, "Mexfly"). Larvae develop inside fruit and rot it. It can infest more than 50 types of fruits and vegetables, including citrus, avocados and mangoes.

**Real 2026 timeline, La Mesa / Spring Valley quarantine, San Diego County, California.** Verify each item against `sources/` before displaying it.

| Date (2026) | What happened | Area | Commercial ag inside |
|---|---|---|---|
| Mar 5 | La Mesa quarantine established after a February detection | ~77 sq mi | None |
| Mar 10 | Expanded | ~82 sq mi | None |
| Mar 17 / Apr 2 | Expanded twice (+1 sq mi each) after detections in orange and avocado trees | 84 sq mi | **None**. The APHIS notice of Apr 17 (DA-2026-16) says so explicitly |
| **Jun 16** | New **Spring Valley** quarantine after one mated female was detected near Spring Valley | ~76 sq mi | **22.5 acres** |
| **Jun 18** ⚡ | Spring Valley quarantine expanded after a **Jun 12** detection of a wild mated female in a grapefruit tree, residential property, **El Cajon** | ~111 sq mi | **338.5 acres**: avocado, citrus, stone fruit, tomatoes |
| Aug 14 | La Mesa and Spring Valley merged after an **Aug 4** detection in a tangelo tree in La Mesa | 173 sq mi | 338.5 acres |

**The "shock":** in April the official word was "no commercial agriculture." Within 48 hours in June, the zone held 338.5 acres of commercial farms. Every distributor picking up in that area had to work out from legal text plus a map which loads were now affected. The notices themselves only say "regulated articles" and point elsewhere for the details.

**Damage framing (be honest):** no crop losses from this specific outbreak were found in our research. Frame the damage as **risk**: a missed load means a rejected shipment, penalties, or carrying larvae into clean commercial groves, which leads to bigger quarantines and closed export markets. Fahad may add one historical fruit-fly outbreak cost figure, clearly labelled as a past event with its source. Do not invent numbers.

**Our product:** the notice goes in, an AI agent produces rules, a zone and flags, and a human approves. It never says "cleared". It says "needs review" and shows its reasoning.

**Demo persona:** a fictional distributor, **Sunridge Produce**, with 25 fictional scheduled pickups for Jun 15 – Aug 20, 2026.

**SDGs:** 2 (resilient food supply), 12 (responsible production), 15 (invasive species).

**Roadmap line (say as future, not as built):** "Notice in, rules out, shipments flagged." The same engine extends to other pests, flood-affected crops and food recalls.

---

## 2. The two hero cases (the demo must nail these) 🎯

### Case 1: "The Avocado Truck" 🥑
- Shipment `SR-1007`: raw label `"Hass avos 40lb x 120"`, pickup **Jun 19, 2026**, origin a fictional grove in the El Cajon area, destination a Los Angeles produce terminal.
- **Geometry constraint (enforced by a test):** the origin point is OUTSIDE the zone generated for the Jun 16 notice and INSIDE the zone generated for the Jun 18 notice. Choose the coordinates programmatically after the zones are built (pick a point in `zone_jun18 − zone_jun16`, on plausible land in the El Cajon area, not in the ocean or on a freeway).
- Expected result: status flips from **No flag (outside zone)** to **REVIEW**. Its detail view shows the verified rule quote, a checklist, a draft compliance email and a driver hold note.

### Case 2: "The Tricky One" 🤔
- Shipment `SR-1015`: raw label `"avocado pulp, frozen, 30lb pails"`, inside the Jun 18 zone.
- Expected result: **UNCLEAR**. The normalizer and rules can't confirm whether processed or frozen product is a regulated article. The UI shows *why*: the ambiguity flag from rule extraction plus the normalizer's low confidence.
- Also demoed through the **Ask the Rules** chat: *"Can I ship frozen avocado pulp from El Cajon?"* returns a grounded answer that says the sources don't settle it and names who to confirm with. It must not invent an answer.

### Supporting moment: "Not everything is flagged"
- Shipment `SR-1011`: `"romaine hearts 24ct"`, inside the zone, so the result is **No flag (not a host)**. This shows the tool doesn't panic-flag everything.

---

## 3. Status vocabulary (exact)

| Code | UI label | Color | Meaning |
|---|---|---|---|
| `REVIEW` | Needs review | Amber `#F59E0B` | Origin inside active zone on pickup date AND commodity is a host AND no exemption applies |
| `UNCLEAR` | Unclear: human check | Violet `#8B5CF6` | Missing or invalid coordinates, commodity unsure (confidence < 0.7), or an ambiguity flag applies to this commodity or form |
| `NOT_HOST` | No flag: not a host | Slate `#64748B` | Inside zone, commodity is a confirmed non-host |
| `OUTSIDE` | No flag: outside zone | Emerald `#10B981` | Origin outside all active zones on pickup date |

Never use the words "cleared", "approved for shipment" or "safe". A small "NEW" badge marks shipments whose status changed with the latest notice.

---

## 4. Architecture: how data flows 🔄

```
sources/ (real notices, 7 CFR 301.32, CDFA pages, host list)
   │
   ├──► [Ingest] chunk + embed ──► ChromaDB (rulebook memory, RAG)
   │
   ▼
Notice "arrives" (user clicks the next notice in the timeline)
   │
   ▼
┌──────────────── LangGraph agent (one run per notice) ─────────────────┐
│ 1. classify_notice      AI   is it a quarantine change? pest, county  │
│ 2. extract_notice       AI   detections[], area, crops, effective date│
│ 3. geocode_detections   tool town/address → lat/lon (cached)          │
│ 4. build_zone           code circles of official radius → union        │
│ 5. extract_rules        AI+RAG regulated articles, exemptions,         │
│                              conditions, ambiguities, verbatim quotes  │
│ 6. normalize_shipments  AI+embeddings messy label → commodity, host?   │
│ 7. match                code point-in-zone + rule logic → status       │
│ 8. verify_citations     code+AI every quote checked against source     │
│ 9. draft_actions        AI   explanation, checklist, email, hold note  │
│10. summarize            AI   one-paragraph run summary + counts        │
└──────────────────────────────────────────────────────────────────────┘
   │  (every step streams events to the UI via SSE)
   ▼
SQLite (runs, zones, statuses, drafts, human decisions, audit log)
   │
   ▼
Next.js UI: map + timeline + agent activity + shipments + detail + chat + evals
```

Each run is stored, so the timeline can scrub between notices instantly without re-running.

---

## 5. Tech stack

### Backend (Python 3.11+)
- **FastAPI** + **uvicorn**: API server
- **LangGraph**: the agent graph (nodes in Section 4), with retries per node
- **Pydantic v2**: schemas for every LLM output, validated with a repair-retry loop
- **google-genai**: Gemini SDK (current official package; check current docs)
- **openai** Python SDK pointed at OpenRouter's OpenAI-compatible endpoint (fallback)
- **ChromaDB** (persistent, local): vector store. Use Chroma's **built-in local default embedding function** (ONNX MiniLM) so embeddings never consume API quota and work offline
- **shapely** + **pyproj**: geodesic-accurate buffers in miles (project to a local metric CRS such as UTM 11N / EPSG:32611, buffer, project back)
- **geopy** (Nominatim): geocoding with a custom user-agent, 1 req/sec, cached, plus a hardcoded fallback table for the detection towns (La Mesa, Spring Valley, El Cajon) so the demo never depends on Nominatim
- **rapidfuzz**: quote verification against sources
- **tenacity**: retries with exponential backoff
- **SQLModel** (SQLite): persistence
- **sse-starlette**: server-sent events for live agent steps
- **pypdf** / **trafilatura** or **beautifulsoup4**: turning PDFs and HTML in `sources/` into text
- **pytest**: tests
- Optional: **Langfuse** tracing, only if `LANGFUSE_*` env vars are set; no-op otherwise

### Frontend
- **Next.js (App Router) + TypeScript**
- **Tailwind CSS** + **shadcn/ui** components
- **MapLibre GL** via **react-map-gl/maplibre**, with a **free basemap that needs no API key** (e.g., OpenFreeMap or CARTO Positron/Dark Matter). Include correct attribution and check the license
- **Turf.js**: client-side area and centroid helpers if needed
- **Framer Motion**: animations (zone growth, status flips, counter)
- **lucide-react**: icons
- **Recharts**: eval charts
- **sonner**: toasts
- **Playwright**: one end-to-end smoke test of the demo path

### Tooling
- Python venv + `requirements.txt` (or `uv` if available; must also work with plain pip)
- `npm` for the frontend; **concurrently** so `npm run dev` at the root starts backend and frontend together
- `.env.example`, `.gitignore`, `README.md`

---

## 6. LLM provider layer (Gemini primary, OpenRouter fallback, cache always) 🔌

### 6.1 One interface
`backend/app/llm/client.py` exposes:

```python
async def generate_json(task: str, prompt: str, schema: type[BaseModel],
                        tier: Literal["fast","strong"]) -> tuple[BaseModel, CallMeta]
async def generate_text(task: str, prompt: str, tier: ...) -> tuple[str, CallMeta]
async def stream_text(task: str, prompt: str, tier: ...) -> AsyncIterator[str]
```

`CallMeta` = provider used, model, cached (bool), latency ms, input/output tokens if available, attempt count. Every node logs it, and the UI shows a provider badge per step.

### 6.2 Provider chain
Controlled by `.env`:

```
LLM_PROVIDER=auto          # auto | gemini | openrouter | replay
GEMINI_API_KEY=
GEMINI_MODEL_FAST=         # Claude Code: fill with a current fast Gemini model after checking docs
GEMINI_MODEL_STRONG=       # current stronger Gemini model
GEMINI_RPM=10              # self-imposed rate limit to stay under free-tier limits
OPENROUTER_API_KEY=
OPENROUTER_MODEL=          # LEFT EMPTY until Fahad confirms (see 6.3)
OPENROUTER_RPM=20
QUARANTINE_RADIUS_MILES=4.5   # VERIFY against sources (see 8.3)
```

Order for `auto`:
1. **Disk cache** (`backend/.cache/llm/`, key = sha256 of provider-agnostic task + prompt + schema name). Hit means return immediately.
2. **Gemini.** On `429` / `RESOURCE_EXHAUSTED` / quota errors, `401`/`403` (bad key), or a `5xx` after 2 retries, mark Gemini as *unhealthy for 10 minutes* and go to 3.
3. **OpenRouter** (if key and model set). Same retry rules.
4. **Replay fallback:** if both fail and a cached response exists for a near-identical task, use it and label it `cached` in the UI. Otherwise raise a clear, human-readable error that the UI shows as a toast plus a red step in Agent Activity. No silent failures.

Additional requirements:
- **Structured output that works on both providers:** ask for JSON matching the Pydantic schema (use native JSON/schema mode where the provider and model support it), parse, validate, and on failure retry up to 2 times with the validation error included. Strip markdown code fences before parsing.
- **Quota savers:** batch shipment normalization (all 25 shipments in 1–2 calls, not 25), batch action drafting per run, keep prompts tight, use `fast` tier everywhere except notice extraction and rule extraction.
- **Client-side rate limiter** per provider using the RPM settings.
- **Health endpoint** `GET /api/health/providers` makes a tiny test call to each configured provider and reports `ok` / `quota` / `bad_key` / `not_configured`. The UI header shows this as a status pill.
- **Manual switch:** a dropdown in Settings (Gemini / OpenRouter / Auto / Replay) that changes the provider for the next run without restarting.
- OpenRouter call details: OpenAI-compatible `base_url="https://openrouter.ai/api/v1"`. Optionally send `HTTP-Referer` and `X-Title: QuarantineShock` headers.

### 6.3 OpenRouter model: STOP AND ASK FAHAD 🛑
Before setting `OPENROUTER_MODEL`:
1. Check OpenRouter's current model list (openrouter.ai/models).
2. Present Fahad with **2–3 cheap candidates** in a small table: model id, price per 1M input/output tokens, context length, whether it supports JSON/structured output, and a one-line opinion. Prefer reliable instruction-following and JSON mode over the absolute cheapest.
3. Mention that `:free` models exist but have tight rate limits and can be unreliable for a live demo.
4. **Wait for his pick.** Then set it in `.env`, run `scripts/preflight.py`, and run the full pipeline once on OpenRouter only (`LLM_PROVIDER=openrouter`) to prove it works. The schemas must validate on that model. If the chosen model keeps failing JSON validation, tell Fahad and suggest the next candidate.

### 6.4 Replay mode (demo insurance)
- `python scripts/warm_cache.py` runs every notice through the full agent once and fills the cache, including chat answers for 5 scripted questions (Section 9.6).
- `LLM_PROVIDER=replay` serves only from cache: zero network, identical output. Agent Activity still animates step by step (with realistic small delays) and labels steps "replayed".
- The Playwright test runs in replay mode.

---

## 7. Data 📂

### 7.1 `sources/` (real documents; Fahad collects, Claude Code fetches where possible)
Try to fetch these yourself first (WebFetch or a download). If blocked, ask Fahad.
- APHIS / CDFA notices for the La Mesa and Spring Valley Mexfly quarantine, 2026 (March, April DA-2026-16, June 16, June 18, August 14). Save each as `sources/notices/2026-MM-DD_<slug>.txt` with a header comment holding the original URL and retrieval date.
- **7 CFR 301.32** (Fruit Flies subpart) from eCFR: `sources/regs/7cfr301_32.txt`
- CDFA's Mexican fruit fly page plus its interior quarantine regulation text: `sources/regs/cdfa_mexfly.txt`
- The official **Mexfly host list**: `sources/regs/mexfly_hosts.txt`
- `sources/manifest.json`: every file with title, url, publisher, date, type (`notice` | `regulation` | `host_list`).

If a June notice's full text can't be obtained, use the best real public text available (press release or news report), mark it `source_quality: "secondary"` in the manifest, and show a small "secondary source" tag in the UI. **Never write notice text yourself.**

### 7.2 `data/shipments.json` (fictional, 25 records)
Fields: `id, pickup_date, origin_name, lat, lon, product_raw, quantity, destination, carrier, notes`.

Mix (Claude Code generates, positions computed after zones exist):
- ~7 host commodities that end up inside a zone at some stage (avocado, citrus, stone fruit, tomato variants with messy labels: `"navels bin"`, `"heirloom toms 25lb"`, `"cara cara 4/5 bu"`, `"yellow peaches 2L"`, `"meyer lemons"`, …), including hero `SR-1007`
- ~4 hosts outside all zones (other parts of San Diego County)
- ~4 non-hosts inside zones (romaine `SR-1011`, onions, cilantro, …). **Fahad must verify** non-host status against the host list
- ~4 ambiguous items: frozen avocado pulp `SR-1015`, `"mixed fruit box - assorted"`, `"juice oranges for processing"`, `"dried mango slices"`
- ~2 data-quality problems: one missing coordinates, one with a typo-heavy label (`"avacodo hass"`)
- Pickup dates spread so some are before Jun 16, some Jun 16–18, some after Aug 14

Labelled clearly as fictional everywhere.

### 7.3 Answer keys (Fahad verifies by hand)
- `data/labels.csv`: `id, canonical_commodity, host_status (host|not_host|unclear)`. Claude Code drafts it from the host list; **Fahad reviews every row** before evals count. Put `reviewed_by_human: false` in a header until he confirms.
- `data/gold_rules.json`: 6–8 rules Fahad writes from the regulation (Claude Code can help him find passages but must not author the "gold" answers). Used to score rule extraction.

---

## 8. Agent nodes in detail 🧠

All prompts live in `backend/app/prompts/*.md` (editable, versioned). Every AI node returns a Pydantic model.

### 8.1 `classify_notice` (fast)
In: notice text. Out: `NoticeClass {is_quarantine_change, pest, county, action: establish|expand|merge|release, confidence}`.

### 8.2 `extract_notice` (strong)
Out:
```python
class Detection(BaseModel):
    place: str            # "El Cajon"
    detail: str           # "grapefruit tree, residential property"
    date: date | None
    sex_status: str | None
    quote: str            # verbatim span from the notice
class NoticeExtract(BaseModel):
    notice_date: date
    effective_date: date | None
    quarantine_name: str
    action: str
    detections: list[Detection]   # only detections NEW in this notice or stated as basis
    stated_area_sq_mi: float | None
    stated_commercial_acres: float | None
    crops_mentioned: list[str]
    ambiguities: list[str]
```
The UI shows extracted fields next to highlighted spans in the notice text.

### 8.3 `geocode_detections` + `build_zone`
- Geocode each `place` (cache, then Nominatim, then the fallback table). Place the detection point at the town centroid, marked approximate.
- **Radius:** search the RAG store for the official quarantine radius for Mexfly in these sources. If found, use it and show the quote. If not found, use `QUARANTINE_RADIUS_MILES` and show "radius from config: verify" in the UI. Tell Fahad at Phase 2 which one happened.
- Zone for a notice = union of buffers around **all detections cumulative to that notice within that quarantine**. For the Aug 14 merge, take the union of both quarantines.
- Compute the generated area in sq mi and compare it with `stated_area_sq_mi`. Show "Generated 108 sq mi vs official 111 sq mi (−3%)" in the UI. This is an eval signal, not a bug. If the error is > 25%, tell Fahad, since detection placement or the radius likely needs adjusting.
- Store zones as GeoJSON per notice.

### 8.4 `extract_rules` (strong, RAG)
- Retrieve the top chunks from Chroma for queries like "regulated articles Mexican fruit fly", "exemptions", "treatment certification movement", "host list avocado citrus". Pass chunks with ids.
- Out:
```python
class Rule(BaseModel):
    id: str
    applies_to: list[str]        # commodities or categories
    requirement: str             # plain language
    conditions: list[str]
    exemptions: list[str]
    quote: str                   # verbatim
    source_chunk_id: str
class Ambiguity(BaseModel):
    topic: str                   # "processed/frozen product"
    explanation: str
    affected_forms: list[str]    # ["frozen","processed","pulp","juice"]
    quote: str | None
    source_chunk_id: str | None
class RuleSet(BaseModel):
    rules: list[Rule]
    host_commodities: list[str]
    ambiguities: list[Ambiguity]
```
- Cache per source-set hash (rules don't change per notice unless sources change).

### 8.5 `normalize_shipments` (fast, embeddings + LLM, batched)
- For each `product_raw`, get the top-5 nearest canonical names from the host list and a common-produce list via Chroma (local embeddings).
- One batched LLM call: for each shipment, given the raw label and its candidates, return `{id, canonical_commodity, form (fresh|frozen|processed|dried|mixed|unknown), host_status, confidence, reasoning}`.

### 8.6 `match` (pure Python, no AI) ✅
For each shipment:
1. Find active zones on `pickup_date` (zones whose notice effective date ≤ pickup date, latest version per quarantine).
2. Missing or invalid coordinates → `UNCLEAR`.
3. Outside all active zones → `OUTSIDE`.
4. Inside: if `host_status == not_host` and confidence ≥ 0.7 → `NOT_HOST`; if `host_status == unclear` or confidence < 0.7 or `form` is in any `Ambiguity.affected_forms` → `UNCLEAR`; else if `host` → `REVIEW`.
5. Record `reasons: list[str]` (machine-readable codes plus human text) and the `changed_since_previous_notice` flag.

Fully unit-tested, including both hero cases.

### 8.7 `verify_citations` (code + fast AI)
- For every quote (notice extract, rules, ambiguities, drafts): normalize whitespace and quotes, then check it is a substring of its source chunk or document (rapidfuzz partial ratio ≥ 95 on normalized text). Fail → mark `unverified`, show red in the UI, and exclude it from drafts.
- Then a light LLM judge pass: "does this quote actually support this claim?" → `supports | partial | no`.
- Out: a grounding score like `Citations verified: 14/14 · Supports claim: 13/14`.

### 8.8 `draft_actions` (fast, batched per run; only for `REVIEW` and `UNCLEAR`)
Per shipment:
```python
class ActionPack(BaseModel):
    shipment_id: str
    explanation: str          # 2–4 plain sentences, why flagged
    rule_ids: list[str]       # must reference verified rules only
    checklist: list[str]      # what to confirm with CDFA/county ag commissioner (treatment, certificate, permit), phrased "confirm whether…"
    email_subject: str
    email_body: str           # to internal compliance team
    driver_hold_note: str     # short SMS-style note
```
Wording rule: never claim legal certainty. Use "needs review", "confirm with".

### 8.9 `summarize` (fast)
One paragraph plus counts: newly flagged, total REVIEW / UNCLEAR, zone change. Shown at the top of the run.

### 8.10 Events
Every node emits SSE events `{run_id, node, status: started|progress|done|error, message, meta: CallMeta, ts}`. Progress messages are human-friendly ("Found 1 new detection: El Cajon, Jun 12").

---

## 9. UI spec (make it look great) 🎨

**Feel:** a calm, premium "operations command center", not a generic dashboard. Dark theme by default (slate-950 background, subtle grid texture, soft glass panels) with a light-theme toggle. One accent color for the brand (e.g. lime/chartreuse `#A3E635`, a nod to agriculture), and status colors from Section 3. Font: Inter or Geist for UI, a mono font (JetBrains Mono / Geist Mono) for quotes, ids and agent logs. Generous spacing, rounded-2xl panels, smooth micro-animations. Must look good on a 1366×768 laptop and on a projector (1920×1080), with no horizontal scroll.

**Logo:** a simple original mark (stylized fly inside a dashed circle or radar sweep), made as an inline SVG. Not based on any real brand.

### 9.1 Intro / Story screen (`/`)
A full-screen narrative in 3–4 animated cards, advanced with the arrow keys or a "Next" button:
1. "April 17, 2026: *the quarantine contains no commercial agriculture.*" (with source tag)
2. "June 18, 2026: **338.5 acres** of avocado, citrus, stone fruit and tomatoes inside." Big animated number 0 → 338.5.
3. "Distributors had to read legal text and a map by hand. One missed truck can carry the pest out."
4. "QuarantineShock: notice in, rules out, shipments flagged." → button **Launch Command Center**.

Small footer: "Real public notices · fictional shipments · decision support, not legal advice."

### 9.2 Command Center (`/app`): main layout
- **Header:** logo + name, scenario label "Sunridge Produce · San Diego County", provider status pill (Gemini ● / OpenRouter ● / Replay ●), Settings gear, Evals button.
- **Left rail: Notice Timeline.** A vertical list of the real notices with dates and area chips. Already-processed notices are solid; the next unprocessed one pulses with a **"📨 New notice received"** button. Clicking a processed notice scrubs the whole app to that state (instant, from stored runs). A compact slider at the bottom of the map mirrors this.
- **Center: Map.**
  - Basemap zoomed to East San Diego County.
  - Previous zone as a dashed outline; current zone as a translucent amber fill that **animates its growth** when a new run finishes.
  - Detection markers: pulsing red dot with a small fly icon; tooltip with date and detail.
  - Shipment dots colored by status, with "NEW" halos on changed ones. Hover shows a mini card; click opens the detail drawer.
  - Overlay chip: "Zone 111 sq mi (official) · 108 sq mi (generated)".
  - Legend. Attribution.
- **Top-center counter:** "🚨 **4** newly flagged since last notice" with an animated count-up and a subtle shake on increase.
- **Right panel tabs:**
  1. **Agent Activity:** live vertical stepper of the 10 nodes, each with icon, status spinner/check/error, human message, provider badge (Gemini/OpenRouter/cached/replayed), latency. Expandable to show the structured output (pretty JSON) and the prompt name. A run summary at the top when done.
  2. **Shipments:** a table (shadcn DataTable) with id, product (raw and canonical), pickup date, origin, status chip, NEW badge. Filter by status, search, sort. Row click opens the detail drawer.
  3. **Ask the Rules:** chat (Section 9.6).
  4. **Notice:** the selected notice's text with extracted fields highlighted (hover a field to highlight its span), and an extracted-data card.

### 9.3 Shipment detail drawer
- Header: id, raw label → canonical commodity (with confidence bar), status chip.
- **Why:** reason list, the explanation.
- **Rule evidence:** each quote in a mono blockquote with a source link, a "✓ verified" or "✗ unverified" badge and a supports-claim badge.
- **Checklist:** checkboxes (local state).
- **Draft email + driver note:** editable textareas with Copy buttons.
- **Decision:** buttons **Approve review plan / Hold shipment / Escalate**, plus an optional note. Saves to SQLite with timestamp, writes to the audit log, shows a toast, and the status chip gets a small decision icon.
- Mini-map of the origin vs the zone edge with the distance to the boundary ("0.8 mi inside zone").

### 9.4 Evals page (`/app/evals`), the honesty panel
Cards plus Recharts:
- **Commodity normalizer accuracy** vs `labels.csv` (overall, plus a confusion table host / not_host / unclear). Shows "answer key reviewed by human: yes/no".
- **Rule extraction:** how many `gold_rules` were matched (LLM-judge or keyword matching; show the method).
- **Citation grounding:** verified %, supports-claim %.
- **Zone accuracy:** generated vs official area per notice (bar chart).
- **Limits box (always visible):** zones are approximate (town-centroid detections + radius); ambiguous clauses need a human; fictional shipments; supports review, not legal decisions.
- A button "Re-run evals" calls `POST /api/evals/run`.

### 9.5 Settings modal
Provider dropdown (Auto / Gemini / OpenRouter / Replay), provider health check button, radius display (read-only plus its source), "Reset demo" (clears runs and decisions, keeps caches), "Export audit log (CSV)".

### 9.6 Ask the Rules chat
- Streaming answers. RAG over Chroma only. The system prompt forces: answer only from the provided chunks, cite chunk ids, and if the sources don't answer, say so and name who to confirm with (CDFA / County Agricultural Commissioner / APHIS).
- Citations render as clickable chips that open the source passage in a side sheet.
- Each answer's quotes pass through the same verifier, with badges shown.
- Suggested question chips (these 5 are warmed into the cache):
  1. "Can I ship frozen avocado pulp from El Cajon?"
  2. "Is romaine lettuce regulated under this quarantine?"
  3. "What changed in the June 18 notice?"
  4. "What does a grower need to move host fruit out of the zone?"
  5. "Which crops are affected by the expansion?"

### 9.7 Global UX
- Persistent thin banner: "Decision support only. Fictional shipment data. Zones approximate." (dismissible per session)
- Loading skeletons, empty states, error toasts with plain-English messages ("Gemini hit its rate limit, switched to OpenRouter").
- Keyboard: `N` = process next notice, `←/→` = scrub timeline, `Esc` = close drawer. This makes presenting easy.
- Accessibility: status uses icon + text, not only color; good contrast.

---

## 10. API endpoints (FastAPI)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| GET | `/api/health/providers` | provider checks (6.2) |
| GET | `/api/notices` | timeline list with processed flag |
| GET | `/api/notices/{id}` | text + extract + highlights |
| POST | `/api/runs` `{notice_id}` | start an agent run → `{run_id}` |
| GET | `/api/runs/{run_id}/events` | SSE stream |
| GET | `/api/runs/{run_id}` | full run result |
| GET | `/api/state?notice_id=` | zone GeoJSON, detections, shipment statuses at that notice |
| GET | `/api/shipments/{id}?notice_id=` | detail + action pack + evidence |
| POST | `/api/shipments/{id}/decision` | approve / hold / escalate + note |
| POST | `/api/chat` | streaming RAG answer |
| GET | `/api/sources/{chunk_id}` | source passage |
| POST | `/api/evals/run` · GET `/api/evals` | evals |
| GET | `/api/settings` · POST `/api/settings/provider` | provider switch |
| POST | `/api/demo/reset` | reset runs and decisions |
| GET | `/api/audit.csv` | audit export |

Frontend talks to the backend through `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). Enable CORS for localhost.

---

## 11. Repo layout

```
quarantineshock/
├─ SPEC.md
├─ README.md
├─ .env.example  .gitignore
├─ package.json              # root: "dev" runs backend + frontend via concurrently
├─ sources/                  # real docs + manifest.json
├─ data/                     # shipments.json, labels.csv, gold_rules.json, fallback_geocodes.json
├─ backend/
│  ├─ requirements.txt
│  ├─ app/
│  │  ├─ main.py  config.py  db.py  events.py
│  │  ├─ llm/ (client.py, gemini.py, openrouter.py, cache.py, ratelimit.py)
│  │  ├─ rag/ (ingest.py, store.py, retrieve.py)
│  │  ├─ geo/ (geocode.py, zones.py)
│  │  ├─ agent/ (graph.py, nodes/*.py, state.py)
│  │  ├─ matching.py  verify.py  schemas.py
│  │  ├─ prompts/*.md
│  │  └─ routes/*.py
│  └─ tests/
├─ frontend/                 # Next.js app
│  └─ tests/e2e/demo.spec.ts # Playwright
└─ scripts/
   ├─ setup.py        # venv, pip install, npm install, copy .env.example → .env if missing
   ├─ ingest.py       # sources → text → chunks → Chroma
   ├─ preflight.py    # checks keys, providers, geocoder, Chroma index, data files
   ├─ warm_cache.py   # runs all notices + chat questions to fill cache
   └─ eval.py         # writes data/eval_results.json
```

Commands Fahad will run (document them in the README in this exact order):
```
python scripts/setup.py
python scripts/ingest.py
python scripts/preflight.py
python scripts/warm_cache.py
npm run dev        # opens backend :8000 + frontend :3000
```

---

## 12. Build phases (with checkpoints) 🧱

Work through these in order. Each phase ends with: tests green, app running, and a plain-English update to Fahad.

**Phase 0: Setup (≤30 min)**
Scaffold the repo, `.env.example`, setup script, root `npm run dev`, empty FastAPI + Next.js "hello" pages. Ask Fahad to paste his Gemini key into `.env` (and the OpenRouter key if he has it now). Run preflight. ✅ *Checkpoint: both servers start on his machine.*

**Phase 1: Sources + RAG (≤60 min)**
Fetch or collect sources, write the manifest, ingest into Chroma, add a retrieval test. Generate the `labels.csv` draft and ask Fahad to review it, and to write `gold_rules.json` with help finding passages. ✅ *Checkpoint: show Fahad 3 retrieved passages for "avocado regulated articles".*

**Phase 2: LLM layer + notice → zone (≤75 min)**
Provider client with cache, fallback, rate limiting and health. `classify_notice`, `extract_notice`, geocode, `build_zone` for all notices. Area comparison. Tests for the fallback (mock a 429 from Gemini → OpenRouter is used; if no OpenRouter key → clear error). ✅ *Checkpoint: report generated vs official areas, and the radius source.* **If Fahad has given an OpenRouter key, do the Section 6.3 model confirmation here.**

**Phase 3: Rules, normalize, match, verify, draft (≤90 min)**
Remaining nodes plus the LangGraph wiring plus SSE events. Generate shipments with hero coordinates chosen from the zone difference. Tests: hero case flips, romaine is NOT_HOST, frozen pulp is UNCLEAR, missing coords are UNCLEAR, all displayed quotes verified. ✅ *Checkpoint: print a plain table of statuses per notice for Fahad.*

**Phase 4: UI (≤150 min)**
Story screen, Command Center, map, timeline, agent activity, shipments table, detail drawer, chat, settings, evals page. Polish the animations. ✅ *Checkpoint: Fahad clicks through the full demo script himself.*

**Phase 5: Hardening (≤45 min)**
`warm_cache.py`, replay mode, the Playwright e2e test in replay mode, an `LLM_PROVIDER=openrouter` full run (if the key is available), README, screenshots in the README. Fix every console error and warning on the demo path.

---

## 13. Tests that must pass ✅

**pytest**
- `test_zones.py`: buffers are in miles (a single 4.5-mile circle ≈ 63.6 sq mi ± 2%); union works; `SR-1007` is outside the Jun 16 zone and inside the Jun 18 zone.
- `test_matching.py`: all 4 statuses, including the hero and supporting cases; date logic (pickup before notice effective date uses the previous zone).
- `test_llm_fallback.py`: Gemini 429 → OpenRouter; both down + cache → cached; both down, no cache → clear error; JSON repair retry works.
- `test_verify.py`: an exact quote passes, an altered quote fails, a whitespace and smart-quote variation passes.
- `test_api.py`: the main endpoints return 200 with valid shapes; SSE emits all 10 node events in order for one run (replay mode).

**Playwright (replay mode)**
Story → Launch → process the Jun 16 notice → process the Jun 18 notice → the counter increases → `SR-1007` shows Needs review → open the drawer → the verified quote is visible → click Hold → toast → Chat: ask the frozen pulp question → the answer contains a citation chip and does not claim certainty.

---

## 14. Definition of done (check every box before saying "done")

- [ ] `npm run dev` starts everything from a clean clone after following the README
- [ ] The full demo works with **Gemini**
- [ ] The full demo works with **OpenRouter** (Fahad-confirmed model) using `LLM_PROVIDER=openrouter`
- [ ] The full demo works with **no internet** using `LLM_PROVIDER=replay`
- [ ] Auto-fallback demonstrated: an invalid Gemini key leads to OpenRouter taking over, with a toast shown
- [ ] All displayed quotes are verified verbatim against real sources
- [ ] No fabricated notice text, dates or numbers anywhere
- [ ] Hero cases behave exactly as in Section 2
- [ ] Evals page shows real computed numbers
- [ ] All tests pass; no console errors on the demo path
- [ ] Looks polished at 1366×768 and 1920×1080
- [ ] README: what it is, the story, setup steps, provider config, limits, credits/sources
- [ ] `.env` is not committed

---

## 15. The 2-minute demo script (for Fahad)

1. **Story screen (20s):** April said no farms. June 18: 338.5 acres. Distributors read legal text by hand.
2. **Launch (10s):** the map shows the Jun 16 state; the Sunridge shipments are mostly green.
3. **Press N, "New notice received: June 18" (30s):** Agent Activity runs live: reads the notice, finds the El Cajon detection, builds the zone, checks the rules, normalizes 25 shipments, verifies 14/14 quotes. The zone grows and the counter jumps.
4. **Case 1 (25s):** click the avocado truck: why it's flagged, the verified quote, checklist, draft email, then **Hold shipment**. "This truck was leaving tomorrow."
5. **Case 2 (20s):** ask the chat about frozen avocado pulp. It says the sources don't settle it and who to ask. "It knows where its knowledge stops."
6. **Evals (15s):** normalizer accuracy, citation grounding, zone area error, limits.
7. **Close (10s):** "AI reads and writes, code decides, humans approve. Notice in, rules out, shipments flagged. Next: other pests, floods, recalls."

---

## 16. Open items (ask Fahad when relevant, don't block on them early)
- Hackathon submission format and demo time limit (affects README, video and whether to deploy)
- Whether to deploy publicly (optional: Vercel for the frontend + Render/Railway for the backend, only after Phase 5 is green; replay mode works well for a hosted demo)
- OpenRouter model choice (Section 6.3)
- Confirmation that the radius and host list values match the sources
