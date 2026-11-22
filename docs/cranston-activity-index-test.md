# Cranston Legislative Activity Index, version 0.1-test

This is a separate research sandbox at `/cranston-activity-index-test.html`. It is marked noindex,nofollow, omitted from the sitemap and not added to profile scores. It is publicly accessible to people with the link; no authentication is implied.

## Reproduce

1. Review the committed `data/cranston/sponsorship-2026.json` snapshot and classifications.
2. Run `python scripts/build_cranston_activity_pilot.py` to write `data/cranston/activity-index-pilot-2026.json` and the page from `templates/cranston-activity-index-test.html`.
3. Run `node --test scripts/test_activity_index.mjs` and `node --check activity-index-test.mjs`.

The builder uses only Python standard library. Scoring uses the same pure `activity-index-model.mjs` functions in Node tests and the browser. The page embeds its frozen JSON snapshot; it never silently loads new sponsorship data. The source file SHA-256, version and configuration are included in the results CSV.

## Initial classification

42 unique identified items: 15 local-rule proposals, 2 fiscal measures, 1 property approval, 5 state-directed advocacy measures, 1 symbolic display policy and 18 recognition/commemorative items. The fiscal items are a school-building revolving fund and a rescue-service budget measure. The property item is the Cardinal Road sale. Labels describe the proposed governmental function, not legal validity, enactment or policy quality. Generic zoning titles do not support detailed issue significance coding.

## Baseline

Category weights: local rules 1, fiscal measures 1, all other categories 0. Named council sponsors share 1 credit equally per measure. Explicit cosponsors receive .25 each; this is a per-member credit, not shared across cosponsors. A member cannot receive both roles on one item. Earlier-year items considered in 2026 are included, with an option to exclude them. No first-listed sponsor is presumed the lead author.

Weighted activity is the sum of category weight times role credit. Activity index is 100 times a member's weighted activity divided by the cohort mean across the nine 2026 members. 100 is a relative mean, not a percentage or performance standard. If every raw total is zero, the normalized index is not defined. No expected-performance adjustment is made.

All default weights are illustrative hypotheses, not empirical estimates. Three fixed presets are compared: baseline, sponsors only, and baseline with advocacy weight .5. Custom weights range from 0 to 5. Joint sponsor credit can be split or full. No single ranking is treated as authoritative.

## Verification

The baseline raw totals are Graziano 2.25, Andujar 1.75, Ritz 3.75, Traficante 4.5, Vaziri .75, Campopiano 0, Buonanno 1.75, Haroian 1.75 and Wall 3. Total 19.5, cohort mean 19.5/9. The tests check raw totals against these counted contributions, mean normalization, credit changes, carryovers, zero denominator, invalid weights, duplicate measures and conflicting roles.

## Limits

Partial extraction is not comparable missingness across members. No score here measures overall effectiveness, passage success, oversight, committee effort, implementation or constituency service. Amendment authorship and a full budget-contribution inventory remain unmeasured rather than observed zeros. Procedural movers/seconders and routine Yes votes do not create sponsorship credit. A zero score means no weighted credit detected under the model, not no work performed.

## Institutional sources

- Council powers and administrative boundaries: https://ecode360.com/46510612
- Budget responsibilities: https://ecode360.com/46510655
- Education and ratification: https://ecode360.com/46510782
- Rhode Island home rule: https://rilegislature.gov/riconstitution/Constitution/C13.aspx
- CEL research background: https://thelawmakers.org/methodology

These sources inform distinctions between types of action. The scoring weights and fractional-credit convention are RIEP test assumptions, not rules derived from these sources or a replication of CEL methodology.
