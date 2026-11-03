"""
BLACKBOX — user-facing strategy platform (ETH KI challenge), v2.

The journey: hero -> "Let's go" -> pick your path (7-question quiz where EVERY
answer visibly constrains the result, or build your own mix from raw stats) ->
"Start my Blackbox" -> a personal paper portfolio marked to LIVE markets by the
same strategy rules, with a separate news and historical-evidence screen.
Password authentication persists accounts and portfolios through state_store.
Guest demo portfolios retain a local browser id. Design: premium-site-workflow + emil-design-eng.
"""
import os, json, time, secrets, hashlib
import supabase_auth as sa
from werkzeug.security import generate_password_hash, check_password_hash
from state_store import with_state_lock
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, request, render_template_string, Response, session
from dotenv import load_dotenv

HERE = os.path.dirname(__file__)
load_dotenv(os.path.join(HERE, ".env"))
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
    if os.getenv("DATABASE_URL"):
        raise RuntimeError("APP_SECRET must be set when DATABASE_URL is configured")
    p = os.path.join(HERE, "logs", "app_secret.txt")
    if os.path.exists(p):
        return open(p).read().strip()
    s = secrets.token_hex(32)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(s)
    return s


app.secret_key = _app_secret()
app.permanent_session_lifetime = timedelta(days=60)
app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SECURE=bool(os.getenv("DATABASE_URL")))
_cache = {}


@app.before_request
def reject_cross_origin_mutations():
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('Origin')
        allowed = {request.host_url.rstrip('/'),
                   os.getenv('PUBLIC_APP_URL', 'https://blackbox.wiktor-kaluzny2008.workers.dev').rstrip('/')}
        if origin and origin.rstrip('/') not in allowed:
            return jsonify({'error': 'Cross-origin request rejected'}), 403


@app.after_request
def private_response_headers(response):
    if request.path.startswith('/api/') or request.path == '/account':
        response.headers['Cache-Control'] = 'no-store, private'
        response.vary.add('Cookie')
    return response


def _lang():
    return "pl" if request.cookies.get("bb_lang") == "pl" else "en"


def cached(key, ttl, fn):
    now = time.time()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    v = fn()
    if v is not None and not (isinstance(v, dict) and v.get('available') is False):
        _cache[key] = (now, v)
    return v


def _load(path, default=None):
    if path in (USERS, ACCOUNTS):
        from state_store import load
        return load("users" if path == USERS else "accounts", path)
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def _save_users(u):
    from state_store import save
    save("users", USERS, u)


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


