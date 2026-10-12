# How to use QuarantineShock

This is a short guide to running the demo on your own computer. The first-time setup is in the README.

## Start it

1. Open a terminal in the project folder.
2. Run `npm run dev`.
3. Wait about 20 seconds until it says Ready.
4. Open http://localhost:3000 in your browser.

To stop it, click the terminal and press Ctrl + C.

## Run the demo

1. Click Launch Command Center (or Skip intro).
2. Click the gear icon at the top right and choose Reset and fast-forward to Jun 16.
3. Press N to process the next notice (June 18). The Agent tab shows the 10 steps as they run. The zone grows and four loads are newly flagged.
4. In the Overview tab, click a flagged load. The side panel shows why it was flagged and the rule quotes behind it. You can click Hold shipment.
5. Open the Ask tab and ask a question about the rules. For example: "Can I ship frozen avocado pulp from El Cajon?" Each answer has numbered links to the source text.
6. Click Evals at the top right to see accuracy, citation checks and zone error.

## Keyboard shortcuts

* N: process the next notice
* Left and right arrows: move between processed notices
* Esc: close a side panel

## What is on the screen

* Left: the notices in date order.
* Middle: the map. Amber means needs review. Purple means unclear. Grey means not a host. Green means outside the zone. Red bugs are where flies were found. The dashed line is the zone before this notice.
* Right: four tabs. Overview shows the counts and the loads to look at. Agent shows the 10 AI steps. Loads lists all 25 loads. Ask answers questions about the rules.

## Settings (gear icon)

* Auto: saved answers first, then Gemini.
* Replay: no internet needed. Use this if the connection is bad. The map background still needs internet.
* Check provider health: tests your Gemini key.
* Export audit log: saves every decision with a timestamp as a CSV file.

## If something goes wrong

* "Can't reach the API": make sure the terminal running `npm run dev` is still open. Restart it if not.
* Gemini rate limit message: switch to Replay in Settings.
* You changed `.env`: stop the app and run `npm run dev` again.
* You added documents to `sources/`: run `python scripts/ingest.py` and then `python scripts/warm_cache.py`.
* Anything else looks wrong: use the gear icon and choose Reset and fast-forward to Jun 16.
