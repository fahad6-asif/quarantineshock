# How to use QuarantineShock (beginner guide)

## 1. Start it (every time)
1. Open **PowerShell** (Start menu → type "PowerShell").
2. Go to the project folder:
   ```
   cd C:\Users\hp\Documents\QuarantineShock
   ```
3. Start everything:
   ```
   npm run dev
   ```
4. Wait until you see `Ready` (about 10–20 seconds). **Leave this window open**; closing it stops the app.
5. Open your browser at **http://localhost:3000**.

To stop: click the PowerShell window and press **Ctrl + C**.

## 2. Get ready to present (once, before each demo)
1. Click **Launch Command Center** (or "Skip intro").
2. Click the **⚙ gear** (top right) → **Reset & fast-forward to Jun 16**.
3. The map now shows the June 16 state, and the timeline shows a green **"New notice received"** button.

## 3. The demo, step by step
| Do this | What happens | What to say |
|---|---|---|
| Open http://localhost:3000, press **→** three times | Story cards: April "no commercial agriculture" → June 338.5 acres | "In April: no farms. In June: 338.5 acres, in 48 hours." |
| Click **Launch Command Center** | Map + timeline + agent panel | "This is Sunridge Produce, a fictional distributor with 25 pickups." |
| Press **N** | The **Agent** tab ticks through 10 steps; then **Overview** shows the 4 newly flagged loads; the zone grows to El Cajon | "The AI read the notice, redrew the zone, read the rules, checked every load, and verified every quote." |
| In **Overview**, click **Hass avos 40lb x 120** | Drawer: why it's flagged, Hold/Approve buttons, what to confirm. Click **Rule evidence** to see the verified quotes | "This truck was leaving tomorrow." |
| Click **Hold shipment** | Green toast "Shipment on hold", saved to the audit log | "A human decides. The tool never clears a load." |
| **Ask** tab → click "Can I ship frozen avocado pulp from El Cajon?" | Answer with numbered citation chips; says the sources don't settle it | "It knows where its knowledge stops." |
| Click a numbered chip | Side panel shows the exact source passage | "Every claim links to the real regulation." |
| Top right **Evals** | Accuracy, citations verified, zone error, limits | "We measure ourselves, including where we're wrong." |

## 4. Keyboard shortcuts
- **N**: process the next notice
- **← / →**: move back and forth between processed notices
- **Esc**: close a drawer

## 5. Reading the screen
- **Left**: the notices in date order. The green button is the next one to process.
- **Middle**: the map. Amber = Needs review, purple = Unclear, grey = not a host, green = outside. Red bugs = where flies were found. Dashed line = the zone before this notice.
- **Right, 4 tabs**:
  - **Overview**: the counts and the loads you need to look at. Start here.
  - **Agent**: the 10 AI steps. Click a step to see its output.
  - **Loads**: all 25 loads (Flagged / Changed / All).
  - **Ask**: questions about the rules, answered with sources.
- **Badges**: `Gemini` = live AI, `saved` = saved answer reused, `offline` = replay mode, `code` = plain Python (no AI).
- **Top right**: a dot that shows whether the AI is ready, plus Evals, the theme switch and Settings.

## 6. Settings (⚙)
- **Auto** (normal): saved answers first, then Gemini.
- **Replay**: no internet needed at all (use if Wi-Fi is bad). The map background needs internet, everything else works.
- **Check provider health**: tests your Gemini key.
- **Export audit log (CSV)**: every decision with a timestamp.

## 7. If something goes wrong
| Problem | Fix |
|---|---|
| Browser says "can't reach the API" | Is the PowerShell window with `npm run dev` still open? Restart it. |
| Red toast "Gemini hit its rate limit" | Switch to **Replay** in Settings. The demo still works. |
| You changed `.env` | Stop (Ctrl + C) and run `npm run dev` again. |
| Everything is weird | ⚙ → Reset & fast-forward to Jun 16. |
| You added or changed documents in `sources/` | Run `python scripts/ingest.py`, then `python scripts/warm_cache.py`. |

## 8. Your homework
1. **`data/labels.csv`**: check each row (is the commodity right? host / not_host / unclear?). Then change `false` to `true` on the first line.
2. **OpenRouter** (backup AI) is already set up with `openai/gpt-oss-120b`; just keep a little credit on your OpenRouter account.
