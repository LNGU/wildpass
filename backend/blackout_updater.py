"""
Automated Blackout Date Updater

Fetches the latest GoWild! Pass blackout dates from Frontier's terms-and-conditions
page and caches them.

The scraper is intentionally strict about *where* on the page it looks. The same
page has at least three "subject to blackout periods" passages (Companion
certificate, GoWild URL pointer, and the GoWild date listing). Earlier versions
of this scraper used a greedy regex over the entire page which scooped up
sentences like "2025-2026 GoWild Annual Pass: May 1, 2025 - April 30, 2026" and
produced bogus 2028 entries with generic "January Period" descriptions.

This rewrite:
- Locates the GoWild! Pass section first, then finds the explicit listing block
  ("subject to blackout periods:" followed by lines like "2026: January 1, 3-4, ...").
- Stops parsing as soon as the page emits the disclaimer
  ("Blackout dates for May 2027 and beyond will be posted in advance...").
- Skips 2028 entirely because Frontier has not published it yet.
- Reuses the hand-curated descriptions in gowild_blackout.py when a scraped
  date matches, falling back to a small US-federal-holiday lookup otherwise.
- Dedupes by (year, start, end) before returning.

If the scraper returns a sane count for the years we care about, the caller
prefers scraped data and falls back to gowild_blackout.py only when the scrape
fails or returns zero entries for the upcoming year.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

FRONTIER_URL = "https://www.flyfrontier.com/frontiermiles/terms-and-conditions/#GoWild!_Pass"
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blackout_cache.json")
UPDATE_INTERVAL_DAYS = 30  # Check monthly

# Years we actually serve from the API. 2028 is intentionally excluded — the page
# says "Blackout dates for May 2027 and beyond will be posted in advance".
TARGET_YEARS = ("2026", "2027")

MONTHS: Dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

# Phrases that, if found inside or near the candidate block, mean we picked up
# the wrong region of the page (e.g. an "Annual Pass" contractual passage rather
# than the blackout date listing).
DENYLIST_PHRASES = (
    "annual pass",
    "renewal term",
    "valid for travel",
    "expiration",
    "expire",
    "purchaser",
    "enrollment price",
)


# =============================================================================
# Caching helpers
# =============================================================================

def should_update() -> bool:
    """Return True if the cache is missing or older than UPDATE_INTERVAL_DAYS."""
    if not os.path.exists(CACHE_FILE):
        return True
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            last_update = datetime.fromisoformat(cache.get("last_updated", "2000-01-01"))
            return (datetime.now() - last_update).days >= UPDATE_INTERVAL_DAYS
    except Exception as e:
        print(f"Error checking update time: {e}")
        return True


# =============================================================================
# Description lookup — prefer hand-curated labels, fall back to US holidays
# =============================================================================

def _curated_descriptions() -> Dict[Tuple[str, str], str]:
    """Build a (start, end) -> description map from gowild_blackout.py."""
    out: Dict[Tuple[str, str], str] = {}
    try:
        from gowild_blackout import GoWildBlackoutDates
        for periods in (GoWildBlackoutDates.BLACKOUT_PERIODS_2026,
                        GoWildBlackoutDates.BLACKOUT_PERIODS_2027):
            for start, end, desc in periods:
                out[(start, end)] = desc
    except Exception as e:
        print(f"⚠️  Could not import curated descriptions: {e}")
    return out


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """nth occurrence of `weekday` (Mon=0..Sun=6) in (year, month)."""
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Last occurrence of `weekday` in (year, month)."""
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    d = next_month - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def _us_holiday_label(d: date) -> Optional[str]:
    """Return a US-federal holiday label for the given date, or None."""
    y, m, day = d.year, d.month, d.day
    if (m, day) == (1, 1):
        return "New Year's Day"
    if m == 1 and d == _nth_weekday(y, 1, 0, 3):
        return "MLK Day"
    if m == 2 and d == _nth_weekday(y, 2, 0, 3):
        return "Presidents Day"
    if m == 5 and d == _last_weekday(y, 5, 0):
        return "Memorial Day"
    if (m, day) == (7, 4):
        return "Independence Day"
    if m == 9 and d == _nth_weekday(y, 9, 0, 1):
        return "Labor Day"
    if m == 10 and d == _nth_weekday(y, 10, 0, 2):
        return "Columbus Day"
    if m == 11 and d == _nth_weekday(y, 11, 3, 4):
        return "Thanksgiving"
    if (m, day) == (12, 25):
        return "Christmas Day"
    return None


