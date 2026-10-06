# Rhode Island House voting-pattern preview

Experimental Kathleen A Fogarty website feature, adapted from the repository Senate widget. Added directly to the candidate profile at the user’s request. Source base: `de0186eb34a10829f1a0513acd6b9bacb7e1b98f`.

## Coverage and method

91 official House journals: 46 in 2025 (January 7–June 20), 45 in 2026 (January 6–June 11). The dates in the repository attendance inventory were compared with fresh official House index/library pages on October 6, 2026. All 1,210 binary Yea/Nay lists reconcile with published totals; 450 divided votes enter the pooled model. This verifies names and counts, not the correctness of every printed individual vote.

Actual CRAN `wnominate` 1.5, R 4.3.3: one dimension, 2.5% minority cutoff, 20 informative votes minimum, 50 successful native bootstrap trials, seed 20261006. Michael Chippendale anchors the positive direction. Party is display metadata from the 2026 candidate roster or historical roster for noncandidates, not a model input. Names, districts, party labels, and source provenance remain reviewable in `representatives.json`. The House model is independent of the Senate model.

Kathleen A Fogarty (House District 35): pooled coordinate **−1.000**, native bootstrap standard error **0.0547**, **420** recorded informative votes used. A coordinate at the boundary does not establish personal extremism or uniquely identify the most liberal member. The fitted model classifies 95.58% of observed votes correctly (in-sample; not a forecasting validation).

Annual fits contain 263 divided votes in 2025 and 187 in 2026. Separate annual coordinates are independently scaled and cannot be used to claim ideological movement. Annual standard errors are unavailable and displayed as such. The pooled ordering correlates 0.9571 with a 5% minority cutoff, 0.9744 with a 10% cutoff, and 0.9437 with the contextual passage-only subset. Contextual motion classes still need review before any motion-specific public claim.

## Source audit

Exact comma-delimited surname matching distinguishes Brien and O’Brien and handles Shallcross Smith. Speaker pro tempore votes retain the actual named member. Wrapped name lists, PDF page breaks, and the missing colon in a June 10, 2026 Nay header are handled explicitly. Unanimous votes are excluded from the model. Missing votes and recusals are missing, never Nay. Grouped floor votes remain one observation; officer-election ballots are recorded separately and not coerced into binary votes. Voice votes are not assigned to individuals. Proxy votes listed in the official roll call are retained as recorded; the model describes recorded voting, not physical attendance.

## Reproduce

Requires Python 3, Poppler `pdftotext`, R, and packages `jsonlite`, `pscl`, `wnominate`.

```sh
python collect_journals.py
python extract_session.py
Rscript model_session.R
python export_positions.py
```

`manifest.json` preserves PDF URLs, dates, SHA-256 checksums, and file sizes. `rollcalls.csv`, `votes_long.csv`, matrices, raw PDFs/text, source indexes, model objects, diagnostics and sensitivity fits are retained locally. Website files are `candidates/house-voting-patterns/{index.html,pilot.css,pilot.js,positions.json}` and the new voting-pattern section in `candidates/kathleen-a-fogarty.html`. The Senate files are unchanged.

Treat liberal/conservative labels as provisional interpretations of observed alignment. Zero is not a calibrated political center. Small position differences should not become precise rankings. These estimates are separate from CEL effectiveness, the RIEP legislative index, and outside scorecards. House/Senate values cannot be compared directly. Source and methodological review remain necessary before public release.

## Validation

Model schema, 75 unique districts, source-inventory equality, JavaScript syntax and DOM interaction checks pass. The standalone HTML renders all 75 dots and supports pooled/annual switching, uncertainty labels, name search, mouse selection and keyboard selection without external widget assets. A visual browser check could not be completed in the execution environment.
