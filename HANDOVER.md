# Handover

Update (2026-11-03): The questionnaire now offers broad areas or specific stock and commodity-fund research ideas, English/Polish language choice, and email/password accounts. Supabase Postgres storage is prepared but must be connected and checked on a dedicated project before deployment; see README. The refreshed crypto volatility model has test AUC 0.667, and it is not used to rank stocks.

Everything needed to pick this up cold. Read `README.md` for how it works; this is what's *done*,
what's *missing*, and what to do first.

---

## Start here (5 minutes)

```bash
pip install -r requirements.txt
python bootstrap.py
python app_user.py            # -> http://localhost:8090
```

No credentials required. Then open the site and take the journey yourself: press *Let's go*, answer
the six questions, create an account, save the recovery key, press *Start my Blackbox*. That's the
whole product in about two minutes, and it's the demo a jury will see.

Reference deployment (already live): **https://app.54-246-124-234.sslip.io**

---

## Status

| Area | State | Notes |
|---|---|---|
| 8 strategies, 20-year backtests | **Done** | Real data, 2006–2026, shipped precomputed |
| Bootstrap wealth projections | **Done** | 800-path block bootstrap, 1/3/5 years |
| Charts (backtest + projection) | **Done** | Chart.js, S&P overlay, double-fan projection |
| Six-question personalisation | **Done** | Verified: one answer changed → different allocation |
| Manual "choose your own" builder | **Done** | Weight steppers + live blended stats |
| AI sentiment scanner | **Done** | ~600 items/scan, 20-min cycle, no API keys |
| Scanner used in every strategy | **Done** | Shown on every card; trims exposure to 0.75× when bearish |
| Accounts + recovery-key login | **Done** | Cross-device login verified end to end |
| Personal paper portfolios | **Done** | Live holdings, notes, daily settlement |
| Google Sign-In | **Code complete, inactive** | Needs a client ID — see below |
| Email login | Not started | Recovery keys work; email is the friendlier second path |
| Database | Not started | JSON stores; fine for a demo, needed before scaling workers |

---

## The one thing that needs a human

**Google Sign-In is fully built but dormant.** The button, token verification and account linking are
all implemented and deployed. It activates the moment a client ID exists. The client ID has to be
created inside a Google account, which is why it isn't in this repo.

1. [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials) →
   *Create Credentials* → *OAuth client ID* → **Web application**.
2. **Authorized JavaScript origins** — add exactly where the app is served:
   - `http://localhost:8090` for local development
   - `https://app.54-246-124-234.sslip.io` (or your own host) for production
3. First time it will ask you to configure the consent screen: External, app name "Blackbox", your
   email, save.
4. Copy the client ID (ends in `.apps.googleusercontent.com`) into `.env`:
   `GOOGLE_CLIENT_ID=...` — then restart the app.

The "Continue with Google" button appears automatically. Recovery-key accounts keep working
alongside it, and an existing anonymous portfolio is adopted into the Google account on first login.

**No client secret is needed.** The app verifies Google ID tokens server-side against Google's public
tokeninfo endpoint, so there is no secret to leak.

---

## Optional: live market marks

The personal-portfolio panel shows what each strategy holds *right now* ("Copper 8.3%, WTI Oil
8.3%…"). That needs market data from a free OANDA practice account.

1. Create one at [oanda.com/demo-account](https://www.oanda.com/demo-account/) — 60 seconds, no card.
2. *Manage API Access* → generate a token.
3. `cp .env.example .env`, fill in `OANDA_API_KEY` and `OANDA_ACCOUNT_ID`, restart.

Without it, every other part of the app works; the holdings panel simply reports that marks are
unavailable. **Never commit `.env`.** It is gitignored — keep it that way.

---

## What I'd do first, in order

1. **Add the Google client ID.** Three minutes, and the login story is complete for the demo.
2. **Take the full journey on a phone.** The layout is responsive and has been checked, but a real
   device walkthrough before presenting is worth more than any amount of code review.
3. **Let the scanner run for a few days** before the demo. Portfolio history accumulates daily at the
   21:00 UTC close, so a chart with a week of real movement is far more convincing than a flat line.
4. **Rehearse the honesty slide.** The "Honesty & limitations" section of the README is deliberately
   blunt — paper money, backtests aren't live fills, projections aren't predictions, sentiment isn't
   truth. Juries reward this, and every claim in it is defensible.
5. Only then add features. If you want one, the highest-value addition is a **strategy detail page**
   with rolling drawdown and per-year returns — the data is already in `catalog.json`.

---

## Demo script (2 minutes)

1. **Hero** — "Your own Blackbox. Live in minutes." Press *Let's go*.
2. **Quiz** — answer as a cautious investor. Point at the risk-capacity score and the "why" trail:
   *"You'd sell in a −20% month — strategies that can fall that far are excluded."* Then change one
   answer and show the allocation change. This is the moment that proves it isn't a canned preset.
3. **A strategy card** — open Macro Gold. Real 20-year curve against the S&P, the projection fan,
   the probability of loss. Mention the mechanism: gold is a zero-yield asset, so it performs when
   real yields fall; gating on falling yields lifted Sharpe from 0.39 to 0.61 and held in both halves
   of the sample. Beta to equities: 0.00.
4. **The scanner** — the AI panel: ~600 sources, per-asset scores, explanations traceable to real
   headlines. Then show a strategy card carrying its live AI read.
5. **Start a Blackbox** — create an account, press go, land on the personal portfolio showing live
   holdings and any scanner tilt. Close with: *"and I can log in from any device and it's still here."*

---

## Things that will bite you

Collected the hard way — the details are in `CLAUDE.md`, but the short version:

- Chart.js needs a fixed-height **wrapper**; height on the canvas makes it grow forever.
- Don't init charts inside `requestAnimationFrame` — it doesn't fire in a backgrounded tab.
- OANDA candles are stamped 21:00 UTC, Coinbase 00:00 — normalise dates before joining anything.
- Books roll in **one** place (`user_engine.settle_users`). Never fold returns during a page load.
- gunicorn runs `-w 1` on purpose: the JSON stores assume a single writer.

---

## Contact points in the code

| You want to change… | Go to |
|---|---|
| The quiz questions | `app_user.py` → the `#quiz` block in the HTML |
| How answers map to allocations | `app_user.py` → `api_recommend()` |
| Which assets a strategy holds today | `user_engine.py` → `_holdings()` |
| How strongly sentiment trims exposure | `user_engine.py` → `marks()`, the `< -40` threshold |
| The sentiment lexicon / sources | `sentiment_scanner.py` → `POS`/`NEG`/`INTENS`, `FEEDS` |
| Strategy statistics or adding a strategy | `catalog.py`, then re-run it (needs OANDA) |
| Colours, type, motion | `app_user.py` → the `:root` CSS block |

## 2026-11-03: sourced recommendation evidence

`market_recs.py`, `news_evidence.py` and `market_evidence.py` now connect fresh public headlines, observed market behavior and seven primary-sourced historical events to the questionnaire results. Each stock/fund/area idea carries its price date, article links, own-instrument 5/20-session historical changes versus SPY, ranking components, reasons and counterarguments. English and Polish are supported. The news overlay is a capped, experimental rule, not a trained return predictor; it abstains when evidence is insufficient. The older historical-analogue panel can also abstain and no longer extrapolates uncovered curves. See `MODEL_AUDIT.md` and the README for methodology, test commands and outstanding predictive/deployment validation. Restart the Python app after installing these changes.