def _fallback_description(start: str, end: str) -> str:
    """Generate a descriptive label when no curated entry matches."""
    try:
        s = datetime.strptime(start, "%Y-%m-%d").date()
        e = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        return "Blackout period"

    # Single-day: prefer a holiday name if it matches
    if s == e:
        label = _us_holiday_label(s)
        if label:
            return label
        return s.strftime("%B %-d")

    # Multi-day: see if any day in range is a US holiday and use its name + "Period"
    cur = s
    while cur <= e:
        label = _us_holiday_label(cur)
        if label:
            return f"{label} Period"
        cur += timedelta(days=1)

    # Otherwise label by month
    if s.month == e.month:
        return f"{s.strftime('%B')} Period"
    return f"{s.strftime('%B')}–{e.strftime('%B')} Period"


# =============================================================================
# Scraper
# =============================================================================

def _locate_gowild_blackout_block(text: str) -> Optional[str]:
    """
    Find the GoWild! Pass blackout listing block.

    The page contains several "subject to blackout periods" sentences. The
    correct one is inside the GoWild! Pass section and is immediately followed
    by lines of the form "YYYY: Month day, day-day, ...".

    Returns the raw text block (up to the disclaimer or two blank lines) or
    None if the structure no longer matches.
    """
    lower = text.lower()
    # Anchor on the GoWild Pass section heading ("14. GoWild! Pass..."),
    # not the table-of-contents link that appears at the top of the page.
    heading_match = re.search(r"\d+\.\s*gowild!?\s*pass", lower)
    gowild_idx = heading_match.start() if heading_match else 0

    # Walk through every "subject to blackout periods" occurrence after the
    # GoWild heading and pick the first one where the next ~50 chars contain a
    # year + colon (e.g. "2026:"). This filters out the URL-pointer passage
    # ("Blackout dates are posted at ...") which has no inline year listing.
    search_from = gowild_idx
    while True:
        idx = lower.find("subject to blackout periods", search_from)
        if idx < 0:
            return None
        # Look ahead a short window for a "YYYY:" marker
        window = text[idx:idx + 400]
        if re.search(r"\b20(2[6-9]|3\d)\s*:", window):
            break
        search_from = idx + 1

    # Skip past the heading line itself, then grab content until the disclaimer
    # sentence ("Blackout dates for May 2027 and beyond will be posted...") or
    # two consecutive blank lines (end of section).
    block_start = idx
    # Search forward for the disclaimer
    disclaimer_match = re.search(
        r"Blackout dates for [A-Za-z]+ \d{4} and beyond will be posted",
        text[block_start:],
        flags=re.IGNORECASE,
    )
    if disclaimer_match:
        block_end = block_start + disclaimer_match.start()
    else:
        # Fall back: 2 blank lines
        blank_match = re.search(r"\n\s*\n\s*\n", text[block_start:])
        block_end = block_start + (blank_match.start() if blank_match else 1500)

    block = text[block_start:block_end]

    # Sanity-check: if any DENYLIST phrase appears we likely matched the wrong
    # passage. Bail and let the caller fall back to curated data.
    lower_block = block.lower()
    for phrase in DENYLIST_PHRASES:
        if phrase in lower_block:
            print(f"⚠️  Blackout block contains denylisted phrase '{phrase}' — refusing to parse")
            return None

    return block


