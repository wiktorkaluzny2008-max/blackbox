# Regime Radar — our own machine-learning model

*Critical reflection and documentation for the KI Challenge 2026.*

This document describes the one component of Blackbox that is **genuinely our own
AI**: a neural network we designed, trained and evaluated ourselves. Every other
"AI" feature in the app *uses* a pre-trained large language model through an API;
Regime Radar is the opposite — we built it from raw data up. It is deliberately
included so the project's methods come from the field of machine learning, as the
challenge requires.

---

## 1. The problem

Financial markets move between **calm** periods and **turbulent** ones (high
volatility). Turbulence is when investors get hurt: crashes, sharp swings, forced
selling. If a model could see turbulence coming even slightly better than chance,
that is genuinely useful — you can lower risk *before* the storm rather than after.

**Task.** A binary classification: *will the next 10 trading days be turbulent
(high realised volatility) or calm?* — predicted only from what is knowable today.

We chose volatility rather than price *direction* on purpose. Predicting whether
prices go up or down is close to impossible (markets are near-efficient), so such a
model would honestly be a coin-flip and make a misleading demo. Volatility, by
contrast, **clusters** — turbulent days tend to follow turbulent days — so it is
genuinely, if imperfectly, learnable. Choosing a learnable target is itself part of
doing honest machine learning.

---

## 2. The data

- **~10 years of real daily prices**, 2016‑07 → 2026‑11, for **13 crypto assets**
  (BTC, ETH, SOL, ADA, XRP, DOGE, LINK, LTC, BCH, ETC, AVAX, DOT, MATIC).
- Source: **Coinbase's public API** (free, no key). Fetched and cached by
  `crypto_backtest.py`.
- Pooling every coin's history gives **30,840 labelled examples** — a
  large dataset. Crypto was chosen because it is liquid, freely available without
  credentials, and volatile enough for the regime question to matter.

## 3. Method

**Features (15, all past-only).** For each day we compute inputs that describe the
market's recent behaviour, using *only* information available up to that day:
multi-window returns (5/10/20/60d), realised volatility (5/10/20/30d), distance
from moving averages (20/50/200d), RSI, and trailing drawdown (30/60d). Preventing
any future information from leaking into the features is the single most important
thing to get right in financial ML — otherwise the model "cheats" and looks amazing
but is worthless live.

**Label.** For day *t*, we measure the realised volatility over the **future**
window *[t+1 … t+10]*. It is labelled **turbulent** if it lands in the top third of
the training era's volatility (> ~101 % annualised). The threshold is fit on the
**training data only** and then applied unchanged — never re-fit on the test set.

**Split (by time, never shuffled).** Train = 2016 → mid‑2022, validation =
mid‑2022 → 2024, test = **2024 → 2026 (untouched)**. Shuffling would let the model
peek at the future; a strict chronological split is the honest way to test a
forecaster. We remove the ten days before each split boundary so forward labels
in one period cannot use prices from the next.

**Models.** A **neural network** (multi-layer perceptron, `scikit-learn`
`MLPClassifier`, hidden layers 32→16) and a **random forest** as a cross-check.
Features are standardised; the forest uses class weights; the decision threshold is tuned on
the **validation** set (not the test set). The model was selected on validation and
the two were statistically tied, so we report and deploy the neural network.

## 4. Results — honestly

Measured on the 2024–2026 test set (11,810 examples), after refreshing public
price data through 2026-11-02 and purging split boundaries:

| Model (out-of-sample) | AUC | Accuracy | Recall | Precision |
|---|---|---|---|---|
| **Our neural network** | **0.667** | 71 % | 49 % | 26 % |
| Random forest (cross-check) | 0.681 | 51 % | 75 % | 20 % |
| Naive baseline — "volatility is already high" | 0.632 | 76 % | 23 % | 22 % |
| Naive baseline — always guess "calm" | 0.500 | 85 % | 0 % | 0 % |

**How to read this.** The right metric here is **AUC** (area under the ROC curve),
which runs from 0.50 (a coin-flip) to 1.00 (perfect) and is not fooled by class
imbalance. Our model scores **0.667** — a **modest** edge, and it
**beats both naive baselines**, including the strong "volatility clusters" rule
(0.632). The forest scored 0.681 on this test, though the neural network was
selected using validation data before the test. The features it leaned on most (recent realised volatility, plus 60-day
momentum and distance from the 200-day trend) confirm it learned something sensible:
turbulence follows turbulence, but trend and momentum add extra signal.

**Why accuracy is misleading here.** Notice that "always guess calm" scores 85 %
accuracy — higher than our model — yet has zero skill (AUC 0.50, it never catches a
single turbulent period). This is the classic trap of imbalanced classification, and
it is exactly why we report AUC, recall and precision, not accuracy alone.

## 5. Error analysis — where it fails

- **It misses about 5 in 10 turbulent periods** (recall 49 %). Sudden, news-driven
  spikes have no early footprint in past prices, so a price-only model cannot see
  them coming.
- **It raises false alarms** (precision 26 %): choppy-but-not-turbulent stretches
  look turbulent to it. For a *risk* tool this is the safer error — occasionally
  de-risking unnecessarily beats missing a real storm — but it is a real cost.
- **Regime shift across time.** The training era (2016–2022) was far more volatile
  than the test era (2024–2026): 34 % of training days were "turbulent" by the fixed
  bar versus only 15 % of test days. Crypto matured and calmed. A model trained on a
  wilder past is therefore slightly miscalibrated for a calmer present — a genuine,
  visible limitation, not something we hid.

## 6. Limitations & honest caveats

- **Crypto only.** We used free crypto data; the patterns may differ for equities or
  bonds. The method transfers, but the specific model would need retraining.
- **A modest edge, not a crystal ball.** AUC 0.667 is modest but far from certainty. We
  present it as a *risk signal*, never as a trade trigger, and it does **not** drive
  any buying or selling in the app — the validated strategies do that.
- **Volatility ≠ direction.** The model says nothing about whether prices will rise
  or fall, only how bumpy the ride will be.
- **No transaction-cost or live-latency modelling** for the model's signal — it is a
  forecast, evaluated as a forecast.

## 7. What we would do next

- Add non-price features (trading volume, the app's own news-sentiment scores, and
  cross-asset signals) — turbulence often shows up in volume and mood first.
- Try a sequence model (LSTM/temporal CNN) that reads the recent path directly.
- Recalibrate on rolling windows so the model adapts as the volatility regime shifts.
- Formally connect the signal to position sizing and backtest the risk-adjusted
  improvement, net of costs.

## 8. How to run the AI

```bash
pip install -r requirements.txt      # includes scikit-learn
python3 regime_ai.py train           # fetches data, trains, evaluates, saves the model
python3 regime_ai.py predict         # prints today's regime call for BTC
```

Training writes the model to `ml/regime_model.pkl` and a full report to
`logs/regime_report.txt` / `logs/regime_report.json`. In the web app, the live
prediction and its honest track record appear on the **Intelligence** page
("Regime Radar"), and the method is explained on the **AI Inside** page.

## 9. On honesty

Everything here is reported as measured. We deliberately show the baselines our
model must beat, the metric that could have flattered us (accuracy) alongside the
ones that tell the truth (AUC, recall), and the places the model fails. A model that
honestly beats a coin-flip on real, unseen data — and that we can explain and
critique — is, we think, worth far more than an impressive number we could not
defend.
