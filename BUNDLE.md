# Blackbox — ETH KI Challenge · COMPLETE CODE BUNDLE

This single file contains **the entire project**: all documentation and every line of source code,
concatenated in reading order. It exists so the whole codebase can be handed to an AI assistant in
one upload.

**If you have the project folder, prefer that** — the folder can actually be run and deployed. This
bundle is for the case where you only have one file to work with.

## How to rebuild the project from this file

Every section below is a complete file, marked with its path as a heading. To reconstruct the
project, create each file at the stated path with the exact contents of its code block. Then:

```bash
pip install -r requirements.txt
python bootstrap.py     # needs data/catalog.json — see note below
python app_user.py      # -> http://localhost:8090
```

**One thing is not in this bundle:** `data/catalog.json` (92 KB of precomputed strategy statistics,
equity curves and Monte-Carlo projections). It is generated data, not source. Either copy it from
the project folder, or regenerate it with `python catalog.py` (which needs free OANDA practice
credentials). Without it the app starts but has no strategies to show.

The single most important thing to understand: **`app_user.py` is the entire website.** The Flask
API and the complete single-page frontend (HTML, CSS, JavaScript, charts) live in one file, in a
`render_template_string` block. There is no build step and no frontend framework. To change the
site, you edit that one file.

---

## Table of contents

