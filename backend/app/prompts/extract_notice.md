You extract structured facts from an official pest-quarantine notice. Accuracy matters more than completeness.

Context (from our document index, not from the notice): this notice is about the "$quarantine" quarantine,
effective $effective_date. Year for dates without a year: 2026.

Rules:
- Use ONLY the notice text. Never invent numbers, dates or places.
- notice_date: the date of the action this notice reports ($effective_date unless the text clearly says otherwise).
- detections: every fly detection the notice states as the basis for a quarantine action. One entry per
  detection site/date. If one sentence reports several flies from the same tree type on the same date, one entry is fine.
  - place: the city/community. If the notice does not name the city, use the quarantine name ("$quarantine")
    and set place_is_inferred=true.
  - detail: host tree + property type, e.g. "grapefruit tree, residential property".
  - date: the detection date (YYYY-MM-DD) if stated.
  - sex_status: e.g. "wild mated female", "wild male".
  - quote: an EXACT, VERBATIM span copied from the notice that states this detection (copy characters exactly; no paraphrase).
- stated_area_sq_mi: the total quarantine area the notice states for the action on $effective_date (not earlier/later actions).
- stated_commercial_acres: commercial agriculture acreage stated for that action; 0 if the notice says it contains no
  commercial agriculture; null if not stated.
- crops_mentioned: crops named as commercial agriculture inside the zone.
- ambiguities: anything a compliance team could misread (e.g. "notice says 'regulated articles' but does not list them").

NOTICE TEXT:
"""
$notice_text
"""
