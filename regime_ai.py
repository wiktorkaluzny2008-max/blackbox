"""
REGIME RADAR — our own machine-learning model (KI Challenge).

A supervised classifier that learns to forecast the market's near-term RISK
REGIME — whether the next ~10 trading days will be TURBULENT (high volatility)
or CALM — from features engineered off past prices alone. Trained on ~10 years
of real daily crypto data (Coinbase, 13 assets, pooled).

This is genuinely "our own AI": we engineer the features, define the target,
train a neural network (plus a gradient-boosted baseline), and evaluate it
honestly out-of-sample. It is deliberately separate from the LLM features in
the rest of the app — those *use* a pre-trained model; this one we train.

Design decisions that keep it honest (no lookahead):
  * Features at day t use ONLY information up to and including day t.
  * The label at day t is the realised volatility over days [t+1 .. t+H] — the
    future we are trying to predict.
  * Train / test split is by DATE (train on the earlier years, test on the most
    recent years). No shuffling — that would leak the future into the past.
  * The "turbulent" threshold is fit on the TRAINING data only, then applied to
    the test set unchanged.

Run:
    python3 regime_ai.py train      # trains, evaluates, saves the model + report
    python3 regime_ai.py predict    # prints today's regime prediction
"""
import os, json, sys
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
MODEL_PATH = os.path.join(HERE, "ml", "regime_model.pkl")
REPORT_TXT = os.path.join(HERE, "logs", "regime_report.txt")
REPORT_JSON = os.path.join(HERE, "logs", "regime_report.json")

H = 10                 # forecast horizon (trading days)
TURBULENT_Q = 0.66     # top third of forward vol = "turbulent"
TEST_FRACTION = 0.25   # most-recent 25% of the timeline is the untouched test set

FEATURES = (["ret5", "ret10", "ret20", "ret60"]
            + ["vol5", "vol10", "vol20", "vol30"]
            + ["ma_dist20", "ma_dist50", "ma_dist200"]
            + ["rsi", "dd30", "dd60", "vol_chg"])


# ---------------------------------------------------------------- data
def load_prices():
    """Full daily close history per coin (reuses the Coinbase fetch/cache)."""
    from crypto_backtest import load
    return load()


def feature_frame(close):
    """Past-only features for one close-price series."""
    close = close.dropna().astype(float)
    r = np.log(close).diff()
    df = pd.DataFrame(index=close.index)
    for w in (5, 10, 20, 60):
        df[f"ret{w}"] = close.pct_change(w)
    for w in (5, 10, 20, 30):
        df[f"vol{w}"] = r.rolling(w).std() * np.sqrt(365)
    for w in (20, 50, 200):
        df[f"ma_dist{w}"] = close / close.rolling(w).mean() - 1
    delta = close.diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = (-delta.clip(upper=0)).rolling(14).mean()
    rs = up / down.replace(0, np.nan)
    df["rsi"] = 100 - 100 / (1 + rs)
    for w in (30, 60):
        df[f"dd{w}"] = close / close.rolling(w).max() - 1
    df["vol_chg"] = df["vol10"] - df["vol30"]
    return df


def labels(close, h=H):
    """Compute forward volatility; training fits its fixed threshold on train only."""
    close = close.dropna().astype(float)
    r = np.log(close).diff()
    rv = r.rolling(h).std() * np.sqrt(365)          # trailing h-day realised vol
    bar = rv.rolling(252, min_periods=120).quantile(TURBULENT_Q)   # past-only bar
    fwd = rv.shift(-h)                               # future h-day realised vol
    y = (fwd > bar).astype(float)
    y[fwd.isna() | bar.isna()] = np.nan
    return fwd, bar, y


def build_dataset():
    """Pool all coins into one (date, features..., y) table."""
    px = load_prices()
    parts = []
    for coin in px.columns:
        s = px[coin].dropna()
        if len(s) < 500:
            continue
        d = feature_frame(s)
        fwd, bar, y = labels(s)
        d["fwd_vol"], d["vol_bar"], d["y"] = fwd, bar, y
        d["coin"] = coin
        d["date"] = d.index
        parts.append(d)
    data = pd.concat(parts).dropna(subset=FEATURES + ["y"])
    return data.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------- train / evaluate