def _parse_year_line(year: str, body: str) -> List[Dict[str, str]]:
    """
    Parse a single line like '2026: January 1, 3-4, 15-16, 19; February 12-13, 16; ...'.

    Returns a list of {'start','end','description'} dicts.
    """
    entries: List[Dict[str, str]] = []
    # Trim and strip trailing punctuation
    body = body.strip().rstrip(".").rstrip(";").strip()
    if not body:
        return entries

    # Month groups are `;` separated. Within a group: 'Month day, day-day, ...'.
    for group in body.split(";"):
        group = group.strip().rstrip(".").strip()
        if not group:
            continue

        # Match the leading month name; the rest is a comma-separated day list.
        m = re.match(
            r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<rest>.+)",
            group,
            re.IGNORECASE,
        )
        if not m:
            continue

        month_num = MONTHS[m.group("month").lower()]
        days_text = m.group("rest")

        for token in days_text.split(","):
            token = token.strip().rstrip(".").strip()
            if not token:
                continue
            # Accept "1", "1-2", "28-30"
            mr = re.match(r"^(\d{1,2})(?:\s*-\s*(\d{1,2}))?$", token)
            if not mr:
                continue
            start_day = int(mr.group(1))
            end_day = int(mr.group(2)) if mr.group(2) else start_day
            if not (1 <= start_day <= 31 and 1 <= end_day <= 31):
                continue
            try:
                start_iso = f"{year}-{month_num:02d}-{start_day:02d}"
                end_iso = f"{year}-{month_num:02d}-{end_day:02d}"
                # Validate by round-tripping through datetime
                datetime.strptime(start_iso, "%Y-%m-%d")
                datetime.strptime(end_iso, "%Y-%m-%d")
            except ValueError:
                continue
            entries.append({"start": start_iso, "end": end_iso, "description": ""})

    return entries


def _parse_blackout_block(block: str) -> Dict[str, List[Dict[str, str]]]:
    """Parse the located block into per-year entry lists."""
    out: Dict[str, List[Dict[str, str]]] = {y: [] for y in TARGET_YEARS}

    # Find lines like "2026: January 1, 3-4 ... December 19-31."
    for match in re.finditer(
        r"(?P<year>20\d{2})\s*:\s*(?P<body>.+?)(?=\n\s*20\d{2}\s*:|\Z)",
        block,
        flags=re.DOTALL,
    ):
        year = match.group("year")
        if year not in TARGET_YEARS:
            continue  # Drop 2025 (past) and 2028+ (not published)
        body = match.group("body")
        # Strip linebreaks inside the body so multi-line wraps still parse
        body = re.sub(r"\s+", " ", body).strip()
        out[year].extend(_parse_year_line(year, body))

    return out


def _enrich_descriptions(periods: Dict[str, List[Dict[str, str]]]) -> Dict[str, List[Dict[str, str]]]:
    """Apply curated descriptions (preferred) or holiday-based fallbacks."""
    curated = _curated_descriptions()
    for year, entries in periods.items():
        for entry in entries:
            key = (entry["start"], entry["end"])
            entry["description"] = curated.get(key) or _fallback_description(entry["start"], entry["end"])
    return periods


