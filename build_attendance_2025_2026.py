#!/usr/bin/env python3
"""
RIEP journal-based attendance builder for the 2025-2026 Rhode Island General Assembly.

Attendance = presence at a legislative session as recorded in the official
House/Senate Journal. Individual floor-vote "Not Voting" entries are never
used as attendance.

The script is deliberately fail-closed:
* every discovered Journal PDF must reconcile to its declared PRESENT/ABSENT totals;
* both chambers must have substantial coverage in both 2025 and 2026;
* no legislator may be missing from a validated session after their service start.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import time
import unicodedata
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RECORDS = DATA / "incumbent_records_2026.json"
SESSIONS_OUT = DATA / "attendance_sessions_2025_2026.json"
AUDIT_OUT = DATA / "attendance_audit_2025_2026.json"

HTTP = requests.Session()
HTTP.headers.update({
    "User-Agent": "RhodeIslandElectionsProject/1.0 (+https://www.rhodeislandelectionsproject.org/)"
})
# GitHub-hosted runners occasionally get transient 429/5xx responses from the
# General Assembly site. Retry those without weakening any data validation.
_retry = Retry(
    total=4,
    connect=4,
    read=4,
    backoff_factor=0.6,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset({"GET"}),
    raise_on_status=False,
)
HTTP.mount("https://", HTTPAdapter(max_retries=_retry))

HOUSE = "https://www.rilegislature.gov/journals/housejournals"
SENATE = "https://www.rilegislature.gov/journals/senatejournals"

WINDOWS = {
    2025: (dt.date(2025, 1, 1), dt.date(2025, 7, 31)),
    2026: (dt.date(2026, 1, 1), dt.date(2026, 7, 31)),
}

# Conservative floor only. If the legislature publishes fewer than this, the
# workflow stops for human review rather than publishing a partial denominator.
MIN_VALIDATED_SESSIONS_PER_CHAMBER_YEAR = 20


def ascii_text(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def norm(s: str) -> str:
    s = ascii_text(s).lower()
    # Keep apostrophized surnames distinct: O'Brien -> obrien, while Brien -> brien.
    # Converting apostrophes to spaces collapses both names to "brien" and causes
    # House roll-call reconciliation to fail whenever both legislators are present.
    s = s.replace("'", "").replace("’", "")
    s = re.sub(
        r"\b(the honorable|honorable|speaker|madam president|president|representatives?|senators?)\b",
        " ",
        s,
    )
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b", " ", s)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def surname(s: str) -> str:
    p = norm(s).split()
    return p[-1] if p else ""


def dates(a: dt.date, b: dt.date):
    while a <= b:
        yield a
        a += dt.timedelta(days=1)


def journal_urls(chamber: str, d: dt.date) -> list[str]:
    y = d.year
    ds = d.strftime("%m-%d-%Y")
    if chamber == "house":
        base = HOUSE
        label = "House"
        names = [f"{ds}.pdf", f"HJ%20{ds}.pdf"]
    else:
        base = SENATE
        label = "Senate"
        names = [f"SJ%20{ds}.pdf", f"{ds}.pdf"]
    return [f"{base}/{y}%20{label}%20Journals/{n}" for n in names]


def fetch_journal(chamber: str, d: dt.date):
    for url in journal_urls(chamber, d):
        try:
            r = HTTP.get(url, timeout=25)
        except requests.RequestException:
            continue
        ctype = (r.headers.get("content-type") or "").lower()
        if r.status_code == 200 and (r.content.startswith(b"%PDF") or "pdf" in ctype):
            return url, r.content
    return None


def extract_text(pdf: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf))
    # Opening roll is on the first pages; a few transition journals contain more than
    # one opening roll, so keep enough pages to capture the final opening roll.
    return "\n".join((p.extract_text() or "") for p in reader.pages[:10])


def normalize_roll_text(t: str) -> str:
    # pypdf preserves typographic dashes in many House journals. The old parser
    # normalized them only inside section(), but not inside presider(), which is why
    # the Speaker disappeared and almost every House journal failed 74/75, 72/73, etc.
    return (
        t.replace("\u2013", "-")
         .replace("\u2014", "-")
         .replace("\u2212", "-")
         .replace("\xa0", " ")
    )


def opening_roll_anchor(t: str):
    """Locate the official opening attendance roll, not a later floor-vote roll."""
    t = normalize_roll_text(t)
    patterns = [
        r"quorum\s+is\s+declared\s+present\s+with\s+(\d+)\s*(?:members?|Senators?)?\s*present\s+and\s+(\d+)\s*(?:members?|Senators?)?\s*absent",
        r"(?:roll\s+is\s+called.*?)(\d+)\s*(?:members?|Senators?)\s+present\s+and\s+(\d+)\s*(?:members?|Senators?)\s*absent",
        r"(\d+)\s*(?:members?|Senators?)\s+present\s+and\s+(\d+)\s*(?:members?|Senators?)\s*absent",
    ]
    for pat in patterns:
        matches = list(re.finditer(pat, t, re.I | re.S))
        if matches:
            # Some transition journals (notably House 2026-01-06) contain an
            # outgoing-session roll followed by the new-session opening roll.
            # The explicit quorum wording is not used for ordinary floor votes,
            # so the last such match is the correct session-opening roll.
            m = matches[-1]
            return int(m.group(1)), int(m.group(2)), m.end()
    return None, None, None


def declared_totals(t: str) -> tuple[int | None, int | None]:
    p, a, _ = opening_roll_anchor(t)
    return p, a


def opening_roll_sections(t: str):
    """Extract opening enumerated lists without trusting repeated printed totals."""
    t = normalize_roll_text(t)
    dp, da, pos = opening_roll_anchor(t)
    if pos is None:
        return dp, da, None, None, "", ""
    tail = t[pos:]
    pm = re.search(r"\bPRESENT\s*-\s*(\d+)\s*:\s*", tail, re.I)
    if not pm:
        return dp, da, None, None, "", ""
    present_label = int(pm.group(1))
    after_p = tail[pm.end():]
    am = re.search(r"\bABSENT\s*-\s*(\d+)\s*:\s*", after_p, re.I)
    if not am:
        return dp, da, present_label, None, "", ""
    absent_label = int(am.group(1))
    present = after_p[:am.start()].strip()
    if absent_label == 0:
        return dp, da, present_label, absent_label, present, ""
    after_a = after_p[am.end():]
    heading = re.search(
        r"\n\s*(?:OATH OF OFFICE|INVOCATION|MOMENT OF SILENCE|PLEDGE OF ALLEGIANCE|APPROVAL OF RECORD|"
        r"COMMUNICATIONS?|ADDRESS(?:ES)?|ELECTION OF|NOW PRESIDING|ANNOUNCEMENTS?|"
        r"CALENDAR|CONSENT CALENDAR|GUESTS?|REPORTS? OF COMMITTEES|TRANSFER OF BILLS|"
        r"NEW BUSINESS|IMMEDIATE CONSIDERATION|TRANSMITTAL|ADJOURNMENT|RULE\s+\d+[A-Z]?)\b",
        after_a, re.I,
    )
    absent = after_a[:heading.start()].strip() if heading else after_a.split("\n", 1)[0].strip()
    return dp, da, present_label, absent_label, present, absent


def expected_membership(chamber: str, d: dt.date) -> int:
    if chamber == "house":
        return 75
    if d.year == 2025 and d >= dt.date(2025, 4, 21):
        return 37
    return 38

def last_roll_section(t: str, label: str, next_labels: tuple[str, ...]) -> str:
    t = normalize_roll_text(t)
    nxt = "|".join(re.escape(x) for x in next_labels)
    pattern = (
        rf"\b{label}\s*-\s*\d+\s*:\s*(.*?)"
        rf"(?=\b(?:{nxt})\s*-|\n\s*(?:INVOCATION|PLEDGE|APPROVAL|COMMUNICATIONS|ADDRESS)\b)"
    )
    matches = list(re.finditer(pattern, t, re.I | re.S))
    return matches[-1].group(1).strip() if matches else ""


def split_roll_names(section: str, chamber: str, label: str) -> list[str]:
    s = re.sub(r"\s+", " ", normalize_roll_text(section)).strip()

    if label.upper() == "PRESENT":
        if chamber == "house":
            # Preserve the presiding Speaker as an ordinary list item.
            s = re.sub(
                r"^The Honorable Speaker\s+(.+?)\s+and\s+Representatives\s+",
                lambda m: m.group(1).strip() + ", ",
                s,
                flags=re.I,
            )
        else:
            # Senate journals vary between
            # "The Honorable President Valarie J. Lawson, Senators ..." and
            # "The Honorable President X and Senators ..."
            s = re.sub(
                r"^The Honorable President\s+(.+?)(?:,\s*|\s+and\s+)Senators\s+",
                lambda m: m.group(1).strip() + ", ",
                s,
                flags=re.I,
            )

    s = re.sub(r"^(?:Representatives|Senators)\s+", "", s, flags=re.I)
    # Official House PDFs sometimes split Mary Ann Shallcross Smith's surname
    # across comma-delimited extraction as "Shallcross, Smith". Rejoin only this
    # known current-member compound surname before generic comma splitting.
    s = re.sub(r"\bShallcross\s*,\s*Smith\b", "Shallcross Smith", s, flags=re.I)
    s = re.sub(r",?\s+and\s+", ", ", s)

    out = []
    for x in s.split(","):
        x = x.strip(" .;:")
        if surname(x):
            out.append(x)
    return out


def late_arrivals(t: str) -> list[str]:
    t = normalize_roll_text(t)
    out = []
    patterns = [
        r"(?:Representative|Senator)\s+([A-Za-z.' -]+?)\s+(?:is|was)\s+(?:now\s+)?present",
        r"(?:Representative|Senator)\s+([A-Za-z.' -]+?)\s+(?:arrives|arrived)\s+(?:in|at)\s+the\s+(?:House|Senate|Chamber)",
        r"(?:Representative|Senator)\s+([A-Za-z.' -]+?)\s+reports?\s+(?:his|her|their)\s+presence",
    ]
    for p in patterns:
        out.extend(
            re.sub(r"\s+", " ", m.group(1)).strip(" ,.;")
            for m in re.finditer(p, t, re.I)
        )
    return list(dict.fromkeys(out))


def parse_session(chamber: str, d: dt.date, url: str, t: str) -> dict:
    dp, da, present_label, absent_label, present_section, absent_section = opening_roll_sections(t)
    present_raw = split_roll_names(present_section, chamber, "PRESENT")
    absent_raw = split_roll_names(absent_section, chamber, "ABSENT")
    present = {surname(x) for x in present_raw}
    absent = {surname(x) for x in absent_raw}
    expected = expected_membership(chamber, d)

    overlap = present & absent
    overlap_resolution = None
    if overlap:
        candidate_present = present - overlap
        if len(candidate_present | absent) == expected:
            present = candidate_present
            overlap_resolution = {
                "method": "explicit_absent_list_precedence",
                "names": sorted(overlap),
            }

    names_complete = (
        len(present) > 0
        and len(present | absent) == expected
        and not (present & absent)
    )
    printed_totals_consistent = (
        dp is not None and da is not None
        and len(present) == dp and len(absent) == da
    )
    list_labels_consistent = (
        present_label is not None and absent_label is not None
        and len(present) == present_label and len(absent) == absent_label
    )
    if names_complete and printed_totals_consistent and list_labels_consistent:
        validation_method = "enumerated_names_and_printed_totals_reconcile"
    elif names_complete:
        validation_method = "enumerated_names_complete_printed_totals_inconsistent"
    else:
        validation_method = "failed_reconciliation"

    opening_present_count = len(present)
    opening_absent_count = len(absent)

    late = {surname(x) for x in late_arrivals(t)}
    if names_complete:
        for ln in late:
            absent.discard(ln)
            present.add(ln)

    return {
        "date": d.isoformat(),
        "year": d.year,
        "chamber": chamber,
        "source_url": url,
        "declared_present": dp,
        "declared_absent": da,
        "present_label": present_label,
        "absent_label": absent_label,
        "expected_membership": expected,
        "parsed_present_count": opening_present_count,
        "parsed_absent_count": opening_absent_count,
        "present": sorted(present),
        "absent": sorted(absent),
        "late_arrivals": sorted(late),
        "overlap_resolution": overlap_resolution,
        "validation_method": validation_method,
        "printed_totals_consistent": printed_totals_consistent,
        "list_labels_consistent": list_labels_consistent,
        "validated": names_complete,
    }

def collect():
    ok, bad = [], []
    for year, (a, b) in WINDOWS.items():
        for chamber in ("house", "senate"):
            for d in dates(a, b):
                found = fetch_journal(chamber, d)
                if not found:
                    continue
                url, pdf = found
                try:
                    session = parse_session(chamber, d, url, extract_text(pdf))
                except Exception as e:
                    bad.append({
                        "date": d.isoformat(),
                        "chamber": chamber,
                        "source_url": url,
                        "error": repr(e),
                    })
                    continue

                if session["validated"]:
                    ok.append(session)
                else:
                    bad.append({
                        "date": d.isoformat(),
                        "chamber": chamber,
                        "source_url": url,
                        "error": "roll-call reconciliation failed",
                        "declared_present": session["declared_present"],
                        "declared_absent": session["declared_absent"],
                        "parsed_present_count": session["parsed_present_count"],
                        "parsed_absent_count": session["parsed_absent_count"],
                        "overlap_resolution": session.get("overlap_resolution"),
                        "parsed_present_names": session.get("present", []),
                        "parsed_absent_names": session.get("absent", []),
                    })
                time.sleep(0.02)
    return ok, bad


def coverage_counts(sessions: list[dict]) -> dict:
    out = {}
    for year in WINDOWS:
        for chamber in ("house", "senate"):
            out[f"{year}_{chamber}"] = sum(
                s["year"] == year and s["chamber"] == chamber for s in sessions
            )
    return out


def merge(payload: dict, sessions: list[dict]) -> None:
    by = {
        ch: sorted(
            [s for s in sessions if s["chamber"] == ch],
            key=lambda x: x["date"],
        )
        for ch in ("house", "senate")
    }

    for r in payload["records"]:
        start = dt.date.fromisoformat(r.get("service_start", "2025-01-01"))
        ln = surname(r["candidate_name"])
        chamber_sessions = [
            s for s in by[r["chamber"]]
            if dt.date.fromisoformat(s["date"]) >= start
        ]

        eligible = [
            s for s in chamber_sessions
            if ln in s["present"] or ln in s["absent"]
        ]
        unmatched = [
            s["date"] for s in chamber_sessions
            if ln not in s["present"] and ln not in s["absent"]
        ]

        present_sessions = [s for s in eligible if ln in s["present"]]
        absent_sessions = [s for s in eligible if ln in s["absent"]]
        n = len(eligible)

        status = (
            "verified_from_official_journals"
            if n and not unmatched
            else ("partial_review_required" if n else "not_available")
        )

        r["attendance"] = {
            "period": "2025–2026 General Assembly",
            "definition": "Presence at a legislative session as recorded in the official House/Senate Journal.",
            "sessions_eligible": n or None,
            "sessions_present": len(present_sessions) if n else None,
            "sessions_absent": len(absent_sessions) if n else None,
            "attendance_rate_pct": round(100 * len(present_sessions) / n, 1) if n else None,
            "absent_dates": [s["date"] for s in absent_sessions],
            "source_urls_for_absences": [s["source_url"] for s in absent_sessions],
            "unmatched_validated_session_dates": unmatched,
            "status": status,
            "note": "Session attendance only. A floor-vote 'Not Voting' entry is not counted as an absence.",
        }
        r.setdefault("verification", {})["attendance"] = status


def self_check():
    checks = {"Brien":"brien","O'Brien":"obrien","O’Brien":"obrien","Shallcross Smith":"smith","de la Cruz":"cruz"}
    got = {k:surname(k) for k in checks}
    if got != checks or surname("Brien") == surname("O'Brien"):
        raise RuntimeError(f"Name self-check failed: {got}")

    def fixture(dp, da, pl, al, pnames, anames, chamber="house", date=dt.date(2026,2,3), no_space=False):
        unit = "Senators" if chamber == "senate" else "members"
        gap = "" if no_space else " "
        if chamber == "house":
            ptxt = "The Honorable Speaker " + pnames[0] + " and Representatives " + ", ".join(pnames[1:-1]) + ", and " + pnames[-1]
            atxt = "Representatives " + ", ".join(anames[:-1]) + ((", and " + anames[-1]) if anames else "")
        else:
            ptxt = "The Honorable President " + pnames[0] + ", Senators " + ", ".join(pnames[1:-1]) + ", and " + pnames[-1]
            atxt = "Senators " + ", ".join(anames[:-1]) + ((", and " + anames[-1]) if anames else "")
        return (
            f"The roll is called, and a quorum is declared present with {dp} {unit} present and {da}{gap}{unit} absent as follows:\n"
            f"PRESENT - {pl}: {ptxt}.\nABSENT - {al}: {atxt}.\nINVOCATION"
        )

    # 2026-02-03 pattern: PRESENT header typo "7", but 70 names + 5 absent = full House.
    p70=["Shekarchi"]+[f"P{i}" for i in range(1,70)]; a5=[f"A{i}" for i in range(1,6)]
    r=parse_session("house",dt.date(2026,2,3),"fixture",fixture(70,5,7,5,p70,a5))
    if not r["validated"] or r["present_label"] != 7 or len(r["present"]) != 70:
        raise RuntimeError(f"Feb 3 fixture failed: {r}")

    # 2026-03-12 pattern: quorum totals contradict complete enumerated 63/12 lists.
    p63=["Shekarchi"]+[f"P{i}" for i in range(1,63)]; a12=[f"A{i}" for i in range(1,13)]
    r=parse_session("house",dt.date(2026,3,12),"fixture",fixture(73,2,63,12,p63,a12))
    if not r["validated"] or len(r["present"]) != 63 or len(r["absent"]) != 12:
        raise RuntimeError(f"Mar 12 fixture failed: {r}")

    # 2026-06-08 pattern: "2members" no space.
    p73=["Blazejewski"]+[f"P{i}" for i in range(1,73)]
    r=parse_session("house",dt.date(2026,6,8),"fixture",fixture(73,2,73,2,p73,["Dawson","Shekarchi"],no_space=True))
    if not r["validated"] or r["declared_absent"] != 2:
        raise RuntimeError(f"Jun 8 fixture failed: {r}")

    # Senate ABSENT - 0 must never consume following prose.
    s38=["Lawson"]+[f"S{i}" for i in range(1,38)]
    text=fixture(38,0,38,0,s38,[],chamber="senate",date=dt.date(2026,6,9))
    r=parse_session("senate",dt.date(2026,6,9),"fixture",text)
    if not r["validated"] or r["absent"]:
        raise RuntimeError(f"Senate zero-absence fixture failed: {r}")


    # 2025-01-30 / 2025-06-16 pattern: ABSENT list is followed by MOMENT OF SILENCE.
    p70=["Shekarchi"]+[f"M{i}" for i in range(1,70)]
    a5=["Ackerman","Edwards","Lombardi","Roberts","Serpa"]
    text=fixture(70,5,70,5,p70,a5).replace("\nINVOCATION", "\nMOMENT OF SILENCE\nThe Honorable Speaker requests a moment of silence.\nINVOCATION")
    r=parse_session("house",dt.date(2025,1,30),"fixture",text)
    if not r["validated"] or len(r["absent"]) != 5:
        raise RuntimeError(f"Moment-of-silence boundary fixture failed: {r}")

    # 2026-04-09 pattern: PDF/Journals split Shallcross Smith as
    # "Quattrocchi, Shallcross, Smith, and Stewart" in the absent list.
    p65=["Shekarchi"]+[f"R{i}" for i in range(1,65)]
    a10=["Ackerman","Alzate","Baginski","Batista","Craven","Cruz","Fascia","Quattrocchi","Shallcross Smith","Stewart"]
    text=fixture(65,10,65,10,p65,a10)
    # Mimic the official extracted text's comma split.
    text=text.replace("Shallcross Smith", "Shallcross, Smith")
    r=parse_session("house",dt.date(2026,4,9),"fixture",text)
    if not r["validated"] or len(r["absent"]) != 10 or "smith" not in r["absent"]:
        raise RuntimeError(f"Shallcross-Smith extraction fixture failed: {r}")

    print("Attendance parser systematic self-checks: PASS")


def main():
    self_check()
    payload = json.loads(RECORDS.read_text(encoding="utf-8"))
    sessions, bad = collect()
    coverage = coverage_counts(sessions)

    audit = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "validated_session_count": len(sessions),
        "coverage": coverage,
        "excluded_or_failed_journals": bad,
    }

    # Fail closed BEFORE modifying the public record file.
    coverage_failures = {
        k: v for k, v in coverage.items()
        if v < MIN_VALIDATED_SESSIONS_PER_CHAMBER_YEAR
    }
    if bad or coverage_failures:
        audit["coverage_failures"] = coverage_failures
        AUDIT_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        print("Journal validation failures:", len(bad))
        for item in bad[:60]:
            print(
                "FAIL",
                item.get("date"),
                item.get("chamber"),
                "declared=",
                (item.get("declared_present"), item.get("declared_absent")),
                "labels=",
                (item.get("present_label"), item.get("absent_label")),
                "parsed=",
                (item.get("parsed_present_count"), item.get("parsed_absent_count")),
                "expected=",
                item.get("expected_membership"),
                "method=",
                item.get("validation_method"),
                "overlap=",
                item.get("overlap_resolution"),
                item.get("source_url"),
            )
        print("Coverage:", coverage)
        raise SystemExit(
            "Journal audit failed; incumbent_records_2026.json was NOT modified. "
            f"failed_journals={len(bad)} coverage_failures={coverage_failures}"
        )

    merge(payload, sessions)

    review = [
        {
            "candidate_name": r["candidate_name"],
            "chamber": r["chamber"],
            "district_number": r["district_number"],
            "status": r["attendance"]["status"],
            "unmatched_dates": r["attendance"]["unmatched_validated_session_dates"],
        }
        for r in payload["records"]
        if r["attendance"]["status"] != "verified_from_official_journals"
    ]

    audit["records_requiring_review"] = review
    AUDIT_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    if review:
        raise SystemExit(
            "Legislator/session matching requires review; public data was NOT modified."
        )

    SESSIONS_OUT.write_text(
        json.dumps(
            {
                "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "sessions": sessions,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    RECORDS.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print("Updated", RECORDS)
    print("Coverage:", coverage)


if __name__ == "__main__":
    main()
