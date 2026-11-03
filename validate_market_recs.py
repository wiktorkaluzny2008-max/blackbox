"""Legacy retrospective price-only diagnostic, NOT validation of news ranking.

Uses a surviving current universe, arithmetic-volatility scoring and daily
equal weights selected monthly; these differ from the live screen. No archived
as-published news, delisted securities, execution timing or costs are included.
Do not use its results to claim the live recommendations predict returns.
"""
import math
import pandas as pd
from market_recs import UNIVERSE, _history


def run():
    prices = {}
    for symbol in UNIVERSE:
        rows = _history(symbol)
        prices[symbol] = pd.Series({pd.Timestamp(t, unit="s").normalize(): p for t, p in rows})
    frame = pd.DataFrame(prices).ffill().dropna()
    returns = frame.pct_change().fillna(0)
    weights = pd.DataFrame(0.0, index=frame.index, columns=frame.columns)
    for i in range(200, len(frame) - 1):
        if i == 200 or frame.index[i].month != frame.index[i - 1].month:
            ranks = []
            for symbol in frame:
                p = frame[symbol].iloc[:i + 1]
                r = p.pct_change().iloc[-63:]
                momentum = p.iloc[-1] / p.iloc[-64] - 1
                trend = p.iloc[-1] / p.iloc[-200:].mean() - 1
                vol = r.std() * math.sqrt(252)
                ranks.append((.6 * momentum + .4 * trend - .4 * vol * .35, symbol))
            chosen = [symbol for _, symbol in sorted(ranks, reverse=True)[:5]]
        weights.loc[frame.index[i + 1], chosen] = .2
    start = max(pd.Timestamp("2023-01-01"), frame.index[201])
    selected = (weights * returns).sum(axis=1).loc[start:]
    spy = returns["SPY"].loc[start:]
    def metrics(r):
        curve = (1 + r).cumprod()
        years = len(r) / 252
        return {"cagr_pct": round((curve.iloc[-1] ** (1 / years) - 1) * 100, 1),
                "max_drawdown_pct": round(((curve / curve.cummax()) - 1).min() * 100, 1)}
    return {"period": [str(start.date()), str(frame.index[-1].date())],
            "screen": metrics(selected), "spy": metrics(spy),
            "note": "Legacy price-only diagnostic with daily equal weights selected monthly. Scoring differs from the live screen; does NOT evaluate the news/history adjustment. Fixed surviving universe, no delisted stocks or trading costs; not a validated return forecast."}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
