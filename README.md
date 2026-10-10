---
title: QuarantineShock
emoji: 🪰
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Notice in, rules out, shipments flagged.
---

# QuarantineShock 🪰

**Notice in, rules out, shipments flagged.**

**▶ Live demo:** _LIVE_URL_ · **Code:** _REPO_URL_

When the government expands a pest quarantine, QuarantineShock's AI agent reads the new notice, redraws the
quarantine zone from the text, checks every shipment a distributor has scheduled, and says within minutes which
loads need a compliance review. Every quote it shows is checked word-for-word against the real rules.

> Decision support, not legal advice. Real public notices · fictional shipments · approximate zones.

## The story (real, 2026)

The Mexican fruit fly (*Anastrepha ludens*, "Mexfly") was found in La Mesa, San Diego County in February 2026.

| Date (2026) | What happened | Official area | Commercial ag inside |
|---|---|---|---|
| Mar 5 | La Mesa quarantine established (Feb 24 detection) | ~77 sq mi | none |
| Mar 10 | Expanded (Feb 26 detection) | ~82 sq mi | none |
| Mar 17 / Apr 2 | Expanded twice. APHIS DA-2026-16 (Apr 17): *"contains no commercial agriculture"* | 84 sq mi | **none** |
| **Jun 16** | New Spring Valley quarantine (Jun 4 detection, avocado tree) | ~76 sq mi | 22.5 acres |
| **Jun 18** | Expanded after a Jun 12 detection in a grapefruit tree in **El Cajon** | ~111 sq mi | **338.5 acres**: avocado, citrus, stone fruit, tomatoes |
| Aug 14 | La Mesa + Spring Valley merged (Aug 4 detection, tangelo tree) | 173 sq mi | 338.5 acres |

In April the official word was "no commercial agriculture". Within 48 hours in June the zone held 338.5 acres of
farms, and every distributor had to work out by hand which loads were affected.

The demo distributor, **Sunridge Produce**, and its 25 pickups are **fictional**.

## Run it (Windows, macOS, Linux)

Needs Python 3.11+ and Node.js 20+. Run these from the project folder, in this order:

```
python scripts/setup.py
python scripts/ingest.py
python scripts/preflight.py
python scripts/warm_cache.py
npm run dev        # opens backend :8000 + frontend :3000
```

1. `setup.py` creates the Python venv, installs everything, and creates `.env` from `.env.example`.
   **Paste your `GEMINI_API_KEY` into `.env`.**
2. `ingest.py` turns the real documents in `sources/` into searchable passages (local embeddings, no API quota).
3. `preflight.py` checks keys, providers, the index and the data files.
4. `warm_cache.py` runs every notice through the agent once and caches every AI answer, so the demo also works with **no internet**.
5. Open http://localhost:3000.

### Before presenting
Command Center → ⚙ Settings → **Reset & fast-forward to Jun 16**, then press **N** for the June 18 notice.
Keyboard: `N` processes the next notice, `←/→` scrubs the timeline, `Esc` closes drawers.