def _dedupe(periods: Dict[str, List[Dict[str, str]]]) -> Dict[str, List[Dict[str, str]]]:
    """Remove duplicate (start, end) entries within each year, preserving order."""
    out: Dict[str, List[Dict[str, str]]] = {}
    for year, entries in periods.items():
        seen = set()
        unique: List[Dict[str, str]] = []
        for entry in entries:
            key = (entry["start"], entry["end"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(entry)
        # Sort by start date for stable output
        unique.sort(key=lambda e: e["start"])
        out[year] = unique
    return out


def fetch_blackout_dates() -> Dict:
    """Fetch + parse blackout dates and cache the result."""
    print(f"Fetching blackout dates from {FRONTIER_URL}...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(FRONTIER_URL, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Error fetching Frontier page: {e}")
        return load_cached_data()

    soup = BeautifulSoup(response.content, "html.parser")
    text_content = soup.get_text()

    block = _locate_gowild_blackout_block(text_content)
    if not block:
        print("⚠️  Could not locate GoWild blackout block — falling back to curated data")
        return get_fallback_data()

    periods = _parse_blackout_block(block)
    # 2028 must always be empty even if some future parser glitch adds entries.
    periods.setdefault("2028", [])
    if "2028" in periods:
        periods["2028"] = []
    periods = _enrich_descriptions(periods)
    periods = _dedupe(periods)

    # Always include 2028 key in the output for backwards-compat with callers
    periods.setdefault("2028", [])

    total = sum(len(v) for v in periods.values())
    print(f"✅ Scraped {total} blackout periods "
          f"({', '.join(f'{y}={len(periods[y])}' for y in periods)})")

    cache_data = {
        "last_updated": datetime.now().isoformat(),
        "blackout_periods": periods,
        "source": "scraper",
        "source_url": FRONTIER_URL,
    }

    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Could not write cache: {e}")

    return cache_data


def load_cached_data() -> Dict:
    """Load blackout dates from cache, or fall back to curated data."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
    return get_fallback_data()


def get_fallback_data() -> Dict:
    """Fallback blackout data sourced from gowild_blackout.py (hand-curated)."""
    try:
        from gowild_blackout import GoWildBlackoutDates

        today = datetime.now().strftime("%Y-%m-%d")
        blackout_data: Dict[str, List[Dict[str, str]]] = {y: [] for y in (*TARGET_YEARS, "2028")}

        for start, end, desc in GoWildBlackoutDates.BLACKOUT_PERIODS_2026:
            if end >= today:
                blackout_data["2026"].append({"start": start, "end": end, "description": desc})

        for start, end, desc in GoWildBlackoutDates.BLACKOUT_PERIODS_2027:
            if end >= today:
                blackout_data["2027"].append({"start": start, "end": end, "description": desc})

        return {
            "last_updated": datetime.now().isoformat(),
            "blackout_periods": blackout_data,
            "source": "fallback",
        }
    except Exception as e:
        print(f"Error loading fallback data: {e}")
        return {
            "last_updated": datetime.now().isoformat(),
            "blackout_periods": {"2026": [], "2027": [], "2028": []},
            "source": "empty",
        }


def update_if_needed() -> Dict:
    """Refresh the cache via scraper when possible, else fall back to curated data."""
    try:
        scraped = fetch_blackout_dates()
        # Sanity check: do we have plausible counts for the upcoming year?
        upcoming_year = str(datetime.now().year)
        if upcoming_year not in TARGET_YEARS:
            upcoming_year = TARGET_YEARS[0]
        upcoming_count = len(scraped.get("blackout_periods", {}).get(upcoming_year, []))

        if upcoming_count >= 10 and scraped.get("source") == "scraper":
            print(f"✅ Using scraped blackout dates ({upcoming_count} for {upcoming_year})")
            return scraped

        print(f"⚠️  Scraper returned {upcoming_count} entries for {upcoming_year} — using curated fallback")
    except Exception as e:
        print(f"⚠️  Scraper failed ({e}) — using curated fallback")

    data = get_fallback_data()
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Could not write fallback cache: {e}")
    return data


def get_blackout_data() -> Dict:
    """Get current blackout data from cache (or trigger fallback if empty)."""
    return load_cached_data() or get_fallback_data()


if __name__ == "__main__":
    print("Testing blackout date updater...")
    data = fetch_blackout_dates()
    periods = data.get("blackout_periods", {})
    total = sum(len(v) for v in periods.values())
    print(f"\nTotal blackout periods: {total}")
    for year in sorted(periods.keys()):
        entries = periods[year]
        print(f"\n{year}: {len(entries)} periods")
        for p in entries[:5]:
            print(f"  {p['start']} → {p['end']}: {p['description']}")
        if len(entries) > 5:
            print(f"  ... +{len(entries) - 5} more")
