"""Dated public news and explicitly labelled, conservative historical topic links.

No language model, user input, portfolio data or credentials enter news requests.
Google News is an aggregator, not an independently verified event feed. All
classification is transparent headline keyword matching; it is not sentiment,
fact checking, a causal model, or a forecast. See ``METHOD`` in API responses.
"""

from concurrent.futures import ThreadPoolExecutor, wait
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import re
import threading
import time
from urllib.parse import urlsplit, urlunsplit
import xml.etree.ElementTree as ET

import requests


UTC = timezone.utc
CACHE_SECONDS = 20 * 60
MAX_AGE_HOURS = 72
FETCH_DEADLINE_SECONDS = 12
MAX_RESPONSE_BYTES = 1_500_000
RSS_URL = "https://news.google.com/rss/search"
METHOD = (
    "Public Google News RSS headlines, at most 72 hours old. Themes use explicit "
    "headline keyword rules, not AI fact verification. Historical links are "
    "illustrative topic comparisons from a small curated event library; they "
    "do not establish causation or predict returns. Speculative, negated and "
    "conflicting event language is excluded from historical support."
)

# These are the only network queries. They contain no user-supplied text.
QUERIES = (
    ("apple", 'Apple AAPL stock when:3d'),
    ("microsoft", 'Microsoft MSFT stock when:3d'),
    ("nvidia", 'Nvidia NVDA stock when:3d'),
    ("jpmorgan", 'JPMorgan JPM stock when:3d'),
    ("johnson", '"Johnson & Johnson" JNJ stock when:3d'),
    ("exxon", '"Exxon Mobil" XOM stock when:3d'),
    ("broad_stocks", '"S&P 500" stock market when:3d'),
    ("technology", 'Nasdaq technology semiconductor stocks when:3d'),
    ("gold", 'gold bullion market when:3d'),
    ("silver", 'silver precious metals market when:3d'),
    ("commodities", 'oil commodities supply market when:3d'),
    ("bonds", 'Treasury bonds Federal Reserve interest rates when:3d'),
    ("macro", 'Federal Reserve inflation bank failure market when:3d'),
)

SYMBOL_AREAS = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "JPM": "Financials", "JNJ": "Healthcare", "XOM": "Energy",
    "SPY": "Broad stocks", "QQQ": "Technology", "GLD": "Gold",
    "SLV": "Silver", "DBC": "Commodities", "TLT": "Bonds", "SHY": "Bonds",
}
COMPANY_SYMBOLS = {"AAPL", "MSFT", "NVDA", "JPM", "JNJ", "XOM"}
_SYMBOL_RULES = {
    "AAPL": r"\b(?:apple|aapl)\b", "MSFT": r"\b(?:microsoft|msft)\b",
    "NVDA": r"\b(?:nvidia|nvda)\b", "JPM": r"\b(?:jpmorgan|jpm)\b",
    "JNJ": r"\b(?:johnson\s*(?:&|and)\s*johnson|jnj)\b",
    "XOM": r"\b(?:exxon(?:\s*mobil)?|xom)\b",
    "SPY": r"\b(?:spy\s+(?:etf|fund)|spdr\s+s&p\s*500)\b",
    "QQQ": r"\b(?:qqq|invesco\s+nasdaq)\b",
    "GLD": r"\b(?:gld\s+(?:etf|fund)|spdr\s+gold)\b",
    "SLV": r"\b(?:slv\s+(?:etf|fund)|ishares\s+silver)\b",
    "DBC": r"\b(?:dbc\s+(?:etf|fund)|invesco\s+db\s+commodity)\b",
    "TLT": r"\btlt\b", "SHY": r"\bshy\s+(?:etf|fund)\b",
}
_AREA_RULES = {
    "Technology": r"\b(?:nasdaq|technology\s+stocks|tech\s+stocks|semiconductors?|chipmakers?)\b",
    "Financials": r"\b(?:banking|bank\s+stocks|banks|financial\s+stocks)\b",
    "Healthcare": r"\b(?:healthcare|health\s+care|pharmaceuticals?|drugmakers?)\b",
    "Energy": r"\b(?:oil|crude|natural\s+gas|energy\s+(?:stocks|sector|market))\b",
    "Broad stocks": r"\b(?:s&p\s*500|stock\s+market|wall\s+street|equities|stocks)\b",
    "Gold": r"\b(?:gold|bullion)\b", "Silver": r"\bsilver\b",
    "Commodities": r"\b(?:commodit(?:y|ies)|oil|crude|copper|wheat)\b",
    "Bonds": r"\b(?:treasur(?:y|ies)|bonds?|fixed\s+income|yields?)\b",
}

