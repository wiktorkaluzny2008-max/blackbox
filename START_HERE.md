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
