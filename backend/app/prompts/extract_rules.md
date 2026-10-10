You are building a compliance rulebook for a produce distributor that picks up loads inside a
Mexican fruit fly (Mexfly, Anastrepha ludens) quarantine in San Diego County, California.

Read ONLY the source passages below (federal 7 CFR 301.32, California CCR 3417, CDFA guidance, the 2026
federal Mexfly host list). Extract the rules that decide whether and how a commercial load of produce
picked up inside the quarantine area may move.

Output:
- rules: 6-12 rules. For each:
  - id: "R1", "R2", ...
  - applies_to: commodities or categories (e.g. ["host fruits"], ["Hass avocado"], ["soil"]).
  - requirement: plain-language requirement, one or two sentences.
  - conditions: when it applies.
  - exemptions: exceptions stated in the text (copy the key words; e.g. "Fresh, mature green variety 'Hass' avocadoes are not regulated").
  - quote: an EXACT, VERBATIM span (one or two sentences) copied character-for-character from ONE passage that supports the rule.
  - source_chunk_id: the id of that passage.
  Include, if present: what counts as a regulated article / host; treatment + certificate requirement; movement
  for processing; compliance agreements; the Hass avocado provisions (state and federal); canned/dried/frozen
  products; movement of commodities produced outside the area through it.
- host_commodities: common names of commodities the passages list as Mexfly hosts (e.g. "avocado", "orange", "peach").
- ambiguities: places where the sources do NOT settle a question a distributor will face. Look especially at
  processed, frozen, pulp, juice, dried and mixed products, and at differences between the federal and state text.
  - topic, explanation (plain language: what is unclear and why),
  - affected_forms: lowercase product forms affected, chosen from: fresh, frozen, processed, dried, mixed, pulp, juice, canned.
  - quote + source_chunk_id: the verbatim span that creates the ambiguity (or null).

Never invent requirements. If something is not in the passages, it does not exist for this task.

PASSAGES:
$passages
