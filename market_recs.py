"""Historical market screen for the questionnaire; never places orders."""
from datetime import datetime, timezone
import math
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from market_evidence import price_metrics, base_score, event_reactions, history_adjustment
import news_evidence

UNIVERSE = {
    "AAPL": ("Apple", "stock", "Technology"),
    "MSFT": ("Microsoft", "stock", "Technology"),
    "NVDA": ("Nvidia", "stock", "Technology"),
    "JPM": ("JPMorgan Chase", "stock", "Financials"),
    "JNJ": ("Johnson & Johnson", "stock", "Healthcare"),
    "XOM": ("Exxon Mobil", "stock", "Energy"),
    "SPY": ("S&P 500 fund", "fund", "Broad stocks"),
    "QQQ": ("Nasdaq 100 fund", "fund", "Technology"),
    "GLD": ("Gold fund", "commodity fund", "Gold"),
    "SLV": ("Silver fund", "commodity fund", "Silver"),
    "DBC": ("Broad commodity fund", "commodity fund", "Commodities"),
    "TLT": ("Long Treasury bond fund", "fund", "Bonds"),
    "SHY": ("Short Treasury bond fund", "fund", "Bonds"),
}
_cache = {}


def _history(symbol, range_name="5y"):
    key = (symbol, range_name)
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < 21600:
        return cached[1]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    # Yahoo's range=max silently returns monthly bars. Explicit bounds preserve
    # daily history and cover our earliest curated event (December 2015).
    params = {"interval": "1d"}
    if range_name == "max":
        params.update(period1=1388534400, period2=int(time.time()))  # 2014-01-01 UTC
    else:
        params["range"] = range_name
    response = requests.get(url, params=params,
                            headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
    response.raise_for_status()
    item = response.json()["chart"]["result"][0]
    if item.get("meta", {}).get("dataGranularity", "1d") != "1d":
        raise ValueError("Daily price interval required")
    closes = item["indicators"]["adjclose"][0]["adjclose"]
    now = datetime.now(timezone.utc)
    by_day = {}
    for timestamp, price in zip(item["timestamp"], closes):
        try:
            timestamp, price = float(timestamp), float(price)
            day = datetime.fromtimestamp(timestamp, timezone.utc).date()
        except (ValueError, TypeError, OverflowError, OSError):
            continue
        if not math.isfinite(price) or price <= 0 or timestamp > now.timestamp():
            continue
        # Conservatively wait until 22 UTC before using today's US closing bar.
        if day == now.date() and now.hour < 22:
            continue
        if day not in by_day or timestamp > by_day[day][0]:
            by_day[day] = (timestamp, price)
    rows = [by_day[day] for day in sorted(by_day)]
    if len(rows) < 210:
        raise ValueError("Insufficient price history")
    _cache[key] = (time.time(), rows)
    return rows


def _fetch_history(symbol):
    try:
        return _history(symbol, "max")
    except (requests.RequestException, KeyError, IndexError, ValueError, TypeError):
        return []


def _news_snapshot():
    try:
        return news_evidence.get_snapshot()
    except Exception:
        return {"status": "unavailable", "items": [], "generated_at": None, "feeds": [], "errors": ["news unavailable"]}


def _explain(item, metrics, capacity, profile, evidence, historical, adjustment, lang):
    pl = lang == "pl"
    fmt = lambda n: f"{n:+.1f}%"
    why = [
        (f"Cena zmieniła się o {fmt(metrics['week'] * 100)} w 5 sesjach i {fmt(metrics['momentum'] * 100)} w 63 sesjach."
         if pl else f"Adjusted price changed {fmt(metrics['week'] * 100)} over 5 sessions and {fmt(metrics['momentum'] * 100)} over 63 sessions."),
        (f"Cena jest {fmt(metrics['trend'] * 100)} względem średniej z 200 sesji; zmienność roczna z ostatnich 63 sesji wynosi {metrics['vol'] * 100:.1f}%."
         if pl else f"Price is {fmt(metrics['trend'] * 100)} relative to its 200-session average; trailing annualized volatility is {metrics['vol'] * 100:.1f}%."),
        (f"Wynik uwzględnia Twój poziom ryzyka {capacity}/100 i horyzont {profile.get('horizon', '3-10y')}; większa zmienność obniża ocenę."
         if pl else f"Your risk-capacity score of {capacity}/100 and {profile.get('horizon', '3-10y')} horizon are used; higher volatility reduces the ranking."),
    ]
    caution = ["To propozycja do dalszej analizy; historyczny spadek ani wynik ankiety nie ograniczają przyszłej straty."
               if pl else "This is a research suggestion; your questionnaire loss tolerance is not a maximum-loss guarantee."]
    headlines = evidence.get("headlines", [])
    if not headlines:
        caution.append("Brak świeżych, powiązanych wiadomości. Ocena opiera się wyłącznie na cenach."
                       if pl else "No fresh relevant news was available. This suggestion is based on prices alone.")
    else:
        why.append(f"Powiązano {len(headlines)} datowanych artykułów z ostatnich 72 godzin; odnośniki poniżej."
                   if pl else f"Linked {len(headlines)} dated articles from the last 72 hours; sources are shown below.")
        if item["kind"] == "stock" and not any(h.get("scope") == "company" for h in headlines):
            caution.append("Wiadomości dotyczą rynku lub sektora, nie tej konkretnej spółki."
                           if pl else "The news is market or sector context, not evidence about this company specifically.")
    if historical["comparisons"]:
        why.append(f"Porównanie obejmuje {len(historical['comparisons'])} wcześniejszych zdarzeń o podobnym temacie i rzeczywiste ceny tego instrumentu."
                   if pl else f"The comparison covers {len(historical['comparisons'])} earlier events sharing a topic, using this instrument's own adjusted prices.")
        caution.append("Podobieństwo dotyczy tematu wiadomości. Nie dowodzi tej samej sytuacji ani tego, że zdarzenie spowodowało zmianę ceny."
                       if pl else "Similarity is topical. It does not establish the same market regime or prove that the event caused the price change.")
    else:
        caution.append("Brak porównywalnego zdarzenia z pełnymi danymi cenowymi; nie przypisano historycznej analogii."
                       if pl else "No comparable event with a complete price window was found; no historical analogy was assigned.")
    if adjustment["status"] == "applied":
        why.append((f"Eksperymentalna korekta za wiadomości i historię: {adjustment['value'] * 100:+.2f} pkt. Wymaga co najmniej dwóch niepokrywających się zdarzeń i dwóch wydawców dla tego samego tematu."
                    if pl else f"Experimental news/history adjustment: {adjustment['value'] * 100:+.2f} points. Requires at least two non-overlapping events and two publishers reporting the same topic."))
        caution.append("Ta korekta nie ma jeszcze niezależnego testu prognostycznego."
                       if pl else "This adjustment has not passed an independent predictive test.")
    else:
        caution.append(("Historia zawiera sprzeczne sygnały; nie zmieniono rankingu." if adjustment["status"] == "conflicting" else "Za mało niezależnych dowodów, aby wiadomości zmieniły ranking.")
                       if pl else ("Historical themes disagree; the ranking was not adjusted." if adjustment["status"] == "conflicting" else "Insufficient independent evidence for a news-based ranking adjustment."))
    if metrics["trend"] < 0:
        caution.append("Cena jest poniżej średniej z 200 sesji: trend przeczy pozytywnej tezie."
                       if pl else "Price is below the 200-session average: the trend is a counterargument to a positive thesis.")
    if profile.get("horizon") == "<1y":
        caution.append("Nawet fundusz krótkich obligacji może stracić; uwzględnij gotówkę oraz ryzyko walutowe USD."
                       if pl else "Even a short Treasury fund can lose value; consider cash needs and USD currency risk.")
    return why, caution


def screen(profile, capacity, lang="en"):
    """Price ranking with sourced news and a bounded, explicitly experimental overlay."""
    scope = profile.get("scope", "areas")
    if scope not in ("areas", "specific"):
        scope = "areas"
    capacity = max(0, min(100, float(capacity)))
    with ThreadPoolExecutor(max_workers=6) as pool:
        news_future = pool.submit(_news_snapshot)
        futures = {s: pool.submit(_fetch_history, s) for s in UNIVERSE}
        histories = {s: f.result() for s, f in futures.items()}
        snapshot = news_future.result()
    fresh = {}
    today = datetime.now(timezone.utc).date()
    for symbol, rows in histories.items():
        if len(rows) < 210:
            continue
        date = datetime.fromtimestamp(rows[-1][0], timezone.utc).date()
        if 0 <= (today - date).days <= 7:
            fresh[symbol] = rows
    candidates = []
    for symbol, rows in fresh.items():
        name, kind, area = UNIVERSE[symbol]
        if scope == "areas" and kind == "stock":
            continue
        if profile.get("horizon") == "<1y" and symbol != "SHY":
            continue
        if profile.get("max_dd") == "-10%" and symbol not in ("SHY", "SPY", "GLD"):
            continue
        if capacity < 40 and symbol in ("NVDA", "SLV", "QQQ", "TLT"):
            continue
        metrics = price_metrics(rows)
        evidence = news_evidence.evidence_for(symbol, area, snapshot)
        historical = event_reactions(rows, fresh.get("SPY", []), evidence.get("events", []))
        adjustment = history_adjustment(historical, evidence.get("headlines", []))
        base = base_score(metrics, capacity)
        item = {"symbol": symbol, "name": name, "kind": kind, "area": area,
                "asof": datetime.fromtimestamp(rows[-1][0], timezone.utc).date().isoformat(),
                "momentum_3m": round(metrics["momentum"] * 100, 1),
                "return_1w": round(metrics["week"] * 100, 1),
                "return_1m": round(metrics["month"] * 100, 1),
                "trend_distance_pct": round(metrics["trend"] * 100, 1),
                "volatility": round(metrics["vol"] * 100, 1), "above_200d": metrics["trend"] > 0,
                "price_source_url": f"https://finance.yahoo.com/quote/{symbol}/history/",
                "news": evidence, "history": historical, "history_adjustment": adjustment,
                "score_breakdown": {"price_risk": round(base * 100, 3),
                                    "news_history": round(adjustment["value"] * 100, 3)},
                "score": base + adjustment["value"]}
        item["justification"], item["cautions"] = _explain(item, metrics, capacity, profile, evidence, historical, adjustment, lang)
        candidates.append(item)
    candidates.sort(key=lambda c: (-c["score"], c["symbol"]))
    if len(fresh) < 10:
        candidates = []
    selected, seen = [], set()
    for item in candidates:
        if scope == "areas" and item["area"] in seen:
            continue
        seen.add(item["area"])
        item.pop("score")
        selected.append(item)
        if len(selected) == 5:
            break
    market = []
    for symbol in ("SPY", "QQQ", "GLD", "DBC", "TLT"):
        if symbol in fresh:
            m = price_metrics(fresh[symbol])
            market.append({"symbol": symbol, "week_pct": round(m["week"] * 100, 2),
                           "month_pct": round(m["month"] * 100, 2),
                           "above_200d": m["trend"] > 0,
                           "asof": datetime.fromtimestamp(fresh[symbol][-1][0], timezone.utc).date().isoformat()})
    pl = lang == "pl"
    return {"scope": scope, "available": len(fresh), "checked": len(UNIVERSE), "items": selected,
            "market_behavior": market, "news_status": snapshot.get("status", "unavailable"),
            "news_generated_at": snapshot.get("generated_at"),
            "news_count": len(snapshot.get("items", [])),
            "source": "Yahoo Finance adjusted daily prices + linked publisher headlines via Google News RSS",
            "method": ("Cena, trend i ryzyko tworzą ocenę bazową. Wiadomości łączymy tematycznie z datowanymi zdarzeniami; mierzymy późniejsze zwroty tego samego instrumentu. Eksperymentalna korekta historyczna jest mała i wymaga niezależnych dowodów."
                       if pl else "Price trend and risk form the base ranking. News topics are linked to dated past events, then subsequent returns are measured for the same instrument. A small experimental historical adjustment requires independent evidence."),
            "notice": ("Wynik jest propozycją do analizy, nie prognozą zysku. Wiadomości są doniesieniami wydawców, a historyczne podobieństwo nie dowodzi związku przyczynowego."
                       if pl else "These are research suggestions, not return forecasts. Headlines are publisher reports; historical similarity does not prove causation or future performance.")}


