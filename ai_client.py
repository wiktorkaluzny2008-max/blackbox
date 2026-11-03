"""
Shared connector to Groq's chat-completion API (OpenAI-compatible), used by the
historical-analog engine, the AI sentiment scanner and the portfolio narrator.

Fails open: ask() returns None on any failure (missing key, network error,
malformed response) so callers degrade gracefully instead of crashing — same
pattern as sentiment_scanner.read_latest() and the OANDA client.
"""
import json
import logging
import urllib.error
import os
import urllib.request

import config

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
# Groq's edge (Cloudflare) blocks the default urllib User-Agent as bot traffic.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def available():
    if os.getenv('AI_PROVIDER') == 'anthropic':
        return (os.getenv('ANTHROPIC_ENABLED') == '1' and bool(os.getenv('ANTHROPIC_API_KEY'))
                and bool(os.getenv('DATABASE_URL')))
    return bool(config.GROQ_API_KEY)


def ask(prompt, system=None, max_tokens=600, timeout=20):
    """One-shot chat completion. Returns the reply text, or None on any failure."""
    if not available():
        return None
    try:
        from flask import has_request_context, request
        if has_request_context() and request.cookies.get("bb_lang") == "pl":
            system = ((system or "") + "\nRespond in natural Polish. Preserve ticker symbols, numbers, and JSON key names exactly.").strip()
    except ImportError:
        pass
    if os.getenv('AI_PROVIDER') == 'anthropic':
        return _ask_haiku(prompt, system, max_tokens, timeout)
    messages = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": prompt}]
    body = json.dumps({"model": MODEL, "messages": messages, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "User-Agent": UA,
        "Accept": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def ask_json(prompt, system=None, max_tokens=600, timeout=20):
    """Like ask(), but parses the reply as JSON. Returns None if the call or
    the parse fails, so callers never need to handle malformed AI output."""
    text = ask(prompt, system=system, max_tokens=max_tokens, timeout=timeout)
    if text is None:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        return None


def _ask_haiku(prompt, system, max_tokens, timeout):
    """Reserve one cent BEFORE every paid attempt; no retries or paid fallback.

    At the verified Haiku 5.5 price, 24KB input + 1000 output tokens cost well
    below one cent. Conservative reservations are not refunded after failures.
    The database lock makes the monthly cap persist across workers/restarts.
    """
    if not isinstance(prompt, str) or not isinstance(system or '', str):
        return None
    if len((prompt + (system or '')).encode('utf-8')) > 24000:
        return None
    try:
        from decimal import Decimal
        from datetime import datetime, timezone
        from state_store import locked, load, save
        limit = min(1000, int(Decimal(os.getenv('AI_MONTHLY_LIMIT_USD', '10')) * 100))
        if limit <= 0 or not os.getenv('DATABASE_URL'):
            return None
        month = datetime.now(timezone.utc).strftime('%Y-%m')
        # No file fallback: this must survive free-hosting restarts.
        with locked():
            usage = load('ai_budget', '')
            reserved = int(usage.get(month, 0))
            if reserved >= limit:
                return None
            usage[month] = reserved + 1
            save('ai_budget', '', usage)
        body = {'model': 'claude-haiku-5-5',
                'max_tokens': max(1, min(int(max_tokens), 1000)),
                'messages': [{'role': 'user', 'content': prompt}]}
        if system:
            body['system'] = system
        req = urllib.request.Request('https://api.anthropic.com/v1/messages',
            data=json.dumps(body).encode(), headers={
                'Content-Type': 'application/json',
                'x-api-key': os.environ['ANTHROPIC_API_KEY'],
                'anthropic-version': '2023-06-01',
            })
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read())
        if data.get('stop_reason') == 'max_tokens':
            logging.warning('Haiku response exceeded output limit')
            return None
        return ''.join(x.get('text', '') for x in data.get('content', [])
                       if x.get('type') == 'text').strip() or None
    except urllib.error.HTTPError as exc:
        logging.warning('Haiku HTTP failure status=%s', exc.code)
        return None
    except Exception as exc:
        logging.warning('Haiku request failed type=%s', type(exc).__name__)
        return None

