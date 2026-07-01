.github/workflows/update-ri-politics-news.yml
ame: Update RI Politics News

on:
  schedule:
    - cron: "17 */6 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  refresh-news-feed:
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Build Rhode Island politics feed
        shell: bash
        run: |
          python - <<'PY'
          from __future__ import annotations

Local comment
Comment on lines R1 to R29


Cancel
Comment
          import json
          import re
          import xml.etree.ElementTree as ET
          from datetime import datetime, timezone
          from email.utils import parsedate_to_datetime
          from html import unescape
          from pathlib import Path
          from urllib.parse import quote_plus
          from urllib.request import Request, urlopen

          QUERY = "Rhode Island politics"
          FEED_URL = (
              "https://news.google.com/rss/search?"
              f"q={quote_plus(QUERY)}&hl=en-US&gl=US&ceid=US:en"
          )
          OUTPUT = Path("data/ri_politics_news.json")
          MAX_ITEMS = 5
          PREFERRED_SOURCES = [
              "Rhode Island Current",
              "The Providence Journal",
              "Providence Journal",
              "WPRI.com",
              "WPRI 12",
              "NBC 10 WJAR",
              "The Boston Globe",
              "GoLocalProv",
              "Ocean State Media",
          ]
          ALLOWED_SOURCE_TOKENS = (
              "Rhode Island Current",
              "Providence Journal",
              "WPRI",
              "NBC 10",
              "Boston Globe",
              "GoLocalProv",
              "Ocean State Media",
          )

          def clean_text(value: str) -> str:
              value = unescape(value or "")
              value = re.sub(r"<[^>]+>", "", value)
              value = re.sub(r"\s+", " ", value).strip()
              return value

          def extract_source_and_title(raw_title: str) -> tuple[str, str]:
              title = clean_text(raw_title)
              for separator in (" - ", " | ", " — "):
                  if separator in title:
                      head, tail = title.rsplit(separator, 1)
                      if tail:
                          return tail.strip(), head.strip()
              return "", title

          def source_allowed(source: str) -> bool:
              return any(token.lower() in source.lower() for token in ALLOWED_SOURCE_TOKENS)

          def parse_pubdate(raw: str) -> str:
              try:
                  return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
              except Exception:
                  return ""

          def normalize_source_rank(source: str) -> tuple[int, str]:
              if source in PREFERRED_SOURCES:
                  return (PREFERRED_SOURCES.index(source), source)
              return (len(PREFERRED_SOURCES) + 1, source)

          request = Request(
              FEED_URL,
              headers={
                  "User-Agent": "Mozilla/5.0",
