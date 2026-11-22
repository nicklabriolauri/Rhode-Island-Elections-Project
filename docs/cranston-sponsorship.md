# Cranston observed sponsorship activity

Public overview: `/cranston-sponsorship.html`. The Council record section on the existing Cranston profiles links to `#sponsorship` without adding another main profile tab.

## Update

Run `python scripts/cranston_sponsorship.py` after updating `data/cranston/records-2026/records.json`. The command regenerates the public JSON, per-member CSV credits, overview and nine existing profile sections. It uses only Python's standard library. The existing `publish_cranston_profile_records.py` also builds the sponsorship data; its final presentation refresh preserves the cards.

Run `python scripts/test_cranston_sponsorship.py` for the initial snapshot's attribution, deduplication, sources, service-period and idempotence checks. Snapshot count assertions should be deliberately updated after reviewed data changes.

## Definitions

This is a partial record of observed member–measure sponsorships, not a new-introduction count, a passage rate, a productivity ranking or a CEL effectiveness score. Multiple names under Sponsored by receive joint credit. Explicit cosponsors are separate, and a member is counted only once per measure. Moving, seconding, speaking or voting Yes does not create a sponsorship credit. Ordinance identifiers normalize leading zeros. Resolution IDs link through the underlying record dataset; other titles use stable normalized-title hashes. Earlier-year items considered in 2026 remain labeled.

Classification separates ordinances, policy-position resolutions, symbolic display policy, and recognition/commemoration. No significance weights are applied. The public source action text remains available because a successful motion to continue or amend is not final adoption.

Three reviewed groups of cosponsor additions are keyed by stable motion ID in `data/cranston/sponsorship-review.json`. Additions require an explicit named source; do not assign unnamed requests. Fields missing from the extraction remain unknown. Full minutes contain some additional sponsorships and some excerpts cross proposal boundaries, so counts can be incomplete in different ways for different members. Repair source boundaries and verify newly recovered attributions before extending coverage.

The 2026 roster has nine members. Only six also have current incoming-term profile pages. Haupt, Mangahas and Stycos receive no outgoing-council counts. Haroian's 2026 sponsorship activity belongs to her Ward 2 service, even though her incoming profile is citywide. Graziano, Campopiano and Buonanno remain accessible in the 2026 overview without inventing new candidate profiles.

## Initial snapshot

42 identified items from 46 formal sponsorship contexts, with council-member attribution on 40. Counts reflect the extracted records, not an exhaustive source-document transcription. The source roster order is used for the overview table, never a count-based rank. Data reviewed November 22, 2026.

## Research background

https://thelawmakers.org/methodology — sponsorship is an input alongside progress through lawmaking stages and substantive importance. These descriptive municipal counts do not reproduce that model.