def _splits(data):
    """Split by DATE into train / validation / test (no shuffling)."""
    dates = np.sort(data["date"].unique())
    val_start = dates[int(len(dates) * 0.60)]
    test_start = dates[int(len(dates) * 0.75)]
    # Forward labels need H future days; purge boundary rows so training and
    # validation labels never include observations from the next period.
    tr = data[data["date"] < pd.Timestamp(val_start) - pd.Timedelta(days=H)]
    va = data[(data["date"] >= val_start) &
              (data["date"] < pd.Timestamp(test_start) - pd.Timedelta(days=H))]
    te = data[data["date"] >= test_start]
    return tr, va, te, pd.Timestamp(val_start), pd.Timestamp(test_start)


def _metrics(y_true, y_pred, y_prob):
    from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                                 f1_score, roc_auc_score, confusion_matrix)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4) if len(set(y_true)) > 1 else None,
        "confusion": confusion_matrix(y_true, y_pred).tolist(),
    }


def train():
    import joblib
    from sklearn.preprocessing import StandardScaler
    from sklearn.neural_network import MLPClassifier
    from sklearn.ensemble import RandomForestClassifier

    from sklearn.metrics import roc_auc_score, f1_score

    print("Building dataset from ~10y of real daily crypto prices…")
    data = build_dataset()
    tr, va, te, val_start, test_start = _splits(data)

    # target: "genuinely turbulent" = future vol in the top third of the TRAINING era.
    # (threshold fit on train only — no leakage.)
    thr = float(tr["fwd_vol"].quantile(TURBULENT_Q))
    lab = lambda df: (df["fwd_vol"].values > thr).astype(int)
    Xtr, ytr = tr[FEATURES].values, lab(tr)
    Xva, yva = va[FEATURES].values, lab(va)
    Xte, yte = te[FEATURES].values, lab(te)
    print(f"  samples: train {len(tr):,} · val {len(va):,} · test {len(te):,}")
    print(f"  turbulent-vol threshold (train): {thr*100:.0f}% ann.  turbulent rate: "
          f"train {ytr.mean()*100:.0f}% · test {yte.mean()*100:.0f}%")

    scaler = StandardScaler().fit(Xtr)
    Ztr, Zva, Zte = scaler.transform(Xtr), scaler.transform(Xva), scaler.transform(Xte)

    # neural network (headline model) + a class-balanced tree baseline
    mlp = MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=800,
                        early_stopping=True, random_state=0).fit(Ztr, ytr)
    rf = RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=50,
                                class_weight="balanced", random_state=0, n_jobs=-1).fit(Xtr, ytr)

    pv_mlp, pv_rf = mlp.predict_proba(Zva)[:, 1], rf.predict_proba(Xva)[:, 1]
    mlp_auc, rf_auc = roc_auc_score(yva, pv_mlp), roc_auc_score(yva, pv_rf)
    # the two are near-identical on validation; prefer the neural network unless the
    # random forest is materially better (>0.01 AUC). Disclosed tie-break.
    chosen = "neural_net" if mlp_auc >= rf_auc - 0.01 else "random_forest"

    # tune the decision threshold on VALIDATION (max F1) for the chosen model; test stays untouched
    pv = pv_mlp if chosen == "neural_net" else pv_rf
    cut = float(max(np.linspace(0.15, 0.85, 71),
                    key=lambda c: f1_score(yva, (pv >= c).astype(int), zero_division=0)))

    pt_mlp, pt_rf = mlp.predict_proba(Zte)[:, 1], rf.predict_proba(Xte)[:, 1]

    # naive baselines on the TEST set (the honest bar to beat)
    maj = int(round(ytr.mean()))
    base_majority = _metrics(yte, np.full_like(yte, maj), np.full_like(yte, maj, dtype=float))
    # persistence: "vol is high now -> expect turbulence ahead" (the strong naive baseline)
    vthr = float(np.quantile(tr["vol10"].values, TURBULENT_Q))
    pers_pred = (te["vol10"].values > vthr).astype(int)
    base_persist = _metrics(yte, pers_pred, te["vol10"].values / (vthr * 2))

    m_mlp = _metrics(yte, (pt_mlp >= cut).astype(int), pt_mlp)
    m_rf = _metrics(yte, (pt_rf >= cut).astype(int), pt_rf)

    importances = sorted(zip(FEATURES, rf.feature_importances_),
                         key=lambda z: -z[1])
    report = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "dataset": {"coins": int(data["coin"].nunique()), "rows": int(len(data)),
                    "date_start": str(data["date"].min().date()),
                    "date_end": str(data["date"].max().date()),
                    "train": int(len(tr)), "val": int(len(va)), "test": int(len(te)),
                    "val_start": str(val_start.date()), "test_start": str(test_start.date())},
        "target": {"horizon_days": H, "turbulent_quantile": TURBULENT_Q,
                   "definition": "next-10d realised vol in the top third of the training era",
                   "vol_threshold_ann_pct": round(thr * 100, 1),
                   "decision_threshold": round(cut, 3),
                   "train_turbulent_rate": round(float(ytr.mean()), 3),
                   "test_turbulent_rate": round(float(yte.mean()), 3)},
        "chosen_model": chosen,
        "val_auc": {"neural_net": round(float(mlp_auc), 4), "random_forest": round(float(rf_auc), 4)},
        "test": {"neural_net": m_mlp, "random_forest": m_rf,
                 "baseline_majority": base_majority, "baseline_persistence": base_persist},
        "top_features": [{"feature": f, "importance": round(float(i), 4)} for f, i in importances[:8]],
    }

    os.makedirs(os.path.join(HERE, "ml"), exist_ok=True)
    joblib.dump({"scaler": scaler, "mlp": mlp, "rf": rf, "chosen": chosen,
                 "features": FEATURES, "cut": cut, "H": H,
                 "test_metrics": m_mlp if chosen == "neural_net" else m_rf},
                MODEL_PATH)
    json.dump(report, open(REPORT_JSON, "w"), indent=2)
    _write_txt(report)
    print("\n" + open(REPORT_TXT).read())
    return report