# Primary source dates were checked against their official releases. Event dates
# are release/event dates, not the date on which an article happens to discuss it.
EVENTS = (
    {"id": "fed_cut_2019_07", "date": "2019-07-31", "theme": "rate_cuts",
     "title": "Federal Reserve lowers its policy rate in July 2019",
     "source_url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20190731a.htm"},
    {"id": "fed_cut_2020_03", "date": "2020-03-15", "theme": "rate_cuts",
     "title": "Federal Reserve emergency rate cut during the pandemic",
     "source_url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm"},
    {"id": "fed_cut_2024_09", "date": "2024-09-18", "theme": "rate_cuts",
     "title": "Federal Reserve lowers its policy rate in September 2024",
     "source_url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm"},
    {"id": "fed_hike_2015_12", "date": "2015-12-16", "theme": "rate_hikes",
     "title": "Federal Reserve raises its policy rate in December 2015",
     "source_url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20151216a.htm"},
    {"id": "fed_hike_2022_03", "date": "2022-03-16", "theme": "rate_hikes",
     "title": "Federal Reserve begins its March 2022 rate increase cycle",
     "source_url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20220316a.htm"},
    {"id": "svb_failure_2023", "date": "2023-03-10", "theme": "bank_stress",
     "title": "Silicon Valley Bank closes and enters FDIC receivership",
     "source_url": "https://www.fdic.gov/news/press-releases/2023/pr23019.html"},
    {"id": "russia_invasion_2022", "date": "2022-02-24", "theme": "geopolitical_conflict",
     "title": "Russian military invasion of Ukraine begins",
     "source_url": "https://www.un.org/sg/en/content/sg/statements/2022-02-24/statement-the-secretary-general-ukraine"},
)

_THEME_RULES = {
    "rate_cuts": r"\b(?:rate\s+cuts?|cut(?:s|ting)?\s+(?:interest\s+)?rates?|lower(?:s|ed|ing)?\s+(?:interest\s+)?rates?|reduc(?:e[sd]?|ing)\s+(?:interest\s+)?rates?)\b",
    "rate_hikes": r"\b(?:rate\s+(?:hikes?|increases?)|hik(?:e[sd]?|ing)\s+(?:interest\s+)?rates?|rais(?:e[sd]?|ing)\s+(?:interest\s+)?rates?|increas(?:e[sd]?|ing)\s+(?:interest\s+)?rates?)\b",
    "inflation_rising": r"\b(?:(?:rising|higher|accelerating|hotter)\s+inflation|inflation\s+(?:rises|accelerates|surges|jumps|increases)|cpi\s+(?:rises|surges|accelerates))\b",
    "inflation_cooling": r"\b(?:(?:falling|lower|cooling|easing|slowing)\s+inflation|inflation\s+(?:falls|cools|slows|eases|declines)|cpi\s+(?:falls|cools|slows))\b",
    "bank_stress": r"\b(?:bank\s+(?:failure|failures|collapse|collapses|run|runs|crisis)|banking\s+crisis|deposit\s+flight)\b",
    "geopolitical_conflict": r"\b(?:military\s+invasion|russia(?:n)?\s+(?:invades|invasion)|invasion\s+of\s+ukraine|russia[\s-]+ukraine\s+war)\b",
    "oil_supply_disruption": r"\b(?:(?:oil|crude)\s+(?:supply\s+)?(?:disruption|disruptions|shortage|shortages)|(?:oil|crude)\s+supply\s+(?:cut|cuts|outage)|disrupt(?:s|ed|ion)?\s+(?:oil|crude)\s+supply)\b",
    "oil_surplus": r"\b(?:(?:oil|crude)\s+(?:supply\s+)?(?:surplus|glut|oversupply)|excess\s+(?:oil|crude)\s+supply)\b",
}
_OPPOSITES = (("rate_cuts", "rate_hikes"), ("inflation_rising", "inflation_cooling"),
              ("oil_supply_disruption", "oil_surplus"))
