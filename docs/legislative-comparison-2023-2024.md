# RIEP / CEL comparison, 2023–2024

The prototype comparison uses the full Rhode Island roster from CEL's public application: 75 House records and 39 Senate records. The Senate has 38 districts; Goodwin and Bissaillon both appear for District 1. Both CEL chamber score means are 1, consistent with using these full historical record populations.

Source: `https://thelawmakers.org:3000/vis/stateTable?state=RI&termStartYear=2023&termEndYear=2024`. Each record's five-stage category counts came from `stateScorecard` using its slesId, chamber, and the same term years. Original responses and full precision are preserved in `data/cel_source_2023_2024.json`, retrieved October 2, 2026. The existing `scripts/build_cel_ratings_2026.py` provides `table()` and `scorecard()` retrieval helpers.

Reproduce with `python scripts/build_legislative_comparison.py`. Rebuild Urso/Ciccone pages with `python scripts/build_candidate_pages.py`. Serve the repository root, then open `/candidates/legislative-comparison.html`.

Equal-weight RIEP formula: N/3 × (introduced / chamber introductions + passed / chamber passage + enacted / chamber enactments). Counts are substantive plus substantive-and-significant, unweighted; commemorative counts are excluded. This approximates RIEP's non-resolution scope using CEL categories rather than independently recounting bill records. CEL also includes committee stages and significance weights. Results test formula agreement on shared inputs, not independent validity.

| Chamber | Records | Pearson r | Spearman rho | Mean absolute rank gap |
|---|---:|---:|---:|---:|
| House | 75 | 0.993248 | 0.990526 | 2.32 |
| Senate | 39 | 0.994879 | 0.992915 | 0.82 |

| Senator | RIEP | CEL SLES | RIEP full-chamber rank | CEL full-chamber rank |
|---|---:|---:|---:|---:|
| John Burke | 0.686210 | 0.636931 | 27 | 28 |
| Frank Ciccone | 1.486134 | 1.531071 | 9 | 9 |

Urso began service in 2025. No historical score is assigned, and her predecessor's record is not substituted. Scores and competition ranks use unrounded values; Spearman uses average ranks for ties. Profiles retain current-session RIEP indices separately.

New profiles use existing sourced campaign, finance, attendance, legislation, and endorsement data. Ciccone's campaign priorities are his submitted RIEP response. His 2024/2020 uncontested primary returns were checked against official RI.gov results. Urso's 2026 primary is labeled as the existing unofficial snapshot. Missing historical primary years and full floor votes remain explicitly under construction.