## The 2-minute demo
1. **Story** (arrow keys): April said no farms; June 18: 338.5 acres.
2. **Launch** → the map shows the June 16 state.
3. **Press N**: Agent Activity runs live (10 steps). The zone grows to El Cajon and the counter jumps to **4 newly flagged**.
4. **The avocado truck (SR-1007)**: *No flag: outside zone* → **Needs review**. The drawer shows verified rule quotes,
   a checklist (including California's conditional Hass exemption), a draft email and a driver hold note → **Hold shipment**.
5. **Ask the Rules**: "Can I ship frozen avocado pulp from El Cajon?" It quotes the federal "frozen below −17.8 °C (0 °F)"
   rule, says the sources don't settle it, and names who to confirm with.
6. **Evals**: normalizer accuracy, citation grounding, zone area error, limits.

## How it works

```
sources/ (real APHIS/CDFA notices, 7 CFR 301.32, CCR 3417, 2026 host list)
   └─► ingest: chunk + local embeddings ─► ChromaDB
Notice arrives ─► LangGraph agent (10 steps, each streamed live to the UI)
  1 classify_notice   AI     4 build_zone      code (+AI finds the radius in the sources)   7 match            CODE ONLY
  2 extract_notice    AI     5 extract_rules   AI + RAG                                      8 verify_citations code + AI judge
  3 geocode           tool   6 normalize       AI + embeddings (host status: code lookup)   9 draft_actions    AI   10 summarize AI
```

* **AI reads and writes. Plain code decides.** Whether a load is flagged is decided by `backend/app/matching.py`
  (unit-tested). Host status comes from a code lookup in the official host lists, not from the AI.
* **Every quote is verified** (`backend/app/verify.py`): it must appear word-for-word in its source, or it's marked
  unverified and kept out of the drafts. Example: the verifier caught the AI inventing the second half of a CCR 3417 clause.
* **Status vocabulary:** Needs review · Unclear: human check · No flag: not a host · No flag: outside zone. The tool never says "cleared" or "safe".

## LLM providers (`.env`)

| Setting | Meaning |
|---|---|
| `LLM_PROVIDER=auto` | cache → Gemini → OpenRouter → closest cached answer (labelled) |
| `gemini` / `openrouter` | that live provider only |
| `replay` | cache only, zero network (demo insurance) |
| `GEMINI_MODEL_FAST` / `_STRONG` | `gemini-3.5-flash-lite` / `gemini-3.5-flash`: fastest on the free tier when tested on 2026-10-10 (3.8-flash took ~4 min per reply) |
| `GEMINI_MODEL_BACKUP` | `gemini-2.5-flash`, used automatically if the main model is overloaded |
| `OPENROUTER_MODEL` | `openai/gpt-oss-120b`: automatic backup when Gemini errors, hits its limit or doesn't answer within `GEMINI_TIMEOUT_S` (40 s). About $0.04 / $0.17 per 1M tokens in/out |

You can also switch the provider at runtime in Settings. The header pill shows provider health.

## Tests

```
npm test                 # backend pytest (36 tests: zones, matching, verifier, LLM fallback, API + SSE)
npm run e2e              # Playwright demo path in replay mode (needs warm_cache.py first)
```

## Limits (read these)
* **Zones are approximate.** Notices name towns, not trap addresses, so detections sit at town centers with the
  official 4.5-mile radius. Official boundaries follow roads and are widened so farms aren't split (CCR 3417(b)(3)),
  so generated areas run smaller: Jun 18 −9%, Aug 14 merge −30%.
* **Ambiguous products** (frozen, processed, dried, mixed) always go to a human.
* **Tomatoes are not on either Mexfly host list** (federal DA-2026-20 or CCR 3417), so "heirloom toms" gets
  *No flag: not a host*, even though the June notice says the zone's farms grow tomatoes.
* The June 16 / June 18 / Aug 14 notice texts are verbatim excerpts of APHIS DA-2026-36 (published Sep 23, 2026) and CDFA documents.
* Basemap tiles need internet. Everything else works offline in replay mode.

## Deployment
The `Dockerfile` builds one container (static website + API on port 7860) and runs on Hugging Face Spaces
(Docker SDK) or any Docker host. The saved AI answers in `backend/.cache/` ship with it, so the demo works with
no API keys. To let visitors ask new chat questions live, add `GEMINI_API_KEY` (and optionally `OPENROUTER_API_KEY`)
as secrets in the Space settings.
* `data/labels.csv` is a draft answer key until a human reviews it; `data/gold_rules.json` must be written by a human.

## Sources (all fetched 2026-10-10; full list in `sources/manifest.json`)
* USDA APHIS [DA-2026-16](https://www.aphis.usda.gov/news/program-update/aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-area-california), [DA-2026-36](https://www.aphis.usda.gov/news/program-update/aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-san-diego-county), [DA-2026-20 host lists](https://www.aphis.usda.gov/news/program-update/aphis-establishes-host-lists-regulated-articles-three-tephritid-fruit-fly)
* [NAPPO Official Pest Report 1191](https://www.pestalerts.org/nappo/official-pest-reports/1191/)
* [eCFR 7 CFR 301.32–301.32-10](https://www.ecfr.gov/current/title-7/subtitle-B/chapter-III/part-301/subpart-L)
* CDFA: [CCR 3417 text](https://www.cdfa.ca.gov/plant/mexfly/docs/regs/3417-TXT-mexfly.pdf), [quarantine boundary text 8/14/2026](https://www.cdfa.ca.gov/plant/mexfly/docs/MexFly_Quarantine_SanDiego_County_Text_20260810.pdf), [processing options](https://www.cdfa.ca.gov/plant/PE/InteriorExclusion/current_options.html), [Official Notice, Spring Valley (Jun 24, 2026)](https://www.sandiegocounty.gov/content/dam/sdc/awm/docs/MXFF_PEP_SpringValley_SanDiegoCounty_Amd2_20260624_SoF.pdf)
* [County of San Diego News Center](https://www.countynewscenter.com/mexican-fruit-fly-quarantine-expanded-in-san-diego-county/)
* Basemap © [CARTO](https://carto.com/attributions), © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors. Geocoding: Nominatim / OpenStreetMap.

SDGs: 2 (resilient food supply), 12 (responsible production), 15 (invasive species).
Roadmap (future, not built): the same engine for other pests, flood-affected crops and food recalls.

## Repo layout
```
sources/   real documents (raw/ originals + extracted notices/ regs/ + manifest.json)
data/      fictional shipments, draft answer key, host table, geocode cache
backend/   FastAPI + LangGraph agent (app/), prompts (app/prompts/*.md), tests/
frontend/  Next.js app (src/), Playwright test (tests/e2e/)
scripts/   setup, fetch_sources, build_sources, ingest, preflight, warm_cache, make_shipments
```