_NEGATION = re.compile(r"\b(?:no|not|never|without|unlikely|avoids?|averts?|denies?|denied|won't|isn't|aren't|doesn't|don't|didn't)\b", re.I)
_UNCERTAIN = re.compile(r"\b(?:may|might|could|would|will|expects?|expected|expectations?|predicts?|prediction|forecasts?|bets?|betting|hopes?|hoping|odds|possible|possibility|potential|poised|considers?|considering|should|whether|if|fears?|risks?|rumou?rs?|discuss(?:es|ing)?|debates?|plans?|awaits?|signals?|weighs?|urges?)\b|\?", re.I)
_RETROSPECTIVE = re.compile(r"\b(?:anniversary|years?\s+ago|looking\s+back|flashback|remembering|20\d{2})\b", re.I)
_EVENT_EXCLUSION = re.compile(
    r"\b(?:ruled?\s+out|off\s+the\s+table|on\s+hold|priced?\s+in|pricing|seen|"
    r"hypothetical|scenarios?|simulation|unless|when|contingent|conditional|"
    r"instead\s+of|rather\s+than|calling\s+for|calls?\s+for)\b", re.I)
_CONFLICT_RESOLUTION = re.compile(
    r"\b(?:cease[\s-]?fire|truce|peace\s+(?:deal|agreement|talks)|"
    r"de[\s-]?escalat\w*|war\s+(?:ends?|ended|ending|over)|"
    r"(?:ends?|ended|ending)\s+(?:the\s+)?(?:war|invasion)|"
    r"withdraw(?:s|al|ing)?|retreat(?:s|ed|ing)?)\b", re.I)
_FED = r"(?:fed|federal\s+reserve|fomc)(?:'s)?"
_RATE_OCCURRENCE = {}
for _theme, _verb, _noun in (
    ("rate_cuts", r"(?:cuts?|lower(?:s|ed)|reduc(?:es|ed))", "cut"),
    ("rate_hikes", r"(?:rais(?:es|ed)|hik(?:es|ed)|increas(?:es|ed))", "hike"),
):
    # A bare topic such as "Fed rate cuts" is insufficient. Require a statement
    # that the Fed acted, rather than trying to enumerate all possible forecasts.
    _RATE_OCCURRENCE[_theme] = re.compile(
        rf"\b{_FED}\s+(?:(?:has|just|unexpectedly|again|finally)\s+){{0,2}}"
        rf"{_verb}\s+(?:(?:its|the)\s+)?(?:(?:interest|policy|benchmark)\s+)?rates?\b|"
        rf"\b{_FED}\s+(?:announc(?:es|ed)|approv(?:es|ed)|deliver(?:s|ed)|implement(?:s|ed))\s+"
        rf"(?:(?:a|another|its|the)\s+)?(?:interest\s+)?rate\s+{_noun}s?\b", re.I)
_MACRO_THEMES = {"rate_cuts", "rate_hikes", "inflation_rising", "inflation_cooling", "bank_stress"}
_cache = None
_cache_time = 0.0
_cache_lock = threading.Lock()
_refresh_lock = threading.Lock()


