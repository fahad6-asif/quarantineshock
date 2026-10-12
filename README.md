# QuarantineShock

Note: This project was made almost entirely with Claude Code as a hackathon entry. I did not write most of the code myself.

Live demo: https://quarantineshock.onrender.com

## What it is

QuarantineShock is a demo tool for pest quarantines. When the government expands a quarantine zone, the tool reads the new notice and redraws the zone on a map. It then checks a list of shipments and shows which ones need a compliance review. Every rule quote it shows is checked word for word against the real source text.

The demo uses real public notices about the Mexican fruit fly in San Diego County in 2026. The distributor (Sunridge Produce) and its 25 shipments are made up.

This is decision support only. It is not legal advice.

## The story behind the demo

In April 2026 the official notice said there was no commercial agriculture inside the quarantine area. On June 16 a new quarantine covered 22.5 acres of commercial farms. Two days later it was expanded and covered 338.5 acres. A distributor would have had to work out by hand which loads were now affected.

## How it works

1. The real documents in `sources/` are split into passages and stored in a local search index (ChromaDB).
2. A new notice arrives and an agent (built with LangGraph) works through it in 10 steps:
   1. Classify the notice (AI)
   2. Extract the details (AI)
   3. Find map coordinates for the detection places (geocoding)
   4. Build the quarantine zone (code)
   5. Find the relevant rules (AI and search)
   6. Normalize the commodity names (AI and embeddings)
   7. Match each shipment against the zone and rules (code only)
   8. Check every quote against its source (code and an AI judge)
   9. Draft actions such as an email and a driver note (AI)
   10. Write a summary (AI)
3. The results show up in the web app.

The main rule is that AI reads and writes, and plain code decides. Whether a load is flagged is decided in `backend/app/matching.py`, not by the AI. Whether a product is a host comes from a lookup in the official host lists.

Any quote that cannot be found word for word in its source is marked as unverified and left out of the drafts.

The tool uses four statuses: Needs review, Unclear (human check), No flag: not a host, and No flag: outside zone. It never says "cleared" or "safe".

## Run it on your computer

You need Python 3.11 or newer and Node.js 20 or newer. Run these from the project folder:

```
python scripts/setup.py
python scripts/ingest.py
python scripts/preflight.py
python scripts/warm_cache.py
npm run dev
```

Then open http://localhost:3000.

* `setup.py` creates the Python environment, installs everything and creates a `.env` file from `.env.example`. Put your `GEMINI_API_KEY` in that file.
* `ingest.py` builds the search index from the documents in `sources/`.
* `preflight.py` checks your keys, the index and the data files.
* `warm_cache.py` runs every notice once and saves the AI answers, so the demo also works with no internet.

See `HOW_TO_USE.md` for a short walkthrough of the demo.

## AI settings

Set `LLM_PROVIDER` in `.env`:

* `auto`: saved answers first, then Gemini, then OpenRouter
* `gemini` or `openrouter`: use only that provider
* `replay`: saved answers only, no internet needed

The saved answers are in `backend/.cache/`. They are why the demo runs without any API keys. You only need `GEMINI_API_KEY` (and optionally `OPENROUTER_API_KEY`) to ask new questions in the chat.

## Tests

```
npm test
npm run e2e
```

`npm test` runs the backend tests. `npm run e2e` runs a browser test in replay mode and needs `warm_cache.py` to have been run first.

## Limits

* Zones are approximate. The notices name towns, not exact trap addresses, so the tool puts each detection at the town center with the official 4.5 mile radius. Official boundaries follow roads, so the generated areas come out smaller.
* Products that are frozen, processed, dried or mixed always go to a human.
* Tomatoes are not on either host list, so the tool does not flag them.
* The June 16, June 18 and August 14 notice texts are word for word excerpts of the real APHIS and CDFA documents.
* `data/labels.csv` is a draft answer key that a person has not reviewed yet.
* The map background needs internet. Everything else works offline in replay mode.

## Deployment

The `Dockerfile` builds one container with the website and the API. `render.yaml` deploys it on Render's free tier. A GitHub Action (`.github/workflows/keepalive.yml`) pings the site every 10 minutes so the free instance does not fall asleep.

To let visitors ask new chat questions on the live site, add `GEMINI_API_KEY` (and optionally `OPENROUTER_API_KEY`) as environment variables in Render.

## Sources

All fetched on 2026-10-10. The full list is in `sources/manifest.json`.

* USDA APHIS: [DA-2026-16](https://www.aphis.usda.gov/news/program-update/aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-area-california), [DA-2026-36](https://www.aphis.usda.gov/news/program-update/aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-san-diego-county), [DA-2026-20 host lists](https://www.aphis.usda.gov/news/program-update/aphis-establishes-host-lists-regulated-articles-three-tephritid-fruit-fly)
* [NAPPO Official Pest Report 1191](https://www.pestalerts.org/nappo/official-pest-reports/1191/)
* [eCFR 7 CFR 301.32](https://www.ecfr.gov/current/title-7/subtitle-B/chapter-III/part-301/subpart-L)
* CDFA: [CCR 3417 text](https://www.cdfa.ca.gov/plant/mexfly/docs/regs/3417-TXT-mexfly.pdf), [quarantine boundary text 8/14/2026](https://www.cdfa.ca.gov/plant/mexfly/docs/MexFly_Quarantine_SanDiego_County_Text_20260810.pdf), [processing options](https://www.cdfa.ca.gov/plant/PE/InteriorExclusion/current_options.html), [Official Notice, Spring Valley (Jun 24, 2026)](https://www.sandiegocounty.gov/content/dam/sdc/awm/docs/MXFF_PEP_SpringValley_SanDiegoCounty_Amd2_20260624_SoF.pdf)
* [County of San Diego News Center](https://www.countynewscenter.com/mexican-fruit-fly-quarantine-expanded-in-san-diego-county/)
* Map tiles by [CARTO](https://carto.com/attributions) and [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors. Geocoding by Nominatim.

## Project layout

```
sources/    the real documents (raw originals plus extracted text and a manifest)
data/       made-up shipments, draft answer key, host table, geocode cache
backend/    FastAPI and LangGraph agent, prompts and tests
frontend/   Next.js app and browser test
scripts/    setup, ingest, preflight, warm_cache and other helpers
```
