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
        r"quorum\s+is\s+declared\s+present\s+with\s+(\d+)\s+(?:members?|Senators?)?\s*present\s+and\s+(\d+)\s+(?:members?|Senators?)?\s*absent",
        r"(?:roll\s+is\s+called.*?)(\d+)\s+(?:members?|Senators?)\s+present\s+and\s+(\d+)\s+(?:members?|Senators?)\s+absent",
        r"(\d+)\s+(?:members?|Senators?)\s+present\s+and\s+(\d+)\s+(?:members?|Senators?)\s+absent",
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
    """Extract PRESENT/ABSENT lists immediately following the quorum sentence."""
    t = normalize_roll_text(t)
    dp, da, pos = opening_roll_anchor(t)
    if pos is None:
        return dp, da, "", ""
    tail = t[pos:]
    pm = re.search(rf"\bPRESENT\s*-\s*{dp}\s*:\s*", tail, re.I)
    if not pm:
        return dp, da, "", ""
    after_p = tail[pm.end():]
    am = re.search(rf"\bABSENT\s*-\s*{da}\s*:\s*", after_p, re.I)
    if not am:
        return dp, da, "", ""
    present = after_p[:am.start()].strip()
    after_a = after_p[am.end():]
    heading = re.search(
        r"\n\s*(?:OATH OF OFFICE|INVOCATION|PLEDGE OF ALLEGIANCE|APPROVAL OF RECORD|"
        r"COMMUNICATIONS?|ADDRESS(?:ES)?|ELECTION OF|NOW PRESIDING|ANNOUNCEMENTS?|"
        r"CALENDAR|NEW BUSINESS|TRANSMITTAL|ADJOURNMENT)\b",
        after_a, re.I,
    )
    absent = after_a[:heading.start()].strip() if heading else after_a.split("\n", 1)[0].strip()
    return dp, da, present, absent

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
    dp, da, present_section, absent_section = opening_roll_sections(t)
    present_raw = split_roll_names(present_section, chamber, "PRESENT")
    absent_raw = split_roll_names(absent_section, chamber, "ABSENT")

    present = {surname(x) for x in present_raw}
    absent = {surname(x) for x in absent_raw}

    # A small number of official House Journals contain a clerical duplication:
    # a member is printed in BOTH the PRESENT and ABSENT lists. Example:
    # 2025-05-01 prints Lima, Newberry and Santucci in both lists. In that Journal
    # the raw PRESENT list has 69 names although the Journal declares PRESENT - 66;
    # removing the three names explicitly repeated under ABSENT yields exactly
    # 66 present + 9 absent = the full 75-member House.
    #
    # Resolve this only when the arithmetic proves the correction. We never guess:
    # the explicit ABSENT list takes precedence only if removing the overlap makes
    # BOTH declared totals and the full declared membership reconcile exactly.
    overlap = present & absent
    overlap_resolution = None
    if overlap and dp is not None and da is not None:
        candidate_present = present - overlap
        declared = dp + da
        if (
            len(candidate_present) == dp
            and len(absent) == da
            and len(candidate_present | absent) == declared
        ):
            present = candidate_present
            overlap_resolution = {
                "method": "explicit_absent_list_precedence",
                "names": sorted(overlap),
            }

    declared = (dp + da) if dp is not None and da is not None else None
    initial_valid = (
        declared is not None
        and len(present) == dp
        and len(absent) == da
        and len(present | absent) == declared
        and not (present & absent)
    )

    late = {surname(x) for x in late_arrivals(t)}
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
        "present": sorted(present),
        "absent": sorted(absent),
        "late_arrivals": sorted(late),
        "overlap_resolution": overlap_resolution,
        "validated": initial_valid,
        "parsed_present_count": len({surname(x) for x in present_raw}),
        "parsed_absent_count": len({surname(x) for x in absent_raw}),
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
    """Fast deterministic checks that run on every GitHub Action invocation."""
    checks = {
        "Brien": "brien",
        "O'Brien": "obrien",
        "O’Brien": "obrien",
        "Shallcross Smith": "smith",
        "de la Cruz": "cruz",
    }
    got = {name: surname(name) for name in checks}
    if got != checks:
        raise RuntimeError(f"Name-normalization self-check failed: {got}")
    if surname("Brien") == surname("O'Brien"):
        raise RuntimeError("Brien/O'Brien collision detected")

    # Official House Journal, Jan. 7, 2025: 73 present / 2 absent.
    h_0107 = """The roll is called, and a quorum is declared present with 73 members present and 2 members absent as follows:
PRESENT – 73: The Honorable Speaker Shekarchi and Representatives Abney, Ackerman, Ajello, Alzate, Azzinaro, Batista, Bennett, Biah, Blazejewski, Boylan, Brien, Caldwell, Carson, Casey, Casimiro, Chippendale, Cortvriend, Corvese, Costantino, Cotter, Craven, Cruz, Dawson, DeSimone, Diaz, Donovan, Edwards, Fascia, Felix, Fellela, Finkelman, Fogarty, Furtado, Giraldo, Hopkins, Hull, Kazarian, Kennedy, Kislak, Knight, Lima, Lombardi, Marszalkowski, McEntee, McGaw, McNamara, Messier, Morales, Nardone, Newberry, Noret, O'Brien, Paplauskas, Perez, Phillips, Place, Potter, Quattrocchi, Read, Roberts, Sanchez, Santucci, Serpa, Shallcross Smith, Shanley, Slater, Solomon, Speakman, Spears, Stewart, Tanzi, and Voas.
ABSENT – 2: Representatives Baginski and Handy.
OATH OF OFFICE"""
    r = parse_session("house", dt.date(2025, 1, 7), "fixture", h_0107)
    if not r["validated"] or (r["declared_present"], r["declared_absent"]) != (73, 2):
        raise RuntimeError(f"House 2025-01-07 fixture failed: {r}")

    # Official House Journal, May 1, 2025: the printed PRESENT list repeats
    # Lima, Newberry and Santucci even though all three are also explicitly ABSENT.
    # The declared totals are 66/9. The parser may correct this only when the
    # arithmetic reconciles exactly to the 75-member House.
    h_0501 = """The roll is called and a quorum is declared present with 66 members present and 9 members absent as follows:
PRESENT – 66: The Honorable Speaker Shekarchi and Representatives Abney, Ackerman, Ajello, Alzate, Azzinaro, Baginski, Batista, Bennett, Biah, Blazejewski, Boylan, Brien, Caldwell, Carson, Casey, Casimiro, Chippendale, Cortvriend, Corvese, Costantino, Cotter, Craven, Cruz, Dawson, DeSimone, Diaz, Donovan, Edwards, Fascia, Finkelman, Furtado, Handy, Hopkins, Hull, Kazarian, Kislak, Knight, Lima, Lombardi, Marszalkowski, McEntee, McGaw, McNamara, Messier, Morales, Nardone, Newberry, O'Brien, Paplauskas, Perez, Phillips, Place, Potter, Quattrocchi, Read, Roberts, Sanchez, Santucci, Serpa, Shallcross Smith, Shanley, Slater, Solomon, Speakman, Spears, Stewart, Tanzi, and Voas.
ABSENT – 9: Representatives Felix, Fellela, Fogarty, Giraldo, Kennedy, Lima, Newberry, Noret and Santucci.
INVOCATION"""
    r = parse_session("house", dt.date(2025, 5, 1), "fixture", h_0501)
    if not r["validated"] or set((r.get("overlap_resolution") or {}).get("names", [])) != {"lima", "newberry", "santucci"}:
        raise RuntimeError(f"House 2025-05-01 overlap fixture failed: {r}")

    # Official House Journal, Jan. 6, 2026 contains two opening rolls:
    # 62/13 for adjournment of 2025 and 68/7 after commencement of 2026.
    h_0106 = """The roll is called and a quorum is declared present with 62 members present and 13 members absent as follows:
PRESENT – 62: The Honorable Speaker Shekarchi and Representatives Abney, Ackerman, Ajello, Alzate, Azzinaro, Baginski, Bennett, Biah, Blazejewski, Boylan, Brien, Caldwell, Casey, Casimiro, Chippendale, Corvese, Cotter, Craven, Cruz, Dawson, DeSimone, Diaz, Donovan, Fascia, Fellela, Finkelman, Fogarty, Giraldo, Handy, Hopkins, Kazarian, Kennedy, Knight, Lombardi, Marszalkowski, McEntee, McGaw, McNamara, Messier, Morales, Nardone, Newberry, Noret, O'Brien, Paplauskas, Perez, Phillips, Place, Potter, Read, Roberts, Santucci, Serpa, Shallcross Smith, Shanley, Solomon, Speakman, Spears, Stewart, Tanzi, and Voas.
ABSENT – 13: Representatives Batista, Carson, Cortvriend, Costantino, Edwards, Felix, Furtado, Hull, Kislak, Lima, Quattrocchi, Sanchez, and Slater.
COMMENCEMENT OF 2026
The roll is called and a quorum is declared present with 68 members present and 7 members absent as follows:
PRESENT – 68: The Honorable Speaker Shekarchi and Representatives Abney, Ackerman, Ajello, Alzate, Azzinaro, Baginski, Batista, Bennett, Biah, Blazejewski, Boylan, Brien, Caldwell, Casey, Casimiro, Chippendale, Corvese, Cotter, Craven, Cruz, Dawson, DeSimone, Diaz, Donovan, Fascia, Felix, Fellela, Finkelman, Fogarty, Furtado, Giraldo, Handy, Hopkins, Hull, Kazarian, Kennedy, Knight, Lombardi, Marszalkowski, McEntee, McGaw, McNamara, Messier, Morales, Nardone, Newberry, Noret, O'Brien, Paplauskas, Perez, Phillips, Place, Potter, Read, Roberts, Sanchez, Santucci, Serpa, Shallcross Smith, Shanley, Slater, Solomon, Speakman, Spears, Stewart, Tanzi, and Voas.
ABSENT – 7: Representatives Carson, Cortvriend, Costantino, Edwards, Kislak, Lima, and Quattrocchi.
COMMUNICATION FROM THE SPEAKER"""
    r = parse_session("house", dt.date(2026, 1, 6), "fixture", h_0106)
    if not r["validated"] or (r["declared_present"], r["declared_absent"]) != (68, 7):
        raise RuntimeError(f"House 2026-01-06 transition fixture failed: {r}")

    # Official House Journal, May 7, 2026: 75/0 verifies zero-absence handling.
    h_0507 = """The roll is called, and a quorum is declared present with 75 members present and 0 members absent as follows:
PRESENT – 75: The Honorable Speaker Shekarchi and Representatives Abney, Ackerman, Ajello, Alzate, Azzinaro, Baginski, Batista, Bennett, Biah, Blazejewski, Boylan, Brien, Caldwell, Carson, Casey, Casimiro, Chippendale, Cortvriend, Corvese, Costantino, Cotter, Craven, Cruz, Dawson, DeSimone, Diaz, Donovan, Edwards, Fascia, Felix, Fellela, Finkelman, Fogarty, Furtado, Giraldo, Handy, Hopkins, Hull, Kazarian, Kennedy, Kislak, Knight, Lima, Lombardi, Marszalkowski, McEntee, McGaw, McNamara, Messier, Morales, Nardone, Newberry, Noret, O'Brien, Paplauskas, Perez, Phillips, Place, Potter, Quattrocchi, Read, Roberts, Sanchez, Santucci, Serpa, Shallcross Smith, Shanley, Slater, Solomon, Speakman, Spears, Stewart, Tanzi, and Voas.
ABSENT – 0: Representatives
INVOCATION"""
    r = parse_session("house", dt.date(2026, 5, 7), "fixture", h_0507)
    if not r["validated"] or (r["declared_present"], r["declared_absent"]) != (75, 0):
        raise RuntimeError(f"House 2026-05-07 zero-absence fixture failed: {r}")

    # Official Senate Journal, Apr. 14, 2026: 32/6 and President Lawson included.
    s_0414 = """The roll is called and a quorum is declared present with 32 Senators present and 6 Senators absent as follows:
PRESENT –32: The Honorable President Valarie J. Lawson, Senators Acosta, Appollonio, Bell, Bissaillon, Britto, Burke, de la Cruz, DiMario, Dimitri, DiPalma, Euer, Famiglietti, Gallo, Gu, LaMountain, Lauria, McKenney, Murray, Paolino, Patalano, Pearson, Raptakis, Rogers, Sosnowski, Thompson, Tikoian, Ujifusa, Urso, Valverde, Vargas, and Zurier.
ABSENT – 6: Senators Ciccone, Felag, Kallman, Mack, Morgan, and Quezada.
INVOCATION"""
    r = parse_session("senate", dt.date(2026, 4, 14), "fixture", s_0414)
    if not r["validated"] or (r["declared_present"], r["declared_absent"]) != (32, 6):
        raise RuntimeError(f"Senate 2026-04-14 fixture failed: {r}")

    print("Attendance parser self-checks: PASS")


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
                "parsed=",
                (item.get("parsed_present_count"), item.get("parsed_absent_count")),
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
