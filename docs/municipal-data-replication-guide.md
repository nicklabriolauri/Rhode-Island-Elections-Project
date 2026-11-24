# Municipal data replication guide

Use this guide to build a reviewable dataset for the next Rhode Island municipality. Begin with one council term and one election cycle. Write down the municipality, covered bodies, dates, election cycle, source cutoff and reviewer. Record which datasets are in scope before gathering documents. The project maintainer handles campaign finance separately.

## 1. Make a source inventory

| Dataset | Start with | Check before entering data |
| --- | --- | --- |
| Seats and service | City charter, council roster, clerk records | Number of ward and at-large seats, start and end dates, vacancies, appointments and replacements |
| Elections and geography | RI Board of Elections contest returns, official ward and precinct GIS and maps, sample ballots | Boundary vintage, contest and seat IDs, number of seats, write-ins and certified versus unofficial results |
| Legislative records | City clerk’s adopted measures, agendas and packets, local and RI Secretary of State open-meetings archives | Full council versus committee, meeting status, approved versus draft minutes, and amendments or corrected records |
| Council powers and profile evidence | City charter and ordinances, official profiles, dated statements and published scorecards | Effective text and section, scope of any rating, period covered and direct evidence for each claim |

Save original public documents and a source register with a stable source ID, publisher, document title, original URL and filename, retrieval date, approval status, and SHA-256 where a file was downloaded. Keep each source version. Log expected but unavailable documents and where you looked. Use PDF page numbers as displayed by the viewer, starting at 1. For web sources, record section or table names and a short evidence excerpt. Keep contact details and unpublished working material out of public deliverables.

## 2. Build the master workbook before publishing profiles

Use one header row on each tab. No merged cells within the data. Use ISO dates, stable IDs and numeric amounts. Export the reviewed tabs as UTF-8 CSV. Preserve underlying records when updating formulas or displays.

| Tab | Grain and fields to capture |
| --- | --- |
| People and service | One row per person × seat × stint. Include person ID, display name, source name or alias, profile slug, office/seat ID, ward or at-large, service start/end and source ID. |
| Elections | One candidate or write-in option per contest. Include contest ID, date, seat IDs or ward, seats available, votes, contest total, result status and source. Keep winners separate from sitting officials. |
| Meetings and sources | One row per meeting with body, date/time, regular/special type and minutes status. Link all versions through the source register rather than adding duplicate sessions. Include meetings without minutes in coverage. |
| Attendance | One eligible member per meeting. Code opening roll call as present, absent or not recorded. Record later arrivals/departures separately, with timestamps if available. |
| Measures and attribution | One row per ordinance or resolution with ID, official number if supplied, type, primary topic, title and observed stage. In a separate tab enter one attribution per person × measure × role × source. |
| Motions and votes | One motion per decision with measure ID when known, text, stage/action, mover, seconder, aggregate outcome and tally. Enter one individual vote per member × motion only where the minutes support it. |
| Powers and profile evidence | One proposition per row with person or office ID, evidence type, date, source and excerpt. For endorsements or issue ratings, record issuer, election or reporting period and exact status as published. |
| Coverage and review queue | One gap or discrepancy per row. Include affected IDs, source/page, issue, proposed correction and rationale, reviewer, review date and disposition. |

Put source ID and page/section on evidence rows. Use explicit statuses such as **not recorded**, **source unavailable**, and **not applicable**. Use zero only when the source or a calculation with complete inputs supports zero. Source approval status and human review status are independent.

## 3. Use an LLM for extraction and a human for approval

Process one meeting packet at a time. Give the model the source IDs, source files, roster for that date, workbook column names and allowed values. OCR scans as needed and check dates, names and tallies visually against the originals. Keep the prompt, model/version if available, date, source IDs, raw response and accepted corrections so another student can reproduce the workflow.

Copy this prompt and fill in the brackets.

> Extract [record types] for [municipality, body and date] using only [attached documents and source IDs]. Return CSV with these exact columns [paste the workbook headers]. For each row give the source ID, one-based PDF page or named section, and a short supporting excerpt. Keep the original wording for names and motion text. Use the supplied roster to resolve identities and flag ambiguous matches. Treat missing facts as unknown. Never infer a named vote from an aggregate outcome or sponsorship from a mover or seconder. Return conflicts and unreadable fields in a separate review-queue table. End with row counts and reconciliation failures so I can compare them with the source.

