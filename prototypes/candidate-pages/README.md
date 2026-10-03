# Candidate page framework (local prototype)

This folder is intentionally disconnected from the public navigation. It contains three distinct page designs:

- `race.html?chamber=house&district=33` — district comparison and links to each candidate.
- `candidate.html?id=house-33-rep-primary-jessica-drew-day` — one candidate, without opponent content.
- `finance.html?id=house-33-rep-primary-jessica-drew-day` — a dedicated filing summary with links to source documents and the current detailed finance page.

Run from the repository root with `python3 -m http.server 8000`, then visit `http://localhost:8000/prototypes/candidate-pages/race.html?chamber=house&district=33`. For an unopposed example, use Senate District 9 or John Burke's candidate ID.

All displayed facts come from current project JSON. Portraits and digital conversation are clearly labeled placeholders. Historical candidate performance uses matched district general-election results; the precinct section shows **turnout** in a candidate's public filing home precinct, not precinct-level votes for that candidate. The scorecards retain their source year. Missing sections say so explicitly.

Before production: verify candidate IDs and name joins across data sets; add licensed, credited candidate photos with alt text; connect 2026 primary results and precinct-level candidate election returns if available; design a sourced social listening methodology; review finance source bucket reconciliation; perform keyboard, screen-reader, mobile, and data QA. Only then wire public routes from the homepage and existing race workspace.
