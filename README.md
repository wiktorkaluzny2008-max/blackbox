# Blackbox — ETH KI Challenge

> **New here? Read [`START_HERE.md`](START_HERE.md) first** — it gets you running in five minutes and
> shows how to hand the project to your own Claude. To give an AI the whole codebase in a single
> upload, use [`BUNDLE.md`](BUNDLE.md) (every file concatenated; regenerate with `python make_bundle.py`).

**An AI-personalised systematic investing platform.** A user answers six questions (or picks
strategies themselves), gets a custom multi-strategy allocation built from 20 years of validated
backtests, presses *Let's go*, and receives their own live paper portfolio — continuously informed
by an NLP engine that reads news and social sentiment and explains itself.

Live: **https://app.54-246-124-234.sslip.io**

Everything in this repo is real. Every performance number comes from a 20-year backtest on actual
market data (2006–2026). Nothing is mocked, simulated for show, or invented.

---

## Contents

1. [Quickstart](#quickstart)
2. [What the product does](#what-the-product-does)
3. [Architecture](#architecture)
4. [The three pillars](#the-three-pillars)
5. [Code tour — every module](#code-tour--every-module)
6. [API reference](#api-reference)
7. [Deployment](#deployment)
8. [Project state & roadmap](#project-state--roadmap)
9. [Honesty & limitations](#honesty--limitations)

---

## Quickstart

```bash
pip install -r requirements.txt
python bootstrap.py        # seeds logs/ with the precomputed catalog + sentiment
python app_user.py         # -> http://localhost:8090
```

**That's it — no API keys needed.** The catalog (8 strategies with full backtests, statistics and
Monte-Carlo projections) ships precomputed in `data/catalog.json`, and the sentiment scanner uses
only free public endpoints.

| What you get with no credentials | What needs a free OANDA practice key |
|---|---|
| All 8 strategies, stats, charts, projections | Live per-strategy holdings ("owns Copper 8.3%…") |
| The 6-question personalisation engine | Live intraday day-returns on your portfolio |
| Accounts, login, personal portfolios | Rebuilding the catalog from scratch (`catalog.py`) |
| The AI news/social scanner (live) | — |

To unlock live marks: create a free [OANDA practice account](https://www.oanda.com/demo-account/)
(60 seconds, no card), generate an API token, and copy `.env.example` to `.env` with the values.

Optionally run the scanner daemon in a second terminal so sentiment refreshes every 20 minutes:

```bash
python run_scanner.py
```

---

## What the product does

The user journey, in the order a judge will experience it:

1. **Hero page** — one call to action: *Let's go*.
2. **Two paths.**
   - *Guide me*: six questions (experience, horizon, drawdown tolerance, crash reaction, goal,
     priority). Every answer measurably changes the result — several act as hard caps.
   - *I'll choose myself*: browse all 8 strategies by CAGR / volatility / max drawdown and set
     your own weights with steppers; a sticky bar shows blended stats and unlocks at exactly 100%.
3. **A custom allocation is constructed** — not selected from presets. Weights are continuous
   functions of a computed risk-capacity score (0–100), with a transparent "why" trail explaining
   which answers shaped or capped the mix.
4. **Create an account** (recovery key or Google) and press *Start my Blackbox*.
5. **A personal paper portfolio goes live**: 10,000 units of practice capital, marked daily to real
   markets by the same validated rules, showing what the machine holds *right now* and why —
   including where the AI scanner has trimmed exposure.

---

## Architecture

```
                    ┌──────────────────────────────────────────┐
   Browser  ───────►│  app_user.py    Flask + single-page UI    │
                    │  · accounts / sessions / Google OAuth     │
                    │  · 6-question personalisation engine      │
                    │  · charts (Chart.js), quiz, builder       │
                    └───┬───────────────┬──────────────────┬────┘
                        │               │                  │
              ┌─────────▼──────┐  ┌─────▼─────────┐  ┌─────▼────────────┐
              │ catalog.json   │  │ user_engine   │  │ sentiment.json   │
              │ 8 strategies,  │  │ live holdings │  │ NLP asset scores │
              │ 20y backtests, │  │ + day-returns │  │ + explanations   │
              │ projections    │  │ + AI tilt     │  │                  │
              └───────▲────────┘  └──┬────────┬───┘  └────────▲─────────┘
                      │              │        │               │
              ┌───────┴──────┐  ┌────▼───┐ ┌──▼──────┐  ┌─────┴──────────┐
              │ catalog.py   │  │ OANDA  │ │Coinbase │  │sentiment_      │
              │ (build step) │  │ API    │ │public   │  │scanner.py      │
              └──────────────┘  └────────┘ └─────────┘  │Google News RSS │
                                                        │+ Reddit JSON   │
                                                        └────────────────┘
                                   ▲
                            run_scanner.py  (daemon: scan every 20 min,
                                             settle all user books at 21:05 UTC)
```

**Data stores** (all plain JSON under `logs/`, no database):

| File | Contents |
|---|---|
| `catalog.json` | The 8 strategies: stats, equity curves, bootstrap projections, methodology |
| `sentiment.json` | Latest AI scan: per-asset scores, trends, explanations, top headlines |
| `app_accounts.json` | Accounts: name, hashed recovery key, Google subject id, linked portfolio |
| `app_users.json` | Portfolios: mix, NAV, base date, daily history |

---

## The three pillars

### 1. Validated strategies (not curve-fitted)

Eight strategies, each backtested on ~20 years of real data (2006-03-20 → 2026-06-28):

| id | Strategy | CAGR | Sharpe | Vol | Max DD | Beta | Risk |
|---|---|---|---|---|---|---|---|
| `crypto_trend` | Crypto Momentum | 48.45% | 1.28 | 35.8% | −50.7% | 0.02 | Very High |
| `stack_agg` | Multi-Edge Aggressive | 10.98% | 0.60 | 21.3% | −56.4% | 0.25 | High |
| `spx_hold` | S&P 500 Buy & Hold | 8.71% | 0.53 | 19.1% | −56.9% | 1.00 | High |
| `gold_macro` | Macro Gold | 5.80% | 0.61 | 10.1% | −22.0% | 0.00 | Moderate |
| `stack_bal` | Multi-Edge Balanced | 4.92% | 0.69 | 7.3% | −19.8% | 0.10 | Moderate |
| `commod_trend` | Commodity Trend | 4.53% | 0.46 | 10.9% | −29.0% | 0.10 | Moderate |
| `equity_season` | Seasonal Equity | 3.63% | 0.58 | 6.6% | −12.5% | 0.14 | Moderate |
| `risk_parity` | Risk Parity | 2.88% | 0.39 | 8.0% | −26.1% | 0.26 | Conservative |

The headline result is **`stack_bal`**: the highest Sharpe (0.69) with a −19.8% worst case versus
the S&P's −56.9%, and a beta of 0.10 — meaning it barely moves with the stock market. That is the
whole pitch of diversification made concrete.

**How the edges were found** (`research/`, three rounds of pre-specified tests):

- Every hypothesis was **written down before testing**, then validated on a **split-half**
  design — select on the first decade, confirm on the second. A rule that only works in one half
  is discarded.
- Every candidate was run through a **cost ladder** (basis points per round trip). This is what
  kills most published anomalies.
- Things we found and **killed honestly**: metals reopen drift (gross Sharpe 1.13 but dies at
  2bp/day), pair mean-reversion (all four pairs dead), panic dip-buying (Sharpe 0.11), FX
  weekend-gap fade (only 24 events — not enough evidence).
- The one genuinely new edge that survived all three bars: **rates-gated gold** (`gold_macro`).
  Gold is a zero-yield asset, so it should perform when real yields fall. Gating a gold trend
  strategy on "US 10-year bond above its 100-day average" (i.e. yields falling) took Sharpe from
  0.39 to 0.61, held in **both** halves of the sample, and is cost-immune because it trades rarely.
  It also has **beta 0.00** to equities — genuinely independent.

### 2. The AI scanner (`sentiment_scanner.py`)

Continuously scans **Google News RSS + Reddit public JSON** (no API keys; availability and rate limits depend on the providers) across six
asset buckets: equities, gold, rates, FX, crypto, oil. For each item it runs a finance-specific NLP
lexicon — polarity terms weighted by intensifiers and negation-aware — then aggregates to a
**score from −100 to +100** with a trend and a **plain-English explanation** traceable to the actual
headlines that drove it.

A typical live scan reads ~600 items in about 40 seconds.

The scanner is **present in every strategy** in two ways:

- **Displayed** — every strategy card and modal shows the live AI read for that strategy's asset
  buckets ("AI: bearish −36").
- **Acted upon** — in a user's portfolio, if any of a strategy's buckets scores below −40, that
  strategy's exposure is scaled to **0.75×** with a visible explanation. The crypto bot applies a
  wider, symmetric version of the same tilt.

This is deliberate design, not a limitation: sentiment **modulates** validated rules rather than
generating trades on its own. Sentiment-only trading does not survive cost analysis; sentiment as a
risk overlay does, and it stays explainable — which is the point of the challenge.

### 3. Personalisation that actually personalises

The naive version of this product maps a quiz to a handful of canned presets, which means most
answers change nothing. This one **constructs** the allocation:

```python
# Continuous risk-capacity score, then hard caps that bind
raw = goal + drawdown_tolerance + crash_reaction + horizon + experience   # 0..13
caps = [5.0 if new_investor, 1.5 if horizon < 1y, 4.5 if dd_limit == -10%, ...]
score = min([raw] + caps)          # a single answer CAN dominate the outcome
f = score / 13.0                   # normalised risk capacity, 0..1

crypto_ok = (dd == "-50%+") and (exp != "new") and (horizon in ("3-10y", "10y+"))

w = {"risk_parity":   45 * (1 - f) ** 1.6,       # decays as capacity rises
     "gold_macro":    18 + 8 * (1 - f),
     "stack_bal":     24,
     "equity_season": 12 + 10 * f,
     "commod_trend":   5 + 9 * f,
     "stack_agg":     30 * f ** 1.3,             # grows super-linearly
     "crypto_trend":  (24 * f ** 2.0) if crypto_ok else 0.0}

w = {k: v * priority_tilt.get(k, 1) for k, v in w.items()}   # 'smooth' / 'beat' / 'max'
# drop dust (<5%), then largest-remainder rounding to exactly 100%
```

Verified: six profiles differing by **one answer each** produce **six different allocations**.
The user is shown their risk-capacity score and the exact reasons ("You'd sell in a −20% month —
strategies that *can* fall that far are excluded").

---

## Code tour — every module

3,455 lines total. Ordered by importance to the challenge.

### `app_user.py` (1,113 lines) — the web application

A single Flask file: JSON API + the entire single-page UI in one `render_template_string` block.
Chosen deliberately — one file, no build step, no framework, deploys by copying.

**Accounts & sessions.** Signed Flask cookies (60-day), secret from `APP_SECRET` or auto-persisted
to `logs/app_secret.txt` so restarts don't log everyone out.

*Recovery-key accounts* — works with zero external services. A key is three words plus four digits
(`vega-krypton-violet-3293`), stored only as `sha256(salt + key.lower())`:

```python
def _gen_key():
    r = secrets.SystemRandom()
    return "-".join(r.choice(WORDS) for _ in range(3)) + "-" + str(r.randrange(1000, 9999))

def _hash_key(key, salt):
    return hashlib.sha256((salt + key.strip().lower()).encode()).hexdigest()
```

*Google Sign-In* — fully implemented, dormant until `GOOGLE_CLIENT_ID` is set. Uses Google Identity
Services on the client; the server verifies the ID token against Google's tokeninfo endpoint,
checking audience, issuer and expiry. **No client secret required** for this flow:

```python
info = rq.get("https://oauth2.googleapis.com/tokeninfo",
              params={"id_token": cred}, timeout=10).json()
if (info.get("aud") != cid or "accounts.google.com" not in str(info.get("iss", ""))
        or int(info.get("exp", 0)) < time.time()):
    return jsonify({"error": "invalid token"}), 401
```

Accounts link by Google `sub` (the stable user id), so a returning user maps to the same portfolio.
An anonymous portfolio created before signing up is adopted into the new account via `adopt_uid`.

**The personalisation engine** — `/api/recommend`, the algorithm shown above.

**Portfolios** — create replaces any previous one (and deletes the orphan); reads are display-only.
Book-rolling happens in exactly one place (see `user_engine.settle_users`), which avoids the classic
bug where a portfolio's value changes depending on how often the page is refreshed.

**The UI**, in one HTML/CSS/JS block. Dark theme (`#0A0A0F`), one violet accent, Geist/Inter,
reveal-on-scroll via `IntersectionObserver`, all animation on `transform`/`opacity` only, and a
`prefers-reduced-motion` block that disables it. Charts are Chart.js with a hard-won detail:

```css
/* Chart.js REQUIRES a fixed-height positioned wrapper with responsive mode —
   height on the canvas itself makes it grow unbounded. */
.chartbox{position:relative;height:280px;min-width:0}
.chartbox canvas{position:absolute;inset:0}
```

Two chart types matter. The **backtest chart** plots growth of 10,000 with the S&P 500 dashed behind
it (nearest-date matching, because each strategy's weekly-sampled curve has its own date grid). The
**projection chart** is a double fan: grey 5–95% band, violet 25–75% band, bold median line, plus
horizon chips and an explicit probability of loss.

### `user_engine.py` (261 lines) — every user's personal Blackbox

Derives **today's actual holdings** for each strategy from the same live rules, then marks user
portfolios to market.

```python
def _holdings(sid):
    """Today's target weights {instrument: weight} for one strategy, per its rules."""
    if sid == "gold_macro":
        gate = _above_ma("USB10Y_USD", 100) and _above_ma("XAU_USD", 200)
        if gate:
            return {"XAU_USD": 1.0}, "Gold uptrend + falling yields — fully long gold."
        return {}, "Rates gate off (yields rising) or gold below trend — in cash."
    if sid == "equity_season":
        if datetime.now(timezone.utc).month not in HALLOWEEN:      # Nov–Apr
            return {}, "Out of the Nov-Apr seasonal window — sitting in cash."
        act = [i for i in INDICES if _above_ma(i, 200)]
        return {i: 1/len(INDICES) for i in act}, f"In season; {len(act)}/{len(INDICES)} above trend."
    ...
```

Those human-readable notes are what the UI shows, so the user always sees *why* the machine is
positioned the way it is — including "100% cash" states, which is where most systems go quiet.

The portfolio return is one line, and it is where the scanner acts:

```
user day-return = Σ_s  weight_s × scanner_tilt_s × strategy_day_return_s
```

```python
bad = [b for b, s in scores.items() if s < -40]
if bad:
    tilt, tilt_why = 0.75, f"Scanner strongly bearish on {', '.join(bad)} — exposure trimmed to 75%."
```

`settle_users()` is the **single** place books roll: it runs after the 21:00 UTC daily close, settles
every user's portfolio (including users who never log in), and writes atomically.

All market data is cached (daily candles 30 min, prices 7 min, marks 20 min) so the app stays fast
and never hammers the broker.

### `sentiment_scanner.py` (197 lines) — the NLP engine

Zero dependencies beyond the standard library. `score_text()` walks tokens applying a finance
lexicon with intensifier and negation handling; `tag_asset()` re-tags items into asset buckets by
keyword; `explain()` produces the human sentence shown in the UI; `read_latest(max_age_min=90)` is
the interface the bots use, returning `None` on stale data so callers **fail open** rather than
trading on old information. Writes `logs/sentiment.json` plus an append-only history CSV.

### `catalog.py` (222 lines) — the build step

Regenerates `logs/catalog.json` from raw market data: assembles each strategy's daily return series,
computes CAGR / Sharpe / volatility / max drawdown / beta / per-decade Sharpe, downsamples equity
curves weekly for the charts, and runs an **800-path block bootstrap** for the wealth projections
(percentiles 5/25/50/75/95 at 1/3/5 years, plus probability of loss). Block bootstrapping resamples
*blocks* of consecutive days rather than individual days, preserving volatility clustering — which
is why the projection fans are honest rather than optimistic.

Only needs to be re-run when strategies change or to extend the data. **Requires OANDA credentials.**

### Supporting modules

| File | Lines | Role |
|---|---|---|
| `oanda_client.py` | 239 | REST wrapper: candles, prices, orders, trades. Retries + rate-limit handling. |
| `crypto_bot.py` | 195 | Coinbase public data; 200-day trend, inverse-vol weights, vol targeting. Supplies crypto marks. |
| `backtest_factors.py` | 245 | Multi-asset daily history loader/cache used by `catalog.py`. |
| `instruments.py` | 170 | Per-instrument specs: pip size, precision, value per unit. |
| `crypto_backtest.py` | 114 | Crypto daily history for the catalog build. |
| `config.py` | 60 | Loads `.env`; OANDA endpoints; strategy constants. |
| `notifier.py` | 51 | Push notifications (ntfy). Optional, no-op without config. |
| `run_scanner.py` | 51 | Daemon: scan every 20 min → settle user books after the close. |
| `logger.py` | 40 | Rotating file + console logging. |
| `bootstrap.py` | 52 | One-time setup: seeds `logs/`, checks dependencies. |

### `research/` — the evidence

`research_deep.py`, `research_deep2.py`, `research_deep3.py`. Run them to reproduce the edge hunt:
pre-specified hypotheses, split-half validation, cost ladders, and the correlation matrix showing the
edges are genuinely independent (pairwise 0.04–0.25). `research_deep3.py` is the one that validates
the rates-gated gold sleeve. **Requires OANDA credentials.**

---

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | The single-page application |
| `GET` | `/api/catalog` | All 8 strategies: stats, curves, projections, methodology |
| `GET` | `/api/sentiment` | Latest AI scan: scores, trends, explanations, headlines |
| `GET` | `/api/marks` | Live per-strategy holdings, day-returns, notes, tilts |
| `GET` | `/api/config` | Feature flags (whether Google Sign-In is configured) |
| `POST` | `/api/recommend` | Questionnaire and area/specific scope → custom mix, risk capacity, explanations, and sourced market evidence |
| `POST` | `/api/auth/register` | Create account → returns a one-time recovery key |
| `POST` | `/api/auth/recover` | Log in with a recovery key |
| `POST` | `/api/auth/google` | Log in with a Google ID token |
| `POST` | `/api/auth/logout` | End session |
| `GET` | `/api/me` | Current account + its portfolio (or `{"signed_in": false}`) |
| `POST` | `/api/user/create` | Start a Blackbox from a mix (must sum to 100%) |
| `GET` | `/api/user/<uid>` | Portfolio: NAV, day return, history, per-strategy detail |
| `POST` | `/api/user/<uid>/delete` | Delete a portfolio and unlink it |

Example — the personalisation engine:

```bash
curl -X POST http://localhost:8090/api/recommend \
  -H 'Content-Type: application/json' \
  -d '{"experience":"experienced","horizon":"10y+","max_dd":"-50%+",
       "react":"buy","goal":"maximize","priority":"max"}'
```

```json
{"tier": 3, "label": "Maximum Growth", "capacity": 100,
 "mix": {"stack_agg": 27, "crypto_trend": 21, "stack_bal": 16,
         "equity_season": 15, "gold_macro": 12, "commod_trend": 9},
 "why": ["Deep drawdown tolerance + long horizon unlocked a crypto momentum satellite",
         "Priority 'max wealth' tilted into the levered engines"],
 "blend": {"cagr_est": 14.6, "vol_est": 19.8, "dd_est": -40.1}}
```

---

## Deployment

Currently on a single AWS EC2 `t3.micro` (Ubuntu, ~913 MB RAM) behind Caddy, which provisions HTTPS
automatically. No domain is needed: `sslip.io` maps any IP to a hostname, so
`app.54-246-124-234.sslip.io` gets a real certificate.

```bash
# on the server
git clone <your-repo> ~/blackbox-ki && cd ~/blackbox-ki
pip3 install --user -r requirements.txt
python3 bootstrap.py
cp .env.example .env && nano .env          # optional: OANDA + Google

sudo cp deploy/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now blackbox-app trading-scanner

sudo cp deploy/Caddyfile /etc/caddy/Caddyfile   # edit the hostname first
sudo systemctl reload caddy
```

`deploy/*.service` are copied verbatim from the running production server (paths updated to
`blackbox-ki`). The app runs under gunicorn with **one worker** on purpose — the JSON stores assume a
single writer. Scaling past one worker means moving to SQLite or Postgres first.

**Enabling Google Sign-In:**

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → *Create Credentials* →
   *OAuth client ID* → **Web application**.
2. Authorized JavaScript origins: exactly where the app is served
   (`http://localhost:8090` for dev, `https://your.host` for prod).
3. Configure the consent screen (External, app name, your email).
4. Put the client ID in `.env` as `GOOGLE_CLIENT_ID=...`, restart the app.

The button appears automatically. Nothing else changes — recovery-key accounts keep working
alongside it.

---

## Project state & roadmap

**Working and verified end-to-end in a browser against the live server:**

- 8 strategies with real 20-year statistics, equity curves and bootstrap projections
- Six-question personalisation, verified to produce distinct allocations per answer
- Manual builder mode with live blended statistics
- Accounts: register → recovery key → start portfolio → sign out → **log back in and the portfolio
  is still there**
- Google Sign-In implemented (needs only a client ID)
- Personal paper portfolios with live holdings, notes, and scanner tilts
- AI scanner running on a 20-minute cycle; books settling daily at the close

**Natural next steps, in the order I'd do them:**

1. **Google client ID** — 3 minutes, and the login story is complete.
2. **Email as a second recovery path** — recovery keys are secure but unforgiving. SMTP + a signed
   magic link reuses the existing session layer.
3. **Move JSON stores to SQLite** — required before running more than one gunicorn worker.
4. **A per-user history chart with more than a few days of data** — the settle loop is already
   accumulating it; it simply needs calendar time.
5. **Strategy detail pages** with rolling drawdown and per-year return tables — the data is already
   in `catalog.json`.
6. **Multi-language (DE/EN)** if the challenge audience wants it — all copy is in one file.

---

## Honesty & limitations

Written plainly, because a jury will ask and this is the part that earns trust.

- **All portfolios are paper.** Users get 10,000 units of practice capital. No real money, no
  brokerage account, no custody. The separate live trading system that shares this research runs on
  an OANDA **practice** account.
- **Backtests are backtests.** Costs are modelled (a cost ladder is applied to every candidate), but
  they are not the same as live fills. Live results will be worse than backtests. This is why the
  research process deliberately killed several strategies that looked good gross and died net.
- **Projections are probabilistic, not predictions.** The fans come from block-bootstrapping actual
  historical returns. They show what the past distribution implies, which is not what the future
  will do. The probability-of-loss number is displayed prominently for exactly this reason.
- **Crypto's 48% CAGR is real but survivorship-flavoured.** It covers an exceptional decade for the
  asset class and includes a −50.7% drawdown. It is gated behind three separate eligibility checks
  in the personalisation engine for that reason.
- **The scanner reads sentiment, not truth.** It measures the mood of published text. It is used as
  a bounded risk overlay (0.75× exposure), never as a standalone trade signal.
- **This is not investment advice**, and the app says so on every page.

---

*Built for the ETH KI Challenge. The research, the scanner and the platform are all original work;
market data comes from OANDA (practice API), Coinbase public endpoints, Google News RSS and Reddit's
public JSON.*

## Market ideas in the questionnaire

The seventh question selects broad investment areas or specific stocks and commodity-linked funds. `market_recs.py` requests adjusted daily price history since 2014 using explicit date bounds and validates the daily interval from Yahoo Finance’s public chart endpoint for a fixed universe of 13 instruments: AAPL, MSFT, NVDA, JPM, JNJ, XOM, SPY, QQQ, GLD, SLV, DBC, TLT and SHY. The base ranking uses three-month momentum and the 200-day trend, with a volatility penalty linked to risk capacity. Short horizons and low drawdown tolerance restrict the candidate list; these filters do not guarantee a maximum loss. Area results use funds, while the specific option also permits individual stocks.

Prices are cached for six hours. Each instrument needs at least 210 complete daily observations and a latest price no more than seven calendar days old; future prices and today's US bar before 22:00 UTC are excluded. At least ten of the 13 instruments must have usable prices before any ideas are ranked. Results show the observation date, recent weekly/monthly moves, trend, volatility and source links. These are research suggestions for the paper portfolio, not a machine-learning return forecast, direct commodity ownership or a buy instruction. The crypto Regime Radar remains separate. Yahoo's endpoint is a third-party dependency and may change.

## News and historical evidence

Opening a recommendation requests public Google News RSS feeds through `news_evidence.py`. This is an on-demand scan with a 20-minute cache, not continuous monitoring. Fixed company, area and macro queries send no questionnaire text. Headlines must have a source publisher, a safe link and a publication timestamp within the preceding 72 hours. Future or undated items are rejected and repeated titles/links are deduplicated. Feed failures are reported as partial or unavailable; missing news leaves the price-based screen available without a news adjustment.

Explicit headline rules distinguish company evidence from sector or macro context. Eligible reported topics can link to a small library of seven dated events, each with a Federal Reserve, FDIC or UN primary-source link. Hypothetical, negated and conflicting event language is excluded from historical support. These are topic matches, not verified repetitions of an event. Publisher counts mean distinct publisher labels and do not establish independent reporting.

`market_evidence.py` measures the same instrument's adjusted return from the event-day close (the next available session if the market was closed) to five and 20 trading sessions later. It reports actual start/end dates, the SPY return over those same dates and the excess return. Missing or incomplete event windows are omitted rather than extrapolated. These comparisons describe subsequent price movements; they neither isolate the event's causal effect nor establish a predictive relationship.

A small experimental ranking adjustment is allowed only when one topic has at least two covered historical events separated by at least 45 calendar days and eligible current headlines from at least two distinct publishers. It uses 10% of the median 20-session excess return, capped at plus or minus one ranking point. Opposing historical themes or insufficient support give a zero adjustment. Ranking points are neither expected returns nor probabilities, and this overlay has not passed a predictive validation test.

The `market` field returned by `POST /api/recommend` includes current market behavior, dated headlines, primary event links, measured historical windows, missing-data status, score components, justifications and cautions. Explanations and interface labels support English and Polish through the existing language selection; original source headlines and event titles remain as supplied. No language model invents the prices, returns or adjustment. The separate legacy historical-analogue panel can abstain and labels its sparse strategy-curve changes as approximate context, not individual-stock evidence.

## Password login and Supabase preparation

New accounts require an email and a password of at least 12 characters. Passwords are stored as salted PBKDF2 hashes. Existing recovery-key accounts remain usable; new recovery keys are longer. Account sessions are signed by Flask and portfolio endpoints check ownership. The questionnaire profile and portfolio mix are saved together.

Local development stores accounts and portfolios in `logs/*.json`. For a dedicated Supabase project, apply `supabase_schema.sql`, set `DATABASE_URL` to the connection string from Supabase Dashboard → Connect, and set a stable `APP_SECRET` on the server. Do not expose either value in browser code. `import_local_state.py` imports existing JSON data once and refuses to replace populated database state. The table has RLS enabled and denies browser roles; the trusted Flask server connects directly to Postgres. Keep the Flask/Gunicorn origin running and put Cloudflare in front as a reverse proxy. This code has not been adapted to Cloudflare Workers or Pages.

The database integration cannot be verified until a dedicated Supabase project is connected. Run the schema, import, registration, login, portfolio and restart checks in that deployment before switching traffic. Account and portfolio writers use one Postgres advisory lock across app and scanner processes. The JSON-blob layout is still best kept to the existing single Gunicorn worker until it is replaced with normalized tables and load tested.

## Market screen verification

`validate_market_recs.py` is an older, price-only retrospective diagnostic. Its recorded 2023-01-01 through 2026-11-02 run showed a 24.9% gross annualized return versus 20.9% for SPY, with maximum drawdowns of -19.3% and -18.8%, respectively. These figures do not validate the current news/history overlay. The fixed current-symbol universe introduces survivorship bias; the check omits transaction costs, taxes and slippage, and is not an untouched out-of-sample test. There is no immutable dataset of news as received at each historical decision time, so a timestamp-faithful historical test of the new overlay has not been performed. Neither that diagnostic nor a handful of event comparisons establishes a predictive edge.

The deterministic evidence tests cover headline freshness, duplicates, safe source links, speculative language, incomplete event windows, benchmark date alignment, ranking-adjustment gates and bounds, and price outages. Run them without network access or credentials:

```bash
python3 -B -m unittest test_news_evidence test_market_evidence test_historical_analog test_market_route
```

These are correctness checks, not investment-performance validation. The existing crypto Regime Radar is separate and will show unavailable if its input prices are over seven days old.

## Languages

The navigation includes English and Polski. The selected language is remembered in the browser. Static public interface text and strategy descriptions are stored in `pl.json`; that file was generated from public site copy and then supplemented with reviewed financial terms. Dynamic AI replies request Polish when the Polish option is selected. Original source headlines, ticker symbols and user-entered text remain as provided. Translation quality should be reviewed by a native Polish speaker before a public launch.

## Volatility-model verification

The bundled crypto Regime Radar was independently retrained against refreshed Coinbase data through 2026-11-02. We purged ten days around train/validation/test boundaries so forward labels cannot cross into the next period. The selected neural net scored AUC 0.667 on 11,810 later-period examples; the random-forest cross-check scored 0.681 and a simple volatility-persistence baseline scored 0.632. See `REGIME_AI.md` and `logs/regime_report.json`. This model estimates crypto turbulence only. It does not forecast stock or fund returns. MATIC history ends in 2025 and remains a historical training series.

For the limits of what has been verified, see `MODEL_AUDIT.md`.

The 2026-11-03 integration check passed 49 deterministic tests, including English/Polish API responses and empty results during a price outage. JavaScript syntax and escaped English/Polish evidence rendering were checked separately. Public live checks returned all 13 price series through 2026-11-02 and 151 recent headlines; all seven event windows were covered for QQQ, GLD and XOM. These are implementation checks, not a predictive-performance result.