A second student opens the source and checks all published names, attributions, vote tallies and document links. Compare the original evidence and the candidate correction before marking the row reviewed. Preserve the original extract and record the accepted change under the same stable ID.

## 4. Apply the same rules in every city

**Seats and maps.** Central Falls had five ward contests and one citywide contest electing two councilors in the 2026 data. Use the city's actual rules for the next rollout. A valid address inside a ward should return that ward’s seat and the applicable at-large offices. Confirm all ward and precinct IDs, and test an inside address per ward, an outside address, and a border or ambiguous case. Match candidate votes to contest totals including write-ins. Preserve ties and the source’s certification status. A new election result does not change the roster before the new term begins.

**Legislation.** Track each measure through stages such as introduction, referral, reading, council adoption and effective/enacted status when the record supports them. One measure can have several motions. Code the primary topic with a shared vocabulary such as budget/tax, housing/property, schools, infrastructure, public safety, governance and ceremonial/recognition. Document mapping decisions before comparing cities. Keep lead sponsor, co-sponsor, by-request attribution, agenda attribution, presenter, mover and seconder distinct. The Central Falls property-acquisition resolution in the register is attributed to Alberto Rivas-Lugo **by request**. Its adoption and its attribution are separately documented. It does not earn verified lead-sponsor credit on that evidence. See the [Central Falls register](../data/central-falls/council-measures-2026.csv) and [Cranston sponsorship methods](cranston-sponsorship.md).

**Attendance and disagreement.** Compare equivalent bodies and date ranges. Publish opening attendance as present divided by eligible member-meetings with known opening status, with the number of unknowns and missing meetings reported alongside it. Use documented departures or arrivals for later motions only when the source supports them. For named dissent, report named no votes divided by recorded named yes plus no votes, and report abstentions, recusals, aggregate-only decisions and missing votes separately. If comparing motion-level dissent instead, use motions with a known yea/nay tally and label that denominator. A unanimous aggregate result can be retained at motion level without generating personal vote rows. An adopted measure can still have recorded dissent.

**Legislative effectiveness and powers.** Compare verified lead sponsorship across an equivalent universe of measures and disclose attribution coverage. Treat unavailable sponsorship as unknown. Compare stage advancement only when both cities have reliable evidence for the same stages, observation window and measure types. Routine motions, seconding and voting frequency do not establish effectiveness. If coverage is inadequate, publish observed activity and explain the gap. Compare council powers separately using charter and ordinance sections for budget, taxation, appointments, oversight, veto/override and other relevant authority. Meeting minutes show how authority was exercised.

## 5. Rebuild and hand off

Use the repository examples below. They are city-specific and should be run from the repo root in a review branch. Commit changes after reviewing the diff.

- **Records.** Follow the [Cranston records runbook](cranston-records-intern-guide.md) for the collector, parser, export and checks. Use [Cranston's normalized CSVs](../data/cranston/records-2026/csv/) as the starting schema and the [Central Falls measures CSV](../data/central-falls/council-measures-2026.csv) as a compact comparison example.
- **Maps.** Read the input requirements in the [Central Falls map builder](../scripts/build_central_falls_map.py) before using its `--source-dir` argument. It expects locally obtained source files and GDAL. Run `node scripts/test_municipal_map.cjs` for shared map logic and the Cranston precinct fixture. Add manual address and coverage checks for the new city.
- **Website.** Add reviewed identities and routes to the [local representation registry](../data/local_representatives.json). Reuse the existing municipal profile and map layouts. Test the candidate directory by name, ward/map navigation, and source PDF links. Rebuild with `python scripts/build_sitemap.py` after adding the profile links. Check the sitemap for the intended URLs. Sitemap inclusion makes pages discoverable. Verify Google indexing separately in Search Console if needed.

The student handoff is a reviewed master workbook, matching CSV exports, source register and originals or stable links, a coverage and review log, and rebuild instructions identifying input files and commands. Add a short note giving the date range, record counts, which checks passed, and which claims remain unresolved. The maintainer reviews the handoff before publishing. A new city is ready when another student can trace its published claims to the originals and rerun the calculations with the same inputs.
