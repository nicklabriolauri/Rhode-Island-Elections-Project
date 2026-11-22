# Cranston 2026 council records

Snapshot checked November 21, 2026. The machine-readable `records.json` gives the current retrieval timestamp and coverage.

- 22 numbered resolutions in ClerkBase, each with its adopted PDF and a matched motion.
- 19 distinct full council meeting records, including the separately published April 29 budget meeting.
- 155 recorded motions, including aggregate-only outcomes.
- 1,128 explicitly named member votes and 171 member-meeting attendance observations.
- Five review items: three inconsistent printed/name tallies, one unassigned motion result and one unresolved opening attendance entry.

The state dashboard lists duplicate filings for some sessions and has no minutes for several others. The importer deduplicates identical meeting text, prefers approved versions, labels drafts, and preserves the original sources. Committee attendance is outside this dataset. Incoming members do not inherit their predecessors' votes.

`originals/` retains government documents. `sources.json` preserves extracted text, retrieval metadata and hashes. `records.json` contains normalized meetings, attendance, motions, member votes and resolution matches. `csv/` provides flat-table exports for Excel or statistical software. `source-indexes.json` records the ClerkBase table of contents used for discovery. Human corrections belong in a separate `review-overrides.json`, not in the original source text.

Start with [the intern guide](../../../docs/cranston-records-intern-guide.md). Run `python scripts/test_cranston_records.py` before publication. The [public archive](https://www.rhodeislandelectionsproject.org/cranston-records.html) links each decision to its source.
