# Cranston Legislative Activity Index, version 0.2-test

This is a separate research sandbox at `/cranston-activity-index-test.html`. It is marked noindex,nofollow, omitted from the sitemap and not added to profile scores. It is publicly accessible to people with the link; no authentication is implied.

## Reproduce

1. Review the committed `data/cranston/sponsorship-2026.json` snapshot and classifications.
2. Run `python scripts/build_cranston_activity_pilot.py` to write `data/cranston/activity-index-pilot-2026.json` and the page from `templates/cranston-activity-index-test.html`.
3. Review `data/cranston/activity-index-coding-2026.json` for every measure before rebuilding.
4. Run `node --test scripts/test_activity_index.mjs` and `node --check activity-index-test.mjs`.

The builder uses only Python standard library. Scoring uses the same pure `activity-index-model.mjs` functions in Node tests and the browser. The page embeds its frozen JSON snapshot; it never silently loads new sponsorship data. The source file SHA-256, version and configuration are included in the results CSV.

## Initial classification

42 unique identified items: 15 local-rule proposals, 2 fiscal measures, 1 property approval, 5 state-directed advocacy measures, 1 symbolic display policy and 18 recognition/commemorative items. The fiscal items are a school-building revolving fund and a rescue-service budget measure. The property item is the Cardinal Road sale. Labels describe the proposed governmental function, not legal validity, enactment or policy quality. Generic zoning titles do not support detailed issue significance coding.

## Three-tier model and topic tags

The default RIEP test weights are symbolic/advocacy 1, routine administrative approvals 2, and substantive municipal policymaking 5. The 42 identified items are assigned 24 symbolic/advocacy, 1 administrative and 17 substantive tier codes. These are RIEP coding choices, not CEL's commemorative/substantive/substantive-significant categories or a reproduction of CEL scoring.

Detailed action functions remain available underneath: local rule, fiscal measure, property approval, state advocacy, symbolic display and recognition. The property sale is coded as routine approval because this extract does not establish a broader policy change. Coding is provisional and not a legal ruling or a policy-quality judgment.

Every item has one primary topic and up to two secondary topics, with a coding rationale in `data/cranston/activity-index-coding-2026.json`. That file is the explicit human-review input. The builder rejects new or missing measure IDs until coding is completed, and validates the fixed topic vocabulary and unique tags. Generic zoning titles support a Housing and land use tag, not a speculative account of economic effects.

Health-awareness commemorations are tagged Health and Community recognition and remain in the symbolic tier. State library funding requests are tagged Education and libraries and Budget and taxation and remain advocacy. Topic labels do not multiply or change scores.

Named council sponsors share 1 credit equally per measure. Explicit cosponsors receive .25 each; this is a per-member credit, not shared across cosponsors. A member cannot receive both roles on one item. Earlier-year items considered in 2026 are included, with an option to exclude them. No first-listed sponsor is presumed the lead author.

Weighted activity is the sum of tier weight times role credit. Activity index is 100 times a member's weighted activity divided by the cohort mean across the nine 2026 members. 100 is a relative mean, not a percentage or performance standard. If every raw total is zero, the normalized index is not defined. No expected-performance adjustment is made.

All default weights are illustrative hypotheses, not empirical estimates. Three fixed presets compare 1–2–5, 1–2–3 and 1–1–1, holding other credit assumptions constant. Custom weights range from 0 to 10. Joint sponsor credit can be split or full. No single ranking is treated as authoritative.

The member audit has a topic filter matching primary or secondary tags. It filters displayed evidence only; it does not change overall scores or the cohort mean. The topic breakdown allocates each item's points to its primary topic exactly once. These subtotals sum to the member total without double-counting secondary tags. A separate coded-measures CSV includes tiers, action types, topic tags, coding rationale and sources.

## Verification

Independent Python Fraction calculations against the original six action types verify the new baseline totals. Node regression tests check all nine member totals, mean normalization, role changes, carryovers, zero denominator, invalid weights, duplicate measures and conflicting roles. Additional tests check valid topic tags, secondary-topic filtering, score invariance when a topic changes and primary-topic subtotal reconciliation.

## Limits

Partial extraction is not comparable missingness across members. No score here measures overall effectiveness, passage success, oversight, committee effort, implementation or constituency service. Amendment authorship and a full budget-contribution inventory remain unmeasured rather than observed zeros. Procedural movers/seconders and routine Yes votes do not create sponsorship credit. A zero score means no weighted credit detected under the model, not no work performed.

## Institutional sources

- Council powers and administrative boundaries: https://ecode360.com/46510612
- Budget responsibilities: https://ecode360.com/46510655
- Education and ratification: https://ecode360.com/46510782
- Rhode Island home rule: https://rilegislature.gov/riconstitution/Constitution/C13.aspx
- CEL research background: https://thelawmakers.org/methodology

These sources inform distinctions between types of action. The scoring weights and fractional-credit convention are RIEP test assumptions, not rules derived from these sources or a replication of CEL methodology.
