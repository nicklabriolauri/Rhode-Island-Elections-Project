# Cranston council records: intern replication guide

For a new municipality, start with the [municipal data replication guide](municipal-data-replication-guide.md). Use this page for the Cranston-specific records workflow and worked roll-call example.
## What one record means

- **Meeting:** one full council session. Special sessions have their own IDs. Two state filings can describe the same session. Compare date, time, body and document contents before counting attendance twice.
- **Resolution:** adopted text in the city's numbered resolution index. An agenda is a proposal and is not evidence of passage.
- **Motion:** one action put to a vote, including adoption, amendment, referral, reconsideration or adjournment. Several motions can concern the same resolution. A yes vote on a motion to reject a budget is support for rejection.
- **Individual vote:** one member's explicitly named choice on one motion. Never copy a sponsor's name or the meeting attendance list into the vote field.
- **Attendance:** the opening roll call for one meeting. It does not prove attendance throughout the meeting. Preserve later arrivals/departures separately if recorded. Committee meetings require a separate membership roster and denominator.

## Repeat this workflow

1. Open https://clerkshq.com/cranston-ri. Expand **Council Resolutions**, select **2026 Resolutions**, and record every numbered row. Open the number to retrieve the adopted PDF. Keep the original filename, resolution number, adopted date, title and link. Do not fill gaps in numbering by guessing.
2. Expand **City Council Minutes** and select 2026. Check the state meeting dashboard too: https://opengov.sos.ri.gov/OpenMeetingsPublic/OpenMeetingDashboard?EntityID=715. The state can have newer minutes than ClerkBase.
3. For every listed 2026 meeting, open Meeting Details. Record the date, time and minutes availability. Prefer the newest explicitly **Approved** minutes. When only a draft exists, label it **Draft**. Retain older versions as source history, not extra meetings. No minutes on file means missing coverage, never an absence.
4. Download the minutes and adopted resolutions. Keep the source URL, downloaded filename and retrieval date. The collector saves originals and SHA-256 hashes in `data/cranston/records-2026/`.
5. Read the opening **ROLL CALL**. Enter Present, Absent or Not recorded for the correct individual. Ignore the preprinted letterhead roster if the actual roll call differs. Check the roster sums and any later arrival/departure notes.
6. Find the resolution by subject and adoption date. Look under **Reports of Committees** as well as **Resolutions**. Read the complete motion: adoption, referral and amendment are separate actions.
7. Enter each named vote and the overall tally. Confirm that named yes/no/abstention counts match the minutes. Check recusal and absence statements separately. When the minutes only say unanimous, preserve the aggregate result without creating individual votes.
8. Link the motion to the numbered resolution only when the date and subject match uniquely. Use the review queue for ambiguous matches, missing numbers, unclear names, inconsistent tallies or unavailable documents.
9. A second reviewer opens the original source and checks the names, motion meaning, date, tally and source page. Fill in **Reviewer**, **Review date** and **Review status** in the master workbook. Leave the original source excerpt unchanged. Put a correction in **Proposed correction** with its source and reason.
10. Send the completed workbook back to the project maintainer. The workbook does not publish directly to the website. The maintainer applies accepted changes in `review-overrides.json`, rebuilds the JSON and profile sections, runs the checks and publishes the changes through GitHub.

## Worked example

Resolution **2026-2**, authorizing tangible tax abatements, was adopted January 20, 2026. The resolution PDF contains the adopted measure. In the January 20 council minutes, the opening roll call is on PDF page 1 and the vote is on PDF page 2, in the Finance Committee report. The motion is Traficante's motion to adopt, seconded by Haroian. The recorded vote is **8–0**: Andujar, Ritz, Vaziri, Traficante, Campopiano, Buonanno, Haroian and Wall voted aye. Graziano was absent. Do not treat Wall's signature on the resolution as the source of his vote.

## Identity and service periods

The 2025–2026 council term ends January 4, 2027. Current Ward 2 member Kristen Haroian's votes remain her Ward 2 record when she moves to a citywide seat. Incoming members Haupt and Mangahas have no 2026 council votes. Stycos has earlier service but is not a 2026 council member. Never transfer an outgoing member's history to the winner of their seat.

## Running the scripts

Use Python 3.11+ with `pymupdf` and `beautifulsoup4`. Scanned PDFs also require Tesseract with English language data.

```bash
python -m pip install -r scripts/cranston-records-requirements.txt
python scripts/collect_cranston_2026.py
python scripts/build_cranston_records.py
python scripts/publish_cranston_profile_records.py
python scripts/test_cranston_records.py
python scripts/export_cranston_records_csv.py
```

The GitHub workflow **Import Cranston 2026 council records** can also be run manually from Actions. It collects public files and rebuilds records when its code is updated. There is no recurring schedule. Review the resulting changes and review queue after every import.

## Workbook tabs

**Guide:** workflow, definitions and worked example. **Summary:** member attendance and named vote totals calculated from the detail sheets. **Resolutions:** numbered adopted resolution inventory and source matching. **Meetings:** imported sessions and document status. **Attendance:** one member per opening roll call. **Motions:** each extracted decision and its source excerpt. **Votes:** one member per reconciled named motion. **Coverage:** every state meeting filing, including those without minutes. **Review queue:** unresolved extraction/matching issues with editable review fields. **Dictionary:** field definitions and allowed values.

Only use `Reviewed` after completing the source check. A script extraction is labeled `Source extracted`, not manually reviewed. A checked source can still be a draft. Review status and document approval status measure different things.

The CSV exporter writes portable flat tables in `data/cranston/records-2026/csv/`. Open them in Excel or import them into the matching master-workbook tabs. Preserve human review notes by stable IDs when refreshing. The website publishes aggregate outcomes as well as named votes, but only reconciled named votes appear in individual profile histories.
