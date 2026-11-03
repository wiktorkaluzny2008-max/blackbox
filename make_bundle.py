"""
Generates BUNDLE.md — every source file in this project concatenated into ONE
markdown document, so the entire codebase can be handed to an AI in a single
upload (or pasted into a chat) without needing the folder structure.

    python make_bundle.py

Re-run after changing any source file to keep the bundle in sync.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "BUNDLE.md")

# order matters: most important first, so a reader (human or model) meets the
# product before the plumbing
FILES = [
    ("START_HERE.md", "md", "Read this first: how to run it and hand it to your AI"),
    ("README.md", "md", "What this project is, the architecture, the research behind it"),
    ("CLAUDE.md", "md", "Working conventions, ground rules and known gotchas"),
    ("HANDOVER.md", "md", "Current status, next steps, demo script"),
    ("app_user.py", "python", "THE WHOLE WEB APP — Flask API + the entire single-page UI"),
    ("user_engine.py", "python", "Per-user live paper portfolios; where the AI scanner acts"),
    ("sentiment_scanner.py", "python", "The NLP news/social sentiment engine"),
    ("catalog.py", "python", "Builds the strategy catalog: stats, curves, bootstrap projections"),
    ("run_scanner.py", "python", "Daemon: 20-min scan cycle + daily settlement of user books"),
    ("bootstrap.py", "python", "One-time setup"),
    ("oanda_client.py", "python", "OANDA REST wrapper (market data + orders)"),
    ("crypto_bot.py", "python", "Coinbase data + crypto trend engine"),
    ("backtest_factors.py", "python", "Multi-asset daily history loader used by catalog.py"),
    ("crypto_backtest.py", "python", "Crypto history for the catalog build"),
    ("instruments.py", "python", "Per-instrument specs (pip size, precision, value per unit)"),
    ("config.py", "python", "Environment loading and constants"),
    ("logger.py", "python", "Logging"),
    ("notifier.py", "python", "Optional push notifications"),
    ("requirements.txt", "text", "Dependencies"),
    (".env.example", "bash", "Environment variables (documented, no values)"),
    ("deploy/blackbox-app.service", "ini", "systemd unit for the web app"),
    ("deploy/trading-scanner.service", "ini", "systemd unit for the scanner daemon"),
    ("deploy/Caddyfile", "text", "Reverse proxy + automatic HTTPS"),
    ("research/research_deep.py", "python", "Edge research round 1 — pre-specified structural tests"),
    ("research/research_deep2.py", "python", "Edge research round 2 — cost ladders"),
    ("research/research_deep3.py", "python", "Edge research round 3 — validates rates-gated gold"),
]

HEADER = """# Blackbox — ETH KI Challenge · COMPLETE CODE BUNDLE

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

"""


def main():
    parts = [HEADER]
    toc = []
    for path, lang, desc in FILES:
        full = os.path.join(HERE, path)
        if not os.path.exists(full):
            print(f"  SKIP (missing): {path}")
            continue
        anchor = path.replace("/", "").replace(".", "").replace("_", "").lower()
        toc.append(f"- [`{path}`](#{anchor}) — {desc}")
    parts.append("\n".join(toc) + "\n\n---\n")

    total = 0
    for path, lang, desc in FILES:
        full = os.path.join(HERE, path)
        if not os.path.exists(full):
            continue
        src = open(full, encoding="utf-8").read()
        lines = src.count("\n") + 1
        total += lines
        # markdown files get nested in a fenced block deep enough not to collide
        fence = "````" if lang == "md" else "```"
        parts.append(f"\n## `{path}`\n\n*{desc}* — {lines} lines\n\n"
                     f"{fence}{lang}\n{src}\n{fence}\n")
        print(f"  + {path} ({lines} lines)")

    parts.append(f"\n---\n\n*Bundle contains {len(FILES)} files, {total:,} lines total.*\n")
    open(OUT, "w", encoding="utf-8").write("".join(parts))
    kb = os.path.getsize(OUT) / 1024
    print(f"\nWrote BUNDLE.md — {total:,} lines, {kb:.0f} KB")


if __name__ == "__main__":
    main()