def _utc(value=None):
    value = value or datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value):
    return _utc(value).isoformat().replace("+00:00", "Z")


def _date(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _utc(parsed) if parsed.tzinfo else None
    except (ValueError, TypeError, AttributeError):
        try:
            parsed = parsedate_to_datetime(value)
            # RSS dates without a time zone are not reliable enough to use.
            return parsed.astimezone(UTC) if parsed.tzinfo else None
        except (ValueError, TypeError, AttributeError, OverflowError):
            return None


def _fresh(item, now):
    published = _date(item.get("published_at"))
    return bool(published and now - timedelta(hours=MAX_AGE_HOURS) <= published <= now)


def _plain(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


def _safe_url(value):
    try:
        parsed = urlsplit((value or "").strip())
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
            return ""
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
    except ValueError:
        return ""


def classify_themes(title):
    """Return lexical topics; disagreement and negation abstain conservatively."""
    text = _plain(title).replace("’", "'")
    themes = {name for name, pattern in _THEME_RULES.items() if re.search(pattern, text, re.I)}
    themes.update(name for name, pattern in _RATE_OCCURRENCE.items() if pattern.search(text))
    if _NEGATION.search(text):
        return []
    # Historical Fed episodes require an explicit US central-bank reference.
    fed = r"(?:fed|federal\s+reserve|fomc)(?:'s)?"
    for theme in ("rate_cuts", "rate_hikes"):
        action = _THEME_RULES[theme].replace(r"\b", "")
        # A Fed mention elsewhere in an ECB/BOJ article does not associate the
        # other central bank's decision with the Federal Reserve.
        linked = rf"\b{fed}\s+(?:(?:delivers?|announces?|makes?|approves?|implements?|unexpectedly|again|finally|aggressively)\s+){{0,2}}{action}\b|\b{action}\s+(?:by|from|at)\s+(?:the\s+)?{fed}\b"
        if not re.search(linked, text, re.I) and not _RATE_OCCURRENCE[theme].search(text):
            themes.discard(theme)
    for first, second in _OPPOSITES:
        if first in themes and second in themes:
            themes.difference_update((first, second))
    return sorted(themes)


def _classify(title):
    title = _plain(title).replace("’", "'")
    symbols = sorted(name for name, pattern in _SYMBOL_RULES.items() if re.search(pattern, title, re.I))
    areas = {name for name, pattern in _AREA_RULES.items() if re.search(pattern, title, re.I)}
    areas.update(SYMBOL_AREAS[symbol] for symbol in symbols)
    themes = classify_themes(title)
    eligible = bool(themes and not _UNCERTAIN.search(title) and not _RETROSPECTIVE.search(title)
                    and not _EVENT_EXCLUSION.search(title))
    # A generic geopolitical headline is not an analogue of Russia/Ukraine.
    event_themes = [theme for theme in themes if eligible
                    and (theme not in _RATE_OCCURRENCE or _RATE_OCCURRENCE[theme].search(title))
                    and (theme != "geopolitical_conflict" or (
                        re.search(r"\brussia(?:n)?\b", title, re.I)
                        and re.search(r"\bukraine\b", title, re.I)
                        and not _CONFLICT_RESOLUTION.search(title)))]
    event_ids = [event["id"] for event in EVENTS if event["theme"] in event_themes]
    return {"symbols": symbols, "areas": sorted(areas), "themes": themes,
            "event_ids": event_ids, "event_match_themes": sorted(set(event_themes)),
            "classification": "headline_keyword_match",
            "historical_support_eligible": bool(event_ids),
            "event_language": "reported_topic" if event_ids else "uncertain_or_unmatched"}


def _parse_feed(xml, query_id, now):
    root = ET.fromstring(xml)
    if root.tag not in ("rss", "{http://www.w3.org/2005/Atom}feed"):
        raise ValueError("Not an RSS feed")
    items, rejected = [], 0
    for node in root.findall("./channel/item")[:80]:
        title = _plain(node.findtext("title"))[:400]
        source = node.find("source")
        publisher = _plain(source.text if source is not None else "")[:160]
        url = _safe_url(node.findtext("link"))
        published = _date(node.findtext("pubDate"))
        if not title or not url or not publisher or not published:
            rejected += 1
            continue
        if title.endswith(" - " + publisher):
            title = title[:-(len(publisher) + 3)].strip()
        item = {"title": title, "url": url, "publisher": publisher,
                "publisher_url": _safe_url(source.get("url", "")) if source is not None else "",
                "published_at": _iso(published), "query_ids": [query_id]}
        if not _fresh(item, now):
            rejected += 1
            continue
        item["id"] = hashlib.sha256((title.casefold() + "|" + url).encode()).hexdigest()[:16]
        item.update(_classify(title))
        items.append(item)
    return items, rejected


def _dedupe(items):
    """Collapse duplicates across queries and syndicated identical headlines."""
    result, by_title, by_url = [], {}, {}
    for item in sorted(items, key=lambda row: row["published_at"], reverse=True):
        key = re.sub(r"[^\w]+", " ", item["title"].casefold()).strip()
        prior = by_title.get(key) or by_url.get(item["url"])
        if prior is not None:
            prior["query_ids"] = sorted(set(prior["query_ids"] + item["query_ids"]))
            by_title[key] = prior
            by_url[item["url"]] = prior
            continue
        by_title[key] = by_url[item["url"]] = item
        result.append(item)
    return result


def _fetch_feed(query_id, query, now):
    started = time.monotonic()
    with requests.get(RSS_URL, params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                      headers={"User-Agent": "BlackboxMarketResearch/1.0 (public RSS)"},
                      timeout=(2.5, 4), stream=True, allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Unexpected RSS response status")
        data = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            data.extend(chunk)
            if len(data) > MAX_RESPONSE_BYTES or time.monotonic() - started > 8:
                raise ValueError("RSS response exceeds size or duration limit")
    items, rejected = _parse_feed(bytes(data), query_id, now)
    # Equal per-query caps keep prolific gold/market feeds from crowding out
    # individual companies; the complete snapshot stays below 160 headlines.
    items = sorted(items, key=lambda row: row["published_at"], reverse=True)[:12]
    return items, {"id": query_id, "status": "ok", "accepted": len(items), "rejected": rejected,
                   "source": "Google News RSS"}


def _unavailable(now, feeds=None, errors=None):
    return {"generated_at": _iso(now), "status": "unavailable", "items": [],
            "feeds": feeds or [], "errors": errors or [], "method": METHOD,
            "source": "Google News RSS", "max_age_hours": MAX_AGE_HOURS,
            "cache_seconds": CACHE_SECONDS, "cache_hit": False}


def get_snapshot(now=None, force=False):
    """Fetch a shared market snapshot, without ever querying private user data.

    One refresh at a time, 6 workers and a 12-second response deadline. A partial
    snapshot is usable and explicitly labelled. Expired headlines are never
    served as a silent fallback, including when all upstream requests fail.
    """
    global _cache, _cache_time
    now = _utc(now)
    with _cache_lock:
        if not force and _cache is not None and time.monotonic() - _cache_time < CACHE_SECONDS:
            value = deepcopy(_cache)
            value["items"] = [item for item in value["items"] if _fresh(item, now)]
            value["cache_hit"] = True
            if not value["items"]:
                value["status"] = "unavailable"
            return value
    if not _refresh_lock.acquire(blocking=False):
        return _unavailable(now, errors=[{"id": "refresh", "reason": "refresh_in_progress"}])
    executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="market-news")
    try:
        futures = {executor.submit(_fetch_feed, key, query, now): key for key, query in QUERIES}
        completed, pending = wait(futures, timeout=FETCH_DEADLINE_SECONDS)
        items, feeds, errors = [], [], []
        for future in completed:
            key = futures[future]
            try:
                feed_items, report = future.result()
                items.extend(feed_items)
                feeds.append(report)
            except Exception as exc:
                # Do not expose request details, credentials or upstream bodies.
                errors.append({"id": key, "reason": type(exc).__name__})
                feeds.append({"id": key, "status": "error", "accepted": 0})
        for future in pending:
            future.cancel()
            key = futures[future]
            errors.append({"id": key, "reason": "deadline"})
            feeds.append({"id": key, "status": "timeout", "accepted": 0})
        value = _unavailable(now, sorted(feeds, key=lambda row: row["id"]), sorted(errors, key=lambda row: row["id"]))
        value["items"] = _dedupe(items)[:160]
        value["status"] = ("partial" if errors else "ok") if value["items"] else "unavailable"
        value["publisher_count"] = len({item["publisher"].casefold() for item in value["items"]})
        with _cache_lock:
            _cache, _cache_time = deepcopy(value), time.monotonic()
        return value
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
        _refresh_lock.release()


def evidence_for(symbol, area, snapshot, now=None):
    """Return honest company, area and macro context plus optional event links.

    ``theme_support`` counts only fresh, deduplicated headlines eligible for an
    event link. Publisher counts indicate distinct labels, not independence or
    corroboration. Callers must not treat them as verified event occurrences.
    """
    now = _utc(now)
    symbol = str(symbol or "").upper()
    area = SYMBOL_AREAS.get(symbol, area)
    rows = []
    for original in snapshot.get("items", []):
        if not _fresh(original, now):
            continue
        item = deepcopy(original)
        # Derive tags from text again so imported/saved snapshots cannot inject
        # ticker associations or historical event IDs.
        item.update(_classify(item.get("title", "")))
        if symbol in item["symbols"]:
            item["scope"] = "company" if symbol in COMPANY_SYMBOLS else "instrument"
        elif area in item["areas"]:
            item["scope"] = "area"
        elif set(item["themes"]) & _MACRO_THEMES:
            item["scope"] = "macro"
        else:
            continue
        rows.append(item)
    rows = _dedupe(rows)
    # Preserve breadth of evidence for support counts while limiting UI length.
    rows.sort(key=lambda item: (item["scope"] in ("company", "instrument"), item["published_at"]), reverse=True)
    displayed = rows[:12]
    event_ids = {event_id for item in displayed for event_id in item["event_ids"]}
    support = {}
    for item in displayed:
        for theme in item["event_match_themes"]:
            if not any(event["theme"] == theme and event["id"] in item["event_ids"] for event in EVENTS):
                continue
            entry = support.setdefault(theme, {"headline_count": 0, "publishers": [], "publisher_count": 0, "headline_ids": []})
            entry["headline_count"] += 1
            entry["headline_ids"].append(item["id"])
            if item["publisher"].casefold() not in {name.casefold() for name in entry["publishers"]}:
                entry["publishers"].append(item["publisher"])
            entry["publisher_count"] = len(entry["publishers"])
    events = [deepcopy(event) for event in EVENTS if event["id"] in event_ids]
    return {"status": snapshot.get("status", "unavailable") if displayed else "no_relevant_news",
            "snapshot_at": snapshot.get("generated_at"), "method": METHOD,
            "headlines": displayed, "headline_count": len(displayed),
            "company_headline_count": sum(item["scope"] == "company" for item in displayed),
            "publisher_count": len({item["publisher"].casefold() for item in displayed}),
            "themes": sorted({theme for item in displayed for theme in item["themes"]}),
            "event_ids": [event["id"] for event in events], "events": events,
            "theme_support": support,
            "historical_match_status": "topic_matches_only" if events else "no_supported_match",
            "source": "Google News RSS", "max_age_hours": MAX_AGE_HOURS}