@app.route("/api/historical-analog")
def api_historical_analog():
    try:
        import historical_analog as ha
        doc = ha.read_latest() or ha.analyze()
        return jsonify(doc or {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


@app.route("/api/regime")
def api_regime():
    """Live prediction from our own trained neural network (Regime Radar).
    Distinct from the LLM features — this is a model we trained ourselves."""
    def build():
        import regime_ai, json as _j
        pred = regime_ai.predict("BTC-USD")
        report = _load(os.path.join(HERE, "logs", "regime_report.json"), {})
        if not pred:
            return {"available": False}
        pred["report"] = report
        return pred
    try:
        return jsonify(cached("regime", 1200, build))
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


# ---------------- AI content features (all fail open, all grounded in real data) ----
@app.route("/api/ai/briefing")
def api_ai_briefing():
    try:
        import ai_features
        doc = cached(_lang() + "_ai_briefing", 60, ai_features.briefing)
        return jsonify(doc or {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


@app.route("/api/ai/coach", methods=["POST"])
def api_ai_coach():
    p = request.get_json(force=True, silent=True) or {}
    try:
        import ai_features
        text = ai_features.coach(p.get("question", ""), p.get("history"))
        return jsonify({"answer": text} if text else {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


@app.route("/api/ai/glossary", methods=["POST"])
def api_ai_glossary():
    term = (request.get_json(force=True, silent=True) or {}).get("term", "")
    try:
        import ai_features
        text = cached(_lang() + "_gloss_" + term.strip().lower()[:60], 86400,
                      lambda: ai_features.glossary(term))
        return jsonify({"text": text} if text else {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


@app.route("/api/ai/strategy/<sid>")
def api_ai_strategy(sid):
    try:
        import ai_features
        text = cached(_lang() + "_deepdive_" + sid, 86400, lambda: ai_features.strategy_deep_dive(sid))
        return jsonify({"text": text} if text else {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


@app.route("/api/ai/positioning")
def api_ai_positioning():
    try:
        import ai_features
        doc = cached(_lang() + "_ai_positioning", 1200, ai_features.positioning)
        return jsonify(doc or {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


@app.route("/api/ai/compare", methods=["POST"])
def api_ai_compare():
    p = request.get_json(force=True, silent=True) or {}
    a, b = p.get("a", ""), p.get("b", "")
    try:
        import ai_features
        key = _lang() + "_cmp_" + "_".join(sorted([a, b]))
        text = cached(key, 86400, lambda: ai_features.compare(a, b))
        return jsonify({"text": text} if text else {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


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

    def _parts_blend(m):
        parts, cagr, vol, ddw = [], 0.0, 0.0, 0.0
        for sid, wt in m.items():
            s = cat.get(sid)
            if not s:
                continue
            st = s["stats"]
            parts.append({"id": sid, "name": s["name"], "weight": wt, "risk": s["risk"],
                          "cagr": st["cagr"], "sharpe": st["sharpe"], "max_dd": st["max_dd"]})
            cagr += wt / 100 * st["cagr"]; vol += wt / 100 * st["vol"]; ddw += wt / 100 * st["max_dd"]
        return parts, {"cagr_est": round(cagr, 1), "vol_est": round(vol, 1), "dd_est": round(ddw, 1)}

    parts, blend = _parts_blend(mix)
    freetext = p.get("freetext")
    if freetext:
        try:
            import quiz_nudge
            nudged = quiz_nudge.nudge(mix, parts, freetext)
        except Exception:
            nudged = None
        if nudged:
            mix, reason = nudged
            parts, blend = _parts_blend(mix)
            why.append(f"Your own words: {reason}")
    from market_recs import screen
    market = screen(p, capacity, lang=_lang())
    return jsonify({"tier": tier, "label": TIER_LABELS[tier], "capacity": capacity,
                    "why": [x for x in why if x], "mix": mix, "parts": parts,
                    "blend": blend, "market": market})


@app.route("/api/user/create", methods=["POST"])
@with_state_lock
def user_create():
    a, aid = _me()
    if not a:
        return jsonify({"error": "Sign in to create a portfolio.", "login_required": True}), 401
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
    allowed_profile = {k: str(v)[:120] for k, v in (p.get("profile") or {}).items()
                       if k in {"experience", "horizon", "max_dd", "react", "goal", "priority", "scope"}}
    users[uid] = {"name": name, "mix": mix, "profile": allowed_profile, "created": today,
                  "base_nav": 10000.0, "base_date": today, "history": [[today, 10000.0]]}
    # Signed-in accounts keep previous portfolios in their history.
    a, aid = _me()
    if a:
        old = a.get("uid")
        accounts = _accounts()
        accounts[aid]["uid"] = uid
        accounts[aid]["portfolio_ids"] = list(dict.fromkeys(
            (accounts[aid].get("portfolio_ids") or []) + ([old] if old else []) + [uid]))
        if not p.get("name"):
            users[uid]["name"] = a["name"]
        _save_accounts(accounts)
    _save_users(users)
    if not a:
        session["anon_uid"] = uid
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
    from state_store import save
    save("accounts", ACCOUNTS, a)


def _gen_key():
    return secrets.token_urlsafe(32)


def _hash_key(key, salt):
    return hashlib.sha256((salt + key.strip().lower()).encode()).hexdigest()


def _auth_sessions():
    from state_store import load
    return load('auth_sessions', os.path.join(HERE, 'logs', 'auth_sessions.json'))


def _save_auth_sessions(records):
    from state_store import save
    save('auth_sessions', os.path.join(HERE, 'logs', 'auth_sessions.json'), records)


@with_state_lock
def _supabase_session_user():
    sid = session.get('auth_sid')
    records = _auth_sessions()
    record = records.get(sid)
    if not record or record.get('until', 0) < time.time():
        return None
    tokens = record['tokens']
    try:
        if tokens.get('expires_at', 0) < time.time() + 30:
            tokens = sa.refresh(tokens['refresh_token'])
            record['tokens'] = tokens
            _save_auth_sessions(records)
        user = sa.get_user(tokens['access_token'])
        sa.assert_active(user)
        if user['id'] != record['user_id']:
            return None
        return user
    except sa.AuthError as exc:
        if exc.status >= 500 or exc.status == 429:
            raise  # Outages must not silently destroy a valid login.
        records.pop(sid, None)
        _save_auth_sessions(records)
        session.pop('auth_sid', None)
        session.pop('aid', None)
        return None


def _me():
    aid = session.get('aid')
    account = _accounts().get(aid) if aid else None
    if not account:
        return None, None
    if account.get('supabase_user_id'):
        user = _supabase_session_user()
        if not user or user['id'] != account['supabase_user_id']:
            return None, None
    return account, aid


def _login(aid, tokens=None):
    session.pop('auth_sid', None)
    session.permanent = True
    session['aid'] = aid
    if tokens:
        sa.assert_active(tokens.get('user'))
        records = _auth_sessions()
        now = time.time()
        records = {k: v for k, v in records.items() if v.get('until', 0) > now}
        sid = secrets.token_urlsafe(32)
        records[sid] = {'user_id': tokens['user']['id'], 'tokens': tokens,
                        'until': now + 60 * 86400}
        _save_auth_sessions(records)
        session['auth_sid'] = sid


@app.errorhandler(sa.AuthError)
def auth_service_error(exc):
    messages = {
        'email_not_confirmed': 'Confirm your email before signing in.',
        'user_already_exists': 'This email is already registered. Please sign in.',
        'email_exists': 'This email is already registered. Please sign in.',
        'over_email_send_rate_limit': 'Email limit reached. Please try again later.',
        'over_request_rate_limit': 'Too many attempts. Please try again later.',
    }
    message = messages.get(exc.code, 'Authentication is temporarily unavailable. Please try again.'
                           if exc.status >= 500 else 'Email or password was not recognised.')
    return jsonify({'error': message}), exc.status


def _bind_supabase_user(accounts, tokens, legacy_aid=None):
    user = tokens.get('user') or {}
    sa.assert_active(user)
    suid = user['id']
    aid = next((k for k, a in accounts.items() if a.get('supabase_user_id') == suid), None)
    if legacy_aid:
        if aid and aid != legacy_aid:
            raise sa.AuthError('account_link_conflict', 409)
        aid = legacy_aid
    if aid is None:
        # Never attach a pre-existing portfolio by email alone.
        if any((a.get('email') or '').casefold() == (user.get('email') or '').casefold()
               for a in accounts.values()):
            raise sa.AuthError('account_link_conflict', 409)
        aid = secrets.token_hex(8)
        accounts[aid] = {'name': str((user.get('user_metadata') or {}).get('name') or 'Trader')[:24],
                         'email': user.get('email'), 'created': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                         'uid': None, 'portfolio_ids': []}
        adopt = session.get('anon_uid')
        if adopt and adopt in _load(USERS, {}):
            accounts[aid]['uid'] = adopt
            accounts[aid]['portfolio_ids'] = [adopt]
            session.pop('anon_uid', None)
    accounts[aid]['supabase_user_id'] = suid
    # After migration the old password/recovery key cannot bypass Supabase.
    accounts[aid].pop('password_hash', None)
    accounts[aid].pop('key_hash', None)
    _save_accounts(accounts)
    _login(aid, tokens)
    return accounts[aid]


def _can_access(uid):
    account, _ = _me()
    return bool(account and (account.get("uid") == uid or uid in account.get("portfolio_ids", [])))


@app.route("/api/config")
def api_config():
    return jsonify({"google_client_id": (os.getenv("GOOGLE_CLIENT_ID") or None) if not sa.enabled() else None,
                    "auth_provider": "supabase" if sa.enabled() else "legacy"})


@app.route("/api/i18n/pl")
def polish_translations():
    return jsonify(_load(os.path.join(HERE, "pl.json"), {}))


@app.route("/api/auth/register", methods=["POST"])
@with_state_lock
def auth_register():
    p = request.get_json(force=True, silent=True) or {}
    name = (p.get("name") or "").strip()[:24] or "Trader"
    email = (p.get("email") or "").strip().casefold()
    password = p.get("password") or ""
    if not email or "@" not in email or len(password) < 12:
        return jsonify({"error": "Enter an email and a password of at least 12 characters"}), 400
    accounts = _accounts()
    if any((a.get("email") or "").casefold() == email for a in accounts.values()):
        return jsonify({"error": "email already registered"}), 409
    if sa.enabled():
        result = sa.signup(email, password, name)
        if not result.get('access_token'):
            return jsonify({'ok': True, 'confirmation_required': True})
        account = _bind_supabase_user(accounts, result)
        return jsonify({'ok': True, 'name': account['name']})
    aid = secrets.token_hex(8)
    key = _gen_key()
    salt = secrets.token_hex(8)
    acct = {"name": name, "salt": salt,
            "key_hash": generate_password_hash(key, method="pbkdf2:sha256:600000"),
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "uid": None, "google_sub": None, "email": email, "picture": None,
            "password_hash": generate_password_hash(password, method="pbkdf2:sha256:600000")}
    adopt = p.get("adopt_uid")
    if adopt and adopt == session.get("anon_uid") and adopt in _load(USERS, {}):
        acct["uid"] = adopt
        acct["portfolio_ids"] = [adopt]
        session.pop("anon_uid", None)
    accounts[aid] = acct
    _save_accounts(accounts)
    _login(aid)
    _notify(f"New platform account: \"{name}\" (recovery-key), total {len(accounts)}")
    return jsonify({"ok": True, "name": name, "recovery_key": key})


@app.route("/api/auth/password", methods=["POST"])
@with_state_lock
def auth_password():
    p = request.get_json(force=True, silent=True) or {}
    email = (p.get("email") or "").strip().casefold()
    password = p.get("password") or ""
    if len(email) > 254 or len(password) > 1024:
        return jsonify({"error": "invalid credentials"}), 401
    if sa.enabled():
        accounts = _accounts()
        legacy_aid = next((k for k, a in accounts.items()
                           if (a.get('email') or '').casefold() == email and not a.get('supabase_user_id')), None)
        if legacy_aid:
            legacy = accounts[legacy_aid]
            if not legacy.get('password_hash') or not check_password_hash(legacy['password_hash'], password):
                return jsonify({'error': 'Email or password was not recognised.'}), 401
            try:
                sa.migrate(email, password, legacy['name'], legacy_aid)
            except sa.AuthError as exc:
                if exc.code not in {'email_exists', 'user_already_exists'}:
                    raise
            # A duplicate is safe only if Supabase also verifies the supplied password.
        tokens = sa.signin(email, password)
        account = _bind_supabase_user(accounts, tokens, legacy_aid)
        return jsonify({'ok': True, 'name': account['name']})
    for aid, account in _accounts().items():
        if ((account.get("email") or "").casefold() == email
                and account.get("password_hash")
                and check_password_hash(account["password_hash"], password)):
            _login(aid)
            return jsonify({"ok": True, "name": account["name"]})
    return jsonify({"error": "invalid credentials"}), 401


@app.route("/api/auth/recover", methods=["POST"])
def auth_recover():
    p = request.get_json(force=True, silent=True) or {}
    key = (p.get("key") or "")
    accounts = _accounts()
    for aid, a in accounts.items():
        if sa.enabled() and a.get("supabase_user_id"):
            continue
        stored = a.get("key_hash") or ""
        valid = (check_password_hash(stored, key) if stored.startswith("pbkdf2:")
                 else secrets.compare_digest(stored, _hash_key(key, a.get("salt") or "")))
        if stored and valid:
            _login(aid)
            return jsonify({"ok": True, "name": a["name"]})
    return jsonify({"error": "key not recognised"}), 401


@app.route("/api/auth/google", methods=["POST"])
@with_state_lock
def auth_google():
    if sa.enabled():
        return jsonify({"error": "Please use email and password to sign in."}), 400
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
        if adopt and adopt == session.get("anon_uid") and adopt in _load(USERS, {}):
            accounts[aid]["uid"] = adopt
            accounts[aid]["portfolio_ids"] = [adopt]
            session.pop("anon_uid", None)
        _notify(f"New platform account: \"{accounts[aid]['name']}\" (Google), total {len(accounts)}")
    accounts[aid]["email"] = info.get("email")
    accounts[aid]["picture"] = info.get("picture")
    _save_accounts(accounts)
    _login(aid)
    return jsonify({"ok": True, "name": accounts[aid]["name"]})


@app.route("/api/auth/logout", methods=["POST"])
@with_state_lock
def auth_logout():
    sid = session.get('auth_sid')
    if sid:
        records = _auth_sessions()
        record = records.pop(sid, None)
        _save_auth_sessions(records)
        if record:
            try:
                sa.signout(record['tokens']['access_token'])
            except sa.AuthError:
                pass  # Local session is revoked even if the provider is unavailable.
    session.pop('auth_sid', None)
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    a, aid = _me()
    if not a:
        return jsonify({"signed_in": False})
    portfolio = _user_payload(a["uid"]) if a.get("uid") else None
    return jsonify({"signed_in": True, "name": a["name"], "email": a.get("email"),
                    "picture": a.get("picture"), "google": bool(a.get("google_sub")),
                    "portfolio_ids": a.get("portfolio_ids", [a["uid"]] if a.get("uid") else []),
                    "portfolio": portfolio})


def _user_payload(uid):
    users = _load(USERS, {})
    u = users.get(uid)
    if not u:
        return None
    try:
        from user_engine import marks
        mk = marks(u["mix"])["strategies"]
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
            "profile": u.get("profile", {}),
            "nav": nav_now, "day_ret": round(day * 100, 3),
            "since_start": round((nav_now / 10000 - 1) * 100, 2),
            "history": u["history"], "strategies": strat_view,
            "note": "Paper portfolio marked to live markets by the same validated rules. Estimates, not investment advice."}


@app.route("/api/user/<uid>", methods=["GET"])
def user_get(uid):
    if not _can_access(uid):
        return jsonify({"error": "forbidden"}), 403
    p = _user_payload(uid)
    if not p:
        return jsonify({"error": "not found"}), 404
    return jsonify(p)


@app.route("/api/user/<uid>/narrate")
def user_narrate(uid):
    if not _can_access(uid):
        return jsonify({"error": "forbidden"}), 403
    p = _user_payload(uid)
    if not p:
        return jsonify({"error": "not found"}), 404
    try:
        import portfolio_narrator as pn
        text = cached(_lang() + "_narrate_" + uid, 900, lambda: pn.narrate(p))
        return jsonify({"text": text} if text else {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


@app.route("/api/user/<uid>/ask", methods=["POST"])
def user_ask(uid):
    if not _can_access(uid):
        return jsonify({"error": "forbidden"}), 403
    p = _user_payload(uid)
    if not p:
        return jsonify({"error": "not found"}), 404
    q = (request.get_json(force=True, silent=True) or {}).get("question", "")
    try:
        import portfolio_narrator as pn
        text = pn.answer(p, q)
        return jsonify({"answer": text} if text else {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


@app.route("/api/user/<uid>/review")
def user_review(uid):
    if not _can_access(uid):
        return jsonify({"error": "forbidden"}), 403
    p = _user_payload(uid)
    if not p:
        return jsonify({"error": "not found"}), 404
    try:
        import ai_features
        mixkey = _lang() + "_review_" + uid + "_" + "_".join(f"{k}{v}" for k, v in sorted((p.get("mix") or {}).items()))
        text = cached(mixkey, 3600, lambda: ai_features.portfolio_review(p))
        return jsonify({"text": text} if text else {"available": False})
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})


@app.route("/api/user/<uid>/delete", methods=["POST"])
@with_state_lock
def user_delete(uid):
    if not _can_access(uid):
        return jsonify({"error": "forbidden"}), 403
    users = _load(USERS, {})
    users.pop(uid, None)
    _save_users(users)
    a, aid = _me()
    if a and a.get("uid") == uid:
        accounts = _accounts()
        accounts[aid]["uid"] = None
        accounts[aid]["portfolio_ids"] = [x for x in accounts[aid].get("portfolio_ids", []) if x != uid]
        _save_accounts(accounts)
    elif a and uid in a.get("portfolio_ids", []):
        accounts = _accounts()
        accounts[aid]["portfolio_ids"] = [x for x in a["portfolio_ids"] if x != uid]
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
@app.route("/start")
@app.route("/strategies")
@app.route("/briefing")
@app.route("/intel")
@app.route("/learn")
@app.route("/ai")
@app.route("/compare")
@app.route("/account")
def index():
    return render_template_string(PAGE)


PAGE = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blackbox — Real strategies. Real numbers.</title>
<link rel="icon" href="/icon.png"><link rel="apple-touch-icon" href="/icon.png">
<meta name="theme-color" content="#0B0906">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700;9..144,800&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<script src="https://accounts.google.com/gsi/client" async defer></script>
<style>
:root{--bg:#0B0906;--surface:#171310;--surface2:#1F1912;--line:rgba(201,168,106,.16);
--txt:#F3ECDD;--mut:#A79A82;--acc:#C9A961;--acc2:#B08D4F;--deep:#8B6B32;
--green:#5FBF8F;--red:#E2716B;--ease:cubic-bezier(.22,1,.36,1)}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--txt);font:16px/1.6 'Inter',sans-serif;-webkit-font-smoothing:antialiased;overflow-x:hidden}
h1,h2,h3{font-family:'Fraunces','Inter',serif;letter-spacing:-.01em}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
.rv{opacity:0;transform:translateY(24px);transition:opacity .7s var(--ease),transform .7s var(--ease)}
.rv.in{opacity:1;transform:none}
.hero{position:relative;min-height:100svh;display:flex;align-items:center;overflow:hidden}
.orb{position:absolute;border-radius:50%;filter:blur(90px);opacity:.5;pointer-events:none}
.o1{width:560px;height:560px;background:radial-gradient(circle,#C9A96155,transparent 65%);top:-120px;left:-120px;animation:d1 22s ease-in-out infinite}
.o2{width:640px;height:640px;background:radial-gradient(circle,#8B6B3245,transparent 65%);bottom:-200px;right:-160px;animation:d2 26s ease-in-out infinite}
@keyframes d1{50%{transform:translate(70px,50px)}}
@keyframes d2{50%{transform:translate(-60px,-40px)}}
.hero::after{content:"";position:absolute;inset:0;background:rgba(11,9,6,.3)}
.hero .wrap{position:relative;z-index:2;padding:90px 24px 60px}
.kicker{display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--acc);
border:1px solid var(--line);border-radius:999px;padding:7px 14px;background:rgba(201,168,106,.07);margin-bottom:26px}
.kicker .dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 10px var(--green);animation:pl 2.4s infinite}
@keyframes pl{50%{opacity:.4}}
h1{font-family:'Fraunces','Inter',serif;font-size:clamp(42px,7.2vw,88px);font-weight:600;font-style:italic;line-height:1.05}
h1 .w{display:inline-block;opacity:0;transform:translateY(26px);animation:win .7s var(--ease) forwards}
@keyframes win{to{opacity:1;transform:none}}
.grad{background:linear-gradient(92deg,#E8D5A3,#C9A961);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;font-style:normal}
.sub{max-width:560px;color:var(--mut);font-size:18px;margin:24px 0 36px}
.cta{display:inline-flex;align-items:center;gap:10px;background:linear-gradient(135deg,#DCBB78,#B08D4F);
color:#1A140A;font-weight:700;font-size:16px;padding:16px 30px;border-radius:14px;border:0;cursor:pointer;
box-shadow:0 10px 40px -8px rgba(160,124,58,.55);transition:transform .16s var(--ease),box-shadow .2s var(--ease)}
.cta:hover{box-shadow:0 14px 52px -8px rgba(160,124,58,.75)}
.cta:active{transform:scale(.97)}
.cta.ghost{background:var(--surface2);border:1px solid var(--line);box-shadow:none;color:var(--txt)}
.cta:disabled{opacity:.45;cursor:not-allowed}
.hstats{display:flex;gap:34px;margin-top:56px;flex-wrap:wrap}
.hstat .n{font-family:'Fraunces';font-size:26px;font-weight:700}
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
.mode.on{border-color:var(--acc);background:rgba(201,168,106,.08)}
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
.chip.on{border-color:var(--acc);color:var(--txt);background:rgba(201,168,106,.18)}
.reco{display:none;margin-top:30px;border-top:1px solid var(--line);padding-top:28px}
.reco.show{display:block;animation:fup .5s var(--ease)}
.why{margin:14px 0 4px;padding:0 0 0 2px}
.why li{list-style:none;color:var(--mut);font-size:14px;padding:5px 0 5px 26px;position:relative}
.why li::before{content:"→";position:absolute;left:0;color:var(--acc)}
.blend{display:flex;gap:26px;flex-wrap:wrap;margin:18px 0 8px}
.b .n{font-family:'Inter';font-size:22px;font-weight:800}
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
.qtext{width:100%;background:var(--surface2);border:1px solid var(--line);border-radius:12px;color:var(--txt);
padding:14px 16px;font:400 14.5px/1.6 'Inter';resize:vertical;min-height:80px}
.qtext:focus{outline:none;border-color:var(--acc)}
/* builder */
.builderwrap{display:none;margin-top:22px}
.bbar{position:sticky;bottom:14px;z-index:30;background:rgba(23,19,16,.92);backdrop-filter:blur(12px);
border:1px solid var(--line);border-radius:18px;padding:16px 22px;display:flex;gap:20px;align-items:center;flex-wrap:wrap;
box-shadow:0 18px 50px -20px rgba(0,0,0,.7);margin-top:26px}
.bbar .tot{font-family:'Inter';font-weight:800;font-size:22px}
.bbar .bs{font-size:13px;color:var(--mut)}
.step{display:flex;align-items:center;gap:8px;margin-top:14px}
.step button{width:34px;height:34px;border-radius:10px;border:1px solid var(--line);background:var(--surface2);
color:var(--txt);font-size:17px;font-weight:700;cursor:pointer;transition:transform .13s}
.step button:active{transform:scale(.92)}
.step .v{font-family:'Inter';font-weight:800;min-width:52px;text-align:center;font-size:17px}
/* catalog */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px;margin-top:44px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:24px;cursor:pointer;
transition:transform .22s var(--ease),border-color .22s,box-shadow .22s var(--ease)}
@media(hover:hover){.card:hover{transform:translateY(-4px);border-color:rgba(201,168,106,.5);box-shadow:0 18px 50px -20px rgba(160,124,58,.5)}}
.card .top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px}
.card h3{font-size:19px;line-height:1.25}
.badge{font-size:11px;font-weight:700;padding:4px 10px;border-radius:999px;white-space:nowrap}
.badge.Conservative{background:rgba(95,191,143,.14);color:var(--green)}
.badge.Moderate{background:rgba(201,168,106,.16);color:var(--acc)}
.badge.High{background:rgba(251,191,36,.13);color:#fbbf24}
.badge.VeryHigh{background:rgba(251,113,133,.13);color:var(--red)}
.card .tag{color:var(--mut);font-size:14px;min-height:44px;margin-bottom:12px}
.sentchip{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:700;border-radius:999px;
padding:4px 11px;margin-bottom:12px;background:var(--surface2);border:1px solid var(--line)}
.sentchip .sd{width:7px;height:7px;border-radius:50%}
.spark{width:100%;height:56px;display:block;margin-bottom:14px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.st .n{font-family:'Inter';font-weight:800;font-size:16.5px}
.st .l{font-size:10.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
/* modal */
.mask{position:fixed;inset:0;background:rgba(8,6,4,.72);backdrop-filter:blur(6px);z-index:50;display:none;align-items:center;justify-content:center;padding:20px}
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
.hchip .n{font-family:'Inter';font-weight:800;font-size:15px;display:block}
.method{font-size:14px;color:var(--mut);line-height:1.65;margin-top:20px;border-left:3px solid var(--deep);padding-left:14px}
/* me */
#me{background:var(--surface);border-block:1px solid var(--line)}
.mehead{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;flex-wrap:wrap}
.nav-big{font-family:'Fraunces';font-size:clamp(40px,6vw,64px);font-weight:600;letter-spacing:-.01em}
.pill{display:inline-block;font-size:13px;font-weight:700;border-radius:999px;padding:6px 14px;margin-left:8px;vertical-align:14px}
.pill.up{background:rgba(95,191,143,.15);color:var(--green)}
.pill.dn{background:rgba(226,113,107,.15);color:var(--red)}
.metric-term{cursor:help;border-bottom:1px dotted var(--acc);transition:color .15s}
.metric-term:hover{color:var(--acc)}
.mpop{position:fixed;z-index:70;max-width:300px;background:var(--surface2);border:1px solid var(--acc);
border-radius:14px;padding:14px 16px;box-shadow:0 20px 50px -18px rgba(0,0,0,.8);font-size:13px;line-height:1.6;color:var(--txt)}
.mpop h5{font-size:13px;color:var(--acc);margin-bottom:6px;font-family:'Inter';font-weight:700}
.dstats{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:14px 10px}
.dstat .dn{font-family:'Inter';font-weight:800;font-size:18px}
.dstat .dl{font-size:10.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em;margin-top:2px}
.mehead-btns{display:flex;gap:10px;flex-wrap:wrap}
.badges{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}
.badge2{display:flex;align-items:center;gap:8px;background:var(--surface2);border:1px solid var(--line);
border-radius:999px;padding:8px 14px;font-size:12.5px;font-weight:600;cursor:default}
.badge2 .be{font-size:15px}
.badge2 .bt{color:var(--txt)}
.megrid{display:grid;grid-template-columns:1.2fr 1fr;gap:20px;margin-top:32px}
@media(max-width:900px){.megrid{grid-template-columns:1fr}}
.scard2{background:var(--surface2);border:1px solid var(--line);border-radius:18px;padding:20px;margin-top:14px}
.scard2 .h2r{display:flex;justify-content:space-between;align-items:center;gap:10px}
.scard2 h3{font-size:16.5px}
.wtag{font-family:'Inter';font-weight:800;color:var(--acc)}
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
.gauge{height:10px;border-radius:5px;background:linear-gradient(90deg,#E2716B,#2B241A 50%,#5FBF8F);position:relative;margin:10px 0 6px}
.gauge i{position:absolute;top:-4px;width:4px;height:18px;border-radius:2px;background:#fff;box-shadow:0 0 8px rgba(255,255,255,.6);transition:left .8s var(--ease)}
.sscore{font-family:'Inter';font-weight:800;font-size:22px}
.sexp{font-size:13.5px;color:var(--mut);margin:10px 0 12px;min-height:40px}
.head{font-size:12.5px;padding:8px 0;border-top:1px solid rgba(201,168,106,.1);color:var(--mut);display:flex;gap:8px;justify-content:space-between}
.acard{background:var(--surface2);border:1px solid var(--line);border-radius:20px;padding:26px;margin-top:32px}
.acard .ah{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
.acard h3{font-size:19px}
.adate{font-size:13px;color:var(--mut);white-space:nowrap}
.areason{font-size:13.5px;color:var(--mut);margin:14px 0 20px;padding:12px 14px;background:rgba(201,168,106,.07);border-radius:12px;border-left:2px solid var(--acc)}
.agrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.arow{display:flex;justify-content:space-between;padding:11px 13px;background:var(--surface);border-radius:10px;font-size:13px}
.askel{color:var(--mut);font-size:14px;display:flex;align-items:center;gap:10px;padding:20px 0}
.qarow{font-size:13.5px;padding:10px 0;border-top:1px solid rgba(201,168,106,.1)}
.qarow .q{color:var(--txt);font-weight:600;margin-bottom:4px}
.qarow .a{color:var(--mut)}
.qform{display:flex;gap:8px;margin-top:12px}
.qform .ain{padding:11px 14px;font-weight:500;font-size:14px}
.head .t{flex:1}
.head .s{white-space:nowrap;font-weight:700}
/* Regime Radar (our own trained model) */
.regcard{background:linear-gradient(135deg,rgba(201,168,106,.08),rgba(201,168,106,.02));border:1px solid var(--acc);border-radius:22px;padding:30px;margin-top:30px}
.reghead{display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.regverdict{font-family:'Fraunces';font-style:italic;font-weight:600;font-size:clamp(34px,6vw,54px);line-height:1}
.regverdict.calm{color:var(--green)}.regverdict.turbulent{color:var(--red)}
.regmeta{color:var(--mut);font-size:13.5px}
.reggauge{height:12px;border-radius:6px;background:linear-gradient(90deg,#5FBF8F,#DCBB78,#E2716B);position:relative;margin:22px 0 8px}
.reggauge i{position:absolute;top:-5px;width:5px;height:22px;border-radius:3px;background:#fff;box-shadow:0 0 8px rgba(255,255,255,.7);transition:left .8s var(--ease)}
.regstats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:14px;margin-top:22px}
.regstat{background:var(--surface2);border:1px solid var(--line);border-radius:14px;padding:14px}
.regstat .rn{font-family:'Inter';font-weight:800;font-size:20px}
.regstat .rl{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em;margin-top:3px}
.regnote{font-size:13.5px;color:var(--mut);line-height:1.7;margin-top:20px;border-left:3px solid var(--acc);padding-left:16px}
.regtable{width:100%;border-collapse:collapse;font-size:13px;margin-top:14px}
.regtable th,.regtable td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line)}
.regtable th{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
.regtable td.win{color:var(--green);font-weight:700}
/* AI Inside explainer page */
.principle{background:linear-gradient(135deg,rgba(201,168,106,.1),rgba(201,168,106,.03));border:1px solid var(--acc);
border-radius:20px;padding:28px;margin-top:34px}
.principle .pbig{font-family:'Fraunces';font-style:italic;font-size:clamp(22px,3.2vw,30px);font-weight:600;color:var(--txt);margin-bottom:12px}
.principle p{color:var(--mut);font-size:15px;line-height:1.7}
.airole-h{font-family:'Fraunces';font-weight:600;font-size:22px;margin:48px 0 4px}
.capgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin-top:18px}
.capcard{background:var(--surface2);border:1px solid var(--line);border-radius:18px;padding:22px}
.capcard .capi{font-size:26px;margin-bottom:10px}
.capcard h4{font-size:16.5px;margin-bottom:8px}
.capcard p{color:var(--mut);font-size:13.8px;line-height:1.65}
.honesty{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:28px;margin-top:48px}
.honesty h3{font-size:22px;margin-bottom:16px}
.honesty ul{list-style:none;padding:0}
.honesty li{color:var(--mut);font-size:14px;line-height:1.7;padding:12px 0 12px 26px;position:relative;border-top:1px solid var(--line)}
.honesty li:first-child{border-top:0}
.honesty li::before{content:"✓";position:absolute;left:0;color:var(--acc);font-weight:700}
.honesty b{color:var(--txt)}
.aitech{margin-top:34px;border-left:3px solid var(--deep);padding:6px 0 6px 18px}
.aitech h4{font-size:14px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin-bottom:8px}
.aitech p{color:var(--mut);font-size:14px;line-height:1.7}
/* AI content: briefing / positioning / learn / compare */
.airich{font-size:14.5px;line-height:1.75;color:var(--txt);white-space:pre-wrap}
.briefrow{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}
.bscore{flex:1;min-width:100px;background:var(--surface2);border:1px solid var(--line);border-radius:14px;padding:14px}
.bscore .ba{font-size:11px;color:var(--mut);text-transform:capitalize}
.bscore .bv{font-family:'Inter';font-weight:800;font-size:22px;margin-top:3px}
.posgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px;margin-top:36px}
.poscard{background:var(--surface2);border:1px solid var(--line);border-radius:18px;padding:20px}
.poscard h3{font-size:16.5px;display:flex;justify-content:space-between;align-items:center;gap:10px}
.postag{font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px}
.postag.brake{background:rgba(226,113,107,.14);color:var(--red)}
.postag.clear{background:rgba(95,191,143,.14);color:var(--green)}
.posnote{font-size:13.5px;color:var(--mut);line-height:1.65;margin-top:10px}
.poshold{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.poshold .htag{font-size:11.5px;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:4px 9px;color:var(--mut)}
.glchip{border:1px solid var(--line);background:var(--surface2);color:var(--txt);border-radius:999px;padding:9px 15px;font-size:13.5px;font-weight:600;cursor:pointer;transition:border-color .2s,background .2s}
.glchip:hover{border-color:var(--acc)}
.glchip.on{border-color:var(--acc);background:rgba(201,168,106,.12)}
.cmppick{display:flex;gap:16px;align-items:flex-end;margin-top:30px;flex-wrap:wrap}
.cmplabel{display:block;font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
.cmpsel{min-width:220px;cursor:pointer}
.cmpvs{font-family:'Fraunces';font-style:italic;color:var(--mut);padding-bottom:12px}
.cmptable{width:100%;border-collapse:collapse;font-size:14px}
.cmptable th,.cmptable td{padding:12px 14px;text-align:left;border-bottom:1px solid var(--line)}
.cmptable th{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.cmptable td.metric{color:var(--mut)}
.cmptable td.val{font-family:'Inter';font-weight:700;color:var(--txt)}
/* top nav + auth */
.topnav{position:fixed;top:0;left:0;right:0;z-index:40;background:rgba(11,9,6,.65);
backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}
.tn{display:flex;align-items:center;min-height:60px;gap:14px;max-width:1440px}
.brand{font-family:'Fraunces';font-weight:600;font-style:italic;font-size:17px;letter-spacing:.02em;cursor:pointer;flex-shrink:0}
.navlinks{display:flex;gap:2px;flex:1;min-width:0;overflow-x:auto;scrollbar-width:none;-ms-overflow-style:none}
.navlinks::-webkit-scrollbar{display:none}
.navlinks a{color:var(--mut);font-size:13px;font-weight:600;padding:8px 12px;border-radius:999px;cursor:pointer;transition:color .2s,background .2s;white-space:nowrap;flex-shrink:0}
.navlinks a:hover{color:var(--txt)}
.navlinks a.on{color:var(--acc);background:rgba(201,168,106,.1)}
.language{background:var(--surface2);color:var(--txt);border:1px solid var(--line);border-radius:9px;padding:7px 6px;font-size:12px;flex-shrink:0}
#authbox{flex-shrink:0}
.cta.small{padding:9px 18px;font-size:14px;border-radius:11px}
.uchip{display:flex;gap:10px;align-items:center}
.uchip img{width:30px;height:30px;border-radius:50%;border:1px solid var(--line)}
.uinit{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#DCBB78,#B08D4F);
display:grid;place-items:center;font-weight:800;font-size:14px;color:#1A140A}
.uchip .un{font-weight:600;font-size:14px;max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.amodal{max-width:440px}
.ain{width:100%;background:var(--surface2);border:1px solid var(--line);border-radius:12px;color:var(--txt);
padding:14px 16px;font:600 15px 'Inter'}
.ain:focus{outline:none;border-color:var(--acc)}
.aerr{color:var(--red);font-size:13px;margin-top:10px;min-height:16px}
.keybox{font-family:'Inter';font-weight:800;font-size:19px;letter-spacing:.04em;text-align:center;
background:var(--surface2);border:1px dashed rgba(201,168,106,.55);border-radius:14px;padding:18px 14px;margin-top:14px;
user-select:all;word-break:break-all}
.ordiv{display:flex;align-items:center;gap:12px;color:var(--mut);font-size:12px;margin:16px 0}
.ordiv::before,.ordiv::after{content:"";flex:1;height:1px;background:var(--line)}
@media(max-width:640px){.uchip .un{display:none}}
footer{border-top:1px solid var(--line);padding:44px 0 60px;color:var(--mut);font-size:13px}
footer .d{max-width:820px;line-height:1.7}
@media(prefers-reduced-motion:reduce){.rv,.orb,h1 .w,.gauge i{animation:none!important;transition:none!important;opacity:1!important;transform:none!important}}
@media(max-width:640px){section{padding:64px 0}.quiz{padding:24px}.stats{grid-template-columns:repeat(2,1fr);gap:12px}}
/* Whole translated phrases retain their spacing and wrap naturally. */
h1{line-height:1.12;max-width:1050px}
h1 .hero-line{display:block;text-wrap:balance;overflow-wrap:break-word}
@media(max-width:1250px){
 .tn{flex-wrap:wrap;gap:8px 12px;padding-top:10px;padding-bottom:10px}
 .tn .brand{margin-right:auto}
 .navlinks{order:4;flex:0 0 100%;width:100%;padding-bottom:3px;scrollbar-width:thin}
 .navlinks::-webkit-scrollbar{display:block;height:3px}
 .navlinks::-webkit-scrollbar-thumb{background:var(--line);border-radius:3px}
 .hero .wrap{padding-top:150px}
 section:not(.hero){scroll-margin-top:120px}
}
@media(max-width:480px){
 .tn{column-gap:8px}
 .tn .cta.small{padding:9px 10px;font-size:13px}
 .tn .brand{font-size:16px}
 .hero .wrap{padding-top:145px;padding-bottom:48px}
 h1{font-size:clamp(36px,10vw,46px)}
 .kicker{font-size:11px;line-height:1.5;max-width:100%}
 .sub{font-size:16px}
 .hstats{gap:22px;margin-top:36px}
 .hstat{flex:1 1 135px;min-width:0}
}
</style></head><body>

<nav class="topnav"><div class="wrap tn">
  <div class="brand" onclick="go('home')">BLACKBOX</div>
  <div class="navlinks">
    <a data-page="home" onclick="go('home')">Home</a>
    <a data-page="start" onclick="go('start')">Start</a>
    <a data-page="strategies" onclick="go('strategies')">Strategies</a>
    <a data-page="briefing" onclick="go('briefing')">Briefing</a>
    <a data-page="intel" onclick="go('intel')">Intelligence</a>
    <a data-page="learn" onclick="go('learn')">Learn</a>
    <a data-page="ai" onclick="go('ai')">AI Inside</a>
    <a data-page="compare" onclick="go('compare')">Compare</a>
    <a data-page="account" onclick="go('account')">Your Blackbox</a>
  </div>
  <select class="language" id="language" aria-label="Language" onchange="changeLanguage(this.value)">
    <option value="en">English</option><option value="pl">Polski</option>
  </select>
  <div id="authbox"><button class="cta ghost small" onclick="openAuth()">Sign in</button></div>
</div></nav>

<div id="page-home">
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
</div>

<div id="page-start" style="display:none">
<section id="journey" style="padding-top:150px">
  <div class="wrap">
    <div class="rv"><div class="sec-k">01 — Start your journey</div>
    <h2>Two ways in. One press of go.</h2>
    <p class="lead">Answer seven questions and every answer visibly shapes the outcome — or skip the quiz and build your own mix straight from the numbers.</p></div>
    <div class="modes rv">
      <div class="mode" id="modeQuiz" onclick="setMode('quiz')"><h3>🧭 Guide me</h3><p>A seven-question profile. We show exactly which answers capped or shaped your mix — no black box.</p></div>
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
      <div class="q"><div class="ql">7 · What kind of ideas would you like to explore?</div>
        <div class="chips" data-k="scope"><button class="chip on" data-v="areas">Broad investment areas</button><button class="chip" data-v="specific">Specific stocks and commodity funds</button></div>
        <div class="note" style="margin-top:6px">We screen historical prices and show the data date. These are research ideas, not trade instructions.</div></div>
      <div class="q">
        <div class="ql">In your own words — anything about your situation, goals or concerns the six questions didn't capture? (optional)</div>
        <textarea class="qtext" id="freetext" rows="3" placeholder="e.g. I just had a baby and want to be a bit more careful than usual, even though my risk tolerance on paper is high…"></textarea>
        <div class="note" style="margin-top:6px">If you write something here, AI reads it and may apply a small, bounded adjustment to your mix — it can never override the validated math above, only nudge it, and it always explains why.</div>
      </div>
      <button class="cta" onclick="recommend()">Build my mix →</button>
      <div class="reco" id="reco"></div>
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
</div>

<div id="page-strategies" style="display:none">
<section id="catalog" style="padding-top:150px">
  <div class="wrap">
    <div class="rv in"><div class="sec-k">01 — The strategies</div>
    <h2>Real numbers. Nothing invented.</h2>
    <p class="lead">Every stat is a 20-year backtest — true drawdowns included. The AI scanner's live read is on every card. Click a card for the full profile.</p></div>
    <div class="builderwrap" id="builderwrap">
      <p class="lead" style="margin-top:6px">Set weights with the steppers on the strategy cards below. Your mix must total 100%.</p>
      <div class="bbar" id="bbar">
        <div><div class="tot" id="btot">0%</div><div class="bs">allocated</div></div>
        <div style="flex:1;min-width:180px"><div class="mixbar" id="bmix" style="margin:0 0 6px"></div><div class="bs" id="bstats">—</div></div>
        <button class="cta" id="bgo" disabled onclick="showName(builderMix())">Let's go →</button>
      </div>
    </div>
    <div class="grid" id="cards"></div>
  </div>
</section>
</div>

<div id="page-intel" style="display:none">
<section style="padding-top:150px">
  <div class="wrap">
    <div class="rv in"><div class="sec-k">Our own AI · trained from scratch</div>
    <h2>Regime Radar</h2>
    <p class="lead">This is the one model we <em>built and trained ourselves</em> — a neural network, not a borrowed language model. It learned from ~10 years of real daily market data (about 30,000 examples) to forecast whether the days ahead will be <b>turbulent</b> (high volatility) or <b>calm</b>. Every other AI feature in Blackbox uses a pre-trained model; this one we trained. Here is its live call and its honest, measured track record.</p></div>
    <div id="regimeBox"></div>
  </div>
</section>

<section id="intel" style="background:var(--surface);border-block:1px solid var(--line)">
  <div class="wrap">
    <div class="rv in"><div class="sec-k">AI market intelligence</div>
    <h2>The scanner reads the market's mood</h2>
    <p class="lead">An NLP engine scans hundreds of news and social sources, scores each asset class, explains itself — and trims exposure in your Blackbox when it turns strongly bearish on a strategy's assets.</p></div>
    <div class="sgrid" id="sgrid"></div>
  </div>
</section>

<section id="analog">
  <div class="wrap">
    <div class="rv in"><div class="sec-k">02 — Historical analog</div>
    <h2>Where has the market seen this before?</h2>
    <p class="lead">AI reads today's real headlines and matches them to the closest event from a fixed library of real past market events — then shows how each strategy's real, backtested returns actually moved in the months after. AI only picks which past event fits; every number comes from the same 20-year backtests as the rest of the app.</p></div>
    <div id="analogBox"></div>
  </div>
</section>

<section id="positioning" style="background:var(--surface);border-block:1px solid var(--line)">
  <div class="wrap">
    <div class="rv in"><div class="sec-k">03 — AI positioning desk</div>
    <h2>How AI is supporting each strategy right now</h2>
    <p class="lead">Each strategy's position is decided by its validated rule. On top of that, the AI reads the live news sentiment for that strategy's assets and acts as a risk brake — trimming exposure to 75% when the mood turns strongly bearish. Below, AI explains each strategy's current stance and how the overlay is supporting it. The rule is the driver; the AI is the co-pilot.</p></div>
    <div id="posGrid"></div>
  </div>
</section>
</div>

<div id="page-briefing" style="display:none">
<section style="padding-top:150px">
  <div class="wrap" style="max-width:900px">
    <div class="rv in"><div class="sec-k">Daily briefing</div>
    <h2>Today's market, read by AI</h2>
    <p class="lead">News refreshes on demand when you visit this page. The briefing uses recent scans only and reports their time and source count. Source availability varies; this is educational commentary, not investment advice.</p></div>
    <div id="briefingScores" class="briefrow"></div>
    <div id="briefingBox" class="acard" style="margin-top:22px"></div>
    <div class="note" style="margin-top:14px">Free hosting may sleep between visits. News is refreshed on demand, not continuously.</div>
  </div>
</section>
</div>

<div id="page-learn" style="display:none">
<section style="padding-top:150px">
  <div class="wrap" style="max-width:900px">
    <div class="rv in"><div class="sec-k">Learn</div>
    <h2>Understand what you're investing in</h2>
    <p class="lead">Systematic investing has its own vocabulary. Tap any term below for a plain-English explanation from the AI, or ask the tutor anything — how a strategy works, what a metric means, why diversification lowers risk. It's grounded in this app's own real strategies, and it never gives buy/sell advice.</p></div>

    <h3 style="margin-top:34px;font-size:20px">Key terms — tap to explain</h3>
    <div class="chips" id="glossChips" style="margin-top:14px"></div>
    <div id="glossBox" class="acard" style="margin-top:18px;display:none"></div>

    <h3 style="margin-top:40px;font-size:20px">Ask the AI tutor</h3>
    <div class="acard" style="margin-top:14px">
      <div id="coachLog"></div>
      <div class="qform"><input class="ain" id="coachInput" placeholder="e.g. Why does gold do well when yields fall?" onkeydown="if(event.key==='Enter')askCoach()">
        <button class="cta ghost small" onclick="askCoach()">Ask</button></div>
    </div>
  </div>
</section>
</div>

<div id="page-ai" style="display:none">
<section style="padding-top:150px">
  <div class="wrap" style="max-width:940px">
    <div class="rv in"><div class="sec-k">How it works</div>
    <h2>The AI inside Blackbox</h2>
    <p class="lead">Blackbox is built on eight strategies validated over 20 years of real market data. Artificial intelligence is layered through the whole product — but in a very deliberate way. This page explains exactly what the AI does, how it's implemented, and, just as importantly, what it does <em>not</em> do.</p></div>

    <div class="principle rv in">
      <div class="pbig">The rule is the driver. The AI is the co-pilot.</div>
      <p>Every buy, sell and hold decision comes from a validated, backtested rule — not from AI. The AI reads the market, supports those rules with a bounded risk brake, personalises your mix within strict limits, and explains everything in plain language. It never trades on its own, and it never invents a number.</p>
    </div>

    <h3 class="airole-h">0 · The AI we built ourselves — Regime Radar</h3>
    <div class="capgrid">
      <div class="capcard rv in" style="grid-column:1/-1;border-color:var(--acc)"><div class="capi">🧠</div><h4>Our own trained neural network</h4>
        <p>There is one crucial distinction on this page. Every feature below <em>uses</em> a large language model that someone else pre-trained. <b>Regime Radar is different — it is a model we built and trained from scratch.</b> We took ~10 years of real daily market data (about 30,000 examples across 13 assets), engineered the input features ourselves, defined the target (will the next 10 days be turbulent or calm?), and trained a <b>neural network</b> to learn the pattern — no human wrote the rule, the model discovered it from the data. We then tested it honestly on years of data it never saw during training: it scores an <b>AUC around 0.67</b>, a modest, imperfect edge that beats the naive baselines (a coin-flip is 0.50). This is the machine-learning core of the project — see it live on the <a onclick="go('intel')" style="color:var(--acc);cursor:pointer">Intelligence</a> page, and the honest results, error analysis and limitations in our written reflection.</p></div>
    </div>

    <h3 class="airole-h">1 · The AI reads the market</h3>
    <div class="capgrid">
      <div class="capcard rv in"><div class="capi">📰</div><h4>Live sentiment scanner</h4>
        <p>Every cycle, an AI model reads hundreds of real news headlines and social posts across six asset classes — equities, gold, rates, FX, crypto, oil — and scores the mood from −100 to +100, with a plain-English explanation traceable to the actual headlines. It reads for real meaning (handling context and negation), not just keywords.</p></div>
      <div class="capcard rv in"><div class="capi">🕰️</div><h4>Historical analog</h4>
        <p>AI matches today's real headlines to the closest event from a fixed library of real past market events — the 2008 crash, the Taper Tantrum, COVID, and more — then shows how each strategy's <em>real, backtested</em> returns actually moved in the months after. AI only picks which past event fits; every number is from the backtests.</p></div>
    </div>

    <h3 class="airole-h">2 · The AI supports the strategies</h3>
    <div class="capgrid">
      <div class="capcard rv in"><div class="capi">🛡️</div><h4>Sentiment risk overlay</h4>
        <p>This is where AI directly supports each strategy. When the scanner reads a strategy's assets as strongly bearish (a score below −40), that strategy's exposure is automatically trimmed to 75% — a risk brake layered on top of the validated rule. The rule decides the position; the AI decides whether to ease off it.</p></div>
      <div class="capcard rv in"><div class="capi">🎛️</div><h4>AI positioning desk</h4>
        <p>For every strategy, the AI reads its live rule-based stance and the live sentiment on its assets, then writes a short note explaining where it's positioned right now and whether the risk overlay is supporting or trimming it. You can see this on the Intelligence page.</p></div>
    </div>

    <h3 class="airole-h">3 · The AI personalises — within limits</h3>
    <div class="capgrid">
      <div class="capcard rv in"><div class="capi">✍️</div><h4>Free-text quiz nudge</h4>
        <p>After the six questions, you can describe your situation in your own words. AI reads it and may apply a <em>small, bounded</em> adjustment to your mix — never more than a gentle tilt, never adding or removing a strategy, never overriding the validated math. And it always explains, in writing, what in your words drove the change.</p></div>
      <div class="capcard rv in"><div class="capi">🧭</div><h4>AI risk review</h4>
        <p>Once your portfolio is live, AI reviews your actual mix — how diversified or concentrated it is, and its blend of return and risk — reading the exact figures for you. The blended numbers are computed precisely in code; the AI only puts them into words.</p></div>
    </div>

    <h3 class="airole-h">4 · The AI explains &amp; teaches</h3>
    <div class="capgrid">
      <div class="capcard rv in"><div class="capi">📊</div><h4>Daily briefing</h4>
        <p>A plain-English summary of the day's market, synthesised from the live sentiment scan and the historical analog.</p></div>
      <div class="capcard rv in"><div class="capi">💬</div><h4>Portfolio narration &amp; Q&amp;A</h4>
        <p>Your Blackbox writes its own summary, and you can ask it questions — answered only from your real portfolio data.</p></div>
      <div class="capcard rv in"><div class="capi">🎓</div><h4>Tutor &amp; glossary</h4>
        <p>An AI tutor answers investing questions grounded in this app's own strategies, and any metric can be explained on tap.</p></div>
      <div class="capcard rv in"><div class="capi">⚖️</div><h4>Strategy deep-dives &amp; compare</h4>
        <p>AI explains why any strategy works, and talks you through the trade-offs when you compare two — always from the real numbers.</p></div>
    </div>

    <div class="honesty rv in">
      <h3>What the AI does <span style="color:var(--red)">not</span> do</h3>
      <ul>
        <li><b>It does not make trades on its own.</b> Every buy/sell/hold comes from validated, backtested rules — moving-average trends, momentum, a rates gate on gold, seasonality. AI never originates a trade.</li>
        <li><b>It does not "learn" from your data or rewrite the strategies.</b> The language model was pre-trained on a vast amount of text — that's what lets it read and explain — but it does not train itself on this app, and the strategies come from 20-year statistical validation, not from AI. (So when we say "AI reads the news," we mean it applies what it already learned about language — not that it's inventing new trading rules.)</li>
        <li><b>It never invents a performance number.</b> Every figure traces to real backtests in the catalog. Where a blended number appears, it's calculated exactly in code and the AI is only allowed to state it verbatim.</li>
        <li><b>It does not give personalised buy/sell advice.</b> It explains and contextualises; it never tells you what to buy or sell. This is practice money, and none of it is investment advice.</li>
      </ul>
    </div>

    <div class="aitech rv in">
      <h4>Under the hood</h4>
      <p>All of the above runs through a single shared connector to a large language model (Llama, served by Groq), behind one API key. Every AI feature "fails open": if the model is ever unavailable, the app keeps working and the feature simply says so — the validated strategies and every real number are never affected. That's the whole design: real, tested rules at the core; AI as the analyst, risk co-pilot, and teacher around them.</p>
    </div>
  </div>
</section>
</div>

<div id="page-compare" style="display:none">
<section style="padding-top:150px">
  <div class="wrap" style="max-width:1000px">
    <div class="rv in"><div class="sec-k">Compare</div>
    <h2>Put two strategies side by side</h2>
    <p class="lead">Pick any two of the eight strategies to compare their real 20-year statistics head to head — return, risk, drawdown and how independent each is from the stock market — then let the AI talk you through the trade-offs. Every number is from the same backtests as the rest of the app.</p></div>
    <div class="cmppick">
      <div><label class="cmplabel">Strategy A</label><select class="ain cmpsel" id="cmpA"></select></div>
      <div class="cmpvs">vs</div>
      <div><label class="cmplabel">Strategy B</label><select class="ain cmpsel" id="cmpB"></select></div>
    </div>
    <div id="cmpTable" style="margin-top:24px"></div>
    <div id="cmpBox" class="acard" style="margin-top:20px;display:none"></div>
  </div>
</section>
</div>

<div id="page-account" style="display:none">
<section id="me" style="padding-top:150px">
  <div class="wrap">
    <div id="mebody"><div class="skel"><span class="sp"></span>Syncing your Blackbox with live markets…</div></div>
  </div>
</section>
</div>

<div class="mask" id="mask" onclick="if(event.target===this)closeModal()"><div class="modal" id="modal"></div></div>

<div id="mpop" class="mpop" style="display:none"></div>

<div class="mask" id="amask" onclick="if(event.target===this)closeAuth()">
  <div class="modal amodal">
    <button class="x" onclick="closeAuth()">×</button>
    <h2 style="font-size:26px;margin-bottom:6px">Your Blackbox account</h2>
    <p style="color:var(--mut);font-size:14px">Log back in from any device. Practice capital only — no real money.</p>
    <div id="gwrap" style="margin:20px 0 0;display:none"><div id="gbtn" style="display:flex;justify-content:center"></div>
      <div class="ordiv"><span>or</span></div></div>
    <div class="aview" id="av-choice" style="margin-top:18px">
      <button class="cta" style="width:100%" onclick="showAV('create')">Create my account</button>
      <button class="cta ghost" style="width:100%;margin-top:10px" onclick="showAV('password')">Sign in with email and password</button>
      <button class="cta ghost" style="width:100%;margin-top:10px" onclick="showAV('key')">I have a recovery key</button>
    </div>
    <div class="aview" id="av-create" style="display:none;margin-top:18px">
      <input class="ain" id="regname" placeholder="Your name" maxlength="24">
      <input class="ain" id="regemail" type="email" autocomplete="email" placeholder="Email address" style="margin-top:10px">
      <input class="ain" id="regpassword" type="password" autocomplete="new-password" placeholder="Password (at least 12 characters)" style="margin-top:10px">
      <button class="cta" style="width:100%;margin-top:12px" onclick="doRegister()">Create account →</button>
      <div class="aerr" id="regerr"></div>
    </div>
    <div class="aview" id="av-password" style="display:none;margin-top:18px">
      <input class="ain" id="loginemail" type="email" autocomplete="email" placeholder="Email address">
      <input class="ain" id="loginpassword" type="password" autocomplete="current-password" placeholder="Password" style="margin-top:10px">
      <button class="cta" style="width:100%;margin-top:12px" onclick="doPasswordLogin()">Sign in →</button>
      <div class="aerr" id="passworderr"></div>
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
  <div style="font-family:'Fraunces';font-style:italic;font-weight:600;font-size:19px;color:var(--txt);margin-bottom:12px">BLACKBOX</div>
  <div class="d" id="disc"></div>
</div></footer>

<script>
const $=s=>document.querySelector(s);
let CAT=null,SENT=null,MODE=null,PENDMIX=null,PENDPROFILE=null,curveChart=null,projChart=null,navChart=null,ME=null,GCID=null;
const COLORS=["#C9A961","#7A9B76","#B5716B","#8B98A8","#C08552","#9C8AA5","#6B8F87","#B08D4F"];
const BUCKETS={stack_bal:["equities","gold","oil"],stack_agg:["equities","gold","oil"],equity_season:["equities"],
gold_macro:["gold","rates"],commod_trend:["oil","gold"],risk_parity:["equities","rates","fx"],
crypto_trend:["crypto"],spx_hold:["equities"]};
const uid=()=>localStorage.getItem('bb_uid');

let PL_MAP={},ACTIVE_LANG=localStorage.getItem('bb_lang')==='pl'?'pl':'en';
const t=s=>{
  if(ACTIVE_LANG!=='pl')return s;
  if(PL_MAP[s])return PL_MAP[s];
  if(typeof s==='string'&&s.startsWith('Your own words:'))return 'Twoje słowa:'+s.slice('Your own words:'.length);
  return s;
};
const originalText=new WeakMap(),originalAttrs=new WeakMap();
function translateText(node){
  if(!node.parentElement||node.parentElement.closest('script,style,textarea,[data-no-translate]'))return;
  const current=node.nodeValue,trimmed=current.trim();
  if(!trimmed)return;
  if(!originalText.has(node))originalText.set(node,current);
  const original=originalText.get(node),key=original.trim();
  const translated=ACTIVE_LANG==='pl'&&PL_MAP[key];
  const value=translated?original.replace(key,translated):original;
  if(current!==value)node.nodeValue=value;
}
function translateElement(el){
  if(el.nodeType!==1||el.closest('[data-no-translate]'))return;
  for(const attr of ['placeholder','title','aria-label']){
    if(!el.hasAttribute(attr))continue;
    let saved=originalAttrs.get(el)||{};
    if(!(attr in saved)){saved[attr]=el.getAttribute(attr);originalAttrs.set(el,saved)}
    const value=ACTIVE_LANG==='pl'?(PL_MAP[saved[attr]]||saved[attr]):saved[attr];
    if(el.getAttribute(attr)!==value)el.setAttribute(attr,value);
  }
}
function translateTree(root=document.body){
  if(!root)return;
  if(root.nodeType===3){translateText(root);return}
  if(root.nodeType!==1)return;
  translateElement(root);
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){
    if(walker.currentNode.nodeType===3)translateText(walker.currentNode);
    else translateElement(walker.currentNode);
  }
  document.documentElement.lang=ACTIVE_LANG;
  const select=document.getElementById('language');if(select)select.value=ACTIVE_LANG;
}
async function changeLanguage(lang,initial=false){
  ACTIVE_LANG=lang==='pl'?'pl':'en';localStorage.setItem('bb_lang',ACTIVE_LANG);
  document.cookie='bb_lang='+ACTIVE_LANG+'; path=/; max-age=31536000; SameSite=Lax';
  if(!initial){location.reload();return}
  if(ACTIVE_LANG==='pl'&&!Object.keys(PL_MAP).length){
    PL_MAP=await fetch('/api/i18n/pl').then(r=>r.json()).catch(()=>({}));
  }
  renderHeadline();
  translateTree();
}
new MutationObserver(records=>{
  if(ACTIVE_LANG!=='pl')return;
  for(const record of records)for(const node of record.addedNodes)translateTree(node);
}).observe(document.body,{childList:true,subtree:true});
if(ACTIVE_LANG==='pl')changeLanguage('pl',true);

function renderHeadline(){
  const heading=$('#hl');
  heading.setAttribute('data-no-translate','');
  const phrases=ACTIVE_LANG==='pl'
    ? ['Twój własny Blackbox.','Gotowy w kilka minut.']
    : ['Your own Blackbox.','Live in minutes.'];
  heading.replaceChildren(...phrases.map((text,i)=>{
    const line=document.createElement('span');
    line.className='w hero-line'+(i?' grad':'');
    line.style.animationDelay=(i*120)+'ms';
    line.textContent=text;
    return line;
  }));
}
renderHeadline();

const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{rootMargin:'-80px'});
document.querySelectorAll('.rv').forEach(el=>io.observe(el));
document.addEventListener('click',e=>{const g=e.target.closest('.chips');if(!g)return;const b=e.target.closest('.chip');if(!b)return;
g.querySelectorAll('.chip').forEach(c=>c.classList.remove('on'));b.classList.add('on')});

/* ---------- pages/router ---------- */
const PAGES=['home','start','strategies','briefing','intel','learn','ai','compare','account'];
function pageFromPath(){const p=(location.pathname||'/').replace(/^\//,'');return PAGES.includes(p)?p:'home'}
function go(page,push){
  if(!PAGES.includes(page))page='home';
  PAGES.forEach(p=>{const el=document.getElementById('page-'+p);if(el)el.style.display=(p===page?'':'none')});
  document.querySelectorAll('.navlinks a').forEach(a=>a.classList.toggle('on',a.dataset.page===page));
  if(push!==false)history.pushState({page},'',page==='home'?'/':'/'+page);
  window.scrollTo(0,0);
  // reveal-on-scroll can't fire for elements that were display:none when observed,
  // so force-reveal this page's content when it's shown.
  const cur=document.getElementById('page-'+page);
  if(cur)cur.querySelectorAll('.rv').forEach(el=>el.classList.add('in'));
  onPageShown(page);
}
window.addEventListener('popstate',e=>go((e.state&&e.state.page)||pageFromPath(),false));
function onPageShown(page){
  if(page==='strategies'){ensureStrategiesPage();}
  if(page==='briefing'){loadBriefing();}
  if(page==='intel'){loadRegime();renderSentiment();loadAnalog();loadPositioning();}
  if(page==='learn'){ensureLearnPage();}
  if(page==='compare'){ensureComparePage();}
  if(page==='account'){ensureAccountPage();}
}

function heroGo(){ if((ME&&ME.signed_in&&ME.portfolio)||uid()){go('account')} else {go('start')} }

/* ---------- accounts ---------- */
function renderAuth(){
  const b=$('#authbox');
  if(ME&&ME.signed_in){
    b.innerHTML=`<div class="uchip">${ME.picture?`<img src="${ME.picture}" referrerpolicy="no-referrer" alt="">`:`<span class="uinit">${esc((ME.name||'?')[0].toUpperCase())}</span>`}
      <span class="un">${esc(ME.name)}</span>
      <button class="cta ghost small" onclick="doLogout()">Sign out</button></div>`;
  } else b.innerHTML='<button class="cta ghost small" onclick="openAuth()">Sign in</button>';
}
function openAuth(){$('#amask').classList.add('show');showAV('choice')}
function closeAuth(){$('#amask').classList.remove('show')}
function showAV(v){document.querySelectorAll('.aview').forEach(x=>x.style.display='none');
  const el=document.getElementById('av-'+v);if(el)el.style.display='block'}
async function doPasswordLogin(){
  const r=await fetch('/api/auth/password',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({email:$('#loginemail').value,password:$('#loginpassword').value})}).then(r=>r.json()).catch(()=>null);
  if(!r||!r.ok){$('#passworderr').textContent=r&&r.error||'Email or password was not recognised.';return}
  $('#loginpassword').value='';closeAuth();afterAuth();
}
async function refreshMe(){ME=await fetch('/api/me').then(r=>r.json()).catch(()=>({signed_in:false}));
  renderAuth();
  $('#heroCta').textContent=((ME.signed_in&&ME.portfolio)||uid())?'View my Blackbox →':"Let's go →";}
async function afterAuth(){await refreshMe();
  if(ME.signed_in&&ME.portfolio){go('account')}
  else{go('start')}}
async function doRegister(){
  const name=$('#regname').value.trim()||'Trader';
  const email=$('#regemail').value.trim(),password=$('#regpassword').value;
  if(!email.includes('@')||password.length<12){$('#regerr').textContent='Enter an email and a password of at least 12 characters.';return}
  const r=await fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name,email,password,adopt_uid:uid()})}).then(r=>r.json()).catch(()=>null);
  if(!r||!r.ok){$('#regerr').textContent=r&&r.error||'Could not create the account — try again.';return}
  $('#regpassword').value='';
  if(r.confirmation_required){
    $('#regerr').textContent=ACTIVE_LANG==='pl'?'Sprawdź skrzynkę i potwierdź adres e-mail, a następnie zaloguj się.':'Check your inbox to confirm your email, then sign in.';
    return;
  }
  localStorage.removeItem('bb_uid');
  if(!r.recovery_key){closeAuth();await afterAuth();return}
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
  ME={signed_in:false};window._meUid=null;LAST_PORTFOLIO=null;localStorage.removeItem('bb_uid');renderAuth();
  $('#mebody').innerHTML='<div class="skel"><span class="sp"></span>Syncing your Blackbox with live markets…</div>';
  $('#heroCta').textContent=uid()?'View my Blackbox →':"Let's go →";go('home')}
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
function applyStepperVisibility(){
  document.querySelectorAll('.stepper').forEach(s=>s.style.display=MODE==='manual'?'flex':'none');
  const bw=document.getElementById('builderwrap');if(bw)bw.classList.toggle('show',MODE==='manual');
}
function setMode(m){MODE=m;
  if(m==='manual')PENDPROFILE=null;
  $('#modeQuiz').classList.toggle('on',m==='quiz');$('#modeManual').classList.toggle('on',m==='manual');
  $('#quiz').classList.toggle('show',m==='quiz');
  $('#namecard').style.display='none';
  applyStepperVisibility();
  if(m==='manual')go('strategies');
}
let cardsLoaded=false;
function ensureStrategiesPage(){
  if(!cardsLoaded){cardsLoaded=true;renderCards();}
  applyStepperVisibility();
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
  renderAuth();initGIS();
  const have=(ME.signed_in&&ME.portfolio)||uid();
  if(have)$('#heroCta').textContent='View my Blackbox →';
  go(pageFromPath(),false);
}

function showEmptyPortfolio(){
    $('#mebody').innerHTML=`<div class="skel" style="text-align:left;padding:60px 0">
      <h2 style="font-size:28px;margin-bottom:10px">You don't have a Blackbox yet</h2>
      <p style="color:var(--mut);margin-bottom:22px">Answer seven questions or build your own mix to start a personal paper portfolio.</p>
      <button class="cta" onclick="go('start')">Start my Blackbox →</button>
    </div>`;
}
async function ensureAccountPage(){
  $('#mebody').innerHTML='<div class="skel"><span class="sp"></span>'+ (ACTIVE_LANG==='pl'?'Wczytywanie Twojego portfela…':'Loading your portfolio…')+'</div>';
  await loadMe();
}

/* ---------- historical analog ---------- */
async function loadAnalog(){
  const box=$('#analogBox');
  const L=(en,pl)=>ACTIVE_LANG==='pl'?pl:en;
  box.textContent=L('Reading recent headlines against market history…','Porównywanie najnowszych wiadomości z historią rynku…');
  const a=await fetch('/api/historical-analog').then(r=>r.json()).catch(()=>null);
  if(!a||a.available===false||!a.event){
    box.textContent=L('No supported historical comparison is available. This requires fresh sourced news, a sufficiently strong match, covered price windows and a configured AI service.','Brak popartego danymi porównania historycznego. Potrzebne są świeże wiadomości ze źródłami, wystarczające podobieństwo, pełne okna cenowe i skonfigurowana usługa AI.');
    return;
  }
  const e=a.event,rx=a.reactions||{};
  const rows=Object.values(rx).sort((x,y)=>y.pct-x.pct).map(r=>
    `<div class="arow"><span>${esc(t(r.name))}<small style="display:block">${esc(r.start_date)} → ${esc(r.end_date)}</small></span><span>${r.pct>0?'+':''}${esc(r.pct)}%</span></div>`).join('');
  box.innerHTML=`<div class="acard rv in">
    <div class="ah"><h3>${esc(t(e.title))}</h3><span class="adate">${esc(e.date)}</span></div>
    <p style="color:var(--mut);font-size:14px;margin-top:8px">${esc(t(e.summary))}</p>
    <div class="areason">${esc(a.reason||'')}</div>
    <p class="note">${L('Approximate changes in sparse historical strategy curves, with actual observation dates. These are historical associations, not individual-stock evidence or forecasts.','Przybliżone zmiany historycznych krzywych strategii wraz z rzeczywistymi datami obserwacji. Są to zależności historyczne, a nie dowody dotyczące konkretnych akcji ani prognozy.')}</p>
    <div class="agrid">${rows}</div>
    <ul style="padding-left:20px;margin-top:16px">${(a.headlines||[]).map(h=>`<li>${sourceLink(h.url,h.title)} <span class="note">${esc(h.source)} · ${esc(h.published_at)}</span></li>`).join('')}</ul>
  </div>`;
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
  const g=x.createLinearGradient(0,0,0,H);g.addColorStop(0,'rgba(201,168,106,.35)');g.addColorStop(1,'rgba(201,168,106,0)');
  x.beginPath();x.moveTo(0,H);vs.forEach((v,i)=>x.lineTo(X(i),Y(v)));x.lineTo(W,H);x.closePath();x.fillStyle=g;x.fill();
  x.beginPath();vs.forEach((v,i)=>{i?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v))});
  x.strokeStyle='#C9A961';x.lineWidth=2;x.lineJoin='round';x.stroke()}

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
function sourceLink(url,label){
  try{
    const u=new URL(url);
    if(!['https:','http:'].includes(u.protocol)||u.username||u.password)return esc(label);
    return `<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer" style="color:var(--acc)">${esc(label)}</a>`;
  }catch{return esc(label)}
}
function renderMarketEvidence(m){
  const L=(en,pl)=>ACTIVE_LANG==='pl'?pl:en;
  const pct=v=>Number.isFinite(v)?`${v>=0?'+':''}${v.toFixed(2)}%`:'—';
  const date=v=>esc(String(v||'—').slice(0,19).replace('T',' '));
  const headlines=item=>(item.news.headlines||[]).map(h=>`<li style="margin:10px 0">${sourceLink(h.url,h.title)}
    <div class="note">${esc(h.publisher)} · ${date(h.published_at)} UTC · ${h.scope==='company'?L('company report','wiadomość o spółce'):L('market/sector context','kontekst rynku lub sektora')}</div></li>`).join('');
  const history=item=>(item.history.comparisons||[]).map(h=>`<div style="margin:14px 0;border-top:1px solid var(--line);padding-top:10px">
    <b>${sourceLink(h.source_url,h.title)}</b> · ${date(h.date)}
    <div class="note">${L('Observed closes','Zaobserwowane ceny zamknięcia')}: ${date(h.windows['20'].start)} → ${date(h.windows['20'].end)}</div>
    <div>${L('5 sessions','5 sesji')}: ${pct(h.windows['5'].return_pct)} · ${L('20 sessions','20 sesji')}: ${pct(h.windows['20'].return_pct)} · ${L('S&P 500 fund','Fundusz S&P 500')}: ${pct(h.windows['20'].benchmark_pct)}</div>
    <div class="note">${L('20-session difference versus SPY','Różnica względem SPY po 20 sesjach')}: ${pct(h.windows['20'].excess_pct)}</div></div>`).join('');
  return `<div style="margin-top:28px"><h3>${m.scope==='specific'?L('Stocks and funds to research','Akcje i fundusze do analizy'):L('Investment areas to research','Obszary inwestycyjne do analizy')}</h3>
    <p class="note">${esc(m.method)}</p>
    <h4 style="margin-top:18px">${L('How the market is behaving','Jak zachowuje się rynek')}</h4>
    <div style="overflow-x:auto"><table class="cmptable"><thead><tr><th>${L('Market','Rynek')}</th><th>${L('5 sessions','5 sesji')}</th><th>${L('21 sessions','21 sesji')}</th><th>${L('Price date','Data cen')}</th></tr></thead><tbody>
    ${(m.market_behavior||[]).map(b=>`<tr><td>${sourceLink('https://finance.yahoo.com/quote/'+encodeURIComponent(b.symbol)+'/history/',b.symbol)}</td><td>${pct(b.week_pct)}</td><td>${pct(b.month_pct)}</td><td>${date(b.asof)}</td></tr>`).join('')}</tbody></table></div>
    <p class="note">${L('News scan','Skan wiadomości')}: ${date(m.news_generated_at)} UTC · ${m.news_count||0} ${L('fresh linked headlines','świeżych nagłówków z odnośnikami')} · ${L('Feed status','Stan źródeł')}: ${esc(ACTIVE_LANG==='pl'?({ok:'dostępne',partial:'częściowo dostępne',unavailable:'niedostępne'}[m.news_status]||m.news_status):m.news_status)}. ${L('Prices available','Dostępne ceny')}: ${m.available}/${m.checked}.</p>
    ${(m.items||[]).map((item,index)=>`<article style="margin-top:20px;padding:22px;border:1px solid var(--line);border-radius:16px;background:var(--surface2)">
      <h3 style="font-size:20px">${index+1}. ${esc(t(item.area))} · ${esc(item.symbol)} — ${esc(t(item.name))}</h3>
      <p class="note">${sourceLink(item.price_source_url,L('Adjusted price source','Źródło skorygowanych cen'))} · ${date(item.asof)} · ${L('USD-denominated instrument','Instrument denominowany w USD')}</p>
      <h4>${L('Why it appears','Uzasadnienie propozycji')}</h4>
      <ul style="padding-left:20px;line-height:1.7">${item.justification.map(j=>`<li>${esc(j)}</li>`).join('')}</ul>
      <h4 style="margin-top:14px">${L('What could weaken this case','Co osłabia tę propozycję')}</h4>
      <ul style="padding-left:20px;line-height:1.7;color:var(--mut)">${item.cautions.map(c=>`<li>${esc(c)}</li>`).join('')}</ul>
      <details style="margin-top:14px"><summary style="cursor:pointer">${L('Read the news evidence','Zobacz wiadomości źródłowe')} (${(item.news.headlines||[]).length})</summary>
      <ul style="padding-left:20px">${headlines(item)||`<li>${L('No qualifying recent articles.','Brak odpowiednich świeżych artykułów.')}</li>`}</ul></details>
      <details style="margin-top:14px"><summary style="cursor:pointer">${L('What followed similar past topics','Co następowało po podobnych tematach w przeszłości')} (${item.history.comparisons.length})</summary>
      <p class="note">${L('Topic matching is a transparent keyword rule, not a finding that the same event or regime is repeating. Returns run from the event-day close (next session when closed) to later closes.','Tematy są dopasowywane według jawnych reguł słów kluczowych. Nie oznacza to powtórzenia tej samej sytuacji. Zwroty liczymy od zamknięcia w dniu zdarzenia (lub następnej sesji) do późniejszych zamknięć.')}</p>
      ${history(item)||`<p class="note">${L('No fully covered comparable events.','Brak porównań z pełnymi danymi.')}</p>`}
      ${item.history.omitted_event_ids.length?`<p class="note">${item.history.omitted_event_ids.length} ${L('event windows omitted because prices were incomplete.','okien zdarzeń pominięto z powodu niepełnych cen.')}</p>`:''}</details>
      <p class="note" style="margin-top:14px">${L('Ranking points: price and risk','Punkty rankingu: cena i ryzyko')} ${item.score_breakdown.price_risk.toFixed(2)}; ${L('experimental news/history adjustment','eksperymentalna korekta wiadomości i historii')} ${item.score_breakdown.news_history.toFixed(2)}. ${L('These points are not a probability or an expected return.','Te punkty nie są prawdopodobieństwem ani oczekiwanym zwrotem.')}</p>
    </article>`).join('')||`<p class="note">${L('Insufficient current price coverage to rank investments. Try again later.','Za mało aktualnych danych, aby uszeregować inwestycje. Spróbuj później.')}</p>`}
    <p class="note" style="margin-top:18px">${esc(m.notice)}</p></div>`;
}
async function recommend(){
  const p={};document.querySelectorAll('#quiz .chips').forEach(g=>{const on=g.querySelector('.on');if(on)p[g.dataset.k]=on.dataset.v});
  PENDPROFILE=p;
  const ft=($('#freetext').value||'').trim();if(ft)p.freetext=ft;
  const btn=document.querySelector('#quiz .cta');const oldTxt=btn.textContent;
  btn.disabled=true;btn.textContent=ft?'Reading your answer…':'Building…';
  let r;
  try{
    const response=await fetch('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});
    if(!response.ok)throw new Error('recommendation unavailable');
    r=await response.json();
  }catch{
    $('#reco').textContent=ACTIVE_LANG==='pl'?'Nie udało się pobrać analizy. Spróbuj ponownie.':'The analysis could not be loaded. Please try again.';
    $('#reco').classList.add('show');return;
  }finally{btn.disabled=false;btn.textContent=oldTxt}
  const el=$('#reco');
  el.innerHTML=`<h3 style="font-size:24px">${ACTIVE_LANG==='pl'?'Twój portfel:':'Your custom mix:'} ${esc(t(r.label))}</h3>
    <div style="margin:10px 0 4px;font-size:13.5px;color:var(--mut)">${ACTIVE_LANG==='pl'?'Poziom ryzyka':'Risk capacity'}
      <b style="color:var(--txt)">${r.capacity}/100</b> ${ACTIVE_LANG==='pl'?'— na podstawie Twoich odpowiedzi':'— built from your risk answers'}</div>
    <div class="gauge" style="background:linear-gradient(90deg,#5FBF8F,#DCBB78,#E2716B);max-width:340px"><i style="left:calc(${r.capacity}% - 2px)"></i></div>
    <ul class="why">${r.why.map(w=>`<li>${esc(t(w))}</li>`).join('')}</ul>
    <div class="blend">
      <div class="b"><div class="n">${r.blend.cagr_est}%</div><div class="l">est. CAGR (backtest)</div></div>
      <div class="b"><div class="n">${r.blend.vol_est}%</div><div class="l">est. volatility</div></div>
      <div class="b"><div class="n" style="color:var(--red)">${r.blend.dd_est}%</div><div class="l">weighted max drawdown</div></div>
    </div>
    <div class="mixbar">${r.parts.map((x,i)=>`<i style="width:${x.weight}%;background:${COLORS[i%COLORS.length]}"></i>`).join('')}</div>
    <div class="mixlegend">${r.parts.map((x,i)=>`<span><span class="dotc" style="background:${COLORS[i%COLORS.length]}"></span><b>${x.weight}%</b> ${esc(t(x.name))}</span>`).join('')}</div>
    ${renderMarketEvidence(r.market)}
    <button class="cta" style="margin-top:22px" onclick='showName(${JSON.stringify(r.mix)})'>Use this mix →</button>`;
  el.classList.add('show');setTimeout(()=>el.scrollIntoView({behavior:'smooth',block:'nearest'}),80);
}

function showName(mix){PENDMIX=mix;go('start');
  setTimeout(()=>{const nc=$('#namecard');nc.style.display='block';
    nc.scrollIntoView({behavior:'smooth',block:'center'});$('#uname').focus()},80)}
async function startBlackbox(){
  if(!PENDMIX)return;
  await refreshMe();
  if(!ME.signed_in){openAuth();return;}
  const btn=$('#startBtn');btn.disabled=true;btn.textContent='Starting…';
  const name=($('#uname').value||'My').trim();
  const r=await fetch('/api/user/create',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name,mix:PENDMIX,profile:PENDPROFILE||{}})}).then(r=>r.json()).catch(()=>null);
  btn.disabled=false;btn.textContent='🚀 Start my Blackbox';
  if(r&&r.login_required){openAuth();return;}
  if(!r||!r.user_id){alert('Could not start — check the mix totals 100%.');return}
  if(r.signed_in)localStorage.removeItem('bb_uid');else localStorage.setItem('bb_uid',r.user_id);
  $('#heroCta').textContent='View my Blackbox →';
  $('#mebody').innerHTML='<div class="skel"><span class="sp"></span>Syncing your Blackbox with live markets… first sync takes ~20 seconds.</div>';
  go('account');
}
async function resetMe(){if(!confirm('Delete this Blackbox and start over?'))return;
  const puid=window._meUid||uid();
  if(puid)await fetch('/api/user/'+puid+'/delete',{method:'POST'}).catch(()=>{});
  localStorage.removeItem('bb_uid');location.reload()}

async function loadMe(){
  try{
    const response=await fetch('/api/me');
    if(!response.ok)throw new Error('Account unavailable');
    const m=await response.json();
    ME=m;renderAuth();
    let portfolio=m.signed_in?m.portfolio:null;
    if(pageFromPath()!=='account')return;
    if(!m.signed_in){window._meUid=null;LAST_PORTFOLIO=null;$('#mebody').innerHTML='<div class="skel">'+L('Sign in to view your private portfolio.','Zaloguj się, aby zobaczyć swój prywatny portfel.')+'<br><button class="cta" onclick="openAuth()">'+L('Sign in','Zaloguj się')+'</button></div>';return;}
    if(portfolio){renderMe(portfolio);return}
    showEmptyPortfolio();
  }catch{
    if(pageFromPath()!=='account')return;
    $('#mebody').innerHTML='<div class="skel">'+(ACTIVE_LANG==='pl'?'Nie udało się wczytać portfela. Twoje dane nie zostały usunięte.':'Could not load your portfolio. Your saved data has not been deleted.')+
      '<br><button class="cta" onclick="ensureAccountPage()">'+(ACTIVE_LANG==='pl'?'Spróbuj ponownie':'Try again')+'</button></div>';
  }
}
function renderMe(r){
  window._meUid=r.uid;LAST_PORTFOLIO=r;
  const up=r.since_start>=0,dayUp=r.day_ret>=0;
  const names={};CAT.strategies.forEach(s=>names[s.id]=s.name);
  $('#mebody').innerHTML=`
    <div class="mehead rv in">
      <div><div class="sec-k">Your Blackbox</div>
        <h2 style="margin-bottom:4px">${esc(r.name)}'s Blackbox</h2>
        <div style="color:var(--mut);font-size:13.5px">since ${r.created} · paper portfolio · marked to live markets</div></div>
      <div class="mehead-btns"><button class="cta ghost" onclick="printStatement()">🖨 Statement</button>
      <button class="cta ghost" onclick="resetMe()">Change strategy</button></div></div>
    <div style="margin-top:26px">
      <span class="nav-big">${fmt2(r.nav)}</span>
      <span class="pill ${up?'up':'dn'}">${up?'+':''}${r.since_start}% all-time</span>
      <span class="pill ${dayUp?'up':'dn'}">${dayUp?'+':''}${r.day_ret}% today</span></div>
    <div id="badges" class="badges"></div>
    <div class="megrid">
      <div>
        <div class="mbox" style="background:var(--surface2)"><h4>Portfolio value</h4><div class="chartbox short"><canvas id="navchart"></canvas></div>
          <div class="note" style="margin-top:10px">${r.note}</div></div>
        <div class="mbox" style="background:var(--surface2);margin-top:14px"><h4>Your mix</h4>
          <div class="mixbar">${Object.entries(r.mix).map(([id,w],i)=>`<i style="width:${w}%;background:${COLORS[i%COLORS.length]}"></i>`).join('')}</div>
          <div class="mixlegend">${Object.entries(r.mix).map(([id,w],i)=>`<span><span class="dotc" style="background:${COLORS[i%COLORS.length]}"></span><b>${w}%</b> ${names[id]||id}</span>`).join('')}</div></div>
        <div class="mbox" style="background:var(--surface2);margin-top:14px"><h4>AI summary</h4>
          <div id="narrtext" style="margin-top:8px"><span class="askel"><span class="sp"></span>Reading your portfolio…</span></div></div>
        <div class="mbox" style="background:var(--surface2);margin-top:14px"><h4>🧠 AI risk review</h4>
          <div id="reviewtext" style="margin-top:8px"><span class="askel"><span class="sp"></span>Analysing your mix's diversification and risk…</span></div></div>
        <div class="mbox" style="background:var(--surface2);margin-top:14px"><h4>Ask your Blackbox</h4>
          <div id="qalog"></div>
          <div class="qform"><input class="ain" id="qainput" placeholder="e.g. why did I lose money today?" onkeydown="if(event.key==='Enter')askPortfolio()">
            <button class="cta ghost small" onclick="askPortfolio()">Ask</button></div></div>
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
  ng.addColorStop(0,'rgba(201,168,106,.30)');ng.addColorStop(1,'rgba(201,168,106,0)');
  navChart=new Chart(document.getElementById('navchart'),{type:'line',
    data:{labels:hist.map(h=>h.t),datasets:[{data:hist.map(h=>h.v),borderColor:'#C9A961',borderWidth:2.6,
      pointRadius:hist.length<15?4:0,pointBackgroundColor:'#0B0906',pointBorderColor:'#E8D5A3',pointBorderWidth:2,
      pointHoverRadius:6,fill:true,backgroundColor:ng,tension:.3,borderCapStyle:'round'}]},
    options:{responsive:true,maintainAspectRatio:false,resizeDelay:60,interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false},tooltip:{...TT,callbacks:{label:c=>fmt2(c.parsed.y)}}},
      scales:{x:{grid:{display:false},border:{display:false},ticks:{...AXIS,maxTicksLimit:6}},
        y:{position:'right',grid:{color:'rgba(201,168,106,.08)',drawTicks:false},border:{display:false},
          ticks:{...AXIS,maxTicksLimit:5,padding:8,callback:kfmt}}}}});
  loadNarration(r.uid);loadReview(r.uid);renderBadges(r);
}

/* ---------- AI narration + Q&A ---------- */
async function loadNarration(uid){
  const box=$('#narrtext');if(!box)return;
  const r=await fetch('/api/user/'+uid+'/narrate').then(r=>r.json()).catch(()=>null);
  if(window._meUid!==uid)return;
  box.textContent=(r&&r.text)?r.text:L('The AI summary is temporarily unavailable. Please try again later.','Podsumowanie AI jest chwilowo niedostępne. Spróbuj ponownie później.');
}
async function loadReview(uid){
  const box=$('#reviewtext');if(!box)return;
  const r=await fetch('/api/user/'+uid+'/review').then(r=>r.json()).catch(()=>null);
  if(window._meUid!==uid)return;
  box.innerHTML=(r&&r.text)?`<div class="airich">${esc(r.text)}</div>`:L('The AI risk review is temporarily unavailable. Please try again later.','Analiza ryzyka AI jest chwilowo niedostępna. Spróbuj ponownie później.');
}

/* ---------- milestone badges (computed from real portfolio data) ---------- */
function renderBadges(r){
  const box=$('#badges');if(!box)return;
  const hist=r.history||[];
  const days=hist.length;
  const navs=hist.map(h=>h[1]);
  const peak=Math.max(...navs,r.nav);
  const atHigh=r.nav>=peak-0.005;
  // count down days survived (consecutive-agnostic: any day that fell but book still here)
  let downDays=0;for(let i=1;i<navs.length;i++)if(navs[i]<navs[i-1])downDays++;
  const b=[];
  b.push(['🚀','Launched','You started a live paper Blackbox']);
  if(days>=1)b.push(['📅',days+' day'+(days>1?'s':'')+' live','Your book has been marked to market '+days+' day'+(days>1?'s':'')]);
  if(downDays>=1)b.push(['💎','Held through a red day','You stayed invested through '+downDays+' down day'+(downDays>1?'s':'')]);
  if(days>=7)b.push(['🗓️','One week in','A full week of live marks accumulated']);
  if(days>=30)b.push(['🏆','One month in','30+ days of real history']);
  if(r.since_start>0)b.push(['📈','In the green','Positive since you started']);
  if(atHigh&&days>2)b.push(['⛰️','All-time high','Your NAV is at its highest yet']);
  const mixN=Object.keys(r.mix||{}).length;
  if(mixN>=5)b.push(['🌐','Well diversified','Your mix spans '+mixN+' strategies']);
  box.innerHTML=b.map(([e,t,d])=>`<div class="badge2" title="${d}"><span class="be">${e}</span><span class="bt">${t}</span></div>`).join('');
}

/* ---------- printable statement (real data) ---------- */
let LAST_PORTFOLIO=null;
function printStatement(){
  const r=LAST_PORTFOLIO;if(!r)return;
  const names={};(CAT&&CAT.strategies||[]).forEach(s=>names[s.id]=s.name);
  const rows=Object.entries(r.mix).map(([id,w])=>`<tr><td>${names[id]||id}</td><td style="text-align:right">${w}%</td></tr>`).join('');
  const stances=r.strategies.map(s=>`<tr><td>${names[s.id]||s.id}</td><td>${(s.note||'').replace(/</g,'&lt;')}</td></tr>`).join('');
  const w=window.open('','_blank');
  w.document.write(`<html><head><title>Blackbox Statement — ${esc(r.name)}</title>
    <style>body{font:14px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;color:#111;max-width:720px;margin:40px auto;padding:0 20px}
    h1{font-size:24px;margin-bottom:2px}.muted{color:#666;font-size:13px}table{width:100%;border-collapse:collapse;margin:16px 0}
    td,th{padding:8px 10px;border-bottom:1px solid #ddd;text-align:left;font-size:13px}h2{font-size:16px;margin-top:28px}
    .big{font-size:32px;font-weight:800;margin:10px 0}.disc{color:#777;font-size:11px;margin-top:30px;line-height:1.5}</style></head><body>
    <h1>Blackbox — Portfolio Statement</h1>
    <div class="muted">${esc(r.name)}'s Blackbox · started ${r.created} · generated ${new Date().toISOString().slice(0,10)}</div>
    <div class="big">${fmt2(r.nav)} <span style="font-size:15px;font-weight:500;color:#666">practice units</span></div>
    <div class="muted">${r.since_start>=0?'+':''}${r.since_start}% since start · ${r.day_ret>=0?'+':''}${r.day_ret}% today</div>
    <h2>Allocation</h2><table><tr><th>Strategy</th><th style="text-align:right">Weight</th></tr>${rows}</table>
    <h2>Current positioning</h2><table><tr><th>Strategy</th><th>Stance today</th></tr>${stances}</table>
    <div class="disc">Paper portfolio of practice capital — no real money, no brokerage account. Every figure derives from real historical backtests (2006–2026) and live market marks. Backtested performance does not guarantee future results. Not investment advice.</div>
    </body></html>`);
  w.document.close();setTimeout(()=>w.print(),300);
}
async function askPortfolio(){
  const inp=$('#qainput');const q=(inp.value||'').trim();if(!q)return;
  const log=$('#qalog');const uid=window._meUid;
  const row=document.createElement('div');row.className='qarow';
  row.innerHTML=`<div class="q">${q.replace(/</g,'&lt;')}</div><div class="a"><span class="sp"></span> thinking…</div>`;
  log.appendChild(row);inp.value='';inp.disabled=true;
  const r=await fetch('/api/user/'+uid+'/ask',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({question:q})}).then(r=>r.json()).catch(()=>null);
  inp.disabled=false;inp.focus();
  row.querySelector('.a').textContent=(r&&r.answer)?r.answer:L('Could not get an AI answer. Please try again later.','Nie udało się uzyskać odpowiedzi AI. Spróbuj ponownie później.');
}

/* ---------- modal + charts (redesigned) ---------- */
function openModal(id){
  const s=CAT.strategies.find(z=>z.id===id);if(!s)return;
  const st=s.stats,pj=s.projections,sc=sentFor(id);
  $('#modal').innerHTML=`<button class="x" onclick="closeModal()">×</button>
    <span class="badge ${s.risk.replace(' ','')}">${s.risk} risk</span> ${sc?sentChip(id):''}
    <h2 style="font-size:30px;margin:12px 0 6px">${s.name}</h2>
    <p style="color:var(--mut)">${s.tagline}</p>
    <p style="color:var(--mut);font-size:12.5px;margin-top:16px">💡 Tap any underlined metric below for a plain-English AI explanation.</p>
    <div class="stats" style="margin-top:10px">
      <div class="st"><div class="n">${st.cagr}%</div><div class="l">${mt('CAGR')}</div></div>
      <div class="st"><div class="n">${st.sharpe}</div><div class="l">${mt('Sharpe','Sharpe ratio')}</div></div>
      <div class="st"><div class="n">${st.vol}%</div><div class="l">${mt('Volatility')}</div></div>
      <div class="st"><div class="n" style="color:var(--red)">${st.max_dd}%</div><div class="l">${mt('Max DD','Maximum drawdown')}</div></div>
      <div class="st"><div class="n">${st.beta==null?'—':st.beta}</div><div class="l">${mt('Beta vs S&P','Beta (stock market)')}</div></div>
      <div class="st"><div class="n">${st.sharpe_h1} / ${st.sharpe_h2}</div><div class="l">${mt('Sharpe by decade','Split-half validation')}</div></div>
    </div>
    <div class="mrow">
      <div class="mbox"><h4>Growth of 10,000 — backtest vs S&P 500</h4><div class="chartbox"><canvas id="mcurve"></canvas></div>
        <div class="note" style="margin-top:12px"><span class="dotc" style="background:#C9A961"></span>${s.name}
        &nbsp;&nbsp;<span class="dotc" style="background:#6a6a78"></span>S&P 500 buy &amp; hold · ${s.span}</div></div>
      <div class="mbox"><h4>Where 10,000 could be — bootstrap projection</h4><div class="chartbox"><canvas id="mproj"></canvas></div>
        <div class="hchips">
          ${['1y','3y','5y'].map(h=>`<div class="hchip"><span class="n">${fmt(pj[h].p50)}</span>median · ${h}<br>
            <span style="color:var(--mut)">${fmt(pj[h].p25)} – ${fmt(pj[h].p75)} likely</span></div>`).join('')}
        </div>
        <div class="note" style="margin-top:10px">Bands: 800 resamples of real history — inner = likely (25-75%), outer = extremes (5-95%). Chance of loss after 5y: <b>${pj['5y'].prob_loss}%</b>.</div></div>
    </div>
    <div class="mbox" style="margin-top:22px"><h4>Split-half validation — did the edge hold in both halves of history?</h4>
      <div class="dstats">
        <div class="dstat"><div class="dn">${st.sharpe_h1}</div><div class="dl">Sharpe, first decade</div></div>
        <div class="dstat"><div class="dn">${st.sharpe_h2}</div><div class="dl">Sharpe, second decade</div></div>
        <div class="dstat"><div class="dn" style="color:var(--green)">${st.best_year}%</div><div class="dl">Best year</div></div>
        <div class="dstat"><div class="dn" style="color:var(--red)">${st.worst_year}%</div><div class="dl">Worst year</div></div>
        <div class="dstat"><div class="dn">${st.years}</div><div class="dl">Years of data</div></div>
        <div class="dstat"><div class="dn">${st.corr_spx==null?'—':st.corr_spx}</div><div class="dl">Correlation to S&P</div></div>
      </div>
      <div class="note" style="margin-top:12px">Every edge here was found on the first decade and confirmed on the second — a rule that only works in one half is discarded. Two positive Sharpe figures above mean the edge repeated across independent halves of history, which is the honest test that kills most curve-fit strategies.</div></div>
    <div class="method"><b>Methodology.</b> ${s.method}</div>
    <div class="mbox" style="margin-top:18px"><h4>🧠 AI deep-dive — why this works</h4>
      <div id="deepdive"><button class="cta ghost small" onclick="loadDeepDive('${s.id}')">Explain this strategy with AI →</button></div></div>
    <button class="cta" style="margin-top:20px" onclick='closeModal();showName({"${s.id}":100});'>Trade this strategy →</button>`;
  $('#mask').classList.add('show');document.body.style.overflow='hidden';
  setTimeout(()=>{drawCurve(s);drawProj(s)},30);
}
async function loadDeepDive(sid){
  const box=$('#deepdive');
  box.innerHTML='<div class="askel"><span class="sp"></span>AI is analysing the strategy…</div>';
  const d=await fetch('/api/ai/strategy/'+sid).then(r=>r.json()).catch(()=>null);
  box.innerHTML=`<div class="airich">${d&&d.text?esc(d.text):"AI isn't available right now — needs an AI key on the server."}</div>`;
}
function closeModal(){$('#mask').classList.remove('show');document.body.style.overflow='';
  if(projChart){projChart.destroy();projChart=null}if(curveChart){curveChart.destroy();curveChart=null}}

const AXIS={color:'#9C9080',font:{size:11,family:'Inter'}};
const TT={backgroundColor:'rgba(23,19,16,.96)',borderColor:'rgba(201,168,106,.3)',borderWidth:1,
  titleColor:'#A79A82',bodyColor:'#F3ECDD',padding:12,cornerRadius:10,displayColors:false,
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
  g.addColorStop(0,'rgba(201,168,106,.32)');g.addColorStop(.6,'rgba(201,168,106,.06)');g.addColorStop(1,'rgba(201,168,106,0)');
  // yearly x labels only
  let lastYr='';
  const yrLabel=t=>{const y=t.slice(0,4);if(y!==lastYr){lastYr=y;return y}return ''};
  curveChart=new Chart(ctx,{type:'line',data:{labels,datasets:[
    {data:s.curve.map(p=>p.v*10000),borderColor:'#C9A961',borderWidth:2.5,pointRadius:0,pointHitRadius:16,
      fill:true,backgroundColor:g,tension:.3,borderCapStyle:'round'},
    {data:spxData,borderColor:'rgba(145,135,115,.7)',borderWidth:1.4,borderDash:[6,5],pointRadius:0,
      pointHitRadius:12,fill:false,tension:.3,spanGaps:true}]},
    options:{responsive:true,maintainAspectRatio:false,resizeDelay:60,
      interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false},tooltip:{...TT,
        callbacks:{title:i=>i[0]?i[0].label:'',
          label:c=>(c.datasetIndex?'S&P 500   ':'This strategy   ')+fmt(c.parsed.y)}}},
      scales:{x:{grid:{display:false},border:{display:false},
        ticks:{...AXIS,maxRotation:0,autoSkip:false,callback:function(v){return yrLabel(this.getLabelForValue(v)||'')}}},
      y:{position:'right',grid:{color:'rgba(201,168,106,.08)',drawTicks:false},border:{display:false},
        ticks:{...AXIS,maxTicksLimit:5,padding:8,callback:kfmt}}}}});
}
function drawProj(s){
  const ctx=document.getElementById('mproj');if(!ctx)return;
  const pj=s.projections,xs=['today','1 year','3 years','5 years'];
  const band=k=>[10000,pj['1y'][k],pj['3y'][k],pj['5y'][k]];
  const gi=ctx.getContext('2d').createLinearGradient(0,0,0,280);
  gi.addColorStop(0,'rgba(201,168,106,.30)');gi.addColorStop(1,'rgba(201,168,106,.10)');
  projChart=new Chart(ctx,{type:'line',data:{labels:xs,datasets:[
    {data:band('p95'),borderColor:'rgba(160,150,130,.30)',borderWidth:1,borderDash:[4,5],pointRadius:0,fill:false,tension:.35},
    {data:band('p5'),borderColor:'rgba(160,150,130,.30)',borderWidth:1,borderDash:[4,5],pointRadius:0,tension:.35,
      fill:'-1',backgroundColor:'rgba(160,150,130,.06)'},
    {data:band('p75'),borderColor:'transparent',borderWidth:0,pointRadius:0,tension:.35,fill:false},
    {data:band('p25'),borderColor:'transparent',borderWidth:0,pointRadius:0,tension:.35,fill:'-1',backgroundColor:gi},
    {data:band('p50'),borderColor:'#E8D5A3',borderWidth:3,pointRadius:4.5,pointBackgroundColor:'#0B0906',
      pointBorderColor:'#E8D5A3',pointBorderWidth:2.5,pointHoverRadius:6,tension:.35,fill:false}]},
    options:{responsive:true,maintainAspectRatio:false,resizeDelay:60,
      interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false},tooltip:{...TT,filter:i=>[1,3,4].includes(i.datasetIndex),
        itemSort:(a,b)=>b.parsed.y-a.parsed.y,
        callbacks:{label:c=>({1:'Worst 5%   ',3:'Likely low   ',4:'Median   '}[c.datasetIndex]||'')+fmt(c.parsed.y)}}},
      scales:{x:{grid:{display:false},border:{display:false},ticks:{...AXIS,padding:6}},
        y:{position:'right',grid:{color:'rgba(201,168,106,.08)',drawTicks:false},border:{display:false},
          ticks:{...AXIS,maxTicksLimit:5,padding:8,callback:kfmt}}}}});
}

/* ---------- sentiment section ---------- */
function renderSentiment(){
  if(!SENT||!SENT.assets)return;
  const names={equities:'Equities',gold:'Gold & metals',rates:'Rates & Fed',fx:'FX & dollar',crypto:'Crypto',oil:'Oil & energy'};
  $('#sgrid').innerHTML=Object.entries(SENT.assets).map(([a,v],i)=>{
    const pos=Math.max(0,Math.min(100,(v.score+100)/2));
    const col=v.score>12?'var(--green)':v.score<-12?'var(--red)':'var(--mut)';
    return `<div class="scard rv in">
      <div class="h"><h3>${names[a]||a}</h3><span class="sscore" style="color:${col}">${v.score>0?'+':''}${v.score}</span></div>
      <div class="gauge"><i style="left:calc(${pos}% - 2px)"></i></div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--mut)"><span>bearish</span><span>${v.n_items} items · ${v.trend}</span><span>bullish</span></div>
      <div class="sexp">${v.explanation}</div>
      ${(v.top||[]).slice(0,3).map(t=>`<div class="head"><span class="t">${t.title}</span><span class="s" style="color:${t.score>0?'var(--green)':t.score<0?'var(--red)':'var(--mut)'}">${t.src}</span></div>`).join('')}
    </div>`}).join('');
}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const aiUnavail="AI is temporarily unavailable. Please try again later.";

/* ---------- inline 'explain this metric' AI popover ---------- */
const GLOSS_CACHE={};
async function explainMetric(ev,term){
  ev.stopPropagation();
  const pop=$('#mpop');
  const x=Math.min(ev.clientX,innerWidth-320),y=ev.clientY+14;
  pop.style.left=Math.max(12,x)+'px';pop.style.top=y+'px';pop.style.display='block';
  pop.innerHTML=`<h5>${esc(term)}</h5><div><span class="sp"></span> asking AI…</div>`;
  let txt=GLOSS_CACHE[term];
  if(!txt){
    const d=await fetch('/api/ai/glossary',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({term})}).then(r=>r.json()).catch(()=>null);
    txt=(d&&d.text)?d.text:aiUnavail;GLOSS_CACHE[term]=txt;
  }
  pop.innerHTML=`<h5>${esc(term)}</h5><div>${esc(txt)}</div>`;
}
document.addEventListener('click',e=>{const p=$('#mpop');if(p&&p.style.display!=='none'&&!p.contains(e.target)&&!e.target.classList.contains('metric-term'))p.style.display='none'});
// helper to build a clickable metric label
function mt(label,term){return `<span class="metric-term" onclick="explainMetric(event,'${(term||label).replace(/'/g,"\\'")}')">${label}</span>`}

/* ---------- Regime Radar (our own trained neural network) ---------- */
let regimeLoaded=false;
async function loadRegime(){
  if(regimeLoaded)return;regimeLoaded=true;
  const box=$('#regimeBox');
  box.innerHTML='<div class="askel"><span class="sp"></span>Running our neural network on the latest market data…</div>';
  const d=await fetch('/api/regime').then(r=>r.json()).catch(()=>null);
  if(!d||d.available===false||!d.regime){
    box.innerHTML='<div class="askel">The model isn\'t available — run <code>python3 regime_ai.py train</code> to build it.</div>';return;
  }
  const t=d.report&&d.report.test||{};
  const nn=t.neural_net||{},pers=t.baseline_persistence||{},maj=t.baseline_majority||{};
  const pct=Math.round(d.prob_turbulent*100);
  const auc=d.test_auc!=null?d.test_auc.toFixed(2):'—';
  const acc=d.test_accuracy!=null?Math.round(d.test_accuracy*100)+'%':'—';
  const ds=d.report&&d.report.dataset||{};
  box.innerHTML=`<div class="regcard rv in">
    <div class="reghead">
      <div class="regverdict ${d.regime}">${d.regime==='calm'?'Calm':'Turbulent'} ahead</div>
      <div class="regmeta">for the crypto market (BTC), next ${d.horizon_days} days<br>
        model reads <b style="color:var(--txt)">${pct}%</b> chance of turbulence · as of ${d.as_of}</div>
    </div>
    <div class="reggauge"><i style="left:calc(${Math.max(0,Math.min(100,pct))}% - 2px)"></i></div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--mut)"><span>calm</span><span>turbulent</span></div>
    <div class="regstats">
      <div class="regstat"><div class="rn">${auc}</div><div class="rl">Test AUC (skill)</div></div>
      <div class="regstat"><div class="rn">${ds.rows?ds.rows.toLocaleString():'—'}</div><div class="rl">Training examples</div></div>
      <div class="regstat"><div class="rn">${ds.coins||'—'}</div><div class="rl">Assets</div></div>
      <div class="regstat"><div class="rn">neural net</div><div class="rl">Model type</div></div>
    </div>
    <div class="regnote"><b>How to read this honestly:</b> AUC measures skill from 0.5 (a coin-flip) to 1.0 (perfect).
      Our model scores <b>${auc}</b> on data it never saw in training — a <b>real but imperfect</b> edge. It beats the
      naive baselines below. It is not a crystal bell; markets are hard, and we show exactly where it stands.</div>
    <table class="regtable">
      <thead><tr><th>Model (out-of-sample test)</th><th>AUC</th><th>Accuracy</th></tr></thead>
      <tbody>
        <tr><td class="win">Our neural network</td><td class="win">${nn.roc_auc!=null?nn.roc_auc.toFixed(3):'—'}</td><td>${nn.accuracy!=null?(nn.accuracy*100).toFixed(0)+'%':'—'}</td></tr>
        <tr><td>Naive baseline — "vol is already high"</td><td>${pers.roc_auc!=null?pers.roc_auc.toFixed(3):'—'}</td><td>${pers.accuracy!=null?(pers.accuracy*100).toFixed(0)+'%':'—'}</td></tr>
        <tr><td>Naive baseline — always guess "calm"</td><td>0.500</td><td>${maj.accuracy!=null?(maj.accuracy*100).toFixed(0)+'%':'—'}</td></tr>
      </tbody>
    </table>
    <p style="font-size:12px;color:var(--mut);margin-top:14px">Trained on ${ds.date_start||'2016'}–${ds.date_end||'2026'} daily data; tested on the most recent, untouched period (${ds.test_start||''} onward). Full method on the <a onclick="go('ai')" style="color:var(--acc);cursor:pointer">AI Inside</a> page.</p>
  </div>`;
}

/* ---------- AI positioning desk (Intelligence page) ---------- */
let posLoaded=false;
async function loadPositioning(){
  if(posLoaded)return;posLoaded=true;
  const box=$('#posGrid');
  box.innerHTML='<div class="askel"><span class="sp"></span>AI is reading every strategy\'s live positioning…</div>';
  const d=await fetch('/api/ai/positioning').then(r=>r.json()).catch(()=>null);
  if(!d||d.available===false){box.innerHTML='<div class="askel">'+aiUnavail+'</div>';return}
  const names={};(CAT&&CAT.strategies||[]).forEach(s=>names[s.id]=s.name);
  box.innerHTML='<div class="posgrid">'+Object.entries(d).map(([sid,v])=>{
    const brake=v.tilt<1;
    return `<div class="poscard"><h3>${names[sid]||v.name||sid}
      <span class="postag ${brake?'brake':'clear'}">${brake?'AI brake · '+Math.round(v.tilt*100)+'%':'AI clear · 100%'}</span></h3>
      <div class="posnote">${esc(v.ai_note)}</div>
      <div class="poshold">${(v.holdings&&v.holdings.length?v.holdings.map(h=>`<span class="htag">${h.name} ${h.w}%</span>`).join(''):'<span class="htag">100% cash</span>')}</div>
    </div>`}).join('')+'</div>';
}

/* ---------- Daily briefing page ---------- */
let briefLoaded=false;
async function loadBriefing(){
  if(briefLoaded)return;briefLoaded=true;
  const box=$('#briefingBox'),scores=$('#briefingScores');
  box.innerHTML='<div class="askel"><span class="sp"></span>Checking recent news and preparing the briefing…</div>';
  const d=await fetch('/api/ai/briefing').then(r=>r.json()).catch(()=>null);
  if(!d||d.available===false||!d.text){
    briefLoaded=false;scores.innerHTML='';
    const pl=ACTIVE_LANG==='pl';
    const msgs=pl?{refreshing:'Trwa pobieranie aktualnych wiadomości. Spróbuj ponownie za minutę.',news_unavailable:'Brak aktualnych wiadomości. Nie wyświetlamy starego raportu jako dzisiejszego.'}:{refreshing:'Fetching current news. Try again in a minute.',news_unavailable:'Current news is unavailable. An old report will not be shown as today’s briefing.'};
    const msg=msgs[d&&d.reason]||(pl?'AI jest chwilowo niedostępne. Spróbuj ponownie później.':aiUnavail);
    box.innerHTML='<div class="askel">'+esc(msg)+'</div><button class="btn" onclick="loadBriefing()">'+(pl?'Spróbuj ponownie':'Try again')+'</button>';return;
  }
  const names={equities:'Equities',gold:'Gold',rates:'Rates',fx:'FX',crypto:'Crypto',oil:'Oil'};
  scores.innerHTML=Object.entries(d.scores||{}).map(([a,v])=>{
    const col=v>12?'var(--green)':v<-12?'var(--red)':'var(--mut)';
    return `<div class="bscore"><div class="ba">${names[a]||a}</div><div class="bv" style="color:${col}">${v>0?'+':''}${v}</div></div>`}).join('');
  box.innerHTML=`<div class="airich">${esc(d.text)}</div><div class="note">${esc(d.generated||'')} · ${esc(d.n_scanned||0)} ${L('headlines','nagłówków')}</div>`;
}

/* ---------- Learn page (glossary + tutor) ---------- */
let learnLoaded=false;
const GLOSS_TERMS=['CAGR','Sharpe ratio','Max drawdown','Volatility','Beta','Risk parity',
  'Momentum investing','Trend following','Diversification','Volatility targeting',
  'Block bootstrap','Paper trading','Seasonality (Sell in May)','Sentiment overlay'];
function ensureLearnPage(){
  if(learnLoaded)return;learnLoaded=true;
  $('#glossChips').innerHTML=GLOSS_TERMS.map(t=>`<button class="glchip" onclick="explainTerm(this,'${t.replace(/'/g,"\\'")}')">${t}</button>`).join('');
}
async function explainTerm(btn,term){
  document.querySelectorAll('.glchip').forEach(c=>c.classList.remove('on'));btn.classList.add('on');
  const box=$('#glossBox');box.style.display='block';
  box.innerHTML='<div class="askel"><span class="sp"></span>Explaining “'+esc(term)+'”…</div>';
  const d=await fetch('/api/ai/glossary',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({term})}).then(r=>r.json()).catch(()=>null);
  box.innerHTML=`<h3 style="font-size:17px;margin-bottom:8px">${esc(term)}</h3><div class="airich">${d&&d.text?esc(d.text):aiUnavail}</div>`;
}
let COACH_HIST=[];
async function askCoach(){
  const inp=$('#coachInput');const q=(inp.value||'').trim();if(!q)return;
  const log=$('#coachLog');
  const row=document.createElement('div');row.className='qarow';
  row.innerHTML=`<div class="q">${esc(q)}</div><div class="a"><span class="sp"></span> thinking…</div>`;
  log.appendChild(row);inp.value='';inp.disabled=true;
  const d=await fetch('/api/ai/coach',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({question:q,history:COACH_HIST})}).then(r=>r.json()).catch(()=>null);
  inp.disabled=false;inp.focus();
  const ans=(d&&d.answer)?d.answer:aiUnavail;
  row.querySelector('.a').textContent=ans;
  COACH_HIST.push({role:'user',text:q},{role:'ai',text:ans});
}

/* ---------- Compare page ---------- */
let cmpLoaded=false;
function ensureComparePage(){
  if(!cmpLoaded){cmpLoaded=true;
    const opts=(CAT&&CAT.strategies||[]).map(s=>`<option value="${s.id}">${s.name}</option>`).join('');
    $('#cmpA').innerHTML=opts;$('#cmpB').innerHTML=opts;
    const ss=CAT&&CAT.strategies||[];
    if(ss[1])$('#cmpA').value=ss[0].id;if(ss[3])$('#cmpB').value=ss[3].id;
    $('#cmpA').onchange=$('#cmpB').onchange=runCompare;
  }
  runCompare();
}
function runCompare(){
  const a=$('#cmpA').value,b=$('#cmpB').value;
  const sa=CAT.strategies.find(s=>s.id===a),sb=CAT.strategies.find(s=>s.id===b);
  if(!sa||!sb)return;
  const rows=[['CAGR','cagr','%','CAGR'],['Sharpe','sharpe','','Sharpe ratio'],['Volatility','vol','%','Volatility'],
    ['Max drawdown','max_dd','%','Maximum drawdown'],['Beta vs S&P','beta','','Beta (stock market)'],['Risk','risk','','Risk rating']];
  $('#cmpTable').innerHTML=`<table class="cmptable"><thead><tr><th>Metric</th><th>${sa.name}</th><th>${sb.name}</th></tr></thead><tbody>`+
    rows.map(([lab,k,u,term])=>{const va=k==='risk'?sa.risk:sa.stats[k],vb=k==='risk'?sb.risk:sb.stats[k];
      return `<tr><td class="metric">${mt(lab,term)}</td><td class="val">${va}${u}</td><td class="val">${vb}${u}</td></tr>`}).join('')+
    '</tbody></table>';
  const box=$('#cmpBox');box.style.display='block';
  box.innerHTML='<div class="askel"><span class="sp"></span>AI is comparing the two…</div>';
  fetch('/api/ai/compare',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({a,b})}).then(r=>r.json()).then(d=>{
      box.innerHTML=`<h3 style="font-size:17px;margin-bottom:8px">AI verdict</h3><div class="airich">${d&&d.text?esc(d.text):aiUnavail}</div>`;
    }).catch(()=>{box.innerHTML='<div class="askel">'+aiUnavail+'</div>'});
}
boot();
</script></body></html>
"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