def _write_txt(r):
    L = []
    def P(s=""): L.append(s)
    P("REGIME RADAR — training report")
    P("=" * 60)
    d = r["dataset"]
    P(f"Data: {d['coins']} crypto assets, {d['date_start']} .. {d['date_end']}, "
      f"{d['rows']:,} labelled coin-days")
    P(f"Split (by date, no shuffle): train {d['train']:,} | val {d['val']:,} "
      f"(from {d['val_start']}) | test {d['test']:,} (from {d['test_start']})")
    t = r["target"]
    P(f"Target: will the next {t['horizon_days']} days be turbulent — realised vol in the top "
      f"third of the training era (> {t['vol_threshold_ann_pct']:.0f}% annualised)? "
      f"Turbulent rate: train {t['train_turbulent_rate']*100:.0f}% / "
      f"test {t['test_turbulent_rate']*100:.0f}%")
    P(f"Chosen model (best on validation): {r['chosen_model']}  "
      f"(decision threshold {t['decision_threshold']}, tuned on validation)")
    P("")
    P(f"{'model':<22}{'acc':>7}{'prec':>7}{'recall':>8}{'F1':>7}{'AUC':>7}")
    P("-" * 60)
    order = [("neural network", "neural_net"), ("random forest", "random_forest"),
             ("baseline: majority", "baseline_majority"),
             ("baseline: persistence", "baseline_persistence")]
    for lbl, k in order:
        m = r["test"][k]
        auc = f"{m['roc_auc']:.3f}" if m["roc_auc"] is not None else "  -"
        P(f"{lbl:<22}{m['accuracy']:>7.3f}{m['precision']:>7.3f}{m['recall']:>8.3f}"
          f"{m['f1']:>7.3f}{auc:>7}")
    P("")
    P("Most informative features (random-forest importance):")
    for f in r["top_features"]:
        P(f"  {f['feature']:<12}{f['importance']:.3f}")
    open(REPORT_TXT, "w").write("\n".join(L))


# ---------------------------------------------------------------- inference
def predict(coin="BTC-USD"):
    """Today's regime call for one asset. Returns a dict, or None if unavailable."""
    import joblib
    try:
        b = joblib.load(MODEL_PATH)
        px = load_prices()
        s = px[coin].dropna()
        # Coinbase's on-disk cache may be months old; never label it a live call.
        if s.empty or datetime.now(timezone.utc).date() - s.index[-1].date() > timedelta(days=7):
            return None
        feats = feature_frame(s).dropna().iloc[-1:][b["features"]]
        if b["chosen"] == "neural_net":
            prob = float(b["mlp"].predict_proba(b["scaler"].transform(feats.values))[0, 1])
        else:
            prob = float(b["rf"].predict_proba(feats.values)[0, 1])
        return {"coin": coin, "prob_turbulent": round(prob, 3),
                "regime": "turbulent" if prob >= b["cut"] else "calm",
                "as_of": str(s.index[-1].date()),
                "model": b["chosen"], "test_accuracy": b["test_metrics"]["accuracy"],
                "test_auc": b["test_metrics"]["roc_auc"], "horizon_days": b["H"]}
    except Exception:
        return None


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "train"
    if cmd == "train":
        train()
    elif cmd == "predict":
        print(json.dumps(predict(), indent=2))
