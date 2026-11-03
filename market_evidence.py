"""Observed prices and historical event associations used in recommendation reasons.

No language model generates prices, returns or ranking adjustments here.
"""
from bisect import bisect_left
from datetime import datetime, timezone
from statistics import median
import math


def daily_rows(rows):
    result = {}
    for ts, price in rows:
        if math.isfinite(price) and price > 0:
            result[datetime.fromtimestamp(ts, timezone.utc).date()] = price
    return sorted(result.items())


def price_metrics(rows):
    prices = [v for _, v in rows]
    if len(prices) < 210:
        raise ValueError("At least 210 complete daily prices required")
    returns = [math.log(b / a) for a, b in zip(prices[-64:-1], prices[-63:])]
    mean = sum(returns) / len(returns)
    vol = math.sqrt(sum((v - mean) ** 2 for v in returns) / len(returns)) * math.sqrt(252)
    return {"momentum": prices[-1] / prices[-64] - 1,
            "week": prices[-1] / prices[-6] - 1,
            "month": prices[-1] / prices[-22] - 1,
            "trend": prices[-1] / (sum(prices[-200:]) / 200) - 1,
            "vol": vol}


def base_score(metrics, capacity):
    capacity = max(0, min(100, float(capacity)))
    return .6 * metrics["momentum"] + .4 * metrics["trend"] - (1 - capacity / 100) * metrics["vol"] * .35


def event_reactions(rows, benchmark, events):
    """Event-day close (or next session) to 5/20 later sessions; no extrapolation.

    These are associations after known events, not causal or investable backtests.
    Missing coverage is returned explicitly, never replaced by the closest endpoint.
    """
    series = daily_rows(rows)
    dates = [d for d, _ in series]
    market = dict(daily_rows(benchmark))
    market_dates = sorted(market)
    comparisons, omitted = [], []
    for event in sorted(events, key=lambda e: (e["date"], e["id"])):
        day = datetime.fromisoformat(event["date"]).date()
        i = bisect_left(dates, day)
        if not dates or day < dates[0] or i + 20 >= len(dates) or (dates[i] - day).days > 4:
            omitted.append(event["id"])
            continue
        if any((dates[j + 1] - dates[j]).days > 5 for j in range(i, i + 20)):
            omitted.append(event["id"])
            continue
        start, p0 = series[i]
        end = series[i + 20][0]
        # A missing single bar can silently turn 20 observed closes into a
        # longer horizon. Check the fixed US instrument universe against SPY.
        if (market_dates and market_dates[0] <= start and market_dates[-1] >= end
                and [day for day in market_dates if start <= day <= end] != dates[i:i + 21]):
            omitted.append(event["id"])
            continue
        windows = {}
        for horizon in (5, 20):
            end, p1 = series[i + horizon]
            pct = (p1 / p0 - 1) * 100
            benchmark_pct = ((market[end] / market[start] - 1) * 100
                             if start in market and end in market else None)
            windows[str(horizon)] = {
                "start": start.isoformat(), "end": end.isoformat(), "return_pct": round(pct, 2),
                "benchmark_pct": round(benchmark_pct, 2) if benchmark_pct is not None else None,
                "excess_pct": round(pct - benchmark_pct, 2) if benchmark_pct is not None else None,
            }
        comparisons.append({**event, "windows": windows})
    return {"comparisons": comparisons, "omitted_event_ids": omitted,
            "basis": "Adjusted event-day close (next session if closed) to 5 and 20 later trading-session closes; dividends/splits adjusted. Associations, not causal estimates."}


def history_adjustment(history, headlines):
    """Small experimental rerank only with replicated, non-overlapping evidence.

    Require >=2 independent historical windows in ONE topic and >=2 publishers
    explicitly reporting that topic. Never infer sentiment from a headline.
    """
    groups = {}
    for row in history["comparisons"]:
        theme = row.get("theme", "")
        if row["windows"]["20"]["excess_pct"] is not None:
            groups.setdefault(theme, []).append(row)
    qualifying = []
    for theme, examples in groups.items():
        publishers = {h["publisher"].strip().casefold() for h in headlines
                      if theme in h.get("event_match_themes", []) and h.get("publisher")}
        independent = []
        for example in sorted(examples, key=lambda e: (e["date"], e["id"])):
            day = datetime.fromisoformat(example["date"]).date()
            window = example["windows"]["20"]
            if not window.get("start") or not window.get("end"):
                continue
            if not independent or ((day - datetime.fromisoformat(independent[-1]["date"]).date()).days >= 45
                    and window["start"] > independent[-1]["windows"]["20"]["end"]):
                independent.append(example)
        if len(independent) >= 2 and len(publishers) >= 2:
            excess = median(e["windows"]["20"]["excess_pct"] for e in independent)
            qualifying.append({"theme": theme, "events": len(independent), "publishers": len(publishers),
                               "median_excess_pct": round(excess, 2)})
    # Different themes may pull in opposite directions; keep their disagreement visible.
    if not qualifying:
        return {"value": 0.0, "status": "insufficient", "groups": []}
    values = [g["median_excess_pct"] for g in qualifying]
    if min(values) < 0 < max(values):
        return {"value": 0.0, "status": "conflicting", "groups": qualifying}
    # Only 10% of the median excess return, capped at +/-1 score point.
    adjustment = max(-.01, min(.01, median(values) / 100 * .1))
    return {"value": adjustment, "status": "applied", "groups": qualifying}
