You are a plant-quarantine analyst. Classify the official notice text below.

Decide:
- is_quarantine_change: does it establish, expand, merge or release a pest quarantine area?
- pest: common name of the pest (e.g. "Mexican fruit fly").
- county: the county affected.
- action: one of establish | expand | merge | release | other (the main action described).
- confidence: 0..1.

Use only the text. Do not add facts.

NOTICE TEXT:
"""
$notice_text
"""
