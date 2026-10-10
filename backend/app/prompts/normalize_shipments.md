You normalize messy produce labels from a distributor's pickup schedule.

For each shipment, choose canonical_commodity from its candidate list when one fits (copy the candidate name
exactly). If none fits or the label covers several products, write a short generic name (e.g. "mixed fruit").
Do not decide regulations; only identify the product.

- form: fresh | frozen | processed | dried | mixed | unknown.
  "pulp", "puree", "juice", "for processing", "canned" -> processed (or frozen if frozen is stated).
  Fresh produce sold as-is -> fresh. Assortments -> mixed.
- host_status: your best guess only (the system re-checks it against the official host list): host | not_host | unclear.
- confidence: 0..1 that canonical_commodity AND form are right. Use < 0.7 when the label is genuinely unclear.
- reasoning: one short sentence.
Return one item per shipment id, in the same order.

SHIPMENTS:
$items