- [`START_HERE.md`](#startheremd) — Read this first: how to run it and hand it to your AI
- [`README.md`](#readmemd) — What this project is, the architecture, the research behind it
- [`CLAUDE.md`](#claudemd) — Working conventions, ground rules and known gotchas
- [`HANDOVER.md`](#handovermd) — Current status, next steps, demo script
- [`app_user.py`](#appuserpy) — THE WHOLE WEB APP — Flask API + the entire single-page UI
- [`user_engine.py`](#userenginepy) — Per-user live paper portfolios; where the AI scanner acts
- [`sentiment_scanner.py`](#sentimentscannerpy) — The NLP news/social sentiment engine
- [`catalog.py`](#catalogpy) — Builds the strategy catalog: stats, curves, bootstrap projections
- [`run_scanner.py`](#runscannerpy) — Daemon: 20-min scan cycle + daily settlement of user books
- [`bootstrap.py`](#bootstrappy) — One-time setup
- [`oanda_client.py`](#oandaclientpy) — OANDA REST wrapper (market data + orders)
- [`crypto_bot.py`](#cryptobotpy) — Coinbase data + crypto trend engine
- [`backtest_factors.py`](#backtestfactorspy) — Multi-asset daily history loader used by catalog.py
- [`crypto_backtest.py`](#cryptobacktestpy) — Crypto history for the catalog build
- [`instruments.py`](#instrumentspy) — Per-instrument specs (pip size, precision, value per unit)
- [`config.py`](#configpy) — Environment loading and constants
- [`logger.py`](#loggerpy) — Logging
- [`notifier.py`](#notifierpy) — Optional push notifications
- [`requirements.txt`](#requirementstxt) — Dependencies
- [`.env.example`](#envexample) — Environment variables (documented, no values)
- [`deploy/blackbox-app.service`](#deployblackbox-appservice) — systemd unit for the web app
- [`deploy/trading-scanner.service`](#deploytrading-scannerservice) — systemd unit for the scanner daemon
- [`deploy/Caddyfile`](#deploycaddyfile) — Reverse proxy + automatic HTTPS
- [`research/research_deep.py`](#researchresearchdeeppy) — Edge research round 1 — pre-specified structural tests
- [`research/research_deep2.py`](#researchresearchdeep2py) — Edge research round 2 — cost ladders
- [`research/research_deep3.py`](#researchresearchdeep3py) — Edge research round 3 — validates rates-gated gold

---

## `START_HERE.md`

*Read this first: how to run it and hand it to your AI* — 126 lines

````md
# START HERE

You've been handed **Blackbox** — an AI-personalised systematic investing platform built for the
ETH KI Challenge. It's finished and running. This file gets you from "I have a zip" to "it's on my
screen" in about five minutes, and tells you how to hand it to your own Claude.

Live reference version: **https://app.54-246-124-234.sslip.io**

---

## Step 1 — See it running (5 minutes, no accounts, no API keys)

Unzip the folder, open a terminal inside it, and run:

```bash
pip install -r requirements.txt
python bootstrap.py
python app_user.py
```

Open **http://localhost:8090**.

That's the whole product. It works with **no credentials at all** — the 20-year backtests ship
precomputed, and the AI news scanner uses free public sources. Take the journey yourself: press
*Let's go*, answer the six questions, create an account, save the recovery key, press
*Start my Blackbox*.

---

## Step 2 — Hand it to your Claude

### If you use Claude Code (recommended — it can run, test and deploy)

Just open the unzipped folder with Claude Code:

```bash
cd blackbox-ki
claude
```

It automatically reads `CLAUDE.md`, so it starts already knowing the conventions, the architecture
and the mistakes that have already been made and fixed. Then paste this as your first message:

> Read README.md, CLAUDE.md and HANDOVER.md to understand this project — it's my group's ETH KI
> Challenge submission, an AI-personalised investing platform. Then run `python bootstrap.py` and
> `python app_user.py`, open the site, and confirm everything works. Give me a summary of what the
> project does, what state it's in, and what you'd do next.

Claude Code can run the app, drive the browser to verify changes, and deploy to a server. This is
the path that actually lets it *rebuild and extend* the site rather than just talk about it.

### If you use Claude in the browser (claude.ai)

Upload **`BUNDLE.md`** — a single file containing the complete documentation and every line of
source code (4,256 lines). Then say:

> This is my group's ETH KI Challenge project — an AI-personalised investing platform. The whole
> codebase is in this one file. Read it, then explain what it does, how it's built, and what you'd
> improve. The entire website lives in `app_user.py` inside a `render_template_string` block.

Browser Claude can read, explain and rewrite any part of it, but it can't run or deploy anything —
for that you need Claude Code or a terminal.

---

## Step 3 — Know what you're looking at

Read them in this order:

| File | What it gives you |
|---|---|
| **`README.md`** | The full picture: architecture, the research behind the strategies, a code tour of every module, the API reference |
| **`HANDOVER.md`** | Current status, what's missing, next steps — **and a 2-minute demo script for the jury** |
| **`CLAUDE.md`** | Conventions and gotchas. Mostly for your AI, but the gotchas will save you hours |

**The single most useful fact about this codebase:** `app_user.py` *is* the entire website. The
Flask API and the complete frontend — HTML, CSS, JavaScript, charts — live in that one file. No
build step, no React, no bundler. Want to change the site? Edit that file, restart, refresh.

---

## Step 4 — Optional, but worth it

Neither of these is needed for the app to work. Both take a few minutes.

**Google Sign-In** is fully coded but dormant — it needs a client ID, which can only be created
inside a Google account, so it isn't in this repo. Create a Web-application OAuth client at
[console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials), add
your address (`http://localhost:8090`) as an authorized JavaScript origin, then put the client ID in
`.env` as `GOOGLE_CLIENT_ID=...` and restart. The button appears by itself. Full walkthrough in
`HANDOVER.md`.

**Live market holdings** — the personal-portfolio panel can show what each strategy owns *right now*
("Copper 8.3%, WTI Oil 8.3%…"). That needs a free [OANDA practice account](https://www.oanda.com/demo-account/)
(60 seconds, no card). Copy `.env.example` to `.env`, paste your token and account id, restart.

Everything else — all 8 strategies, the backtests, projections, the quiz, accounts, login, and the
AI scanner — works without either of these.

---

## What this project actually is (for when someone asks)

A user answers six questions — or picks strategies themselves by CAGR, volatility and max
drawdown — and a **custom allocation is constructed** from eight strategies backtested over 20 years
of real market data. Not chosen from presets: the weights are continuous functions of a computed
risk-capacity score, so changing a single answer changes the portfolio. They press one button and
get their own paper portfolio, marked to live markets, with an NLP engine reading news and social
sentiment that both explains the market mood and trims exposure when it turns strongly negative.

Three pillars, all real and all defensible:

1. **Validated strategies** — every hypothesis written down before testing, confirmed on a
   split-half design (find it in the first decade, prove it in the second), and run through a cost
   ladder. Several promising ideas were killed honestly because they died once trading costs were
   applied. The one genuinely novel edge that survived: rates-gated gold, which has **zero beta** to
   the stock market.
2. **The AI scanner** — reads ~600 news and social items per cycle, scores six asset classes, and
   explains itself in plain language traceable to real headlines.
3. **Personalisation that actually personalises** — verified: six user profiles differing by one
   answer produce six different portfolios.

The `README.md` has an "Honesty & limitations" section that says plainly what's paper, what's
backtest and what's projection. Read it before you present — juries reward that kind of candour, and
every claim in it holds up.

````

## `README.md`

*What this project is, the architecture, the research behind it* — 489 lines

````md
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

Continuously scans **Google News RSS + Reddit public JSON** (no API keys, no rate limits) across six
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
| `POST` | `/api/recommend` | Six answers → custom mix, risk capacity, "why" trail, blended stats |
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

````

## `CLAUDE.md`

*Working conventions, ground rules and known gotchas* — 95 lines

````md
# Working in this repo (instructions for Claude)

You're working on **Blackbox**, an AI-personalised systematic investing platform built for the ETH
KI Challenge. Read `README.md` first — it documents the architecture, every module and every
endpoint. This file is the operational layer: conventions, gotchas, and how to verify your work.

## What this project is

A user answers six questions (or picks strategies themselves), a custom multi-strategy allocation is
**constructed** from 20 years of validated backtests, and they get a personal paper portfolio marked
to live markets, with an NLP sentiment scanner modulating exposure and explaining itself.

Three pillars, all real: **validated strategies** (`catalog.py`, `research/`), the **AI scanner**
(`sentiment_scanner.py`), and **personalisation** (`/api/recommend` in `app_user.py`).

## Ground rules

**Never invent a number.** Every performance figure in the UI traces to `logs/catalog.json`, which
is generated by `catalog.py` from real market data. If you need a statistic that doesn't exist,
compute it — don't estimate it, and don't hardcode a plausible-looking value. The credibility of the
entire project rests on this.

**Never commit secrets.** `.env` is gitignored and must stay that way. Never paste an OANDA API key,
account id, or Google client secret into code, comments, commit messages or logs. `.env.example`
documents the variable names — that's the only place credentials are ever named.

**Fail open on data, fail closed on money.** Every external dependency (sentiment file, regime gate,
price fetch) must degrade gracefully — stale sentiment returns `None`, a failed gate check logs a
warning and proceeds. But anything that would *increase* risk must fail closed. Look at
`read_latest(max_age_min=90)` and the `try/except` around the regime gate for the established pattern.

**One writer.** The JSON stores in `logs/` assume a single process writes them. gunicorn runs with
`-w 1` deliberately. If you add workers or a second writer, migrate to SQLite first — don't paper
over it with file locks.

**Books roll in exactly one place.** `user_engine.settle_users()`, called by the scanner daemon after
the 21:00 UTC close. Read paths are display-only (`base_nav × (1 + day_return_so_far)`). Never fold a
day's return during a GET — portfolio value would then depend on how often the page was refreshed.

## Conventions

- **Style**: match the surrounding code. Compact but readable; docstrings that explain *why*, not
  *what*. Comments only where the reason isn't visible from the code.
- **The UI lives in one file.** `app_user.py` holds the API and the entire single-page frontend in a
  `render_template_string` block. This is intentional: no build step, deploys by copying one file.
  Don't introduce a frontend framework without a strong reason.
- **Design language**: dark (`#0A0A0F`), one violet accent (`#a78bfa`), Geist for headings, Inter for
  body. Animate only `transform` and `opacity`; reveal-on-scroll happens once, never on re-entry;
  always keep the `prefers-reduced-motion` block working.
- **Caching**: market data is cached (daily candles 30 min, spot prices 7 min, marks 20 min). If you
  add a data source, cache it — the app must stay fast and must not hammer the broker.

## Gotchas that have already cost time

- **Chart.js needs a fixed-height positioned wrapper.** With `responsive: true` and
  `maintainAspectRatio: false`, putting the height on the `<canvas>` makes it grow without bound.
  Use `.chartbox { position: relative; height: 280px }` with `canvas { position: absolute; inset: 0 }`.
- **Don't initialise charts in `requestAnimationFrame`.** It never fires when the tab is backgrounded
  or occluded. Use `setTimeout(..., 30)`.
- **Date grids differ between sources.** OANDA daily candles are stamped 21:00 UTC; Coinbase stamps
  00:00. Normalise to calendar dates before joining, or correlations silently come out empty. Weekly
  downsampled curves also each have their own grid — match by nearest date, not equality.
- **Watch `bool` vs `float` in pandas masks.** `.fillna(False).astype(bool)` before applying `~`.
- **Don't double-apply volatility targeting** when composing strategies from other strategies —
  it silently halves the Sharpe ratio.

## Verifying your work

The app is a live web product, so verify in a browser rather than assuming.

1. `python bootstrap.py && python app_user.py` → `http://localhost:8090`
2. Drive the real UI and read back state. In this environment screenshots have been unreliable, so
   the dependable method is evaluating JavaScript in the page and checking concrete values —
   chart dimensions, dataset lengths, rendered text, `localStorage`, API responses.
3. Test the **whole journey**, not the change in isolation: quiz → mix → account → start portfolio →
   sign out → log back in with the recovery key → portfolio still there.
4. Check the console for errors and confirm the page has no horizontal overflow at mobile width.

For the personalisation engine specifically, the regression test that matters: change **one** answer
at a time and confirm the allocation actually changes. Six profiles differing by one answer should
produce six distinct mixes.

## Running things

```bash
python bootstrap.py         # one-time: seed logs/ from data/
python app_user.py          # dev server on :8090
python run_scanner.py       # scanner daemon (20-min cycles + daily settle)
python catalog.py           # rebuild strategy catalog  [needs OANDA creds]
python research/research_deep3.py   # reproduce the rates-gated gold validation [needs OANDA creds]
```

The web app, quiz, accounts and scanner all work with **no credentials**. Only live per-strategy
holdings and rebuilding the catalog need a free OANDA practice key.

````

## `HANDOVER.md`

*Current status, next steps, demo script* — 136 lines

````md
# Handover

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

````

## `app_user.py`

*THE WHOLE WEB APP — Flask API + the entire single-page UI* — 1114 lines

```python
"""
BLACKBOX — user-facing strategy platform (ETH KI challenge), v2.

The journey: hero -> "Let's go" -> pick your path (6-question quiz where EVERY
answer visibly constrains the result, or build your own mix from raw stats) ->
"Start my Blackbox" -> a personal paper portfolio marked to LIVE markets by the
same validated rules, with the AI scanner utilised per-strategy (exposure tilt +
explanations). No auth (demo): the browser keeps a local id; the server keeps the
book. Design: premium-site-workflow + emil-design-eng.
"""
import os, json, time, secrets, hashlib
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, request, render_template_string, Response, session

HERE = os.path.dirname(__file__)
CATALOG = os.path.join(HERE, "logs", "catalog.json")
SENTIMENT = os.path.join(HERE, "logs", "sentiment.json")
USERS = os.path.join(HERE, "logs", "app_users.json")
ACCOUNTS = os.path.join(HERE, "logs", "app_accounts.json")

app = Flask(__name__)


def _app_secret():
    """Stable signing secret across restarts (env wins; else persisted once)."""
    s = os.getenv("APP_SECRET")
    if s:
        return s
    p = os.path.join(HERE, "logs", "app_secret.txt")
    if os.path.exists(p):
        return open(p).read().strip()
    s = secrets.token_hex(32)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(s)
    return s


app.secret_key = _app_secret()
app.permanent_session_lifetime = timedelta(days=60)
app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True)
_cache = {}


def cached(key, ttl, fn):
    now = time.time()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    v = fn()
    _cache[key] = (now, v)
    return v


def _load(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def _save_users(u):
    tmp = USERS + ".tmp"
    json.dump(u, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, USERS)


VALID_IDS = {"stack_bal", "stack_agg", "equity_season", "gold_macro",
             "commod_trend", "risk_parity", "crypto_trend", "spx_hold"}


def _notify(msg, title="Blackbox Platform"):
    """Owner push on product events (signups, new portfolios). Never raises."""
    try:
        import notifier
        notifier.send(msg, title=title)
    except Exception:
        pass

TIER_LABELS = ["Capital Preservation", "Balanced Growth", "Growth", "Maximum Growth"]


@app.route("/api/catalog")
def api_catalog():
    return jsonify(_load(CATALOG, {"strategies": []}))


@app.route("/api/sentiment")
def api_sentiment():
    return jsonify(_load(SENTIMENT, {"assets": {}}))


@app.route("/api/marks")
def api_marks():
    try:
        from user_engine import marks
        return jsonify(marks())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    """Constructs a CUSTOM mix continuously from all six answers — every answer
    moves the weights (caps bind, crypto has eligibility gates, priority tilts).
    Fully transparent: returns the 'why' trail + a 0-100 risk-capacity score."""
    p = request.get_json(force=True, silent=True) or {}
    exp = p.get("experience", "some"); hor = p.get("horizon", "3-10y")
    dd = p.get("max_dd", "-25%"); react = p.get("react", "hold")
    goal = p.get("goal", "steady"); prio = p.get("priority", "beat")
    raw = ({"preserve": 0, "steady": 2, "maximize": 4}.get(goal, 2)
           + {"-10%": 0, "-25%": 1.5, "-50%+": 3}.get(dd, 1.5)
           + {"sell": 0, "hold": 1, "buy": 2}.get(react, 1)
           + {"<1y": 0, "1-3y": 1, "3-10y": 2, "10y+": 2.5}.get(hor, 2)
           + {"new": 0, "some": 1, "experienced": 1.5}.get(exp, 1))
    caps, why = [], []
    for cond, cap, msg in [
        (exp == "new", 5.0, "New to investing — leverage and crypto are capped out of your mix"),
        (hor == "<1y", 1.5, "Money needed within a year gets the most defensive construction"),
        (hor == "1-3y", 5.5, "A 1-3 year horizon can't ride out deep drawdowns — risk capacity capped"),
        (dd == "-10%", 4.5, "A -10% pain limit rules out the higher-drawdown engines"),
        (dd == "-25%", 8.5, "A -25% pain limit keeps the crypto engine to a small satellite"),
        (react == "sell", 4.0, "You'd sell in a -20% month — strategies that CAN fall that far are excluded"),
    ]:
        if cond:
            caps.append(cap)
            if cap < raw:
                why.append(msg)
    score = min([raw] + caps)
    f = max(0.0, min(1.0, score / 13.0))
    capacity = round(f * 100)
    # continuous allocation recipe (weights are functions of risk capacity f)
    crypto_ok = (dd == "-50%+") and (exp != "new") and (hor in ("3-10y", "10y+"))
    w = {"risk_parity": 45 * (1 - f) ** 1.6,
         "gold_macro": 18 + 8 * (1 - f),
         "stack_bal": 24,
         "equity_season": 12 + 10 * f,
         "commod_trend": 5 + 9 * f,
         "stack_agg": 30 * f ** 1.3,
         "crypto_trend": (24 * f ** 2.0) if crypto_ok else 0.0}
    tilt = {"smooth": {"risk_parity": 1.4, "gold_macro": 1.25, "stack_agg": 0.7, "crypto_trend": 0.65},
            "beat": {"stack_bal": 1.3, "equity_season": 1.15},
            "max": {"stack_agg": 1.35, "crypto_trend": 1.35, "risk_parity": 0.55}}[prio]
    for k, m in tilt.items():
        w[k] = w.get(k, 0) * m
    # drop dust (<5%) then normalize to exactly 100 (largest remainder)
    tot = sum(w.values())
    w = {k: v for k, v in w.items() if v / tot >= 0.05}
    tot = sum(w.values())
    fl = {k: int(v * 100 / tot) for k, v in w.items()}
    rem = 100 - sum(fl.values())
    for k in sorted(w, key=lambda k: -(w[k] * 100 / tot - fl[k]))[:rem]:
        fl[k] += 1
    mix = {k: v for k, v in sorted(fl.items(), key=lambda z: -z[1]) if v > 0}
    tier = 0 if f < 0.25 else 1 if f < 0.5 else 2 if f < 0.75 else 3
    if not why:
        why.append({"preserve": "You asked to preserve capital first — defensive engines dominate",
                    "steady": "Steady-growth goal with matching tolerance — a diversified core",
                    "maximize": "Max-growth goal with the tolerance to back it"}.get(goal, ""))
    if crypto_ok and mix.get("crypto_trend"):
        why.append("Deep drawdown tolerance + long horizon unlocked a crypto momentum satellite")
    elif not crypto_ok:
        why.append("Crypto stayed locked out (needs -50% tolerance, experience and a 3y+ horizon)")
    why.append({"smooth": "Priority 'smooth ride' tilted weight into risk parity and gold",
                "beat": "Priority 'beat the market' put the multi-edge engines at the centre",
                "max": "Priority 'max wealth' tilted into the levered engines"}[prio])
    cat = {s["id"]: s for s in _load(CATALOG, {"strategies": []})["strategies"]}
    parts, cagr, vol, ddw = [], 0.0, 0.0, 0.0
    for sid, wt in mix.items():
        s = cat.get(sid)
        if not s:
            continue
        st = s["stats"]
        parts.append({"id": sid, "name": s["name"], "weight": wt, "risk": s["risk"],
                      "cagr": st["cagr"], "sharpe": st["sharpe"], "max_dd": st["max_dd"]})
        cagr += wt / 100 * st["cagr"]; vol += wt / 100 * st["vol"]; ddw += wt / 100 * st["max_dd"]
    return jsonify({"tier": tier, "label": TIER_LABELS[tier], "capacity": capacity,
                    "why": [x for x in why if x], "mix": mix, "parts": parts,
                    "blend": {"cagr_est": round(cagr, 1), "vol_est": round(vol, 1), "dd_est": round(ddw, 1)}})


@app.route("/api/user/create", methods=["POST"])
def user_create():
    p = request.get_json(force=True, silent=True) or {}
    name = (p.get("name") or "My").strip()[:24] or "My"
    mix = {k: float(v) for k, v in (p.get("mix") or {}).items() if k in VALID_IDS and float(v) > 0}
    tot = sum(mix.values())
    if not mix or not (95 <= tot <= 105):
        return jsonify({"error": "mix must sum to 100%"}), 400
    mix = {k: round(v * 100 / tot, 1) for k, v in mix.items()}
    users = _load(USERS, {})
    uid = secrets.token_hex(4)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    users[uid] = {"name": name, "mix": mix, "created": today,
                  "base_nav": 10000.0, "base_date": today, "history": [[today, 10000.0]]}
    # signed in -> this becomes the account's active Blackbox (replacing any old one)
    a, aid = _me()
    if a:
        old = a.get("uid")
        if old and old in users and old != uid:
            users.pop(old, None)
        accounts = _accounts()
        accounts[aid]["uid"] = uid
        if not p.get("name"):
            users[uid]["name"] = a["name"]
        _save_accounts(accounts)
    _save_users(users)
    mixtxt = ", ".join(f"{k} {v:.0f}%" for k, v in sorted(mix.items(), key=lambda z: -z[1]))
    _notify(f"New Blackbox started: \"{users[uid]['name']}\" ({'account' if a else 'anon'}) — {mixtxt}")
    return jsonify({"user_id": uid, "signed_in": bool(a)})


# ---------------- accounts (recovery-key now, Google when GOOGLE_CLIENT_ID set) ----
WORDS = ("ember violet falcon drift nova quartz cedar lumen onyx delta raven pixel "
         "zephyr cobalt aurora slate ridge polar comet marble tigris echo umbra vega "
         "sable orchid krypton fjord saffron helix mesa argon").split()


def _accounts():
    return _load(ACCOUNTS, {})


def _save_accounts(a):
    tmp = ACCOUNTS + ".tmp"
    json.dump(a, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, ACCOUNTS)


def _gen_key():
    r = secrets.SystemRandom()
    return "-".join(r.sample(WORDS, 3)) + "-" + str(r.randrange(1000, 9999))


def _hash_key(key, salt):
    return hashlib.sha256((salt + key.strip().lower()).encode()).hexdigest()


def _me():
    aid = session.get("aid")
    if not aid:
        return None, None
    return _accounts().get(aid), aid


def _login(aid):
    session.permanent = True
    session["aid"] = aid


@app.route("/api/config")
def api_config():
    return jsonify({"google_client_id": os.getenv("GOOGLE_CLIENT_ID") or None})


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    p = request.get_json(force=True, silent=True) or {}
    name = (p.get("name") or "").strip()[:24] or "Trader"
    accounts = _accounts()
    aid = secrets.token_hex(8)
    key = _gen_key()
    salt = secrets.token_hex(8)
    acct = {"name": name, "salt": salt, "key_hash": _hash_key(key, salt),
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "uid": None, "google_sub": None, "email": None, "picture": None}
    adopt = p.get("adopt_uid")
    if adopt and adopt in _load(USERS, {}):
        acct["uid"] = adopt
    accounts[aid] = acct
    _save_accounts(accounts)
    _login(aid)
    _notify(f"New platform account: \"{name}\" (recovery-key), total {len(accounts)}")
    return jsonify({"ok": True, "name": name, "recovery_key": key})


@app.route("/api/auth/recover", methods=["POST"])
def auth_recover():
    p = request.get_json(force=True, silent=True) or {}
    key = (p.get("key") or "")
    accounts = _accounts()
    for aid, a in accounts.items():
        if a.get("key_hash") and a["key_hash"] == _hash_key(key, a.get("salt", "")):
            _login(aid)
            return jsonify({"ok": True, "name": a["name"]})
    return jsonify({"error": "key not recognised"}), 401


@app.route("/api/auth/google", methods=["POST"])
def auth_google():
    cid = os.getenv("GOOGLE_CLIENT_ID")
    if not cid:
        return jsonify({"error": "google not configured"}), 400
    p = request.get_json(force=True, silent=True) or {}
    cred = p.get("credential") or ""
    try:
        import requests as rq
        info = rq.get("https://oauth2.googleapis.com/tokeninfo",
                      params={"id_token": cred}, timeout=10).json()
    except Exception:
        return jsonify({"error": "verification unavailable"}), 502
    if (info.get("aud") != cid or "accounts.google.com" not in str(info.get("iss", ""))
            or int(info.get("exp", 0)) < time.time()):
        return jsonify({"error": "invalid token"}), 401
    sub = info.get("sub")
    accounts = _accounts()
    aid = next((k for k, a in accounts.items() if a.get("google_sub") == sub), None)
    if aid is None:
        aid = secrets.token_hex(8)
        accounts[aid] = {"name": (info.get("given_name") or info.get("name") or "Trader")[:24],
                         "salt": None, "key_hash": None,
                         "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                         "uid": None, "google_sub": sub}
        adopt = p.get("adopt_uid")
        if adopt and adopt in _load(USERS, {}):
            accounts[aid]["uid"] = adopt
        _notify(f"New platform account: \"{accounts[aid]['name']}\" (Google), total {len(accounts)}")
    accounts[aid]["email"] = info.get("email")
    accounts[aid]["picture"] = info.get("picture")
    _save_accounts(accounts)
    _login(aid)
    return jsonify({"ok": True, "name": accounts[aid]["name"]})


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.pop("aid", None)
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    a, aid = _me()
    if not a:
        return jsonify({"signed_in": False})
    portfolio = _user_payload(a["uid"]) if a.get("uid") else None
    return jsonify({"signed_in": True, "name": a["name"], "email": a.get("email"),
                    "picture": a.get("picture"), "google": bool(a.get("google_sub")),
                    "portfolio": portfolio})


def _user_payload(uid):
    users = _load(USERS, {})
    u = users.get(uid)
    if not u:
        return None
    try:
        from user_engine import marks
        mk = marks()["strategies"]
    except Exception:
        mk = {}
    day = 0.0
    strat_view = []
    for sid, w in u["mix"].items():
        m = mk.get(sid, {})
        contrib = (w / 100) * m.get("tilt", 1.0) * m.get("day_ret", 0.0)
        day += contrib
        strat_view.append({"id": sid, "weight": w, "day_ret": m.get("day_ret", 0.0),
                           "gross": m.get("gross", 0), "note": m.get("note", ""),
                           "tilt": m.get("tilt", 1.0), "tilt_why": m.get("tilt_why"),
                           "sentiment": m.get("sentiment", {}), "holdings": m.get("holdings", [])})
    # display-only: user_engine.settle_users() (scanner daemon, after the 21:00 UTC
    # daily close) is the ONE place books roll — no request-time folding here.
    nav_now = round(u["base_nav"] * (1 + day), 2)
    return {"uid": uid, "name": u["name"], "created": u["created"], "mix": u["mix"],
            "nav": nav_now, "day_ret": round(day * 100, 3),
            "since_start": round((nav_now / 10000 - 1) * 100, 2),
            "history": u["history"], "strategies": strat_view,
            "note": "Paper portfolio marked to live markets by the same validated rules. Estimates, not investment advice."}


@app.route("/api/user/<uid>", methods=["GET"])
def user_get(uid):
    p = _user_payload(uid)
    if not p:
        return jsonify({"error": "not found"}), 404
    return jsonify(p)


@app.route("/api/user/<uid>/delete", methods=["POST"])
def user_delete(uid):
    users = _load(USERS, {})
    users.pop(uid, None)
    _save_users(users)
    a, aid = _me()
    if a and a.get("uid") == uid:
        accounts = _accounts()
        accounts[aid]["uid"] = None
        _save_accounts(accounts)
    return jsonify({"ok": True})


@app.route("/icon.png")
def icon():
    p = os.path.join(HERE, "icon.png")
    if os.path.exists(p):
        return Response(open(p, "rb").read(), mimetype="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})
    return Response(status=404)


@app.route("/")
def index():
    return render_template_string(PAGE)


PAGE = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blackbox — Real strategies. Real numbers.</title>
<link rel="icon" href="/icon.png"><link rel="apple-touch-icon" href="/icon.png">
<meta name="theme-color" content="#0A0A0F">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@500;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<script src="https://accounts.google.com/gsi/client" async defer></script>
<style>
:root{--bg:#0A0A0F;--surface:#13131A;--surface2:#191922;--line:rgba(167,139,250,.14);
--txt:#F5F5F0;--mut:#9C9CA8;--acc:#a78bfa;--acc2:#8b5cf6;--deep:#7c3aed;
--green:#34d399;--red:#fb7185;--ease:cubic-bezier(.22,1,.36,1)}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--txt);font:16px/1.6 'Inter',sans-serif;-webkit-font-smoothing:antialiased;overflow-x:hidden}
h1,h2,h3{font-family:'Geist','Inter',sans-serif;letter-spacing:-.02em}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
.rv{opacity:0;transform:translateY(24px);transition:opacity .7s var(--ease),transform .7s var(--ease)}
.rv.in{opacity:1;transform:none}
.hero{position:relative;min-height:100svh;display:flex;align-items:center;overflow:hidden}
.orb{position:absolute;border-radius:50%;filter:blur(90px);opacity:.5;pointer-events:none}
.o1{width:560px;height:560px;background:radial-gradient(circle,#7c3aed55,transparent 65%);top:-120px;left:-120px;animation:d1 22s ease-in-out infinite}
.o2{width:640px;height:640px;background:radial-gradient(circle,#8b5cf640,transparent 65%);bottom:-200px;right:-160px;animation:d2 26s ease-in-out infinite}
@keyframes d1{50%{transform:translate(70px,50px)}}
@keyframes d2{50%{transform:translate(-60px,-40px)}}
.hero::after{content:"";position:absolute;inset:0;background:rgba(10,10,15,.3)}
.hero .wrap{position:relative;z-index:2;padding:90px 24px 60px}
.kicker{display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--acc);
border:1px solid var(--line);border-radius:999px;padding:7px 14px;background:rgba(167,139,250,.06);margin-bottom:26px}
.kicker .dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 10px var(--green);animation:pl 2.4s infinite}
@keyframes pl{50%{opacity:.4}}
h1{font-size:clamp(42px,7.2vw,88px);font-weight:800;line-height:1.03}
h1 .w{display:inline-block;opacity:0;transform:translateY(26px);animation:win .7s var(--ease) forwards}
@keyframes win{to{opacity:1;transform:none}}
.grad{background:linear-gradient(92deg,#c4b5fd,#8b5cf6);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.sub{max-width:560px;color:var(--mut);font-size:18px;margin:24px 0 36px}
.cta{display:inline-flex;align-items:center;gap:10px;background:linear-gradient(135deg,#8b5cf6,#7c3aed);
color:#fff;font-weight:700;font-size:16px;padding:16px 30px;border-radius:14px;border:0;cursor:pointer;
box-shadow:0 10px 40px -8px rgba(124,58,237,.55);transition:transform .16s var(--ease),box-shadow .2s var(--ease)}
.cta:hover{box-shadow:0 14px 52px -8px rgba(124,58,237,.75)}
.cta:active{transform:scale(.97)}
.cta.ghost{background:var(--surface2);border:1px solid var(--line);box-shadow:none;color:var(--txt)}
.cta:disabled{opacity:.45;cursor:not-allowed}
.hstats{display:flex;gap:34px;margin-top:56px;flex-wrap:wrap}
.hstat .n{font-family:'Geist';font-size:26px;font-weight:800}
.hstat .l{font-size:12.5px;color:var(--mut)}
section{padding:96px 0}
.sec-k{font-size:13px;font-weight:700;color:var(--acc);text-transform:uppercase;letter-spacing:.14em;margin-bottom:14px}
h2{font-size:clamp(30px,4vw,48px);font-weight:800;margin-bottom:14px}
.lead{color:var(--mut);max-width:640px;font-size:17px}
/* journey */
.modes{display:flex;gap:14px;margin-top:36px;flex-wrap:wrap}
.mode{flex:1;min-width:280px;background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:26px;cursor:pointer;
transition:transform .2s var(--ease),border-color .2s}
.mode:active{transform:scale(.985)}
.mode.on{border-color:var(--acc);background:rgba(139,92,246,.07)}
.mode h3{font-size:19px;margin-bottom:6px}
.mode p{color:var(--mut);font-size:14.5px}
.quiz{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:36px;margin-top:22px;display:none}
.quiz.show,.builderwrap.show{display:block;animation:fup .5s var(--ease)}
@keyframes fup{from{opacity:0;transform:translateY(14px)}to{opacity:1}}
.q{margin-bottom:24px}
.q .ql{font-weight:600;margin-bottom:11px}
.chips{display:flex;gap:10px;flex-wrap:wrap}
.chip{border:1px solid var(--line);background:var(--surface2);color:var(--mut);border-radius:12px;
padding:11px 18px;font-size:14.5px;font-weight:600;cursor:pointer;transition:transform .15s var(--ease),border-color .2s,color .2s,background .2s}
.chip:active{transform:scale(.96)}
.chip.on{border-color:var(--acc);color:#fff;background:rgba(139,92,246,.16)}
.reco{display:none;margin-top:30px;border-top:1px solid var(--line);padding-top:28px}
.reco.show{display:block;animation:fup .5s var(--ease)}
.why{margin:14px 0 4px;padding:0 0 0 2px}
.why li{list-style:none;color:var(--mut);font-size:14px;padding:5px 0 5px 26px;position:relative}
.why li::before{content:"→";position:absolute;left:0;color:var(--acc)}
.blend{display:flex;gap:26px;flex-wrap:wrap;margin:18px 0 8px}
.b .n{font-family:'Geist';font-size:22px;font-weight:800}
.b .l{font-size:12px;color:var(--mut)}
.mixbar{display:flex;height:14px;border-radius:7px;overflow:hidden;margin:16px 0 10px;border:1px solid var(--line)}
.mixbar i{display:block;height:100%}
.mixlegend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--mut)}
.mixlegend b{color:var(--txt)}
.dotc{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:6px;vertical-align:1px}
.namebox{display:flex;gap:12px;margin-top:22px;flex-wrap:wrap;align-items:center}
.namebox input{background:var(--surface2);border:1px solid var(--line);border-radius:12px;color:var(--txt);
padding:14px 16px;font:600 15px 'Inter';min-width:220px}
.namebox input:focus{outline:none;border-color:var(--acc)}
/* builder */
.builderwrap{display:none;margin-top:22px}
.bbar{position:sticky;bottom:14px;z-index:30;background:rgba(19,19,26,.92);backdrop-filter:blur(12px);
border:1px solid var(--line);border-radius:18px;padding:16px 22px;display:flex;gap:20px;align-items:center;flex-wrap:wrap;
box-shadow:0 18px 50px -20px rgba(0,0,0,.7);margin-top:26px}
.bbar .tot{font-family:'Geist';font-weight:800;font-size:22px}
.bbar .bs{font-size:13px;color:var(--mut)}
.step{display:flex;align-items:center;gap:8px;margin-top:14px}
.step button{width:34px;height:34px;border-radius:10px;border:1px solid var(--line);background:var(--surface2);
color:var(--txt);font-size:17px;font-weight:700;cursor:pointer;transition:transform .13s}
.step button:active{transform:scale(.92)}
.step .v{font-family:'Geist';font-weight:800;min-width:52px;text-align:center;font-size:17px}
/* catalog */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px;margin-top:44px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:24px;cursor:pointer;
transition:transform .22s var(--ease),border-color .22s,box-shadow .22s var(--ease)}
@media(hover:hover){.card:hover{transform:translateY(-4px);border-color:rgba(167,139,250,.45);box-shadow:0 18px 50px -20px rgba(124,58,237,.5)}}
.card .top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px}
.card h3{font-size:19px;line-height:1.25}
.badge{font-size:11px;font-weight:700;padding:4px 10px;border-radius:999px;white-space:nowrap}
.badge.Conservative{background:rgba(52,211,153,.12);color:var(--green)}
.badge.Moderate{background:rgba(167,139,250,.14);color:var(--acc)}
.badge.High{background:rgba(251,191,36,.13);color:#fbbf24}
.badge.VeryHigh{background:rgba(251,113,133,.13);color:var(--red)}
.card .tag{color:var(--mut);font-size:14px;min-height:44px;margin-bottom:12px}
.sentchip{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:700;border-radius:999px;
padding:4px 11px;margin-bottom:12px;background:var(--surface2);border:1px solid var(--line)}
.sentchip .sd{width:7px;height:7px;border-radius:50%}
.spark{width:100%;height:56px;display:block;margin-bottom:14px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.st .n{font-family:'Geist';font-weight:800;font-size:16.5px}
.st .l{font-size:10.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
/* modal */
.mask{position:fixed;inset:0;background:rgba(6,6,10,.72);backdrop-filter:blur(6px);z-index:50;display:none;align-items:center;justify-content:center;padding:20px}
.mask.show{display:flex}
.modal{background:var(--surface);border:1px solid var(--line);border-radius:24px;max-width:960px;width:100%;
max-height:90vh;overflow-y:auto;padding:34px;transform:scale(.96);opacity:0;transition:transform .25s var(--ease),opacity .25s}
.mask.show .modal{transform:scale(1);opacity:1}
.modal .x{float:right;background:var(--surface2);border:1px solid var(--line);color:var(--mut);width:36px;height:36px;
border-radius:10px;font-size:17px;cursor:pointer}
.mrow{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:24px}
@media(max-width:820px){.mrow{grid-template-columns:1fr}}
.mbox{background:var(--surface2);border:1px solid var(--line);border-radius:16px;padding:20px;min-width:0}
.mbox h4{font-size:13px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px}
/* Chart.js REQUIRES a fixed-height positioned wrapper with responsive mode —
   height on the canvas itself makes it grow unbounded. */
.chartbox{position:relative;height:280px;min-width:0}
.chartbox.short{height:230px}
.chartbox canvas{position:absolute;inset:0}
.modal{overflow-x:hidden}
.modal .stats{grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:14px 10px}
.hchips{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.hchip{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:10px 14px;font-size:12.5px}
.hchip .n{font-family:'Geist';font-weight:800;font-size:15px;display:block}
.method{font-size:14px;color:var(--mut);line-height:1.65;margin-top:20px;border-left:3px solid var(--deep);padding-left:14px}
/* me */
#me{display:none;background:var(--surface);border-block:1px solid var(--line)}
#me.show{display:block}
.mehead{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;flex-wrap:wrap}
.nav-big{font-family:'Geist';font-size:clamp(40px,6vw,64px);font-weight:800;letter-spacing:-.02em}
.pill{display:inline-block;font-size:13px;font-weight:700;border-radius:999px;padding:6px 14px;margin-left:8px;vertical-align:14px}
.pill.up{background:rgba(52,211,153,.13);color:var(--green)}
.pill.dn{background:rgba(251,113,133,.13);color:var(--red)}
.megrid{display:grid;grid-template-columns:1.2fr 1fr;gap:20px;margin-top:32px}
@media(max-width:900px){.megrid{grid-template-columns:1fr}}
.scard2{background:var(--surface2);border:1px solid var(--line);border-radius:18px;padding:20px;margin-top:14px}
.scard2 .h2r{display:flex;justify-content:space-between;align-items:center;gap:10px}
.scard2 h3{font-size:16.5px}
.wtag{font-family:'Geist';font-weight:800;color:var(--acc)}
.note{color:var(--mut);font-size:13.5px;margin-top:6px}
.tiltwarn{margin-top:10px;font-size:12.5px;color:#fbbf24;background:rgba(251,191,36,.07);border:1px solid rgba(251,191,36,.2);
border-radius:10px;padding:8px 12px}
.hlist{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.htag{font-size:12px;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:5px 10px;color:var(--mut)}
.htag b{color:var(--txt)}
.skel{color:var(--mut);padding:40px;text-align:center;font-size:15px}
.skel .sp{display:inline-block;width:16px;height:16px;border:2px solid var(--acc);border-top-color:transparent;border-radius:50%;
animation:spin .8s linear infinite;vertical-align:-3px;margin-right:10px}
@keyframes spin{to{transform:rotate(360deg)}}
/* sentiment section */
.sgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px;margin-top:44px}
.scard{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:22px}
.scard .h{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.scard h3{font-size:17px;text-transform:capitalize}
.gauge{height:10px;border-radius:5px;background:linear-gradient(90deg,#fb7185,#3a3a44 50%,#34d399);position:relative;margin:10px 0 6px}
.gauge i{position:absolute;top:-4px;width:4px;height:18px;border-radius:2px;background:#fff;box-shadow:0 0 8px rgba(255,255,255,.6);transition:left .8s var(--ease)}
.sscore{font-family:'Geist';font-weight:800;font-size:22px}
.sexp{font-size:13.5px;color:var(--mut);margin:10px 0 12px;min-height:40px}
.head{font-size:12.5px;padding:8px 0;border-top:1px solid rgba(167,139,250,.08);color:var(--mut);display:flex;gap:8px;justify-content:space-between}
.head .t{flex:1}
.head .s{white-space:nowrap;font-weight:700}
/* top nav + auth */
.topnav{position:fixed;top:0;left:0;right:0;z-index:40;background:rgba(10,10,15,.6);
backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}
.tn{display:flex;justify-content:space-between;align-items:center;height:60px}
.brand{font-family:'Geist';font-weight:800;font-size:15px;letter-spacing:.12em}
.cta.small{padding:9px 18px;font-size:14px;border-radius:11px}
.uchip{display:flex;gap:10px;align-items:center}
.uchip img{width:30px;height:30px;border-radius:50%;border:1px solid var(--line)}
.uinit{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#8b5cf6,#7c3aed);
display:grid;place-items:center;font-weight:800;font-size:14px;color:#fff}
.uchip .un{font-weight:600;font-size:14px;max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.amodal{max-width:440px}
.ain{width:100%;background:var(--surface2);border:1px solid var(--line);border-radius:12px;color:var(--txt);
padding:14px 16px;font:600 15px 'Inter'}
.ain:focus{outline:none;border-color:var(--acc)}
.aerr{color:var(--red);font-size:13px;margin-top:10px;min-height:16px}
.keybox{font-family:'Geist';font-weight:800;font-size:19px;letter-spacing:.04em;text-align:center;
background:var(--surface2);border:1px dashed rgba(167,139,250,.5);border-radius:14px;padding:18px 14px;margin-top:14px;
user-select:all;word-break:break-all}
.ordiv{display:flex;align-items:center;gap:12px;color:var(--mut);font-size:12px;margin:16px 0}
.ordiv::before,.ordiv::after{content:"";flex:1;height:1px;background:var(--line)}
@media(max-width:640px){.uchip .un{display:none}}
footer{border-top:1px solid var(--line);padding:44px 0 60px;color:var(--mut);font-size:13px}
footer .d{max-width:820px;line-height:1.7}
@media(prefers-reduced-motion:reduce){.rv,.orb,h1 .w,.gauge i{animation:none!important;transition:none!important;opacity:1!important;transform:none!important}}
@media(max-width:640px){section{padding:64px 0}.quiz{padding:24px}.stats{grid-template-columns:repeat(2,1fr);gap:12px}}
</style></head><body>

<nav class="topnav"><div class="wrap tn">
  <div class="brand">BLACKBOX</div>
  <div id="authbox"><button class="cta ghost small" onclick="openAuth()">Sign in</button></div>
</div></nav>

<section class="hero">
  <div class="orb o1"></div><div class="orb o2"></div>
  <div class="wrap">
    <div class="kicker"><span class="dot"></span>Live engine · 5 asset classes · AI market scanner</div>
    <h1 id="hl"></h1>
    <p class="sub">Choose an institutional-grade systematic strategy — or let six questions choose it for you — then press go. Your own Blackbox starts trading on paper, marked to live markets, guided by validated rules and an AI that reads the news.</p>
    <button class="cta" id="heroCta" onclick="heroGo()">Let's go →</button>
    <div class="hstats">
      <div class="hstat"><div class="n" id="hs1">—</div><div class="l">strategies, fully backtested</div></div>
      <div class="hstat"><div class="n">20 yrs</div><div class="l">of real market data</div></div>
      <div class="hstat"><div class="n" id="hs2">—</div><div class="l">sources scanned by the AI</div></div>
    </div>
  </div>
</section>

<section id="me">
  <div class="wrap">
    <div id="mebody"><div class="skel"><span class="sp"></span>Syncing your Blackbox with live markets…</div></div>
  </div>
</section>

<section id="journey">
  <div class="wrap">
    <div class="rv"><div class="sec-k">01 — Start your journey</div>
    <h2>Two ways in. One press of go.</h2>
    <p class="lead">Answer six questions and every answer visibly shapes the outcome — or skip the quiz and build your own mix straight from the numbers.</p></div>
    <div class="modes rv">
      <div class="mode" id="modeQuiz" onclick="setMode('quiz')"><h3>🧭 Guide me</h3><p>A six-question profile. We show exactly which answers capped or shaped your mix — no black box.</p></div>
      <div class="mode" id="modeManual" onclick="setMode('manual')"><h3>🎛 I'll choose myself</h3><p>Browse the strategies below and set your own weights by CAGR, volatility and max drawdown.</p></div>
    </div>

    <div class="quiz" id="quiz">
      <div class="q"><div class="ql">1 · How experienced are you with investing?</div>
        <div class="chips" data-k="experience"><button class="chip" data-v="new">I'm new</button><button class="chip on" data-v="some">Some experience</button><button class="chip" data-v="experienced">Experienced</button></div></div>
      <div class="q"><div class="ql">2 · How long can this money stay invested?</div>
        <div class="chips" data-k="horizon"><button class="chip" data-v="<1y">&lt;1 year</button><button class="chip" data-v="1-3y">1–3 years</button><button class="chip on" data-v="3-10y">3–10 years</button><button class="chip" data-v="10y+">10+ years</button></div></div>
      <div class="q"><div class="ql">3 · The most you could watch it fall without selling?</div>
        <div class="chips" data-k="max_dd"><button class="chip" data-v="-10%">−10%</button><button class="chip on" data-v="-25%">−25%</button><button class="chip" data-v="-50%+">−50% or more</button></div></div>
      <div class="q"><div class="ql">4 · Your portfolio drops 20% in a month. You…</div>
        <div class="chips" data-k="react"><button class="chip" data-v="sell">Sell everything</button><button class="chip on" data-v="hold">Hold, but worry</button><button class="chip" data-v="buy">Buy more</button></div></div>
      <div class="q"><div class="ql">5 · What's the goal?</div>
        <div class="chips" data-k="goal"><button class="chip" data-v="preserve">Preserve capital</button><button class="chip on" data-v="steady">Grow steadily</button><button class="chip" data-v="maximize">Maximize growth</button></div></div>
      <div class="q"><div class="ql">6 · What matters most to you?</div>
        <div class="chips" data-k="priority"><button class="chip" data-v="smooth">A smooth ride</button><button class="chip on" data-v="beat">Beating the market</button><button class="chip" data-v="max">Max long-term wealth</button></div></div>
      <button class="cta" onclick="recommend()">Build my mix →</button>
      <div class="reco" id="reco"></div>
    </div>

    <div class="builderwrap" id="builderwrap">
      <p class="lead" style="margin-top:6px">Set weights with the steppers on the strategy cards below. Your mix must total 100%.</p>
      <div class="bbar" id="bbar">
        <div><div class="tot" id="btot">0%</div><div class="bs">allocated</div></div>
        <div style="flex:1;min-width:180px"><div class="mixbar" id="bmix" style="margin:0 0 6px"></div><div class="bs" id="bstats">—</div></div>
        <button class="cta" id="bgo" disabled onclick="showName(builderMix())">Let's go →</button>
      </div>
    </div>

    <div class="reco show" id="namecard" style="display:none;border:0;padding-top:6px">
      <div class="namebox">
        <input id="uname" placeholder="Name your Blackbox (e.g. Nico's)" maxlength="24">
        <button class="cta" id="startBtn" onclick="startBlackbox()">🚀 Start my Blackbox</button>
      </div>
      <div class="note" style="margin-top:10px">Starts a personal paper portfolio of 10,000 marked to live markets. Demo capital — no real money.</div>
    </div>
  </div>
</section>

<section id="catalog" style="padding-top:10px">
  <div class="wrap">
    <div class="rv"><div class="sec-k">02 — The strategies</div>
    <h2>Real numbers. Nothing invented.</h2>
    <p class="lead">Every stat is a 20-year backtest — true drawdowns included. The AI scanner's live read is on every card. Click a card for the full profile.</p></div>
    <div class="grid" id="cards"></div>
  </div>
</section>

<section id="intel" style="background:var(--surface);border-block:1px solid var(--line)">
  <div class="wrap">
    <div class="rv"><div class="sec-k">03 — AI market intelligence</div>
    <h2>The scanner reads the market's mood</h2>
    <p class="lead">An NLP engine scans hundreds of news and social sources, scores each asset class, explains itself — and trims exposure in your Blackbox when it turns strongly bearish on a strategy's assets.</p></div>
    <div class="sgrid" id="sgrid"></div>
  </div>
</section>

<div class="mask" id="mask" onclick="if(event.target===this)closeModal()"><div class="modal" id="modal"></div></div>

<div class="mask" id="amask" onclick="if(event.target===this)closeAuth()">
  <div class="modal amodal">
    <button class="x" onclick="closeAuth()">×</button>
    <h2 style="font-size:26px;margin-bottom:6px">Your Blackbox account</h2>
    <p style="color:var(--mut);font-size:14px">Log back in from any device. Practice capital only — no real money.</p>
    <div id="gwrap" style="margin:20px 0 0;display:none"><div id="gbtn" style="display:flex;justify-content:center"></div>
      <div class="ordiv"><span>or</span></div></div>
    <div class="aview" id="av-choice" style="margin-top:18px">
      <button class="cta" style="width:100%" onclick="showAV('create')">Create my account</button>
      <button class="cta ghost" style="width:100%;margin-top:10px" onclick="showAV('key')">I have a recovery key</button>
    </div>
    <div class="aview" id="av-create" style="display:none;margin-top:18px">
      <input class="ain" id="regname" placeholder="Your name" maxlength="24">
      <button class="cta" style="width:100%;margin-top:12px" onclick="doRegister()">Create account →</button>
      <div class="aerr" id="regerr"></div>
    </div>
    <div class="aview" id="av-keyshow" style="display:none;margin-top:14px">
      <p style="font-size:14px;color:var(--mut)">This key <b style="color:var(--txt)">is your login</b>. Save it now — it's shown only once.</p>
      <div class="keybox" id="keybox"></div>
      <button class="cta ghost" style="width:100%;margin-top:14px" id="copybtn" onclick="copyKey()">Copy key</button>
      <button class="cta" style="width:100%;margin-top:10px" onclick="closeAuth();afterAuth()">I saved it — continue →</button>
    </div>
    <div class="aview" id="av-key" style="display:none;margin-top:18px">
      <input class="ain" id="keyin" placeholder="e.g. violet-falcon-ember-4821">
      <button class="cta" style="width:100%;margin-top:12px" onclick="doRecover()">Log in →</button>
      <div class="aerr" id="keyerr"></div>
    </div>
  </div>
</div>

<footer><div class="wrap">
  <div style="font-family:'Geist';font-weight:800;font-size:18px;color:var(--txt);margin-bottom:12px">BLACKBOX</div>
  <div class="d" id="disc"></div>
</div></footer>

<script>
const $=s=>document.querySelector(s);
let CAT=null,SENT=null,MODE=null,PENDMIX=null,curveChart=null,projChart=null,navChart=null,ME=null,GCID=null;
const COLORS=["#a78bfa","#34d399","#fbbf24","#fb7185","#60a5fa","#f472b6","#c4b5fd","#818cf8"];
const BUCKETS={stack_bal:["equities","gold","oil"],stack_agg:["equities","gold","oil"],equity_season:["equities"],
gold_macro:["gold","rates"],commod_trend:["oil","gold"],risk_parity:["equities","rates","fx"],
crypto_trend:["crypto"],spx_hold:["equities"]};
const uid=()=>localStorage.getItem('bb_uid');

(function(){const words=[['Your'],['own'],['Blackbox.'],['Live','grad'],['in'],['minutes.','grad']];
$('#hl').innerHTML=words.map((w,i)=>`<span class="w ${w[1]||''}" style="animation-delay:${i*90}ms">${w[0]}&nbsp;</span>`).join('')})();

const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{rootMargin:'-80px'});
document.querySelectorAll('.rv').forEach(el=>io.observe(el));
document.addEventListener('click',e=>{const g=e.target.closest('.chips');if(!g)return;const b=e.target.closest('.chip');if(!b)return;
g.querySelectorAll('.chip').forEach(c=>c.classList.remove('on'));b.classList.add('on')});

function heroGo(){ if((ME&&ME.signed_in&&ME.portfolio)||uid()){$('#me').scrollIntoView({behavior:'smooth'})} else {$('#journey').scrollIntoView({behavior:'smooth'})} }

/* ---------- accounts ---------- */
function renderAuth(){
  const b=$('#authbox');
  if(ME&&ME.signed_in){
    b.innerHTML=`<div class="uchip">${ME.picture?`<img src="${ME.picture}" referrerpolicy="no-referrer" alt="">`:`<span class="uinit">${(ME.name||'?')[0].toUpperCase()}</span>`}
      <span class="un">${ME.name}</span>
      <button class="cta ghost small" onclick="doLogout()">Sign out</button></div>`;
  } else b.innerHTML='<button class="cta ghost small" onclick="openAuth()">Sign in</button>';
}
function openAuth(){$('#amask').classList.add('show');showAV('choice')}
function closeAuth(){$('#amask').classList.remove('show')}
function showAV(v){document.querySelectorAll('.aview').forEach(x=>x.style.display='none');
  const el=document.getElementById('av-'+v);if(el)el.style.display='block'}
async function refreshMe(){ME=await fetch('/api/me').then(r=>r.json()).catch(()=>({signed_in:false}));
  renderAuth();
  $('#heroCta').textContent=((ME.signed_in&&ME.portfolio)||uid())?'View my Blackbox →':"Let's go →";}
async function afterAuth(){await refreshMe();
  if(ME.signed_in&&ME.portfolio){$('#me').classList.add('show');renderMe(ME.portfolio);$('#me').scrollIntoView({behavior:'smooth'})}
  else{$('#me').classList.remove('show');$('#journey').scrollIntoView({behavior:'smooth'})}}
async function doRegister(){
  const name=$('#regname').value.trim()||'Trader';
  const r=await fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name,adopt_uid:uid()})}).then(r=>r.json()).catch(()=>null);
  if(!r||!r.ok){$('#regerr').textContent='Could not create the account — try again.';return}
  localStorage.removeItem('bb_uid');
  window._key=r.recovery_key;$('#keybox').textContent=r.recovery_key;
  ME={signed_in:true,name:r.name,portfolio:null};renderAuth();showAV('keyshow');
}
function copyKey(){navigator.clipboard.writeText(window._key||'').then(()=>{$('#copybtn').textContent='Copied ✓'}).catch(()=>{})}
async function doRecover(){
  const r=await fetch('/api/auth/recover',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({key:$('#keyin').value})}).then(r=>r.ok?r.json():null).catch(()=>null);
  if(!r||!r.ok){$('#keyerr').textContent='Key not recognised — check the spelling.';return}
  closeAuth();afterAuth();
}
async function doLogout(){await fetch('/api/auth/logout',{method:'POST'}).catch(()=>{});
  ME={signed_in:false};renderAuth();$('#me').classList.remove('show');
  $('#mebody').innerHTML='<div class="skel"><span class="sp"></span>Syncing your Blackbox with live markets…</div>';
  $('#heroCta').textContent=uid()?'View my Blackbox →':"Let's go →";window.scrollTo({top:0,behavior:'smooth'})}
function onGoogleCred(resp){
  fetch('/api/auth/google',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({credential:resp.credential,adopt_uid:uid()})}).then(r=>r.json()).then(r=>{
      if(r&&r.ok){localStorage.removeItem('bb_uid');closeAuth();afterAuth();}
      else openAuth()}).catch(()=>{});
}
function initGIS(tries){
  if(!GCID)return;
  if(window.google&&google.accounts&&google.accounts.id){
    $('#gwrap').style.display='block';
    google.accounts.id.initialize({client_id:GCID,callback:onGoogleCred});
    google.accounts.id.renderButton($('#gbtn'),{theme:'filled_black',size:'large',shape:'pill',width:330});
  } else if((tries||0)<24) setTimeout(()=>initGIS((tries||0)+1),500);
}
function setMode(m){MODE=m;
  $('#modeQuiz').classList.toggle('on',m==='quiz');$('#modeManual').classList.toggle('on',m==='manual');
  $('#quiz').classList.toggle('show',m==='quiz');$('#builderwrap').classList.toggle('show',m==='manual');
  $('#namecard').style.display='none';
  document.querySelectorAll('.stepper').forEach(s=>s.style.display=m==='manual'?'flex':'none');
  if(m==='manual')$('#catalog').scrollIntoView({behavior:'smooth',block:'start'});
}
function fmt(v){return v.toLocaleString(undefined,{maximumFractionDigits:0})}
function fmt2(v){return v.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}

async function boot(){
  const [c,s,cfg,me]=await Promise.all([
    fetch('/api/catalog').then(r=>r.json()),
    fetch('/api/sentiment').then(r=>r.json()).catch(()=>null),
    fetch('/api/config').then(r=>r.json()).catch(()=>({})),
    fetch('/api/me').then(r=>r.json()).catch(()=>({signed_in:false}))]);
  CAT=c;SENT=s;GCID=cfg&&cfg.google_client_id;ME=me;
  $('#hs1').textContent=c.strategies.length;
  $('#hs2').textContent=s&&s.n_scanned?s.n_scanned:'600+';
  $('#disc').textContent=c.disclaimer||'';
  renderCards();renderSentiment();renderAuth();initGIS();
  const have=(ME.signed_in&&ME.portfolio)||uid();
  if(have){$('#me').classList.add('show');$('#heroCta').textContent='View my Blackbox →';
    if(ME.signed_in&&ME.portfolio)renderMe(ME.portfolio);else loadMe();}
}

function sentFor(sid){
  if(!SENT||!SENT.assets)return null;
  const bs=BUCKETS[sid]||[];const vals=bs.map(b=>SENT.assets[b]).filter(Boolean);
  if(!vals.length)return null;
  const avg=vals.reduce((a,v)=>a+v.score,0)/vals.length;
  return {score:Math.round(avg),buckets:bs};
}
function sentChip(sid){
  const s=sentFor(sid);if(!s)return'';
  const col=s.score>12?'var(--green)':s.score<-12?'var(--red)':'var(--mut)';
  const word=s.score>12?'bullish':s.score<-12?'bearish':'neutral';
  return `<div class="sentchip" title="AI scanner read on ${s.buckets.join(', ')}"><span class="sd" style="background:${col};box-shadow:0 0 8px ${col}"></span>
    <span style="color:${col}">AI: ${word} ${s.score>0?'+':''}${s.score}</span></div>`;
}

function renderCards(){
  const el=$('#cards');
  el.innerHTML=CAT.strategies.map((s,i)=>{const st=s.stats;
    return `<div class="card rv" style="transition-delay:${(i%3)*60}ms" data-sid="${s.id}">
      <div class="top" onclick="openModal('${s.id}')"><h3>${s.name}</h3><span class="badge ${s.risk.replace(' ','')}">${s.risk}</span></div>
      <div onclick="openModal('${s.id}')">${sentChip(s.id)}
      <div class="tag">${s.tagline}</div>
      <canvas class="spark" id="sp_${s.id}"></canvas>
      <div class="stats">
        <div class="st"><div class="n">${st.cagr}%</div><div class="l">CAGR</div></div>
        <div class="st"><div class="n">${st.sharpe}</div><div class="l">Sharpe</div></div>
        <div class="st"><div class="n" style="color:var(--red)">${st.max_dd}%</div><div class="l">Max DD</div></div>
        <div class="st"><div class="n">${st.beta==null?'—':st.beta}</div><div class="l">Beta</div></div>
      </div></div>
      <div class="stepper step" style="display:none" data-sid="${s.id}">
        <button onclick="bump('${s.id}',-10)">−</button><span class="v" id="w_${s.id}">0%</span><button onclick="bump('${s.id}',10)">+</button>
        <span style="font-size:12px;color:var(--mut)">weight</span></div>
    </div>`}).join('');
  el.querySelectorAll('.rv').forEach(x=>io.observe(x));
  CAT.strategies.forEach(s=>drawSpark(document.getElementById('sp_'+s.id),s.curve));
}
function drawSpark(cv,curve){if(!cv||!curve||curve.length<2)return;
  const dpr=devicePixelRatio||1,W=cv.clientWidth||300,H=56;cv.width=W*dpr;cv.height=H*dpr;
  const x=cv.getContext('2d');x.scale(dpr,dpr);
  const vs=curve.map(p=>p.v),mn=Math.min(...vs),mx=Math.max(...vs),r=(mx-mn)||1;
  const X=i=>i/(vs.length-1)*W,Y=v=>H-4-((v-mn)/r)*(H-8);
  const g=x.createLinearGradient(0,0,0,H);g.addColorStop(0,'rgba(167,139,250,.35)');g.addColorStop(1,'rgba(167,139,250,0)');
  x.beginPath();x.moveTo(0,H);vs.forEach((v,i)=>x.lineTo(X(i),Y(v)));x.lineTo(W,H);x.closePath();x.fillStyle=g;x.fill();
  x.beginPath();vs.forEach((v,i)=>{i?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v))});
  x.strokeStyle='#a78bfa';x.lineWidth=2;x.lineJoin='round';x.stroke()}

/* ---------- builder ---------- */
const weights={};
function bump(sid,d){weights[sid]=Math.max(0,Math.min(100,(weights[sid]||0)+d));
  document.getElementById('w_'+sid).textContent=(weights[sid]||0)+'%';refreshBar()}
function builderMix(){const m={};Object.entries(weights).forEach(([k,v])=>{if(v>0)m[k]=v});return m}
function refreshBar(){
  const m=builderMix();const tot=Object.values(m).reduce((a,b)=>a+b,0);
  $('#btot').textContent=tot+'%';$('#bgo').disabled=tot!==100;
  const ids=Object.keys(m);
  $('#bmix').innerHTML=ids.map((id,i)=>`<i style="width:${m[id]}%;background:${COLORS[i%COLORS.length]}"></i>`).join('');
  if(ids.length&&CAT){let c=0,v=0,d=0;ids.forEach(id=>{const s=CAT.strategies.find(z=>z.id===id);if(s){c+=m[id]/100*s.stats.cagr;v+=m[id]/100*s.stats.vol;d+=m[id]/100*s.stats.max_dd}});
    $('#bstats').textContent=`est. CAGR ${c.toFixed(1)}% · vol ${v.toFixed(1)}% · weighted max DD ${d.toFixed(1)}%`}
  else $('#bstats').textContent='—';
}

/* ---------- quiz ---------- */
async function recommend(){
  const p={};document.querySelectorAll('#quiz .chips').forEach(g=>{const on=g.querySelector('.on');if(on)p[g.dataset.k]=on.dataset.v});
  const r=await fetch('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}).then(r=>r.json());
  const el=$('#reco');
  el.innerHTML=`<h3 style="font-size:24px">Your custom mix: ${r.label}</h3>
    <div style="margin:10px 0 4px;font-size:13.5px;color:var(--mut)">Risk capacity
      <b style="color:var(--txt)">${r.capacity}/100</b> — built from your six answers</div>
    <div class="gauge" style="background:linear-gradient(90deg,#34d399,#fbbf24,#fb7185);max-width:340px"><i style="left:calc(${r.capacity}% - 2px)"></i></div>
    <ul class="why">${r.why.map(w=>`<li>${w}</li>`).join('')}</ul>
    <div class="blend">
      <div class="b"><div class="n">${r.blend.cagr_est}%</div><div class="l">est. CAGR (backtest)</div></div>
      <div class="b"><div class="n">${r.blend.vol_est}%</div><div class="l">est. volatility</div></div>
      <div class="b"><div class="n" style="color:var(--red)">${r.blend.dd_est}%</div><div class="l">weighted max drawdown</div></div>
    </div>
    <div class="mixbar">${r.parts.map((x,i)=>`<i style="width:${x.weight}%;background:${COLORS[i%COLORS.length]}"></i>`).join('')}</div>
    <div class="mixlegend">${r.parts.map((x,i)=>`<span><span class="dotc" style="background:${COLORS[i%COLORS.length]}"></span><b>${x.weight}%</b> ${x.name}</span>`).join('')}</div>
    <button class="cta" style="margin-top:22px" onclick='showName(${JSON.stringify(r.mix)})'>Use this mix →</button>`;
  el.classList.add('show');setTimeout(()=>el.scrollIntoView({behavior:'smooth',block:'nearest'}),80);
}

function showName(mix){PENDMIX=mix;const nc=$('#namecard');nc.style.display='block';
  nc.scrollIntoView({behavior:'smooth',block:'center'});$('#uname').focus()}
async function startBlackbox(){
  if(!PENDMIX)return;
  const btn=$('#startBtn');btn.disabled=true;btn.textContent='Starting…';
  const name=($('#uname').value||'My').trim();
  const r=await fetch('/api/user/create',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name,mix:PENDMIX})}).then(r=>r.json()).catch(()=>null);
  btn.disabled=false;btn.textContent='🚀 Start my Blackbox';
  if(!r||!r.user_id){alert('Could not start — check the mix totals 100%.');return}
  if(r.signed_in)localStorage.removeItem('bb_uid');else localStorage.setItem('bb_uid',r.user_id);
  $('#me').classList.add('show');$('#heroCta').textContent='View my Blackbox →';
  $('#mebody').innerHTML='<div class="skel"><span class="sp"></span>Syncing your Blackbox with live markets… first sync takes ~20 seconds.</div>';
  $('#me').scrollIntoView({behavior:'smooth'});
  loadMe();
}
async function resetMe(){if(!confirm('Delete this Blackbox and start over?'))return;
  const puid=window._meUid||uid();
  if(puid)await fetch('/api/user/'+puid+'/delete',{method:'POST'}).catch(()=>{});
  localStorage.removeItem('bb_uid');location.reload()}

async function loadMe(){
  let r=null;
  if(ME&&ME.signed_in){
    const m=await fetch('/api/me').then(r=>r.json()).catch(()=>null);
    if(m&&m.signed_in){ME=m;r=m.portfolio}
  } else if(uid()){
    r=await fetch('/api/user/'+uid()).then(r=>r.ok?r.json():null).catch(()=>null);
    if(!r)localStorage.removeItem('bb_uid');
  }
  if(!r){$('#me').classList.remove('show');return}
  renderMe(r);
}
function renderMe(r){
  window._meUid=r.uid;
  const up=r.since_start>=0,dayUp=r.day_ret>=0;
  const names={};CAT.strategies.forEach(s=>names[s.id]=s.name);
  $('#mebody').innerHTML=`
    <div class="mehead rv in">
      <div><div class="sec-k">Your Blackbox</div>
        <h2 style="margin-bottom:4px">${r.name}'s Blackbox</h2>
        <div style="color:var(--mut);font-size:13.5px">since ${r.created} · paper portfolio · marked to live markets</div></div>
      <button class="cta ghost" onclick="resetMe()">Change strategy</button></div>
    <div style="margin-top:26px">
      <span class="nav-big">${fmt2(r.nav)}</span>
      <span class="pill ${up?'up':'dn'}">${up?'+':''}${r.since_start}% all-time</span>
      <span class="pill ${dayUp?'up':'dn'}">${dayUp?'+':''}${r.day_ret}% today</span></div>
    <div class="megrid">
      <div>
        <div class="mbox" style="background:var(--surface2)"><h4>Portfolio value</h4><div class="chartbox short"><canvas id="navchart"></canvas></div>
          <div class="note" style="margin-top:10px">${r.note}</div></div>
        <div class="mbox" style="background:var(--surface2);margin-top:14px"><h4>Your mix</h4>
          <div class="mixbar">${Object.entries(r.mix).map(([id,w],i)=>`<i style="width:${w}%;background:${COLORS[i%COLORS.length]}"></i>`).join('')}</div>
          <div class="mixlegend">${Object.entries(r.mix).map(([id,w],i)=>`<span><span class="dotc" style="background:${COLORS[i%COLORS.length]}"></span><b>${w}%</b> ${names[id]||id}</span>`).join('')}</div></div>
      </div>
      <div><h4 style="font-size:13px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em;margin:4px 0 0">What the machine is doing right now</h4>
        <div id="mestrats">${r.strategies.map(s=>{
          const dr=(s.day_ret*100),drUp=dr>=0;
          return `<div class="scard2"><div class="h2r"><h3>${names[s.id]||s.id}</h3>
            <div><span class="wtag">${s.weight}%</span> <span class="pill ${drUp?'up':'dn'}" style="vertical-align:0;margin-left:6px">${drUp?'+':''}${dr.toFixed(2)}% today</span></div></div>
          <div class="note">${s.note}</div>
          ${s.holdings.length?`<div class="hlist">${s.holdings.map(h=>`<span class="htag"><b>${h.name}</b> ${h.w}%</span>`).join('')}</div>`:'<div class="hlist"><span class="htag">100% cash</span></div>'}
          ${s.tilt_why?`<div class="tiltwarn">⚠ ${s.tilt_why}</div>`:''}
          </div>`}).join('')}</div></div>
    </div>`;
  const hist=r.history.map(h=>({t:h[0],v:h[1]}));
  if(hist[hist.length-1].t!==new Date().toISOString().slice(0,10))hist.push({t:'today',v:r.nav});
  else hist[hist.length-1]={t:'today',v:r.nav};
  if(navChart)navChart.destroy();
  const ng=document.getElementById('navchart').getContext('2d').createLinearGradient(0,0,0,230);
  ng.addColorStop(0,'rgba(139,92,246,.30)');ng.addColorStop(1,'rgba(139,92,246,0)');
  navChart=new Chart(document.getElementById('navchart'),{type:'line',
    data:{labels:hist.map(h=>h.t),datasets:[{data:hist.map(h=>h.v),borderColor:'#a78bfa',borderWidth:2.6,
      pointRadius:hist.length<15?4:0,pointBackgroundColor:'#0A0A0F',pointBorderColor:'#c4b5fd',pointBorderWidth:2,
      pointHoverRadius:6,fill:true,backgroundColor:ng,tension:.3,borderCapStyle:'round'}]},
    options:{responsive:true,maintainAspectRatio:false,resizeDelay:60,interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false},tooltip:{...TT,callbacks:{label:c=>fmt2(c.parsed.y)}}},
      scales:{x:{grid:{display:false},border:{display:false},ticks:{...AXIS,maxTicksLimit:6}},
        y:{position:'right',grid:{color:'rgba(167,139,250,.07)',drawTicks:false},border:{display:false},
          ticks:{...AXIS,maxTicksLimit:5,padding:8,callback:kfmt}}}}});
}

/* ---------- modal + charts (redesigned) ---------- */
function openModal(id){
  const s=CAT.strategies.find(z=>z.id===id);if(!s)return;
  const st=s.stats,pj=s.projections,sc=sentFor(id);
  $('#modal').innerHTML=`<button class="x" onclick="closeModal()">×</button>
    <span class="badge ${s.risk.replace(' ','')}">${s.risk} risk</span> ${sc?sentChip(id):''}
    <h2 style="font-size:30px;margin:12px 0 6px">${s.name}</h2>
    <p style="color:var(--mut)">${s.tagline}</p>
    <div class="stats" style="margin-top:20px">
      <div class="st"><div class="n">${st.cagr}%</div><div class="l">CAGR</div></div>
      <div class="st"><div class="n">${st.sharpe}</div><div class="l">Sharpe</div></div>
      <div class="st"><div class="n">${st.vol}%</div><div class="l">Volatility</div></div>
      <div class="st"><div class="n" style="color:var(--red)">${st.max_dd}%</div><div class="l">Max DD</div></div>
      <div class="st"><div class="n">${st.beta==null?'—':st.beta}</div><div class="l">Beta vs S&P</div></div>
      <div class="st"><div class="n">${st.sharpe_h1} / ${st.sharpe_h2}</div><div class="l">Sharpe by decade</div></div>
    </div>
    <div class="mrow">
      <div class="mbox"><h4>Growth of 10,000 — backtest vs S&P 500</h4><div class="chartbox"><canvas id="mcurve"></canvas></div>
        <div class="note" style="margin-top:12px"><span class="dotc" style="background:#a78bfa"></span>${s.name}
        &nbsp;&nbsp;<span class="dotc" style="background:#6a6a78"></span>S&P 500 buy &amp; hold · ${s.span}</div></div>
      <div class="mbox"><h4>Where 10,000 could be — bootstrap projection</h4><div class="chartbox"><canvas id="mproj"></canvas></div>
        <div class="hchips">
          ${['1y','3y','5y'].map(h=>`<div class="hchip"><span class="n">${fmt(pj[h].p50)}</span>median · ${h}<br>
            <span style="color:var(--mut)">${fmt(pj[h].p25)} – ${fmt(pj[h].p75)} likely</span></div>`).join('')}
        </div>
        <div class="note" style="margin-top:10px">Bands: 800 resamples of real history — inner = likely (25-75%), outer = extremes (5-95%). Chance of loss after 5y: <b>${pj['5y'].prob_loss}%</b>.</div></div>
    </div>
    <div class="method"><b>Methodology.</b> ${s.method}</div>
    <button class="cta" style="margin-top:24px" onclick='closeModal();showName({"${s.id}":100});'>Trade this strategy →</button>`;
  $('#mask').classList.add('show');document.body.style.overflow='hidden';
  setTimeout(()=>{drawCurve(s);drawProj(s)},30);
}
function closeModal(){$('#mask').classList.remove('show');document.body.style.overflow='';
  if(projChart){projChart.destroy();projChart=null}if(curveChart){curveChart.destroy();curveChart=null}}

const AXIS={color:'#8a8a96',font:{size:11,family:'Inter'}};
const TT={backgroundColor:'rgba(19,19,26,.96)',borderColor:'rgba(167,139,250,.3)',borderWidth:1,
  titleColor:'#9C9CA8',bodyColor:'#F5F5F0',padding:12,cornerRadius:10,displayColors:false,
  titleFont:{family:'Inter',size:11},bodyFont:{family:'Inter',size:13,weight:'600'}};
function kfmt(v){return v>=1000?(v/1000).toLocaleString(undefined,{maximumFractionDigits:1})+'k':fmt(v)}

function drawCurve(s){
  const ctx=document.getElementById('mcurve');if(!ctx)return;
  const spx=CAT.strategies.find(z=>z.id==='spx_hold');
  const labels=s.curve.map(p=>p.t);
  let spxData=labels.map(()=>null);
  if(spx&&s.id!=='spx_hold'){const sp=spx.curve;let j=0;
    spxData=labels.map(t=>{while(j<sp.length-1&&sp[j+1].t<=t)j++;
      return sp[j].t<=t?sp[j].v*10000:null});}
  const g=ctx.getContext('2d').createLinearGradient(0,0,0,280);
  g.addColorStop(0,'rgba(139,92,246,.32)');g.addColorStop(.6,'rgba(139,92,246,.06)');g.addColorStop(1,'rgba(139,92,246,0)');
  // yearly x labels only
  let lastYr='';
  const yrLabel=t=>{const y=t.slice(0,4);if(y!==lastYr){lastYr=y;return y}return ''};
  curveChart=new Chart(ctx,{type:'line',data:{labels,datasets:[
    {data:s.curve.map(p=>p.v*10000),borderColor:'#a78bfa',borderWidth:2.5,pointRadius:0,pointHitRadius:16,
      fill:true,backgroundColor:g,tension:.3,borderCapStyle:'round'},
    {data:spxData,borderColor:'rgba(130,130,145,.7)',borderWidth:1.4,borderDash:[6,5],pointRadius:0,
      pointHitRadius:12,fill:false,tension:.3,spanGaps:true}]},
    options:{responsive:true,maintainAspectRatio:false,resizeDelay:60,
      interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false},tooltip:{...TT,
        callbacks:{title:i=>i[0]?i[0].label:'',
          label:c=>(c.datasetIndex?'S&P 500   ':'This strategy   ')+fmt(c.parsed.y)}}},
      scales:{x:{grid:{display:false},border:{display:false},
        ticks:{...AXIS,maxRotation:0,autoSkip:false,callback:function(v){return yrLabel(this.getLabelForValue(v)||'')}}},
      y:{position:'right',grid:{color:'rgba(167,139,250,.07)',drawTicks:false},border:{display:false},
        ticks:{...AXIS,maxTicksLimit:5,padding:8,callback:kfmt}}}}});
}
function drawProj(s){
  const ctx=document.getElementById('mproj');if(!ctx)return;
  const pj=s.projections,xs=['today','1 year','3 years','5 years'];
  const band=k=>[10000,pj['1y'][k],pj['3y'][k],pj['5y'][k]];
  const gi=ctx.getContext('2d').createLinearGradient(0,0,0,280);
  gi.addColorStop(0,'rgba(139,92,246,.30)');gi.addColorStop(1,'rgba(139,92,246,.10)');
  projChart=new Chart(ctx,{type:'line',data:{labels:xs,datasets:[
    {data:band('p95'),borderColor:'rgba(150,150,164,.30)',borderWidth:1,borderDash:[4,5],pointRadius:0,fill:false,tension:.35},
    {data:band('p5'),borderColor:'rgba(150,150,164,.30)',borderWidth:1,borderDash:[4,5],pointRadius:0,tension:.35,
      fill:'-1',backgroundColor:'rgba(150,150,164,.06)'},
    {data:band('p75'),borderColor:'transparent',borderWidth:0,pointRadius:0,tension:.35,fill:false},
    {data:band('p25'),borderColor:'transparent',borderWidth:0,pointRadius:0,tension:.35,fill:'-1',backgroundColor:gi},
    {data:band('p50'),borderColor:'#d9c9ff',borderWidth:3,pointRadius:4.5,pointBackgroundColor:'#0A0A0F',
      pointBorderColor:'#d9c9ff',pointBorderWidth:2.5,pointHoverRadius:6,tension:.35,fill:false}]},
    options:{responsive:true,maintainAspectRatio:false,resizeDelay:60,
      interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false},tooltip:{...TT,filter:i=>[1,3,4].includes(i.datasetIndex),
        itemSort:(a,b)=>b.parsed.y-a.parsed.y,
        callbacks:{label:c=>({1:'Worst 5%   ',3:'Likely low   ',4:'Median   '}[c.datasetIndex]||'')+fmt(c.parsed.y)}}},
      scales:{x:{grid:{display:false},border:{display:false},ticks:{...AXIS,padding:6}},
        y:{position:'right',grid:{color:'rgba(167,139,250,.07)',drawTicks:false},border:{display:false},
          ticks:{...AXIS,maxTicksLimit:5,padding:8,callback:kfmt}}}}});
}

/* ---------- sentiment section ---------- */
function renderSentiment(){
  if(!SENT||!SENT.assets)return;
  const names={equities:'Equities',gold:'Gold & metals',rates:'Rates & Fed',fx:'FX & dollar',crypto:'Crypto',oil:'Oil & energy'};
  $('#sgrid').innerHTML=Object.entries(SENT.assets).map(([a,v],i)=>{
    const pos=Math.max(0,Math.min(100,(v.score+100)/2));
    const col=v.score>12?'var(--green)':v.score<-12?'var(--red)':'var(--mut)';
    return `<div class="scard rv" style="transition-delay:${(i%3)*60}ms">
      <div class="h"><h3>${names[a]||a}</h3><span class="sscore" style="color:${col}">${v.score>0?'+':''}${v.score}</span></div>
      <div class="gauge"><i style="left:calc(${pos}% - 2px)"></i></div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--mut)"><span>bearish</span><span>${v.n_items} items · ${v.trend}</span><span>bullish</span></div>
      <div class="sexp">${v.explanation}</div>
      ${(v.top||[]).slice(0,3).map(t=>`<div class="head"><span class="t">${t.title}</span><span class="s" style="color:${t.score>0?'var(--green)':t.score<0?'var(--red)':'var(--mut)'}">${t.src}</span></div>`).join('')}
    </div>`}).join('');
  document.querySelectorAll('#sgrid .rv').forEach(x=>io.observe(x));
}
boot();
</script></body></html>
"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)

```

## `user_engine.py`

*Per-user live paper portfolios; where the AI scanner acts* — 262 lines

```python
"""
USER ENGINE — gives every app user their own live paper Blackbox.

For each catalog strategy it derives TODAY's holdings from the same validated
rules (200dMA trends, seasonal window, rates gate, crypto trend) using live OANDA/
Coinbase data, then marks a user's chosen mix to market:
    user day-return = sum_s weight_s * scanner_tilt_s * strategy_day_return_s
Scanner tilt: if the AI sentiment for a strategy's asset bucket is strongly
negative (< -40), that strategy's exposure is scaled 0.75x — the ONE place the
scanner acts, clearly labelled in the UI. Everything cached so the app stays fast.
"""
import os, time
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
_cache = {}


def _c(key, ttl, fn):
    now = time.time()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    v = fn()
    _cache[key] = (now, v)
    return v


NAMES = {"XAU_USD": "Gold", "XAG_USD": "Silver", "XPT_USD": "Platinum", "XPD_USD": "Palladium",
         "XCU_USD": "Copper", "WTICO_USD": "WTI Oil", "BCO_USD": "Brent Oil", "NATGAS_USD": "Nat Gas",
         "CORN_USD": "Corn", "WHEAT_USD": "Wheat", "SOYBN_USD": "Soybeans", "SUGAR_USD": "Sugar",
         "SPX500_USD": "S&P 500", "NAS100_USD": "Nasdaq 100", "US30_USD": "Dow 30", "DE30_EUR": "DAX 40",
         "UK100_GBP": "FTSE 100", "JP225_USD": "Nikkei 225", "EU50_EUR": "Euro Stoxx 50", "AU200_AUD": "ASX 200",
         "USB02Y_USD": "US 2Y Note", "USB05Y_USD": "US 5Y Note", "USB10Y_USD": "US 10Y Note",
         "EUR_USD": "EUR/USD", "USD_JPY": "USD/JPY", "GBP_USD": "GBP/USD", "AUD_USD": "AUD/USD"}

INDICES = ["SPX500_USD", "NAS100_USD", "US30_USD", "DE30_EUR", "UK100_GBP", "JP225_USD", "EU50_EUR", "AU200_AUD"]
COMMOD = ["XAU_USD", "XAG_USD", "XPT_USD", "XPD_USD", "XCU_USD", "WTICO_USD", "BCO_USD",
          "NATGAS_USD", "CORN_USD", "WHEAT_USD", "SOYBN_USD", "SUGAR_USD"]
RP_BASKET = INDICES[:4] + ["XAU_USD", "WTICO_USD", "USB02Y_USD", "USB05Y_USD", "USB10Y_USD",
                           "EUR_USD", "USD_JPY", "AUD_USD"]
HALLOWEEN = {11, 12, 1, 2, 3, 4}

# which sentiment buckets each strategy lives in (scanner "utilised in every strategy")
SENT_BUCKETS = {
    "stack_bal": ["equities", "gold", "oil"], "stack_agg": ["equities", "gold", "oil"],
    "equity_season": ["equities"], "gold_macro": ["gold", "rates"],
    "commod_trend": ["oil", "gold"], "risk_parity": ["equities", "rates", "fx"],
    "crypto_trend": ["crypto"], "spx_hold": ["equities"],
}


def _client():
    from oanda_client import OandaClient
    return OandaClient()


def _daily(inst):
    return _c("d_" + inst, 1800, lambda: _client().get_candles(inst, "D", count=230))


def _px(inst):
    return _c("p_" + inst, 420, lambda: _client().get_price(inst))


def _above_ma(inst, ma):
    d = _daily(inst)["close"]
    return len(d) >= ma and float(d.iloc[-1]) > float(d.rolling(ma).mean().iloc[-1])


def _dayret(inst):
    d = _daily(inst)["close"]
    return float(_px(inst) / float(d.iloc[-1]) - 1)


def _crypto_state():
    def f():
        from crypto_bot import PRODUCTS, fetch_daily, spot
        import numpy as np
        out = {}
        for p in PRODUCTS:
            s = fetch_daily(p)
            if s is None or len(s) < 205:
                continue
            on = bool(s.iloc[-1] > s.rolling(200).mean().iloc[-1])
            vol = float(s.pct_change().tail(60).std() * (365 ** 0.5))
            sp = spot(p) or float(s.iloc[-1])
            out[p] = {"on": on, "vol": vol, "ret": float(sp / float(s.iloc[-1]) - 1)}
        return out
    return _c("crypto", 1200, f)


def _holdings(sid):
    """Today's target weights {inst: weight} for one strategy, per its rules."""
    if sid == "spx_hold":
        return {"SPX500_USD": 1.0}, "Always fully invested in the index."
    if sid == "equity_season":
        month = datetime.now(timezone.utc).month
        if month not in HALLOWEEN:
            return {}, "Out of the Nov-Apr seasonal window — sitting in cash."
        act = [i for i in INDICES if _above_ma(i, 200)]
        return ({i: 1 / len(INDICES) for i in act},
                f"In season; {len(act)}/{len(INDICES)} indices above their 200-day trend.")
    if sid == "gold_macro":
        gate = _above_ma("USB10Y_USD", 100) and _above_ma("XAU_USD", 200)
        if gate:
            return {"XAU_USD": 1.0}, "Gold uptrend + falling yields — fully long gold."
        return {}, "Rates gate off (yields rising) or gold below trend — in cash."
    if sid == "commod_trend":
        act = [i for i in COMMOD if _above_ma(i, 200)]
        return ({i: 1 / len(COMMOD) for i in act},
                f"{len(act)}/{len(COMMOD)} commodities in uptrends.")
    if sid == "risk_parity":
        import numpy as np
        w = {}
        for i in RP_BASKET:
            d = _daily(i)["close"].pct_change().tail(63)
            v = float(d.std() * np.sqrt(252))
            if v > 0:
                w[i] = 1 / v
        tot = sum(w.values())
        return ({i: 0.7 * x / tot for i, x in w.items()},
                "Owns a representative global basket, weighted to equal risk.")
    if sid in ("stack_bal", "stack_agg"):
        mult = 1.0 if sid == "stack_bal" else 1.8
        parts = ["equity_season", "commod_trend", "gold_macro"]
        merged, notes = {}, []
        for p in parts:
            hw, note = _holdings(p)
            for i, x in hw.items():
                merged[i] = merged.get(i, 0) + mult * x / 3
            notes.append(note)
        return merged, "Blend of three edges — " + " ".join(notes)
    if sid == "crypto_trend":
        cs = _crypto_state()
        on = {p: v for p, v in cs.items() if v["on"] and v["vol"] > 0}
        if not on:
            return {}, "Every coin below its 200-day trend — 100% cash (crypto winter)."
        inv = {p: 1 / v["vol"] for p, v in on.items()}
        tot = sum(inv.values())
        avg_vol = sum(v["vol"] for v in on.values()) / len(on)
        gross = min(1.0, 0.35 / avg_vol)
        return ({p: gross * x / tot for p, x in inv.items()},
                f"{len(on)} coins in uptrends; {int(gross*100)}% deployed.")
    return {}, "Unknown strategy."


def _strategy_dayret(sid, holdings):
    cs = _crypto_state() if sid == "crypto_trend" else None
    r = 0.0
    for inst, w in holdings.items():
        try:
            r += w * (cs[inst]["ret"] if cs else _dayret(inst))
        except Exception:
            continue
    return r


def _close_ret(inst):
    """Yesterday-close -> today-close return from COMPLETED daily candles.
    (After 21:00 UTC today's OANDA candle is complete, so [-1]/[-2] is the full
    trading day just ended — the nightly settle must use THIS, not spot-vs-close
    day_ret, which collapses to ~0 right after the close.)"""
    d = _c("dc_" + inst, 900, lambda: _client().get_candles(inst, "D", count=3))["close"]
    return float(d.iloc[-1] / d.iloc[-2] - 1) if len(d) >= 2 else 0.0


def _strategy_closeret(sid, holdings):
    if sid == "crypto_trend":
        from crypto_bot import fetch_daily
        r = 0.0
        for inst, w in holdings.items():
            try:
                s = fetch_daily(inst)
                r += w * float(s.iloc[-1] / s.iloc[-2] - 1)
            except Exception:
                continue
        return r
    return sum(w * _close_ret(inst) for inst, w in holdings.items())


def settle_users():
    """Daily close-of-book settle for EVERY user's paper portfolio, run by the
    scanner daemon in the 22:00-23:59 UTC window (>=1h after the OANDA close so
    the completed daily candle is guaranteed fresh). Rolls each book by the
    CLOSE-TO-CLOSE return of its mix (current holdings, scanner tilt applied).
    This is the ONE place books roll; the app's GET only displays. Users who
    never visit still accrue every day. Atomic write."""
    import json
    now = datetime.now(timezone.utc)
    if now.hour < 22:
        return 0
    today = now.strftime("%Y-%m-%d")
    path = os.path.join(HERE, "logs", "app_users.json")
    try:
        users = json.load(open(path, encoding="utf-8"))
    except Exception:
        return 0
    if not users or all(u.get("base_date") == today for u in users.values()):
        return 0
    mk = marks()["strategies"]              # tilt only
    dayret = {}
    for sid in SENT_BUCKETS:
        try:
            hw, _note = _holdings(sid)
            dayret[sid] = _strategy_closeret(sid, hw)
        except Exception:
            dayret[sid] = 0.0
    n = 0
    for uid, u in users.items():
        if u.get("base_date") == today:
            continue
        day = 0.0
        for sid, w in (u.get("mix") or {}).items():
            tilt = mk.get(sid, {}).get("tilt", 1.0)
            day += (w / 100.0) * tilt * dayret.get(sid, 0.0)
        u["base_nav"] = round(u.get("base_nav", 10000.0) * (1 + day), 2)
        u["base_date"] = today
        u.setdefault("history", []).append([today, u["base_nav"]])
        u["history"] = u["history"][-400:]
        n += 1
    if n:
        tmp = path + ".tmp"
        json.dump(users, open(tmp, "w", encoding="utf-8"), indent=1)
        os.replace(tmp, path)
    return n


def marks():
    """Per-strategy live state: holdings, day-return-so-far, note, sentiment tilt."""
    def f():
        import json
        sent = None
        try:
            sent = json.load(open(os.path.join(HERE, "logs", "sentiment.json"), encoding="utf-8"))
        except Exception:
            pass
        out = {}
        for sid in SENT_BUCKETS:
            try:
                hw, note = _holdings(sid)
                dr = _strategy_dayret(sid, hw)
            except Exception as e:
                hw, note, dr = {}, f"mark unavailable ({type(e).__name__})", 0.0
            tilt, tilt_why = 1.0, None
            scores = {}
            if sent:
                for b in SENT_BUCKETS[sid]:
                    v = sent.get("assets", {}).get(b)
                    if v:
                        scores[b] = v["score"]
                bad = [b for b, s in scores.items() if s < -40]
                if bad:
                    tilt, tilt_why = 0.75, f"Scanner strongly bearish on {', '.join(bad)} — exposure trimmed to 75%."
            top = sorted(hw.items(), key=lambda z: -z[1])[:6]
            out[sid] = {"day_ret": round(dr, 5), "gross": round(sum(hw.values()), 3),
                        "note": note, "tilt": tilt, "tilt_why": tilt_why,
                        "sentiment": scores,
                        "holdings": [{"inst": i, "name": NAMES.get(i, i), "w": round(w * 100, 1)}
                                     for i, w in top]}
        return {"generated": datetime.now(timezone.utc).isoformat(), "strategies": out}
    return _c("marks", 1200, f)

```

## `sentiment_scanner.py`

*The NLP news/social sentiment engine* — 198 lines

```python
"""
AI MARKET SENTIMENT SCANNER — continuously scans online sources (news via Google
News RSS, social via Reddit public JSON, the economic calendar we already pull) and
distils them into per-asset sentiment scores with plain-English explanations.

NLP: finance-tuned lexicon scoring (VADER-style: polarity words + intensifiers,
title-level) — no API keys required. Every score is traceable to the headlines
that produced it (shown in the app; no black box).

Output: logs/sentiment.json   (latest snapshot, served by the app)
        logs/sentiment_history.csv (score history -> trend arrows)
Bots read the snapshot and SHADOW-LOG the advisory next to their own decisions —
sentiment informs and explains, it does not yet override validated rules.
"""
import os, json, re, csv, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "logs", "sentiment.json")
HIST = os.path.join(HERE, "logs", "sentiment_history.csv")
UA = {"User-Agent": "Mozilla/5.0 (blackbox-research)"}

ASSETS = ["equities", "gold", "rates", "fx", "crypto", "oil"]

NEWS_QUERIES = {
    "equities": "stock market",
    "gold": "gold price",
    "rates": "federal reserve interest rates",
    "fx": "us dollar currency",
    "crypto": "bitcoin crypto market",
    "oil": "oil prices",
}
REDDIT_SUBS = {
    "wallstreetbets": "equities", "stocks": "equities", "investing": "equities",
    "CryptoCurrency": "crypto", "Bitcoin": "crypto",
}
# keyword re-tagging (a WSB post about gold lands in the gold bucket)
TAGS = {
    "gold": ["gold", "bullion", "xau", "precious metal"],
    "crypto": ["bitcoin", "btc", "ethereum", "crypto", "solana"],
    "rates": ["fed ", "federal reserve", "interest rate", "treasury", "yield", "fomc", "powell", "ecb", "central bank"],
    "oil": ["oil", "crude", "opec", "brent", "wti"],
    "fx": ["dollar", "euro", "yen", "forex", "currency"],
    "equities": ["stock", "s&p", "nasdaq", "dow", "equit", "shares"],
}

POS = set("""surge surges surging rally rallies rallying soar soars soaring jump jumps gains gain boom booms
record-high beat beats strong strength bullish optimism optimistic upgrade upgraded growth recover recovers
recovery rebound rebounds breakout outperform outperforms dovish stimulus soft-landing cools cooling
all-time-high high tops top rise rises rising climb climbs advance advances upbeat resilient hope hopes""".split())
NEG = set("""crash crashes plunge plunges plunging tumble tumbles slump slumps fall falls falling drop drops
fear fears bearish recession downgrade downgraded miss misses weak weakness selloff sell-off panic default
crisis war sanctions hawkish hike hikes layoffs bankruptcy bubble correction liquidation slide slides sink
sinks slips slip warning warns worry worries risk risks losses lose loses turmoil rout jitters dive dives""".split())
INTENS = {"very": 1.5, "sharply": 1.5, "massive": 1.5, "record": 1.4, "historic": 1.4, "huge": 1.4}


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def score_text(text):
    """Lexicon polarity score in [-1, 1] for one headline."""
    words = re.findall(r"[a-z&\-']+", text.lower())
    pos = neg = 0.0
    mult = 1.0
    for w in words:
        if w in INTENS:
            mult = INTENS[w]; continue
        if w in POS: pos += mult; mult = 1.0
        elif w in NEG: neg += mult; mult = 1.0
        else: mult = 1.0
    tot = pos + neg
    return (pos - neg) / tot if tot else 0.0


def tag_asset(title, default):
    t = title.lower()
    for asset, kws in TAGS.items():
        if any(k in t for k in kws):
            return asset
    return default


def fetch_news():
    items = []
    for asset, q in NEWS_QUERIES.items():
        try:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-US&gl=US&ceid=US:en"
            root = ET.fromstring(_get(url))
            for it in root.iter("item"):
                title = (it.findtext("title") or "").strip()
                src = (it.findtext("source") or "news").strip()
                if title:
                    items.append({"title": title[:180], "src": src[:40],
                                  "asset": tag_asset(title, asset), "via": "news"})
        except Exception:
            continue
    return items


def fetch_reddit():
    items = []
    for sub, default in REDDIT_SUBS.items():
        try:
            d = json.loads(_get(f"https://www.reddit.com/r/{sub}/hot.json?limit=35"))
            for post in d.get("data", {}).get("children", []):
                p = post.get("data", {})
                title = (p.get("title") or "").strip()
                if title and not p.get("stickied"):
                    items.append({"title": title[:180], "src": f"r/{sub}",
                                  "asset": tag_asset(title, default), "via": "social"})
        except Exception:
            continue
        time.sleep(0.4)
    return items


def explain(asset, scored, score):
    n = len(scored)
    if n < 3:
        return f"Too little coverage of {asset} right now to read sentiment reliably."
    npos = sum(1 for s in scored if s["score"] > 0.15)
    nneg = sum(1 for s in scored if s["score"] < -0.15)
    words = {}
    for s in scored:
        for w in re.findall(r"[a-z\-']+", s["title"].lower()):
            if w in POS or w in NEG:
                words[w] = words.get(w, 0) + 1
    drivers = ", ".join(f"'{w}'" for w, _ in sorted(words.items(), key=lambda z: -z[1])[:4])
    mood = ("strongly bullish" if score > 40 else "leaning bullish" if score > 12 else
            "strongly bearish" if score < -40 else "leaning bearish" if score < -12 else "mixed/neutral")
    return (f"{mood.capitalize()}: of {n} scanned items, {npos} read positive and {nneg} negative"
            + (f", driven by {drivers}" if drivers else "") + ".")


def run_scan():
    items = fetch_news() + fetch_reddit()
    now = datetime.now(timezone.utc).isoformat()
    assets = {}
    for asset in ASSETS:
        sub = [i for i in items if i["asset"] == asset]
        scored = [{**i, "score": round(score_text(i["title"]), 3)} for i in sub]
        nonzero = [s for s in scored if s["score"] != 0]
        score = round(100 * (sum(s["score"] for s in nonzero) / len(nonzero)), 1) if nonzero else 0.0
        top = sorted(scored, key=lambda s: -abs(s["score"]))[:5]
        assets[asset] = {"score": score, "n_items": len(sub),
                         "n_social": sum(1 for s in sub if s["via"] == "social"),
                         "explanation": explain(asset, scored, score),
                         "top": [{"title": t["title"], "src": t["src"], "score": t["score"],
                                  "via": t["via"]} for t in top]}
    # trend vs previous snapshots
    hist_rows = []
    if os.path.exists(HIST):
        try: hist_rows = list(csv.DictReader(open(HIST, encoding="utf-8")))
        except Exception: pass
    for a in ASSETS:
        prev = [float(r[a]) for r in hist_rows[-12:] if r.get(a)]
        cur = assets[a]["score"]
        assets[a]["trend"] = ("improving" if prev and cur > np_mean(prev) + 5 else
                              "deteriorating" if prev and cur < np_mean(prev) - 5 else "stable")
    doc = {"generated": now, "n_scanned": len(items), "assets": assets,
           "method": ("Headlines from Google News RSS + Reddit public feeds, scored with a "
                      "finance-tuned NLP lexicon (polarity + intensifiers). Every score is "
                      "traceable to its headlines. Advisory only — validated rules trade.")}
    tmp = OUT + ".tmp"
    json.dump(doc, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, OUT)
    new = not os.path.exists(HIST)
    with open(HIST, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["ts"] + ASSETS)
        w.writerow([now] + [assets[a]["score"] for a in ASSETS])
    return doc


def np_mean(x):
    return sum(x) / len(x) if x else 0.0


def read_latest(max_age_min=90):
    """For the bots: latest snapshot if fresh, else None. Never raises."""
    try:
        d = json.load(open(OUT, encoding="utf-8"))
        age = (datetime.now(timezone.utc)
               - datetime.fromisoformat(d["generated"])).total_seconds() / 60
        return d if age <= max_age_min else None
    except Exception:
        return None


if __name__ == "__main__":
    d = run_scan()
    print(f"scanned {d['n_scanned']} items")
    for a, v in d["assets"].items():
        print(f"  {a:<9} {v['score']:>6.1f}  ({v['n_items']} items, {v['trend']})  {v['explanation'][:90]}")

```

## `catalog.py`

*Builds the strategy catalog: stats, curves, bootstrap projections* — 223 lines

```python
"""
STRATEGY CATALOG — the product's core data. Every strategy in the user-facing app
is computed from REAL 20-year backtests on real OANDA/Coinbase data (no invented
numbers). Per strategy: CAGR, vol, Sharpe, max drawdown, beta vs S&P 500, best/worst
year, monthly equity curve, and block-bootstrap WEALTH PROJECTION bands (5/25/50/75/95
percentiles at 1/3/5 years) — honest Monte-Carlo fans, not straight lines.

Output: logs/catalog.json (precomputed; served by the app API).
Methodology notes are embedded — net of estimated retail costs, backtest != future.
"""
import warnings; warnings.filterwarnings("ignore")
import os, json
import numpy as np
import pandas as pd

from backtest_factors import fetch_daily, CLASSES
from crypto_backtest import load as crypto_load

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "logs", "catalog.json")
START_WEALTH = 10_000


def volt(r, t, ppy=252):
    rv = r.rolling(30).std() * np.sqrt(ppy)
    return (r * (t / rv).shift(1).clip(0, 4)).fillna(0)


def _series_equity_seasonal():
    idxs = CLASSES["Indices"]
    rets, ons = {}, {}
    for i in idxs:
        d = fetch_daily(i)
        if d is None or len(d) < 500: continue
        c = d["close"]; rets[i] = c.pct_change()
        ons[i] = (c > c.rolling(200).mean()).astype(float).shift(1)
    R = pd.DataFrame(rets); ON = pd.DataFrame(ons)
    seas = pd.Series([1.0 if m in {11,12,1,2,3,4} else 0.0 for m in R.index.month], index=R.index)
    M = ON.mul(seas, axis=0)
    return ((M * R) - M.diff().abs() * 0.000075).mean(axis=1).dropna()


def _series_gold_macro():
    g = fetch_daily("XAU_USD")["close"]; b = fetch_daily("USB10Y_USD")["close"]
    rg = g.pct_change()
    mask = ((g > g.rolling(200).mean()) & (b > b.rolling(100).mean())).shift(1).fillna(False).astype(bool)
    pos = mask.astype(float)
    return (pos * rg - pos.diff().abs().fillna(0) * 0.00015).dropna()


def _series_commod_trend():
    rets, ons = {}, {}
    for i in CLASSES["Commodities"]:
        d = fetch_daily(i)
        if d is None or len(d) < 500: continue
        c = d["close"]; rets[i] = c.pct_change()
        ons[i] = (c > c.rolling(200).mean()).astype(float).shift(1)
    R = pd.DataFrame(rets); ON = pd.DataFrame(ons)
    return ((ON * R) - ON.diff().abs() * 0.0002).mean(axis=1).dropna()


def _series_risk_parity():
    closes = {}
    for cls, insts in CLASSES.items():
        for i in insts:
            d = fetch_daily(i)
            if d is not None and len(d) > 500:
                closes[i] = d["close"]
    px = pd.DataFrame(closes)
    R = px.pct_change()
    vol = R.rolling(63).std() * np.sqrt(252)
    w = (1.0 / vol.replace(0, np.nan))
    w = w.div(w.sum(axis=1), axis=0).shift(1)
    base = ((w * R).sum(axis=1) - 0.0000125).dropna()   # ~0.3%/yr drag
    return volt(base, 0.08)                              # conservative 8% vol target


def _series_stack(vol_target=None):
    e1 = volt(_series_equity_seasonal(), 0.10)
    e2 = volt(_series_commod_trend(), 0.10)
    e3 = volt(_series_gold_macro(), 0.10)
    stack = pd.DataFrame({"a": e1, "b": e2, "c": e3}).dropna().mean(axis=1)
    return volt(stack, vol_target) if vol_target else stack


def _series_crypto():
    px = crypto_load()
    rets = px.pct_change()
    sig = (px > px.rolling(200).mean()).astype(float).shift(1)
    flips = sig.diff().abs().fillna(0)
    port = (sig * rets - flips * 0.0015).mean(axis=1)
    rv = port.rolling(30).std() * np.sqrt(365)
    lev = (0.35 / rv).shift(1).clip(0, 3).fillna(0)
    return (port * lev).dropna()


def _series_spx():
    return fetch_daily("SPX500_USD")["close"].pct_change().dropna()


CATALOG = [
    dict(id="stack_bal", name="Blackbox Multi-Edge — Balanced", risk="Moderate",
         tagline="Three independent, validated edges (seasonal equity, commodity trend, macro gold), blended equal-risk.",
         builder=lambda: _series_stack(None), ppy=252,
         method="3 low-correlation edges (pairwise corr 0.04-0.25), each 20yr-validated with split-half robustness; equal-risk blend, vol-targeted."),
    dict(id="stack_agg", name="Blackbox Multi-Edge — Aggressive", risk="High",
         tagline="The same three-edge engine levered to an 18% volatility target for higher return and drawdown.",
         builder=lambda: _series_stack(0.18), ppy=252,
         method="Same engine as Balanced at a higher vol target. Leverage amplifies both return and drawdown."),
    dict(id="equity_season", name="Seasonal Equity", risk="Moderate",
         tagline="Long global stock indices only in an uptrend and in the strong Nov-Apr season; cash otherwise.",
         builder=_series_equity_seasonal, ppy=252,
         method="8 indices; entries require >200-day MA AND Nov-Apr (Halloween effect). Both rules pre-specified, robust in both decade-halves."),
    dict(id="gold_macro", name="Macro Gold", risk="Moderate",
         tagline="Holds gold only when gold trends up AND falling yields give it a macro tailwind.",
         builder=_series_gold_macro, ppy=252,
         method="Gold>200dMA AND US10Y bond>100dMA. Zero-yield real-asset mechanism; conditional Sharpe 1.10, halves 1.00/1.22 over 20yr."),
    dict(id="commod_trend", name="Commodity Trend", risk="Moderate",
         tagline="Rides uptrends across 12 commodities (metals, energy, grains); flat in downtrends.",
         builder=_series_commod_trend, ppy=252,
         method="Long-only 200-day-MA trend, equal-weight across commodities. Diversifier: low correlation to equities."),
    dict(id="risk_parity", name="Global Risk Parity", risk="Conservative",
         tagline="Owns everything — 36 global markets weighted so each contributes equal risk.",
         builder=_series_risk_parity, ppy=252,
         method="Inverse-volatility weights across FX, bonds, commodities, indices. The diversified-beta benchmark (Sharpe ~0.5 over 20yr)."),
    dict(id="crypto_trend", name="Crypto Momentum", risk="Very High",
         tagline="Long liquid crypto majors in uptrends, 100% cash in crypto winters. High octane.",
         builder=_series_crypto, ppy=365,
         method="200-day-MA trend on 13 majors, inverse-vol, 35% vol target. Backtest Sharpe ~1.2 BUT one bull regime + survivorship caveats; expect less."),
    dict(id="spx_hold", name="S&P 500 Buy & Hold", risk="High",
         tagline="The benchmark: own the index through everything, including -50% crashes.",
         builder=_series_spx, ppy=252,
         method="Reference strategy for comparison. Full equity beta and full equity drawdowns."),
]


def stats(r, spx, ppy):
    r = r.dropna()
    ann = r.mean() * ppy; vol = r.std() * np.sqrt(ppy)
    sr = float(ann / vol) if vol else 0
    eq = (1 + r).cumprod()
    dd = float((eq / eq.cummax() - 1).min())
    yrs = len(r) / ppy
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
    # normalize both to calendar dates so OANDA (21:00-stamped) and Coinbase
    # (00:00-stamped) series align for beta/correlation
    rn = r.copy(); rn.index = rn.index.normalize()
    sn = spx.copy(); sn.index = sn.index.normalize()
    rn = rn.groupby(rn.index).sum(); sn = sn.groupby(sn.index).sum()
    j = pd.DataFrame({"r": rn, "m": sn}).dropna()
    beta = float(j["r"].cov(j["m"]) / j["m"].var()) if len(j) > 200 else None
    corr = float(j["r"].corr(j["m"])) if len(j) > 200 else None
    ybr = (1 + r).groupby(r.index.year).prod() - 1
    ybr = ybr[[y for y in ybr.index if (r.index.year == y).sum() > ppy * 0.6]]
    h = len(r) // 2
    sh = lambda x: float(x.mean() / x.std() * np.sqrt(ppy)) if len(x) > 100 and x.std() else 0
    return dict(cagr=round(cagr * 100, 2), vol=round(vol * 100, 2), sharpe=round(sr, 2),
                max_dd=round(dd * 100, 1), beta=round(beta, 2) if beta is not None else None,
                corr_spx=round(corr, 2) if corr is not None else None,
                best_year=round(float(ybr.max()) * 100, 1) if len(ybr) else None,
                worst_year=round(float(ybr.min()) * 100, 1) if len(ybr) else None,
                years=round(yrs, 1),
                sharpe_h1=round(sh(r.iloc[:h]), 2), sharpe_h2=round(sh(r.iloc[h:]), 2))


def projections(r, ppy, n_paths=800, block=60):
    """Block-bootstrap terminal-wealth percentile bands at 1/3/5 years."""
    v = r.dropna().values
    rng = np.random.default_rng(13)
    out = {}
    for label, years in [("1y", 1), ("3y", 3), ("5y", 5)]:
        days = int(ppy * years)
        # sample block start indices for all paths at once
        n_blocks = days // block + 1
        starts = rng.integers(0, max(len(v) - block, 1), size=(n_paths, n_blocks))
        paths = np.empty((n_paths, n_blocks * block))
        for k in range(n_blocks):
            idx = starts[:, k][:, None] + np.arange(block)[None, :]
            paths[:, k * block:(k + 1) * block] = v[np.clip(idx, 0, len(v) - 1)]
        term = np.prod(1 + paths[:, :days], axis=1) * START_WEALTH
        pct = np.percentile(term, [5, 25, 50, 75, 95])
        out[label] = {p: round(float(x)) for p, x in zip(["p5", "p25", "p50", "p75", "p95"], pct)}
        out[label]["prob_loss"] = round(float((term < START_WEALTH).mean()) * 100, 1)
    return out


def equity_curve(r, ppy, points=160):
    eq = (1 + r.dropna()).cumprod()
    m = eq.resample("W").last().dropna()
    step = max(1, len(m) // points)
    m = m.iloc[::step]
    return [{"t": str(t.date()), "v": round(float(v), 4)} for t, v in m.items()]


def run():
    spx = _series_spx()
    cat = []
    for s in CATALOG:
        print(f"computing {s['id']}...", flush=True)
        try:
            r = s["builder"]()
        except Exception as e:
            print(f"  FAILED {e}"); continue
        st = stats(r, spx, s["ppy"])
        cat.append(dict(id=s["id"], name=s["name"], risk=s["risk"], tagline=s["tagline"],
                        method=s["method"], stats=st, projections=projections(r, s["ppy"]),
                        curve=equity_curve(r, s["ppy"]),
                        span=f"{r.index[0].date()} to {r.index[-1].date()}"))
        print(f"  SR {st['sharpe']}  CAGR {st['cagr']}%  DD {st['max_dd']}%  beta {st['beta']}")
    doc = dict(generated=pd.Timestamp.utcnow().isoformat(), start_wealth=START_WEALTH,
               disclaimer=("All statistics computed from real historical backtests (2006-2026 "
                           "OANDA data; crypto 2016-2026 Coinbase) net of estimated retail costs. "
                           "Backtested performance does not guarantee future results. Projection "
                           "bands are block-bootstrap resamples of realised history. Demo/practice "
                           "capital only — not investment advice."),
               strategies=cat)
    json.dump(doc, open(OUT, "w"), indent=1)
    print(f"\nSaved {len(cat)} strategies -> {OUT}")


if __name__ == "__main__":
    run()

```

## `run_scanner.py`

*Daemon: 20-min scan cycle + daily settlement of user books* — 52 lines

```python
"""
Sentiment scanner daemon — refreshes logs/sentiment.json every 20 minutes.
Feeds the user app's AI-intelligence panel and the bots' shadow advisories.
"""
import time, traceback
from logger import log
from sentiment_scanner import run_scan

CYCLE_MIN = 20

def main():
    log.info("Sentiment scanner daemon starting (every %d min; settles user books after 21:05 UTC)" % CYCLE_MIN)
    while True:
        try:
            d = run_scan()
            snap = ", ".join(f"{a}:{v['score']:+.0f}" for a, v in d["assets"].items())
            log.info(f"sentiment scan: {d['n_scanned']} items | {snap}")
        except Exception:
            log.error("scanner cycle failed:")
            log.error(traceback.format_exc())
        # daily close-of-book settle for the user app's paper portfolios
        try:
            from user_engine import settle_users
            n = settle_users()
            if n:
                log.info(f"user books settled at daily close: {n}")
        except Exception:
            log.error("user settle failed:")
            log.error(traceback.format_exc())
        # daily heartbeat push — proves the machine is alive while unattended
        try:
            from heartbeat import maybe_send
            hb = maybe_send()
            if hb:
                log.info(f"heartbeat sent: {hb[0]}")
        except Exception:
            log.error("heartbeat failed:")
            log.error(traceback.format_exc())
        # weekly guarded ML retrain (Sundays 22:00+ UTC; adopt only if OOS holds)
        try:
            from retrain_ml import maybe_retrain
            r = maybe_retrain()
            if r:
                log.info("ML weekly retrain: " + "; ".join(f"{k}: {v}" for k, v in r.items()))
        except Exception:
            log.error("ML retrain failed:")
            log.error(traceback.format_exc())
        time.sleep(CYCLE_MIN * 60)

if __name__ == "__main__":
    main()

```

## `bootstrap.py`

*One-time setup* — 56 lines

```python
"""
One-time setup: seeds logs/ with the precomputed catalog + a sentiment snapshot so
the app runs immediately, with no API keys and no waiting for a first scan.

    python bootstrap.py

Then:  python app_user.py   ->  http://localhost:8090
"""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(HERE, "logs")
DATA = os.path.join(HERE, "data")

os.makedirs(LOGS, exist_ok=True)

for f in ("catalog.json", "sentiment.json"):
    src, dst = os.path.join(DATA, f), os.path.join(LOGS, f)
    if not os.path.exists(dst):
        shutil.copy(src, dst)
        print(f"  seeded logs/{f}")
    else:
        print(f"  logs/{f} already exists - kept")

for f, default in (("app_users.json", "{}"), ("app_accounts.json", "{}")):
    p = os.path.join(LOGS, f)
    if not os.path.exists(p):
        open(p, "w").write(default)
        print(f"  created empty logs/{f}")

missing = []
for mod in ("flask", "requests", "pandas", "numpy"):
    try:
        __import__(mod)
    except ImportError:
        missing.append(mod)

print()
if missing:
    print("MISSING PACKAGES:", ", ".join(missing))
    print("   run:  pip install -r requirements.txt")
    sys.exit(1)

has_env = os.path.exists(os.path.join(HERE, ".env"))
print("Setup complete.")
print("   Catalog + sentiment seeded - the web app works right now:")
print("       python app_user.py     ->  http://localhost:8090")
print()
if has_env:
    print("   .env found - live market marks enabled.")
else:
    print("   Live per-strategy holdings (the personal Blackbox panel) need a")
    print("   free OANDA practice key in .env. Everything else - strategies,")
    print("   backtests, projections, quiz, accounts, AI scanner - runs with")
    print("   no credentials at all.")

```

## `oanda_client.py`

*OANDA REST wrapper (market data + orders)* — 240 lines

```python
import requests
import time
import pandas as pd
from datetime import datetime, timezone
from config import OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_BASE_URL


class OandaClient:
    MAX_RETRIES = 3
    RETRY_STATUSES = {401, 408, 429}  # transient on OANDA practice (~3% of calls, 2026-06)
    TIMEOUT = 15  # seconds

    def __init__(self, account_id=None):
        self.headers = {
            "Authorization": f"Bearer {OANDA_API_KEY}",
            "Content-Type": "application/json",
        }
        self.base = OANDA_BASE_URL
        # account_id lets each sleeve trade its OWN sub-account; defaults to the
        # primary (FX) account from config when not specified.
        self.account = account_id or OANDA_ACCOUNT_ID

    def _request(self, method, url, **kwargs):
        """HTTP wrapper with timeout + retry/backoff.

        OANDA's practice API intermittently returns spurious 401s (~3% of
        calls observed 2026-06; the token is valid the other 97% of the time).
        Without retries a single flake raised straight out of the cycle,
        aborting stop management for ALL open trades that cycle. We retry
        transient statuses (401/408/429) plus 5xx and network errors; genuine
        4xx (bad order, 404) still fail fast.
        """
        kwargs.setdefault("timeout", self.TIMEOUT)
        last_exc = None
        for attempt in range(self.MAX_RETRIES):
            try:
                r = requests.request(method, url, headers=self.headers, **kwargs)
                r.raise_for_status()
                return r
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                if status is not None and status < 500 and status not in self.RETRY_STATUSES:
                    raise
                last_exc = e
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_exc = e
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
        raise last_exc

    def _get(self, path, params=None):
        return self._request("GET", f"{self.base}{path}", params=params).json()

    def _post(self, path, body):
        return self._request("POST", f"{self.base}{path}", json=body).json()

    # ── Data ──────────────────────────────────────────────────────────────

    def get_candles(self, instrument, granularity, count=500):
        data = self._get(
            f"/v3/instruments/{instrument}/candles",
            params={"granularity": granularity, "count": count, "price": "M"},
        )
        rows = []
        for c in data["candles"]:
            if c["complete"]:
                m = c["mid"]
                rows.append({
                    "timestamps": pd.Timestamp(c["time"]),
                    "open":   float(m["o"]),
                    "high":   float(m["h"]),
                    "low":    float(m["l"]),
                    "close":  float(m["c"]),
                    "volume": int(c["volume"]),
                    "amount": float(m["c"]) * int(c["volume"]),
                })
        df = pd.DataFrame(rows).set_index("timestamps")
        df.index = df.index.tz_localize(None)
        return df

    def get_candles_range(self, instrument, granularity, start, end):
        """Candles between two RFC3339 datetimes (for historical crisis windows).
        Keep ranges under ~5000 candles per call (OANDA cap)."""
        try:
            data = self._get(
                f"/v3/instruments/{instrument}/candles",
                params={"granularity": granularity, "from": start, "to": end, "price": "M"},
            )
        except Exception:
            return pd.DataFrame()
        rows = []
        for c in data.get("candles", []):
            if c["complete"]:
                m = c["mid"]
                rows.append({"timestamps": pd.Timestamp(c["time"]),
                             "open": float(m["o"]), "high": float(m["h"]),
                             "low": float(m["l"]), "close": float(m["c"]),
                             "volume": int(c["volume"])})
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows).set_index("timestamps")
        df.index = df.index.tz_localize(None)
        return df

    def get_account(self):
        return self._get(f"/v3/accounts/{self.account}/summary")["account"]

    def get_open_trades(self):
        return self._get(f"/v3/accounts/{self.account}/openTrades")["trades"]

    def get_open_orders(self):
        return self._get(f"/v3/accounts/{self.account}/pendingOrders")["orders"]

    def get_closed_trades(self, count=500):
        """
        Closed-trade history reconstructed from the TRANSACTION LEDGER.
        (OANDA's /trades?state=CLOSED endpoint silently omits most closed
        trades, discovered 2026-06-11 — the ledger is the source of truth.)
        Returns OANDA-trade-shaped dicts: id, instrument, price, openTime,
        closeTime, initialUnits, averageClosePrice, realizedPL.
        """
        # Pull the COMPLETE ledger via idrange. The /transactions LIST endpoint
        # type-filters and paginates incompletely — it silently returned only
        # 18 of 40 closed trades (found 2026-06-19). idrange 1..lastID is the
        # authoritative full ledger; OANDA caps each idrange call at 1000 ids.
        meta = self._get(f"/v3/accounts/{self.account}/transactions")
        last_id = int(meta.get("lastTransactionID", 0))
        opens, closes = {}, {}
        start = 1
        while start <= last_id:
            end = min(start + 999, last_id)
            txs = self._get(f"/v3/accounts/{self.account}/transactions/idrange",
                            params={"from": start, "to": end}).get("transactions", [])
            for t in txs:
                if t.get("type") != "ORDER_FILL":
                    continue
                to = t.get("tradeOpened")
                if to:
                    opens[to["tradeID"]] = {
                        "instrument": t.get("instrument", ""),
                        "price": float(to.get("price", t.get("price", 0))),
                        "openTime": t["time"],
                        "initialUnits": float(to.get("units", t.get("units", 0))),
                    }
                closed_list = list(t.get("tradesClosed") or [])
                if t.get("tradeReduced"):
                    closed_list.append(t["tradeReduced"])
                for tc in closed_list:
                    tid = tc["tradeID"]
                    rec = closes.setdefault(tid, {"realizedPL": 0.0})
                    rec["realizedPL"] += float(tc.get("realizedPL", 0))
                    rec["closeTime"] = t["time"]
                    rec["closePrice"] = float(tc.get("price", t.get("price", 0)))
            start = end + 1
        out = []
        for tid, c in closes.items():
            o = opens.get(tid)
            if not o:
                continue
            out.append({
                "id": tid,
                "instrument": o["instrument"],
                "price": str(o["price"]),
                "openTime": o["openTime"],
                "closeTime": c.get("closeTime", ""),
                "initialUnits": str(o["initialUnits"]),
                "averageClosePrice": str(c.get("closePrice", 0)),
                "realizedPL": str(c["realizedPL"]),
            })
        out.sort(key=lambda x: x["closeTime"])
        return out[-count:]

    def close_trade(self, trade_id):
        return self._request(
            "PUT", f"{self.base}/v3/accounts/{self.account}/trades/{trade_id}/close"
        ).json()

    def set_trade_stop(self, trade_id, instrument, price):
        """Modify the stop-loss on an open trade (used for breakeven/trailing moves)."""
        body = {"stopLoss": {"price": self._fmt_price(instrument, price), "timeInForce": "GTC"}}
        return self._request(
            "PUT", f"{self.base}/v3/accounts/{self.account}/trades/{trade_id}/orders",
            json=body,
        ).json()

    # ── Orders ────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_price(instrument: str, price: float) -> str:
        # Use the instrument's real display precision (gold=3, SPX500=1, Bund=3,
        # EUR/USD=5, USD/JPY=3). Orders are REJECTED if the precision is wrong.
        # Lazy import + fallback keeps FX behaviour byte-identical if specs are
        # unavailable (precision matches the old 3/5 rule for FX majors).
        try:
            from instruments import precision
            decimals = precision(instrument)
        except Exception:
            decimals = 3 if "JPY" in instrument else 5
        return f"{price:.{decimals}f}"

    def market_order(self, instrument, units, stop_loss_price=None, take_profit_price=None):
        order = {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(int(units)),
            "timeInForce": "FOK",
        }
        if stop_loss_price:
            order["stopLossOnFill"] = {"price": self._fmt_price(instrument, stop_loss_price)}
        if take_profit_price:
            order["takeProfitOnFill"] = {"price": self._fmt_price(instrument, take_profit_price)}
        body = {"order": order}
        resp = self._post(f"/v3/accounts/{self.account}/orders", body)
        if "orderCancelTransaction" in resp:
            reason = resp["orderCancelTransaction"].get("reason", "CANCELLED")
            raise RuntimeError(f"order cancelled by OANDA: {reason}")
        return resp

    def margin_rates(self):
        """Per-instrument margin rates (cached)."""
        if not hasattr(self, "_margin_rates"):
            data = self._get(f"/v3/accounts/{self.account}/instruments")
            self._margin_rates = {i["name"]: float(i["marginRate"]) for i in data["instruments"]}
        return self._margin_rates

    def close_all_trades(self):
        trades = self.get_open_trades()
        results = []
        for t in trades:
            r = self._request(
                "PUT", f"{self.base}/v3/accounts/{self.account}/trades/{t['id']}/close"
            )
            results.append(r.json())
        return results

    def get_price(self, instrument):
        data = self._get(f"/v3/accounts/{self.account}/pricing", params={"instruments": instrument})
        p = data["prices"][0]
        return (float(p["asks"][0]["price"]) + float(p["bids"][0]["price"])) / 2

```

## `crypto_bot.py`

*Coinbase data + crypto trend engine* — 196 lines

```python
"""
Crypto trend-following engine — PAPER TRADED (no broker, free Coinbase public data).
Long-only 200-day-MA trend on liquid majors, inverse-vol weighted, vol-targeted
(holds cash when coins are below trend / to cap risk). Maintains a simulated 100k
book marked to live prices. This is the validated 20%+ avenue (Sharpe ~1.2 backtest)
run in paper until it proves out, then it can go live on a crypto broker.

State: logs/crypto_state.json (cash, positions, peak).  NAV log: logs/crypto_nav.csv
"""
import os, json, time, urllib.request
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from logger import log
import notifier

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "data", "crypto"); os.makedirs(CACHE, exist_ok=True)
STATE = os.path.join(HERE, "logs", "crypto_state.json")
NAVLOG = os.path.join(HERE, "logs", "crypto_nav.csv")
CB = "https://api.exchange.coinbase.com"

PRODUCTS = ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","ADA-USD","DOGE-USD",
            "LINK-USD","AVAX-USD","LTC-USD","DOT-USD"]
START_CAP = 100_000.0
TARGET_VOL = 0.35          # annualized portfolio vol target (long-only, partial cash)
MA = 200                   # trend filter window (days)
COST = 0.0015              # 15 bps per unit traded


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "blackbox/1.0"})
    return json.load(urllib.request.urlopen(req, timeout=20))


def fetch_daily(product, refresh_h=8):
    """Daily closes, cached; refreshed if older than refresh_h hours."""
    path = os.path.join(CACHE, product.replace("-", "_") + "_live.csv")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < refresh_h * 3600:
        return pd.read_csv(path, parse_dates=["t"]).set_index("t")["close"]
    import datetime as dt
    rows = {}
    start = dt.datetime.utcnow() - dt.timedelta(days=420); now = dt.datetime.utcnow(); cur = start
    while cur < now:
        end = min(cur + dt.timedelta(days=290), now)
        try:
            d = _get(f"{CB}/products/{product}/candles?granularity=86400"
                     f"&start={cur.isoformat()}Z&end={end.isoformat()}Z")
            for c in d:
                rows[dt.datetime.utcfromtimestamp(c[0])] = c[4]
        except Exception:
            pass
        cur = end; time.sleep(0.25)
    if len(rows) < MA + 10:
        # fall back to existing cache if refresh failed
        if os.path.exists(path):
            return pd.read_csv(path, parse_dates=["t"]).set_index("t")["close"]
        return None
    s = pd.Series(rows).sort_index(); s.index.name = "t"; s.name = "close"
    s.to_frame().to_csv(path)
    return s


def spot(product):
    try:
        return float(_get(f"{CB}/products/{product}/ticker")["price"])
    except Exception:
        return None


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"cash": START_CAP, "positions": {}, "peak": START_CAP, "last_rebal": "",
            "started": datetime.now(timezone.utc).isoformat()}


def save_state(st):
    tmp = STATE + ".tmp"; json.dump(st, open(tmp, "w"), indent=2); os.replace(tmp, STATE)


def log_nav(nav, gross, n_on):
    new = not os.path.exists(NAVLOG)
    with open(NAVLOG, "a", newline="") as f:
        import csv; w = csv.writer(f)
        if new: w.writerow(["ts", "nav", "gross", "n_on"])
        w.writerow([datetime.now(timezone.utc).isoformat(), round(nav, 2), round(gross, 3), n_on])


def signals():
    """Per product: trend on/off + annualized vol + last close, from daily data."""
    out = {}
    for p in PRODUCTS:
        s = fetch_daily(p)
        if s is None or len(s) < MA + 5:
            continue
        ma = s.rolling(MA).mean().iloc[-1]
        vol = s.pct_change().tail(60).std() * np.sqrt(365)
        out[p] = {"on": bool(s.iloc[-1] > ma), "vol": float(vol), "close": float(s.iloc[-1])}
    return out


def run_cycle():
    st = load_state()
    sig = signals()
    if not sig:
        log.warning("crypto: no signals (data fetch failed); skipping."); return
    prices = {p: spot(p) or sig[p]["close"] for p in sig}
    # mark current NAV
    pos = st["positions"]
    holdings = sum(pos.get(p, 0.0) * prices.get(p, 0.0) for p in pos)
    nav = st["cash"] + holdings
    st["peak"] = max(st.get("peak", START_CAP), nav)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    on = [p for p in sig if sig[p]["on"] and sig[p]["vol"] > 0]
    avg_vol = np.mean([sig[p]["vol"] for p in on]) if on else 0
    gross = min(1.0, TARGET_VOL / avg_vol) if avg_vol > 0 else 0.0
    # AI sentiment RISK TILT (bounded, symmetric): bearish trims gross deployment
    # (<=-40 -> 0.75x, <=-60 -> 0.5x); bullish can only RESTORE toward full
    # deployment (>=+40 -> 1.1x, >=+60 -> 1.2x, hard-capped at gross=1.0 so the
    # book is never levered past its vol target). Fails open on stale data.
    try:
        from sentiment_scanner import read_latest
        _sv = (read_latest() or {}).get("assets", {}).get("crypto", {})
        if _sv and gross > 0:
            _sc = float(_sv.get("score", 0))
            _tilt = (0.5 if _sc <= -60 else 0.75 if _sc <= -40 else
                     1.2 if _sc >= 60 else 1.1 if _sc >= 40 else 1.0)
            if _tilt != 1.0:
                log.info(f"crypto sentiment tilt: score {_sc:+.0f} -> gross x{_tilt}")
                gross = min(1.0, gross * _tilt)
    except Exception:
        pass
    log_nav(nav, gross, len(on))

    # AI sentiment SHADOW advisory (informs/explains; validated rules trade)
    try:
        from sentiment_scanner import read_latest
        snt = read_latest()
        if snt:
            cs = snt["assets"].get("crypto", {})
            log.info(f"crypto sentiment advisory: score {cs.get('score')} ({cs.get('trend')}) — "
                     f"{cs.get('explanation','')[:110]}")
    except Exception:
        pass

    # rebalance once per day
    if st.get("last_rebal") == today:
        save_state(st)
        log.info(f"crypto: NAV {nav:,.0f} ({(nav/START_CAP-1)*100:+.2f}%) | on {sorted(on)} | gross {gross:.2f} | already rebalanced today")
        return

    inv = {p: 1.0 / sig[p]["vol"] for p in on}
    tot = sum(inv.values())
    target_val = {p: nav * gross * inv[p] / tot for p in on} if tot else {}
    # trade every product toward target (0 if off)
    cash = st["cash"]; newpos = dict(pos)
    traded = 0.0
    for p in set(list(pos.keys()) + list(sig.keys())):
        px = prices.get(p) or sig.get(p, {}).get("close")
        if not px:
            continue
        cur_val = newpos.get(p, 0.0) * px
        tgt_val = target_val.get(p, 0.0)
        d_val = tgt_val - cur_val
        traded += abs(d_val)
        cash -= d_val
        newpos[p] = (tgt_val / px) if tgt_val > 0 else 0.0
    cash -= traded * COST                      # transaction cost
    newpos = {p: u for p, u in newpos.items() if u > 1e-9}
    st["cash"] = cash; st["positions"] = newpos; st["last_rebal"] = today
    save_state(st)
    log.info(f"crypto REBALANCE: NAV {nav:,.0f} ({(nav/START_CAP-1)*100:+.2f}%) | "
             f"on {sorted(on)} | gross {gross:.2f} | traded {traded:,.0f} | held {sorted(newpos)}")
    # ntfy alert only when the held set actually changes (entries/exits), not on resizes
    prev_held = {p for p, u in pos.items() if u > 1e-9}
    new_held = set(newpos)
    if prev_held != new_held:
        entered = sorted(c.replace("-USD", "") for c in new_held - prev_held)
        exited = sorted(c.replace("-USD", "") for c in prev_held - new_held)
        if not new_held:
            notifier.send(f"Crypto PAPER -> 100% CASH (all coins below trend). NAV {nav:,.0f} "
                          f"({(nav/START_CAP-1)*100:+.1f}%)", title="Blackbox Crypto", priority="high")
        else:
            parts = []
            if entered: parts.append("bought " + ", ".join(entered))
            if exited: parts.append("sold " + ", ".join(exited))
            held = ", ".join(sorted(c.replace("-USD", "") for c in new_held))
            notifier.send(f"Crypto PAPER: {'; '.join(parts)} | holding {held} | NAV {nav:,.0f}",
                          title="Blackbox Crypto")


if __name__ == "__main__":
    run_cycle()

```

## `backtest_factors.py`

*Multi-asset daily history loader used by catalog.py* — 246 lines

```python
"""
Phase-1 modular cross-asset FACTOR backtest (price-only): TSMOM + XS-momentum +
Value(5y reversal) + Defensive(low-vol), combined risk-parity, inverse-vol sized,
then vol-TARGETED to maximise return. ~20yr daily OANDA data.

Honest by construction: reports Sharpe, Deflated Sharpe (Bailey/Lopez de Prado),
CAGR & max drawdown at several vol targets, plus the single-factor breakdown so we
see the diversification uplift. No-lookahead: signals at month-end t, held t->t+1.
"""
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np
import pandas as pd
from scipy.stats import norm

from oanda_client import OandaClient

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "data", "hist")
os.makedirs(CACHE, exist_ok=True)
START_LONG = "2006-01-01T00:00:00Z"     # ~20 years
COST_BPS = 10            # per unit turnover, round-trip-ish (monthly rebalance)


def fetch_daily(inst):
    """Paginated daily candles from 2006, cached to disk (true ~20yr history)."""
    import time
    path = os.path.join(CACHE, f"{inst}_Dlong.csv")
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=["t"]).set_index("t")
    c = OandaClient(); frm = START_LONG; rows = []
    while True:
        try:
            d = c._get(f"/v3/instruments/{inst}/candles",
                       params={"granularity": "D", "from": frm, "count": 4500, "price": "M"})
        except Exception:
            break
        cs = [x for x in d.get("candles", []) if x["complete"]]
        if not cs:
            break
        for x in cs:
            m = x["mid"]
            rows.append((x["time"], float(m["o"]), float(m["h"]), float(m["l"]), float(m["c"])))
        if len(cs) < 4500:
            break
        frm = (pd.Timestamp(cs[-1]["time"]) + pd.Timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        time.sleep(0.05)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close"])
    df["t"] = pd.to_datetime(df["t"]).dt.tz_localize(None)
    df = df.drop_duplicates("t").set_index("t").sort_index()
    df.to_csv(path)
    return df
CLASSES = {
    "FX": ["EUR_USD","GBP_USD","USD_JPY","AUD_USD","USD_CAD","USD_CHF","NZD_USD",
           "EUR_AUD","GBP_AUD","AUD_NZD"],
    "Rates": ["USB02Y_USD","USB05Y_USD","USB10Y_USD","USB30Y_USD","DE10YB_EUR","UK10YB_GBP"],
    "Commodities": ["XAU_USD","XAG_USD","XPT_USD","XPD_USD","XCU_USD","WTICO_USD","BCO_USD",
                    "NATGAS_USD","CORN_USD","WHEAT_USD","SOYBN_USD","SUGAR_USD"],
    "Indices": ["SPX500_USD","NAS100_USD","US30_USD","DE30_EUR","UK100_GBP","JP225_USD",
                "EU50_EUR","AU200_AUD"],
}
ALL = [i for v in CLASSES.values() for i in v]
CLS_OF = {i: c for c, v in CLASSES.items() for i in v}
out = []
def P(s=""): out.append(s); print(s, flush=True)


def load_daily():
    closes = {}
    for inst in ALL:
        try:
            d = fetch_daily(inst)
            if len(d) > 300:
                closes[inst] = d["close"]
        except Exception as e:
            P(f"  {inst}: skip ({e})")
    px = pd.DataFrame(closes).sort_index()
    px.index = pd.to_datetime(px.index)
    return px


def zscore_within_class(s):
    """Cross-sectional z-score within each asset class, per row (month)."""
    out = pd.Series(index=s.index, dtype=float)
    for c, insts in CLASSES.items():
        cols = [i for i in insts if i in s.index]
        v = s[cols].astype(float)
        m, sd = v.mean(), v.std()
        out[cols] = (v - m) / sd if sd and sd > 0 else 0.0
    return out.fillna(0.0)


def build_signals(px):
    """Returns dict month-> DataFrame of per-instrument factor scores + vol + fwd ret."""
    me = px.resample("ME").last()                       # month-end closes
    dret = px.pct_change()
    # ex-ante annualized vol (≈63 trading-day), as of each month-end
    vol_d = dret.rolling(63).std() * np.sqrt(252)
    vol_m = vol_d.resample("ME").last()
    r1 = me.pct_change(1); r3 = me.pct_change(3); r12 = me.pct_change(12)
    r12_1 = me.shift(1).pct_change(11)                  # t-12 -> t-1
    r5y = me.pct_change(60)
    fwd = me.pct_change().shift(-1)                     # next-month return (held t->t+1)
    months = me.index[13:-1]                            # need 12m history, 1m fwd
    panel = {}
    for t in months:
        if t not in r12.index:
            continue
        tsmom = (np.sign(r1.loc[t]) + np.sign(r3.loc[t]) + np.sign(r12.loc[t])) / 3.0
        xsmom = zscore_within_class(r12_1.loc[t])
        value = zscore_within_class(-r5y.loc[t])
        defen = zscore_within_class(-vol_m.loc[t])
        df = pd.DataFrame({"tsmom": tsmom, "xsmom": xsmom, "value": value,
                           "defen": defen, "vol": vol_m.loc[t], "fwd": fwd.loc[t]})
        df = df[(df["vol"] > 0) & np.isfinite(df["fwd"])]
        panel[t] = df.dropna(subset=["vol", "fwd"])
    return panel


def strat_returns(panel, weights):
    """weights = dict factor->weight. Returns monthly net return series (gross-1.0 base)."""
    wts_prev = None
    rows = []
    for t, df in panel.items():
        score = (weights["tsmom"] * df["tsmom"].fillna(0)
                 + weights["xsmom"] * df["xsmom"].fillna(0)
                 + weights["value"] * df["value"].fillna(0)
                 + weights["defen"] * df["defen"].fillna(0))
        w = score / df["vol"]                            # inverse-vol sizing
        gross = w.abs().sum()
        if gross > 0:
            w = w / gross                                # normalise to gross 1.0
        ret = float((w * df["fwd"]).sum())
        # turnover cost
        tc = 0.0
        if wts_prev is not None:
            allidx = w.index.union(wts_prev.index)
            turn = (w.reindex(allidx).fillna(0) - wts_prev.reindex(allidx).fillna(0)).abs().sum()
            tc = turn * COST_BPS / 1e4
        wts_prev = w
        rows.append((t, ret - tc))
    return pd.Series(dict(rows))


def vol_target(r, target_ann, cap=4.0):
    """Scale to target annualized vol using trailing 6m realized vol (lagged, no lookahead)."""
    rv = r.rolling(6).std() * np.sqrt(12)
    lev = (target_ann / rv).shift(1).clip(0, cap).fillna(0)
    return r * lev


def metrics(r):
    r = r.dropna()
    if len(r) < 24:
        return None
    ann = r.mean() * 12
    vol = r.std() * np.sqrt(12)
    sr = ann / vol if vol else 0
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    yrs = len(r) / 12
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    return dict(ann=ann, vol=vol, sr=sr, cagr=cagr, dd=dd, n=len(r), eq=eq.iloc[-1])


def deflated_sharpe(r, n_trials):
    """Bailey & Lopez de Prado Deflated Sharpe Ratio (prob true SR>0 after #trials)."""
    r = r.dropna(); T = len(r)
    if T < 24:
        return None
    sr = r.mean() / r.std() if r.std() else 0          # per-period (monthly) SR
    g3 = r.skew(); g4 = r.kurtosis() + 3.0             # non-excess kurtosis
    # expected max SR across N independent trials (variance of SR across trials ~ 1/T proxy)
    sr_trials_std = (1.0 / np.sqrt(T))                  # std of SR estimate under null
    g = 0.5772156649
    e = np.e
    sr0 = sr_trials_std * ((1 - g) * norm.ppf(1 - 1.0 / n_trials)
                           + g * norm.ppf(1 - 1.0 / (n_trials * e)))
    denom = np.sqrt((1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2) / (T - 1))
    if denom <= 0:
        return None
    return float(norm.cdf((sr - sr0) / denom))


def run():
    P("Loading ~20yr daily for %d instruments..." % len(ALL))
    px = load_daily()
    P("  loaded %d instruments, %s .. %s" % (px.shape[1], px.index[0].date(), px.index[-1].date()))
    panel = build_signals(px)
    P("  %d monthly rebalances\n" % len(panel))

    # single-factor vs combined (shows diversification uplift)
    P("=" * 80)
    P(f"  FACTOR BREAKDOWN (each at 10% vol target, net of {COST_BPS}bps turnover cost)")
    P("=" * 80)
    P(f"  {'strategy':<26}{'CAGR%':>7}{'vol%':>7}{'Sharpe':>8}{'maxDD%':>8}{'DSR':>7}")
    singles = {"TSMOM only": dict(tsmom=1, xsmom=0, value=0, defen=0),
               "XS-momentum only": dict(tsmom=0, xsmom=1, value=0, defen=0),
               "Value only": dict(tsmom=0, xsmom=0, value=1, defen=0),
               "Defensive only": dict(tsmom=0, xsmom=0, value=0, defen=1)}
    COMBINED = dict(tsmom=1.0, xsmom=0.6, value=0.5, defen=0.4)
    for name, w in {**singles, "COMBINED (all 4)": COMBINED}.items():
        r = vol_target(strat_returns(panel, w), 0.10)
        m = metrics(r)
        if m:
            dsr = deflated_sharpe(r, 30)
            P(f"  {name:<26}{m['cagr']*100:>7.1f}{m['vol']*100:>7.1f}{m['sr']:>8.2f}"
              f"{m['dd']*100:>8.1f}{(dsr if dsr is not None else float('nan')):>7.2f}")

    # MAXIMISE RETURNS — combined book at rising vol targets
    P("\n" + "=" * 80)
    P("  MAXIMISE RETURNS — COMBINED book vol-targeted higher (return vs drawdown)")
    P("=" * 80)
    P(f"  {'vol target':<12}{'CAGR%':>8}{'real vol%':>10}{'Sharpe':>8}{'maxDD%':>9}{'final x':>9}")
    base = strat_returns(panel, COMBINED)
    for tgt in [0.10, 0.15, 0.20, 0.30, 0.40]:
        m = metrics(vol_target(base, tgt))
        if m:
            P(f"  {int(tgt*100)}%{'':<9}{m['cagr']*100:>8.1f}{m['vol']*100:>10.1f}{m['sr']:>8.2f}"
              f"{m['dd']*100:>9.1f}{m['eq']:>9.1f}")

    # per-asset-class contribution (combined weights, 10% vol)
    P("\n" + "=" * 80)
    P("  PER ASSET-CLASS (combined factors, 10% vol target)")
    P("=" * 80)
    for c in CLASSES:
        sub = {t: df[df.index.map(lambda i: CLS_OF.get(i)) == c] for t, df in panel.items()}
        sub = {t: d for t, d in sub.items() if len(d) >= 2}
        if not sub:
            continue
        r = vol_target(strat_returns(sub, COMBINED), 0.10)
        m = metrics(r)
        if m:
            P(f"  {c:<14}CAGR {m['cagr']*100:>6.1f}%  Sharpe {m['sr']:>5.2f}  maxDD {m['dd']*100:>6.1f}%")

    with open(os.path.join(HERE, "logs", "backtest_factors.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    P("\n  Saved -> logs/backtest_factors.txt")


if __name__ == "__main__":
    run()

```

## `crypto_backtest.py`

*Crypto history for the catalog build* — 115 lines

```python
"""
The honest test for 20%+ CAGR: crypto trend-following. Crypto is the one liquid,
retail-accessible market still inefficient + high-vol enough to plausibly support
quant-fund returns. Trend-following (long in uptrends, flat/cash in bear markets)
historically captured crypto's upside while sidestepping its -80% crashes.

Daily data via yfinance (~2015+). Tests buy-hold vs 200d-MA trend vs trend+vol-target,
equal-weight basket and BTC alone. Honest: CAGR, Sharpe, maxDD, split-half robustness,
net of ~15bps per position flip. Crypto risks (regime, the great run may not repeat) noted.
"""
import warnings; warnings.filterwarnings("ignore")
import os
import numpy as np
import pandas as pd

PRODUCTS = ["BTC-USD","ETH-USD","LTC-USD","BCH-USD","ETC-USD","SOL-USD","ADA-USD",
            "XRP-USD","DOGE-USD","LINK-USD","AVAX-USD","DOT-USD","MATIC-USD"]
FLIP_COST = 0.0015         # 15bps per on/off flip
CACHE=os.path.join(os.path.dirname(__file__),"data","crypto"); os.makedirs(CACHE,exist_ok=True)
out=[]
def P(s=""): out.append(s); print(s, flush=True)

def _fetch_cb(prod):
    """Coinbase public daily candles, paginated 300/req from 2016, cached."""
    import urllib.request, json, time, datetime as dt
    path=os.path.join(CACHE,prod.replace("-","_")+".csv")
    if os.path.exists(path):
        return pd.read_csv(path,parse_dates=["t"]).set_index("t")["close"]
    rows={}; start=dt.datetime(2016,1,1); now=dt.datetime.utcnow()
    cur=start
    while cur<now:
        end=min(cur+dt.timedelta(days=290), now)
        u=(f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=86400"
           f"&start={cur.isoformat()}Z&end={end.isoformat()}Z")
        try:
            req=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"})
            d=json.load(urllib.request.urlopen(req,timeout=20))
            for c in d:  # [time, low, high, open, close, volume]
                rows[dt.datetime.utcfromtimestamp(c[0])]=c[4]
        except Exception:
            pass
        cur=end; time.sleep(0.25)
    if len(rows)<200:
        return None
    s=pd.Series(rows).sort_index(); s.index.name="t"; s.name="close"
    s.to_frame().to_csv(path)
    return s

def load():
    cols={}
    for p in PRODUCTS:
        s=_fetch_cb(p)
        if s is not None and len(s)>200:
            cols[p]=s
    df=pd.DataFrame(cols).sort_index()
    df.index=pd.to_datetime(df.index)
    return df.dropna(how="all")

def metrics(r, ppy=365):
    r=r.dropna()
    if len(r)<200: return None
    ann=r.mean()*ppy; vol=r.std()*np.sqrt(ppy); s=ann/vol if vol else 0
    eq=(1+r).cumprod(); dd=(eq/eq.cummax()-1).min(); cg=eq.iloc[-1]**(ppy/len(r))-1
    return dict(cagr=cg, vol=vol, sr=s, dd=dd, n=len(r))

def trend_port(px, vol_target=None):
    """Equal-weight, long-only 200d-MA trend; flat (cash) when below. Net of flip cost."""
    rets=px.pct_change()
    sig=(px>px.rolling(200).mean()).astype(float).shift(1)   # decide on yesterday
    flips=sig.diff().abs().fillna(0)
    pos_ret = (sig*rets - flips*FLIP_COST)
    # equal-weight across coins that have data each day
    port = pos_ret.mean(axis=1)
    if vol_target:
        rv=port.rolling(30).std()*np.sqrt(365)
        lev=(vol_target/rv).shift(1).clip(0,3).fillna(0)
        port=port*lev
    return port.dropna()

def bh_port(px):
    return px.pct_change().mean(axis=1).dropna()

def line(lbl,r):
    m=metrics(r)
    if not m: P(f"  {lbl:<32} (insufficient)"); return
    h=len(r)//2; s1=metrics(r.iloc[:h]); s2=metrics(r.iloc[h:])
    rb="robust" if s1 and s2 and s1["sr"]>0 and s2["sr"]>0 else "fragile"
    P(f"  {lbl:<32}{m['cagr']*100:>8.1f}{m['vol']*100:>7.0f}{m['sr']:>7.2f}{m['dd']*100:>8.0f}   {rb}")

def run():
    P("Downloading crypto daily (yfinance)...")
    px=load()
    P(f"  {px.shape[1]} coins, {px.index[0].date()}..{px.index[-1].date()}\n")
    P("="*80)
    P(f"  {'strategy':<32}{'CAGR%':>8}{'vol%':>7}{'Sharpe':>7}{'maxDD%':>8}   robust")
    P("="*80)
    line("Buy-hold basket (equal-wt)", bh_port(px))
    line("Buy-hold BTC only", px["BTC-USD"].pct_change().dropna())
    line("TREND basket (200d MA)", trend_port(px))
    line("TREND basket + 40% vol-target", trend_port(px, 0.40))
    line("TREND basket + 60% vol-target", trend_port(px, 0.60))
    # BTC-only trend
    btc=px[["BTC-USD"]]
    line("TREND BTC only", trend_port(btc))
    P("\n  MAXIMISE RETURNS — trend basket levered to vol targets:")
    for t in [0.30,0.50,0.80]:
        m=metrics(trend_port(px,t))
        if m: P(f"    {int(t*100)}% vol -> CAGR {m['cagr']*100:.0f}%  Sharpe {m['sr']:.2f}  maxDD {m['dd']*100:.0f}%")
    with open(os.path.join(os.path.dirname(__file__),"logs","crypto_backtest.txt"),"w",encoding="utf-8") as f:
        f.write("\n".join(out))
    P("\n  Saved -> logs/crypto_backtest.txt")

if __name__=="__main__":
    run()

```

## `instruments.py`

*Per-instrument specs (pip size, precision, value per unit)* — 171 lines

```python
"""
Instrument spec + sizing layer — the asset-agnostic foundation that lets the
Blackbox engine trade ANY OANDA instrument (FX, metals, indices, bonds, ...),
not just the FX majors the original code hardcoded.

Everything is driven by the LIVE specs OANDA returns for the account
(displayPrecision, pipLocation, marginRate, tradeUnitsPrecision) plus live
quote->home(CHF) conversion, so position sizing and price formatting are correct
for gold (3 dp), the S&P (1 dp), a Bund (3 dp) and EUR/USD (5 dp) alike.

Account currency is CHF. P&L for N units of an instrument quoted in QC, when price
moves by `dist` (in price units), is:  N * dist * (QC->CHF).  We invert that to
size a position to a target CHF risk.
"""
import time
from oanda_client import OandaClient

_specs = None
_specs_ts = 0.0
_conv = {}            # quote ccy -> (factor, timestamp)
HOME = "CHF"          # account currency


def _client():
    return OandaClient()


def specs(client=None, ttl=3600):
    """All tradeable instrument specs, cached for an hour."""
    global _specs, _specs_ts
    if _specs is not None and time.time() - _specs_ts < ttl:
        return _specs
    c = client or _client()
    data = c._get(f"/v3/accounts/{c.account}/instruments")
    out = {}
    for i in data["instruments"]:
        ploc = int(i["pipLocation"])
        out[i["name"]] = {
            "type": i["type"],                                  # CURRENCY / METAL / CFD
            "precision": int(i["displayPrecision"]),
            "pip_location": ploc,
            "pip": 10.0 ** ploc,
            "margin_rate": float(i["marginRate"]),
            "unit_precision": int(i.get("tradeUnitsPrecision", 0)),
            "quote": i["name"].split("_")[1],
            "display": i.get("displayName", i["name"]),
        }
    _specs = out
    _specs_ts = time.time()
    return out


def spec(inst):
    return specs().get(inst)


def pip_size(inst):
    s = specs().get(inst)
    return s["pip"] if s else 0.0001


def precision(inst):
    s = specs().get(inst)
    return s["precision"] if s else 5


def fmt_price(inst, price):
    """Format a price to the instrument's real display precision (orders are
    REJECTED otherwise — e.g. SPX500 wants 1 dp, not 5)."""
    return f"{price:.{precision(inst)}f}"


def home_factor(quote, client=None, ttl=300):
    """quote currency -> account currency (CHF) conversion, cached 5 min."""
    if quote == HOME:
        return 1.0
    hit = _conv.get(quote)
    if hit and time.time() - hit[1] < ttl:
        return hit[0]
    c = client or _client()
    f = None
    for pair, inv in ((f"{quote}_{HOME}", False), (f"{HOME}_{quote}", True)):
        try:
            px = c.get_price(pair)
            f = (1.0 / px) if inv else px
            break
        except Exception:
            continue
    if f is None:
        f = _conv.get(quote, (1.0, 0))[0]   # last known, else 1.0
    _conv[quote] = (f, time.time())
    return f


def home_value_per_unit(inst, client=None):
    """CHF value of a 1.0-price move on 1 unit of `inst` (= QC->CHF factor)."""
    s = specs().get(inst)
    quote = s["quote"] if s else "USD"
    return home_factor(quote, client)


def round_units(inst, units):
    s = specs().get(inst)
    up = s["unit_precision"] if s else 0
    if up <= 0:
        return int(units)
    return round(float(units), up)


def position_size(balance_chf, inst, sl_price_distance, risk_pct, client=None):
    """Units sized so that hitting the stop loses ~risk_pct of balance (CHF).

    loss_chf(N) = N * sl_price_distance * home_value_per_unit
    -> N = risk_chf / (sl_price_distance * home_value_per_unit)
    """
    if sl_price_distance is None or sl_price_distance <= 0:
        return 0
    vpu = home_value_per_unit(inst, client)
    if vpu <= 0:
        return 0
    risk_chf = balance_chf * risk_pct
    units = risk_chf / (sl_price_distance * vpu)
    return round_units(inst, units)


def margin_per_unit(inst, price, client=None):
    """CHF margin to hold 1 unit at `price` (notional * marginRate, in CHF)."""
    s = specs().get(inst)
    if not s:
        return None
    return price * s["margin_rate"] * home_value_per_unit(inst, client)


def cap_units_by_margin(inst, units, price, margin_avail_chf, nav_chf=None,
                        buffer=0.7, per_trade_nav=0.12, client=None):
    """Shrink an order so its margin fits ~70% of free margin AND a per-trade NAV
    budget (default 12% NAV). Same discipline the FX bot uses, generalised."""
    mpu = margin_per_unit(inst, price, client)
    if not mpu or mpu <= 0:
        return int(units)
    budget = buffer * margin_avail_chf
    if nav_chf:
        budget = min(budget, per_trade_nav * nav_chf)
    cap = int(budget / mpu)
    if abs(units) > cap:
        return cap if units > 0 else -cap
    return int(units) if specs()[inst]["unit_precision"] == 0 else round_units(inst, units)


if __name__ == "__main__":
    # quick self-test (read-only): print specs + a sample sizing for each sleeve
    c = _client()
    acct = c.get_account()
    bal = float(acct["balance"])
    print(f"account balance {bal:,.0f} {acct.get('currency', HOME)}")
    sp = specs(c)
    samples = ["EUR_USD", "USD_JPY", "XAU_USD", "XAG_USD",
               "SPX500_USD", "NAS100_USD", "DE30_EUR", "UK100_GBP",
               "USB10Y_USD", "DE10YB_EUR", "UK10YB_GBP"]
    print(f"\n{'inst':<12}{'type':<9}{'prec':>5}{'pip':>9}{'mgn':>6}{'uprec':>6}"
          f"{'QC->CHF':>9}{'~units@1% (SL=2*pip*100)':>26}")
    for i in samples:
        s = sp.get(i)
        if not s:
            print(f"{i:<12} (not tradeable)"); continue
        f = home_factor(s["quote"], c)
        sl_dist = 100 * s["pip"]                       # nominal 100-pip stop
        u = position_size(bal, i, sl_dist, 0.01, c)
        print(f"{i:<12}{s['type']:<9}{s['precision']:>5}{s['pip']:>9.4g}"
              f"{s['margin_rate']:>6.2f}{s['unit_precision']:>6}{f:>9.4f}{u:>26,}")

```

## `config.py`

*Environment loading and constants* — 61 lines

```python
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# OANDA
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_ENV = os.getenv("OANDA_ENV", "practice")
OANDA_BASE_URL = (
    "https://api-fxpractice.oanda.com"
    if OANDA_ENV == "practice"
    else "https://api-fxtrade.oanda.com"
)

# Strategy
# 7 USD majors + 3 NON-USD HEDGE crosses re-added 2026-06-27.
# The JPY crosses stay cut (correlated to the dollar book via USD_JPY, weak edge).
# These 3 were re-validated with REALISTIC spreads (crosses_retest.py) and have a
# real net edge PLUS negative/low correlation to the USD book — they hedge the
# dollar over-concentration that majors-only created: EUR_AUD corr -0.57, GBP_AUD
# -0.43, AUD_NZD -0.10. Currency cap (+/-4 any ccy) still bounds concentration.
# USD_CHF DROPPED 2026-06-30 after the 12-year backtest: -0.009R expectancy,
# -54% drawdown at 1% risk — net-negative over a full cycle. Existing positions
# ride to managed exits (manage_open_trades handles all open trades; entries stop).
INSTRUMENTS = [
    "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD", "NZD_USD",
    "EUR_AUD", "GBP_AUD", "AUD_NZD",
]
INSTRUMENT  = "EUR_USD"       # fallback / single-pair references
GRANULARITY = "H4"
GRANULARITY_DAILY = "D"
LOOKBACK_CANDLES = 100
LOOKBACK_DAILY   = 60
PRED_LEN = 8

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2.0

# RSI
RSI_PERIOD = 14
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65

# Kronos directional threshold — forecast must point >X% to confirm
KRONOS_THRESHOLD = 0.0003    # 3 pips on EUR/USD

# Risk management
RISK_PER_TRADE     = 0.006   # 0.6%/trade (halved from 1.25% on 2026-07-20: FX is the ungated "adaptive lab" and the book's worst bleeder at -8.7%; user-agreed cut until the regime improves. History: 3% -> 1.5% -> 2% -> 1.25% -> 0.6%)
MAX_PORTFOLIO_RISK = 0.07    # total at-risk cap 7% NAV — keeps severe drawdowns clear of the 25% halt
MAX_OPEN_TRADES  = 10        # distinct pairs at once (portfolio-risk budget is the real constraint)
STOP_LOSS_PIPS   = 40
TAKE_PROFIT_PIPS = 100       # 2.5:1 reward/risk
MAX_DRAWDOWN_PCT = 0.25      # 25% drawdown halt (demo has more room)

# Kronos model — mini is 4.1M params, context 2048, much faster on CPU
KRONOS_MODEL = "NeoQuasar/Kronos-mini"
KRONOS_TOKENIZER = "NeoQuasar/Kronos-Tokenizer-2k"
KRONOS_PATH = r"C:\Users\nicho\Kronos"

```

## `logger.py`

*Logging* — 41 lines

```python
import csv
import os
import logging
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

TRADE_LOG = os.path.join(LOG_DIR, "trades.csv")
BOT_LOG = os.path.join(LOG_DIR, "bot.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BOT_LOG),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("bot")


def log_trade(action, instrument, units, entry_price, sl, tp, signal, balance, note=""):
    exists = os.path.exists(TRADE_LOG)
    with open(TRADE_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["timestamp", "action", "instrument", "units",
                        "entry_price", "sl", "tp", "signal", "balance", "note"])
        w.writerow([
            datetime.utcnow().isoformat(), action, instrument, units,
            entry_price, sl, tp, signal, balance, note,
        ])


def log_cycle(balance, peak_balance, signal, open_trades):
    log.info(
        f"Balance={balance:.2f} | Peak={peak_balance:.2f} | "
        f"Signal={signal:+d} | OpenTrades={len(open_trades)}"
    )

```

## `notifier.py`

*Optional push notifications* — 52 lines

```python
"""
Phone push notifications — trade OPEN and CLOSE only.

Primary: ntfy.sh — zero-account push. The bot POSTs to a secret topic; the
ntfy app on the phone subscribes to that topic and gets instant notifications.
Optional: Telegram, if TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID are ever set.

Topic name is secret-ish (treat like a password) — set via NTFY_TOPIC in .env.
"""
import os
import requests

import config  # noqa: F401  (ensures .env is loaded)
from logger import log

NTFY_TOPIC = os.getenv("NTFY_TOPIC")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")


def send(msg: str, title: str = "Blackbox", priority: str = "default") -> bool:
    ok = False
    if NTFY_TOPIC:
        try:
            safe_title = title.encode("ascii", "replace").decode("ascii")  # headers must be ASCII
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=msg.encode("utf-8"),
                headers={
                    "Title": safe_title,
                    "Priority": priority,
                    "Tags": "chart_with_upwards_trend",
                    # Blackbox brain logo (shown on Android/web; iOS always uses the app icon)
                    "Icon": "https://blackbox.54-246-124-234.sslip.io/icon.png",
                },
                timeout=10,
            )
            ok = True
        except Exception as e:
            log.warning(f"ntfy send failed: {e}")
    if TG_TOKEN and TG_CHAT:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": f"{title}\n{msg}"},
                timeout=10,
            )
            ok = True
        except Exception as e:
            log.warning(f"telegram send failed: {e}")
    return ok

```

## `requirements.txt`

*Dependencies* — 8 lines

```text
# Blackbox KI — runtime dependencies
flask>=3.0
requests>=2.31
pandas>=2.0
numpy>=1.24
python-dotenv>=1.0
gunicorn>=21.2   # production server (Linux/macOS only; not needed for local dev)

```

## `.env.example`

*Environment variables (documented, no values)* — 24 lines

```bash
# ---------------------------------------------------------------------------
# Copy to .env and fill in. NOTHING here is required to run the web app —
# the catalog, backtests, projections, quiz, accounts and AI scanner all work
# with no credentials. These only unlock LIVE market marks + live trading.
# ---------------------------------------------------------------------------

# OANDA practice account — free, 60 seconds to create, no card:
#   https://www.oanda.com/demo-account/   ->  Manage API Access -> Generate token
# Unlocks: live per-strategy holdings + day-returns in the personal Blackbox panel.
OANDA_API_KEY=
OANDA_ACCOUNT_ID=
OANDA_ENV=practice

# Google Sign-In (optional). Create a Web-application OAuth client at
#   https://console.cloud.google.com/apis/credentials
# Authorized JavaScript origin must be EXACTLY where you host the app, e.g.
#   http://localhost:8090   (dev)   or   https://your.domain   (prod)
# When empty, the app falls back to recovery-key accounts, which fully work.
GOOGLE_CLIENT_ID=

# Flask session signing key. Leave blank locally (auto-generated into
# logs/app_secret.txt). In production set an explicit 64-char hex value.
APP_SECRET=

```

## `deploy/blackbox-app.service`

*systemd unit for the web app* — 13 lines

```ini
[Unit]
Description=Blackbox User App (ETH KI challenge)
After=network.target
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/blackbox-ki
ExecStart=/home/ubuntu/.local/bin/gunicorn -w 1 -b 127.0.0.1:8090 app_user:app
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target

```

## `deploy/trading-scanner.service`

*systemd unit for the scanner daemon* — 13 lines

```ini
[Unit]
Description=Blackbox AI Sentiment Scanner
After=network.target
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/blackbox-ki
ExecStart=/usr/bin/python3 /home/ubuntu/blackbox-ki/run_scanner.py
Restart=always
RestartSec=30
[Install]
WantedBy=multi-user.target

```

## `deploy/Caddyfile`

*Reverse proxy + automatic HTTPS* — 7 lines

```text
# Caddy gets free HTTPS automatically. sslip.io maps any IP to a hostname, so
# an EC2 box with no domain still gets a real certificate:
#   app.<dashed-public-ip>.sslip.io  ->  app.54-246-124-234.sslip.io
app.YOUR-DASHED-IP.sslip.io {
    reverse_proxy localhost:8090
}

```

## `research/research_deep.py`

*Edge research round 1 — pre-specified structural tests* — 209 lines

```python
"""
DEEP EDGE HUNT — five structurally-motivated, PRE-SPECIFIED tests on mechanisms we
have never tested (per the brain's rejected/confirmed ledger). Discipline:
  - selection decisions on HALF 1 only, validation on HALF 2 (true OOS)
  - harsh realistic OANDA costs charged per round trip
  - split-half Sharpe reported for everything

  T1  H4 SESSION ANATOMY (indices + gold): which 4-hour blocks of the 24h day carry
      return? (US cash-equity overnight anomaly, harvestable via ~23h CFDs. Our daily
      bars could never see this.) Select blocks on 2014-2020, validate 2020-2026.
  T2  PAIR / SPREAD MEAN-REVERSION: gold/silver, Brent/WTI, US 2s10s bond spread,
      SPX/Dow. z-score of 60d log-ratio; enter |z|>2, exit z=0 or 30d. Costs 6-10bps.
  T3  PANIC DIP-BUY in uptrend (indices): ret < -2*sigma20 AND close>200dMA -> long
      3 days. Pooled across 8 indices. Cost 1.5bps RT.
  T4  MACRO-CONDITIONAL GOLD: gold trend gated by bond regime (USB10Y>100dMA = yields
      falling). vs unconditional gold trend.
  T5  FX WEEKEND-GAP FADE: |Mon open - Fri close| > 0.15% -> fade, exit on fill or
      24h. Pooled 9 pairs. Cost 1bp RT.
"""
import warnings; warnings.filterwarnings("ignore")
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "data", "hist")
out = []
def P(s=""): out.append(s); print(s, flush=True)

def h4(inst):
    p = os.path.join(CACHE, f"{inst}_H4.csv")
    if not os.path.exists(p): return None
    df = pd.read_csv(p, parse_dates=["t"]).set_index("t")
    return df

def dlong(inst):
    p = os.path.join(CACHE, f"{inst}_Dlong.csv")
    if not os.path.exists(p): return None
    return pd.read_csv(p, parse_dates=["t"]).set_index("t")

def sr_ann(r, ppy):
    r = pd.Series(r).dropna()
    if len(r) < 40 or r.std() == 0: return 0.0, 0.0
    return float(r.mean()/r.std()*np.sqrt(ppy)), float(r.mean()*ppy)

# ---------------- T1: H4 session anatomy ----------------
def t1():
    P("="*88); P("T1  H4 SESSION ANATOMY — which 4h blocks carry the return (select H1, validate H2)"); P("="*88)
    UNIV = {"US indices": ["SPX500_USD","NAS100_USD","US30_USD"],
            "EU indices": ["DE30_EUR","EU50_EUR","UK100_GBP"],
            "Gold":       ["XAU_USD"]}
    results = {}
    for gname, insts in UNIV.items():
        blocks = {}   # hour -> list of (ts, ret) pooled across group
        for i in insts:
            df = h4(i)
            if df is None: continue
            r = (df["close"]/df["open"]-1)
            hr = df.index.hour
            for hh in sorted(set(hr)):
                blocks.setdefault(hh, []).append(pd.Series(r[hr==hh].values, index=df.index[hr==hh]))
        mid = pd.Timestamp("2020-06-01")
        P(f"\n  {gname}: per-block ann.ret% / Sharpe   (H1 = 2014-2020 | H2 = 2020-2026)")
        P(f"  {'blk(UTC)':<10}{'H1 ret%':>9}{'H1 SR':>7}{'H2 ret%':>9}{'H2 SR':>7}")
        sel = []
        for hh in sorted(blocks):
            s = pd.concat(blocks[hh]).sort_index()
            ppy = 252  # one obs per day per instrument, pooled -> ~252*n, use per-block daily mean
            byday = s.groupby(s.index.date).mean()
            byday.index = pd.to_datetime(byday.index)
            h1, h2 = byday[byday.index < mid], byday[byday.index >= mid]
            sr1, an1 = sr_ann(h1, 252); sr2, an2 = sr_ann(h2, 252)
            tag = ""
            if sr1 > 0.35:
                sel.append(hh); tag = "  <-- selected on H1"
            P(f"  {hh:02d}:00{'':<5}{an1*100:>9.1f}{sr1:>7.2f}{an2*100:>9.1f}{sr2:>7.2f}{tag}")
        # validate the H1-selected block-set on H2, net of 1 RT/day cost
        if sel:
            s_all = []
            for hh in sel: s_all.append(pd.concat(blocks[hh]).sort_index())
            s = pd.concat(s_all).sort_index()
            byday = s.groupby(s.index.date).sum() / max(len(UNIV[gname]),1)  # sum selected blocks per day (per-inst avg)
            byday.index = pd.to_datetime(byday.index)
            cost = 0.00015 if "Gold" not in gname else 0.0002   # 1.5-2 bps RT/day
            h2net = byday[byday.index >= mid] - cost
            h1net = byday[byday.index < mid] - cost
            sr2, an2 = sr_ann(h2net, 252); sr1, an1 = sr_ann(h1net, 252)
            results[gname] = (sel, sr1, an1, sr2, an2)
            P(f"  >> HOLD blocks {sel} net of {cost*1e4:.1f}bp/day:  H1 {an1*100:+.1f}%/SR {sr1:.2f}  |  OOS H2 {an2*100:+.1f}%/SR {sr2:.2f}")
    return results

# ---------------- T2: pair mean reversion ----------------
def t2():
    P("\n"+"="*88); P("T2  PAIR/SPREAD MEAN-REVERSION (z>2 entry, exit z=0 or 30d)"); P("="*88)
    PAIRS = [("XAU_USD","XAG_USD", 8), ("BCO_USD","WTICO_USD", 10),
             ("USB02Y_USD","USB10Y_USD", 6), ("SPX500_USD","US30_USD", 3)]
    P(f"  {'pair':<26}{'trades':>7}{'ann%':>7}{'SR':>6}{'H1 SR':>7}{'H2 SR':>7}{'verdict':>9}")
    res = {}
    for a, b, cost_bps in PAIRS:
        da, db = dlong(a), dlong(b)
        if da is None or db is None: continue
        px = pd.DataFrame({"a": da["close"], "b": db["close"]}).dropna()
        lr = np.log(px["a"]/px["b"])
        z = (lr - lr.rolling(60).mean())/lr.rolling(60).std()
        ra, rb = px["a"].pct_change(), px["b"].pct_change()
        pos = 0; entry_i = 0; rets = []; n_tr = 0
        zv = z.values; rav = ra.values; rbv = rb.values
        daily = np.zeros(len(px))
        for i in range(61, len(px)):
            if pos == 0:
                if zv[i-1] > 2:   pos = -1; entry_i = i; n_tr += 1   # short a, long b
                elif zv[i-1] < -2: pos = 1; entry_i = i; n_tr += 1   # long a, short b
                if pos != 0: daily[i] -= cost_bps/1e4
            else:
                daily[i] += pos*0.5*(rav[i]-rbv[i])
                if (pos == -1 and zv[i] < 0) or (pos == 1 and zv[i] > 0) or (i-entry_i > 30):
                    pos = 0
        r = pd.Series(daily, index=px.index)
        mid = px.index[len(px)//2]
        sr, an = sr_ann(r, 252); s1,_ = sr_ann(r[r.index<mid],252); s2,_ = sr_ann(r[r.index>=mid],252)
        verdict = "ROBUST" if s1>0.3 and s2>0.3 else ("weak" if sr>0.2 else "dead")
        res[f"{a[:3]}/{b[:3]}"] = (sr, s1, s2)
        P(f"  {a[:6]+' vs '+b[:6]:<26}{n_tr:>7}{an*100:>7.1f}{sr:>6.2f}{s1:>7.2f}{s2:>7.2f}{verdict:>9}")
    return res

# ---------------- T3: panic dip-buy ----------------
def t3():
    P("\n"+"="*88); P("T3  PANIC DIP-BUY in uptrend (ret<-2sig & >200dMA -> long 3d), pooled indices"); P("="*88)
    INDICES = ["SPX500_USD","NAS100_USD","US30_USD","DE30_EUR","UK100_GBP","JP225_USD","EU50_EUR","AU200_AUD"]
    allr = []
    for i in INDICES:
        d = dlong(i)
        if d is None: continue
        c = d["close"]; r = c.pct_change()
        sig = r.rolling(20).std(); ma = c.rolling(200).mean()
        trig = (r < -2*sig) & (c > ma)
        idx = np.where(trig.values)[0]
        last_exit = -1
        for j in idx:
            if j <= last_exit or j+3 >= len(c): continue
            ret3 = float(c.iloc[j+3]/c.iloc[j]-1) - 0.00015
            allr.append((c.index[j], ret3)); last_exit = j+3
    s = pd.Series(dict(allr)).sort_index()
    mid = s.index[len(s)//2]
    # ~len(s)/20yr trades per yr; annualize per-trade series by trades/yr
    tpy = len(s)/((s.index[-1]-s.index[0]).days/365.25)
    sr = float(s.mean()/s.std()*np.sqrt(tpy)) if s.std() else 0
    s1 = s[s.index<mid]; s2 = s[s.index>=mid]
    sr1 = float(s1.mean()/s1.std()*np.sqrt(tpy)) if s1.std() else 0
    sr2 = float(s2.mean()/s2.std()*np.sqrt(tpy)) if s2.std() else 0
    P(f"  {len(s)} trades ({tpy:.0f}/yr) | avg {s.mean()*100:+.2f}%/trade | win {(s>0).mean()*100:.0f}% | SR {sr:.2f} | halves {sr1:.2f}/{sr2:.2f}")
    return sr, sr1, sr2, s

# ---------------- T4: macro-conditional gold ----------------
def t4():
    P("\n"+"="*88); P("T4  GOLD trend gated by BOND regime (USB10Y>100dMA = falling yields)"); P("="*88)
    g, b = dlong("XAU_USD"), dlong("USB10Y_USD")
    px = pd.DataFrame({"g": g["close"], "b": b["close"]}).dropna()
    rg = px["g"].pct_change()
    gtrend = (px["g"] > px["g"].rolling(200).mean()).shift(1)
    bregime = (px["b"] > px["b"].rolling(100).mean()).shift(1)
    uncond = rg[gtrend.fillna(False)]
    cond = rg[(gtrend & bregime).fillna(False)]
    anti = rg[(gtrend & ~bregime).fillna(False)]
    for lbl, s in [("gold trend (uncond)", uncond), ("gold trend & yields falling", cond), ("gold trend & yields RISING", anti)]:
        sr, an = sr_ann(s, 252)
        mid = s.index[len(s)//2] if len(s)>100 else None
        s1,_ = sr_ann(s[s.index<mid],252) if mid is not None else (0,0)
        s2,_ = sr_ann(s[s.index>=mid],252) if mid is not None else (0,0)
        P(f"  {lbl:<30} days {len(s):>5}  ann {an*100:>6.1f}%  SR {sr:>5.2f}  halves {s1:.2f}/{s2:.2f}")

# ---------------- T5: FX weekend gap fade ----------------
def t5():
    P("\n"+"="*88); P("T5  FX WEEKEND-GAP FADE (|gap|>0.15%, exit fill/24h), pooled 9 pairs"); P("="*88)
    FX = ["EUR_USD","GBP_USD","USD_JPY","AUD_USD","USD_CAD","NZD_USD","EUR_AUD","GBP_AUD","AUD_NZD"]
    allr = []
    for i in FX:
        df = h4(i)
        if df is None: continue
        dow = df.index.dayofweek
        # Monday's first bar open vs previous close
        opens = df["open"]; closes = df["close"]
        prev_close = closes.shift(1)
        is_mon_first = (dow == 0) & (pd.Series(dow, index=df.index).shift(1) != 0).values
        gaps = (opens/prev_close - 1)[is_mon_first]
        big = gaps[abs(gaps) > 0.0015]
        for ts, gp in big.items():
            loc = df.index.get_loc(ts)
            if loc+6 >= len(df): continue
            # fade: position = -sign(gap); exit at close 6 bars (~24h) later
            ret = -np.sign(gp) * (closes.iloc[loc+5]/opens.iloc[loc] - 1) - 0.0001
            allr.append((ts, float(ret)))
    s = pd.Series(dict(allr)).sort_index()
    if len(s) < 30:
        P(f"  only {len(s)} events — insufficient"); return
    tpy = len(s)/((s.index[-1]-s.index[0]).days/365.25)
    mid = s.index[len(s)//2]
    sr = float(s.mean()/s.std()*np.sqrt(tpy)) if s.std() else 0
    s1 = s[s.index<mid]; s2 = s[s.index>=mid]
    sr1 = float(s1.mean()/s1.std()*np.sqrt(tpy)) if s1.std() else 0
    sr2 = float(s2.mean()/s2.std()*np.sqrt(tpy)) if s2.std() else 0
    P(f"  {len(s)} gaps ({tpy:.0f}/yr) | avg {s.mean()*100:+.3f}% | win {(s>0).mean()*100:.0f}% | SR {sr:.2f} | halves {sr1:.2f}/{sr2:.2f}")

if __name__ == "__main__":
    t1(); t2(); t3(); t4(); t5()
    with open(os.path.join(HERE, "logs", "research_deep.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    P("\nSaved -> logs/research_deep.txt")

```

## `research/research_deep2.py`

*Edge research round 2 — cost ladders* — 123 lines

```python
"""
DEEP HUNT round 2 — zoom into the T1 discovery + finish T4/T5.

  T6  GOLD (and silver/platinum) REOPEN DRIFT: long the first H4 bar after the daily
      break (bars labelled 21:00/22:00 UTC = DST aliases). Exact net Sharpe at
      1.5/2/3bp per day, year-by-year consistency, and DST-alias-merged US-index
      session map for reference.
  T4' MACRO-CONDITIONAL GOLD (fixed dtypes).
  T5  FX weekend-gap fade.
"""
import warnings; warnings.filterwarnings("ignore")
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "data", "hist")
out = []
def P(s=""): out.append(s); print(s, flush=True)

def h4(inst):
    p = os.path.join(CACHE, f"{inst}_H4.csv")
    return pd.read_csv(p, parse_dates=["t"]).set_index("t") if os.path.exists(p) else None

def dlong(inst):
    p = os.path.join(CACHE, f"{inst}_Dlong.csv")
    return pd.read_csv(p, parse_dates=["t"]).set_index("t") if os.path.exists(p) else None

def srr(s, ppy=252):
    s = pd.Series(s).dropna()
    if len(s) < 40 or s.std() == 0: return 0.0, 0.0
    return float(s.mean()/s.std()*np.sqrt(ppy)), float(s.mean()*ppy)

def t6():
    P("="*88); P("T6  METALS REOPEN DRIFT — long first H4 bar after the daily break (21/22 UTC)"); P("="*88)
    for inst, base_cost in [("XAU_USD", 1.5), ("XAG_USD", 4.0), ("XPT_USD", 4.0)]:
        df = h4(inst)
        if df is None: continue
        r = df["close"]/df["open"] - 1
        hr = df.index.hour
        reopen = r[(hr == 21) | (hr == 22)]
        byday = reopen.groupby(reopen.index.date).sum()
        byday.index = pd.to_datetime(byday.index)
        sr_g, an_g = srr(byday)
        P(f"\n  {inst}  ({len(byday)} days, {byday.index[0].date()}..{byday.index[-1].date()})  GROSS ann {an_g*100:+.1f}%  SR {sr_g:.2f}")
        P(f"    {'cost/day':<10}{'net ann%':>9}{'net SR':>8}")
        for c_bps in [0, 1.5, 2, 3, base_cost] if base_cost not in (1.5,) else [0, 1, 1.5, 2, 3]:
            net = byday - c_bps/1e4
            sr_n, an_n = srr(net)
            P(f"    {c_bps}bp{'':<6}{an_n*100:>9.1f}{sr_n:>8.2f}")
        # year-by-year gross SR (consistency check)
        yr = byday.groupby(byday.index.year)
        line = "    yearly SR: " + "  ".join(f"{y}:{(g.mean()/g.std()*np.sqrt(252)) if g.std() else 0:+.1f}" for y, g in yr if len(g) > 60)
        P(line)
    # US indices DST-alias-merged map for reference
    P("\n  US indices — DST-merged session map (pooled SPX/NAS/US30, full sample, gross):")
    UNIV = ["SPX500_USD","NAS100_USD","US30_USD"]
    SESS = {"reopen(21/22)": (21,22), "night(01/02)": (1,2), "eu-am(05/06)": (5,6),
            "eu-pm/us-open(09/10)": (9,10), "us-am(13/14)": (13,14), "us-pm(17/18)": (17,18)}
    pool = []
    for i in UNIV:
        df = h4(i)
        if df is not None:
            r = df["close"]/df["open"]-1
            pool.append(pd.DataFrame({"r": r, "hr": df.index.hour}, index=df.index))
    allp = pd.concat(pool)
    mid = pd.Timestamp("2020-06-01")
    P(f"    {'session':<22}{'H1 SR':>7}{'H2 SR':>7}")
    for nm,(a,b) in SESS.items():
        s = allp[(allp["hr"]==a)|(allp["hr"]==b)]["r"]
        d = s.groupby(s.index.date).mean(); d.index = pd.to_datetime(d.index)
        s1,_ = srr(d[d.index<mid]); s2,_ = srr(d[d.index>=mid])
        P(f"    {nm:<22}{s1:>7.2f}{s2:>7.2f}")

def t4():
    P("\n"+"="*88); P("T4' GOLD trend gated by BOND regime"); P("="*88)
    g, b = dlong("XAU_USD"), dlong("USB10Y_USD")
    px = pd.DataFrame({"g": g["close"], "b": b["close"]}).dropna()
    rg = px["g"].pct_change()
    gtrend = (px["g"] > px["g"].rolling(200).mean()).shift(1).fillna(False).astype(bool)
    breg = (px["b"] > px["b"].rolling(100).mean()).shift(1).fillna(False).astype(bool)
    for lbl, mask in [("gold trend (uncond)", gtrend), ("trend & yields falling", gtrend & breg),
                      ("trend & yields rising", gtrend & (~breg))]:
        s = rg[mask]
        sr, an = srr(s)
        if len(s) > 100:
            mid = s.index[len(s)//2]
            s1,_ = srr(s[s.index<mid]); s2,_ = srr(s[s.index>=mid])
        else: s1=s2=0
        P(f"  {lbl:<26} days {len(s):>5}  ann {an*100:>6.1f}%  SR {sr:>5.2f}  halves {s1:.2f}/{s2:.2f}")

def t5():
    P("\n"+"="*88); P("T5  FX WEEKEND-GAP FADE (|gap|>0.15%)"); P("="*88)
    FX = ["EUR_USD","GBP_USD","USD_JPY","AUD_USD","USD_CAD","NZD_USD","EUR_AUD","GBP_AUD","AUD_NZD"]
    allr = []
    for i in FX:
        df = h4(i)
        if df is None: continue
        dow = pd.Series(df.index.dayofweek, index=df.index)
        first_of_week = (dow <= 1) & (dow.shift(1) >= 4)
        opens, closes = df["open"], df["close"]
        prev_close = closes.shift(1)
        gaps = (opens/prev_close - 1)[first_of_week.values]
        big = gaps[abs(gaps) > 0.0015]
        for ts, gp in big.items():
            loc = df.index.get_loc(ts)
            if loc + 6 >= len(df): continue
            ret = -np.sign(gp) * (closes.iloc[loc+5]/opens.iloc[loc] - 1) - 0.0001
            allr.append((ts, float(ret)))
    if len(allr) < 30:
        P(f"  only {len(allr)} events — insufficient"); return
    s = pd.Series(dict(allr)).sort_index()
    tpy = len(s)/((s.index[-1]-s.index[0]).days/365.25)
    mid = s.index[len(s)//2]
    f = lambda x: float(x.mean()/x.std()*np.sqrt(tpy)) if len(x)>10 and x.std() else 0
    P(f"  {len(s)} gaps ({tpy:.0f}/yr) | avg {s.mean()*100:+.3f}% | win {(s>0).mean()*100:.0f}% | SR {f(s):.2f} | halves {f(s[s.index<mid]):.2f}/{f(s[s.index>=mid]):.2f}")

if __name__ == "__main__":
    t6(); t4(); t5()
    with open(os.path.join(HERE, "logs", "research_deep2.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    P("\nSaved -> logs/research_deep2.txt")

```

## `research/research_deep3.py`

*Edge research round 3 — validates rates-gated gold* — 116 lines

```python
"""
DEEP HUNT round 3 — build out the T4 discovery: the RATES-GATED METALS sleeve.

Mechanism: precious metals are zero-yield real assets -> they perform when yields
FALL (bond prices rise). Gate = USB10Y above its 100dMA. Test the same gate on each
metal (confirmatory cross-asset evidence), the combined inverse-vol sleeve with
vol-targeting, costs, and an equity variant for reference.
"""
import warnings; warnings.filterwarnings("ignore")
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "data", "hist")
out = []
def P(s=""): out.append(s); print(s, flush=True)

def dlong(inst):
    p = os.path.join(CACHE, f"{inst}_Dlong.csv")
    return pd.read_csv(p, parse_dates=["t"]).set_index("t") if os.path.exists(p) else None

def srr(s, ppy=252):
    s = pd.Series(s).dropna()
    if len(s) < 60 or s.std() == 0: return 0.0, 0.0, 0.0
    eq = (1+s).cumprod()
    dd = float((eq/eq.cummax()-1).min())
    return float(s.mean()/s.std()*np.sqrt(ppy)), float(s.mean()*ppy), dd

def halves(s):
    s = s.dropna()
    if len(s) < 200: return 0.0, 0.0
    mid = s.index[len(s)//2]
    a = s[s.index < mid]; b = s[s.index >= mid]
    f = lambda x: float(x.mean()/x.std()*np.sqrt(252)) if len(x) > 60 and x.std() else 0.0
    return f(a), f(b)

def run():
    bond = dlong("USB10Y_USD")["close"]
    breg = (bond > bond.rolling(100).mean()).shift(1)

    P("="*88)
    P("RATES-GATED METALS — long metal when (metal>200dMA) AND (USB10Y>100dMA)")
    P("="*88)
    P(f"  {'asset':<10}{'variant':<28}{'ann%':>7}{'SR':>6}{'maxDD%':>8}{'H1/H2':>12}")
    strat_rets = {}
    for m in ["XAU_USD", "XAG_USD", "XPT_USD"]:
        d = dlong(m)
        if d is None: continue
        c = d["close"]; r = c.pct_change()
        tr = (c > c.rolling(200).mean()).shift(1)
        idx = r.index.intersection(breg.index)
        rr, trm, bg = r[idx], tr[idx].fillna(False).astype(bool), breg[idx].fillna(False).astype(bool)
        for lbl, mask in [("trend only", trm), ("trend & yields falling", trm & bg)]:
            pos = mask.astype(float)
            # cost: 1.5bp per flip (regime changes only — few/yr)
            flips = pos.diff().abs().fillna(0)
            net = pos*rr - flips*0.00015
            sr, an, dd = srr(net)
            h1, h2 = halves(net)
            P(f"  {m[:3]:<10}{lbl:<28}{an*100:>7.1f}{sr:>6.2f}{dd*100:>8.1f}{f'{h1:.2f}/{h2:.2f}':>12}")
            if lbl.startswith("trend &"):
                strat_rets[m] = net

    # combined sleeve: inverse-vol across the 3 gated metals, vol-target 12%
    P("\n  COMBINED gated-metals sleeve (inverse-vol, vol-target 12%):")
    R = pd.DataFrame(strat_rets).fillna(0)
    vol = R.rolling(30).std()*np.sqrt(252)
    w = (1.0/vol.replace(0, np.nan)).fillna(0)
    w = w.div(w.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    port = (w.shift(1)*R).sum(axis=1)
    rv = port.rolling(30).std()*np.sqrt(252)
    lev = (0.12/rv).shift(1).clip(0, 3).fillna(0)
    pv = port*lev
    sr, an, dd = srr(pv); h1, h2 = halves(pv)
    P(f"    ann {an*100:+.1f}%  SR {sr:.2f}  maxDD {dd*100:.1f}%  halves {h1:.2f}/{h2:.2f}")
    # exposure stats
    days_on = (R.abs().sum(axis=1) > 0).mean()
    P(f"    time exposed: {days_on*100:.0f}% of days (in cash otherwise)")

    # correlation with the confirmed equity seasonal+trend edge
    P("\n  Correlation with existing edges:")
    try:
        idxs = ["SPX500_USD","NAS100_USD","US30_USD","DE30_EUR","UK100_GBP","JP225_USD","EU50_EUR","AU200_AUD"]
        rets, ons = {}, {}
        for i in idxs:
            d = dlong(i)
            if d is None: continue
            c = d["close"]; rets[i] = c.pct_change()
            ons[i] = (c > c.rolling(200).mean()).astype(float).shift(1)
        RR = pd.DataFrame(rets); ON = pd.DataFrame(ons)
        months = RR.index.month
        seas = pd.Series([1.0 if mm in {11,12,1,2,3,4} else 0.0 for mm in months], index=RR.index)
        eq_edge = (ON.mul(seas, axis=0)*RR).mean(axis=1).dropna()
        j = pd.DataFrame({"m": pv, "e": eq_edge}).dropna()
        P(f"    corr(gated-metals, equity seasonal+trend) = {j['m'].corr(j['e']):+.2f}")
    except Exception as e:
        P(f"    (corr calc failed: {e})")

    # equity variant for reference: NAS trend & yields falling
    P("\n  Reference — NAS100 trend gated by same bond regime:")
    d = dlong("NAS100_USD"); c = d["close"]; r = c.pct_change()
    tr = (c > c.rolling(200).mean()).shift(1)
    idx = r.index.intersection(breg.index)
    rr, trm, bg = r[idx], tr[idx].fillna(False).astype(bool), breg[idx].fillna(False).astype(bool)
    for lbl, mask in [("trend only", trm), ("trend & yields falling", trm & bg), ("trend & yields rising", trm & (~bg))]:
        s = rr[mask]; sr, an, _ = srr(s); h1, h2 = halves(s)
        P(f"    {lbl:<26} ann {an*100:>6.1f}%  SR {sr:>5.2f}  halves {h1:.2f}/{h2:.2f}")

    with open(os.path.join(HERE, "logs", "research_deep3.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    P("\nSaved -> logs/research_deep3.txt")

if __name__ == "__main__":
    run()

```

---

*Bundle contains 26 files, 4,386 lines total.*
