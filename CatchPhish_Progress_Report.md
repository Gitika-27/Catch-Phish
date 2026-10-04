# CatchPhish
### Real-Time URL Classification through Feature Engineering & ML
**PBL Progress Report — Month 1 & Month 2**

Gitika Omprakash (210425243069) & P. Ashvika (210425243179), AIDS-A, CIT

---

## 1. Novelty Statement

Prior work identified in the literature survey (Sahingoz et al. 2019; Zieni et al. 2023; Das Guptta et al. 2024; Tamal et al. 2024) consistently trades off feature richness against real-time speed, and none provide interpretable, tiered decision output. CatchPhish addresses this gap with three additions:

- **Two-Tier Detection Architecture** — a Tier-1 fast model using only lexical + host-based features available instantly, before the page is fetched, followed by a Tier-2 deep model using webpage content features, invoked only when Tier-1 is uncertain.
- **Confidence-Tiered Risk Scoring** — output is Safe / Suspicious / Dangerous with a 0–100 risk score rather than a brittle binary label.
- **Explainable Detection (SHAP)** — every prediction can be traced to the specific URL characteristics that drove it, addressing the "black box" criticism common to ML-based phishing detectors.

We also identified and explicitly corrected a data-leakage artifact: the PhiUSIIL dataset's `URLSimilarityIndex` feature equals exactly 100.0 for 100% of legitimate URLs, which alone yields perfect (and unrealistic) accuracy. All headline results below exclude this feature from the fast-path model for an honest evaluation; a reference run with it is included to document the artifact transparently.

## 2. Dataset

**PhiUSIIL Phishing URL Dataset** (Prasad & Chandra, 2024): 134,850 legitimate and 100,945 phishing URLs, 54 features spanning lexical, host-based and content-based categories, zero missing values. A stratified subsample of 60,000 rows was used for training in this development phase for compute efficiency; the full 235,795-row dataset is available for the final Colab run before Review 3.

## 3. Feature Engineering

Features were split by acquisition cost/latency:

- **Tier 1 — Lexical + Host** (21 features, instant): URL length, domain length, subdomain count, digit/letter/special-char ratios, obfuscation indicators, HTTPS usage, TLD legitimacy probability, etc.
- **Tier 2 — + Content-based** (28 additional features, requires page fetch): line-of-code count, title-domain match score, redirect/popup/iframe counts, password/hidden-field presence, form submission target, image/CSS/JS counts, etc.

## 4. Model Training & Results

Four base classifiers (Logistic Regression, Random Forest, XGBoost, SVM) plus a stacking ensemble meta-learner were trained and compared for each tier.

### Tier 1 — Fast / Realistic (lexical + host only, no leakage feature)

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
|---|---|---|---|---|---|
| LogisticRegression | 0.9952 | 0.9932 | 0.9984 | 0.9958 | 0.9975 |
| RandomForest | 0.9962 | 0.9949 | 0.9984 | 0.9967 | 0.9982 |
| XGBoost | 0.9966 | 0.9949 | 0.9991 | 0.997 | 0.9979 |
| SVM | 0.9962 | 0.9938 | 0.9997 | 0.9967 | 0.9976 |
| **StackingEnsemble** | **0.9969** | **0.9949** | **0.9997** | **0.9973** | **0.9981** |

### Tier 2 — Deep (lexical + host + content-based features)

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
|---|---|---|---|---|---|
| LogisticRegression | 0.999 | 0.9985 | 0.9997 | 0.9991 | 1.0 |
| RandomForest | 0.9998 | 0.9997 | 0.9999 | 0.9998 | 1.0 |
| XGBoost | 0.9998 | 0.9999 | 0.9999 | 0.9999 | 1.0 |
| SVM | 0.9992 | 0.9988 | 0.9999 | 0.9993 | 1.0 |
| **StackingEnsemble** | **0.9999** | **0.9999** | **1.0** | **0.9999** | **1.0** |

### Reference run — Tier 1 features + `URLSimilarityIndex` included (demonstrates leakage artifact)

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
|---|---|---|---|---|---|
| Random Forest (with leaky feature) | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

**The Stacking Ensemble is the best-performing model in both tiers, and is adopted as CatchPhish's production model. The Tier-1 fast path alone achieves 99.7% accuracy with zero page-fetch latency, validating the two-tier design.**

## 5. Explainability (SHAP)

SHAP (SHapley Additive exPlanations) was applied to the Tier-1 XGBoost model to identify which URL characteristics drive each prediction. `IsHTTPS`, count of special characters, letter ratio, and domain length emerged as the top global predictors — consistent with known phishing patterns (lack of HTTPS, unusual character density, and abnormally long or short domains).

![SHAP summary plot](../outputs/shap_summary.png)

*Figure 1: SHAP summary plot — feature impact on Tier-1 model output (1,000 test samples).*

## 6. Risk-Tiering Logic

Rather than a hard 0/1 cutoff, predicted probability P(legitimate) is mapped to three actionable tiers:

- `P(legit) ≥ 0.65` → **Safe**
- `0.35 < P(legit) < 0.65` → **Suspicious** — Tier-2 deep check triggered automatically
- `P(legit) ≤ 0.35` → **Dangerous**

On a 10-sample held-out demonstration, all tiered predictions matched ground-truth labels.

## 7. Next Steps (Month 3, pre-Review 3)

- Build the real-time inference API (FastAPI/Flask) wrapping the two-tier + risk-scoring logic.
- Build a minimal Chrome extension that calls the API on page navigation and shows the risk tier + top SHAP reasons as a popup.
- Re-run final training on the full 235,795-row dataset (Colab) for the Review 3 headline numbers.
- Stress-test against obfuscated/typosquatted URLs not in the original dataset to check real-world generalization.
- Write final documentation, user manual, and prepare the demo video.

## 8. Artifacts Produced This Session

- `data/PhiUSIIL.csv` — full dataset (235,795 rows)
- `code/01_eda.py`, `code/02_pipeline.py`, `code/03_explainability_and_risk.py` — full reproducible pipeline
- `models/tier1_models.pkl`, `models/tier2_models.pkl` — trained models (5 each, incl. stacking ensemble)
- `models/risk_tier.py` — reusable risk-scoring function
- `outputs/results.json`, `outputs/feature_importance_shap.csv`, `outputs/shap_summary.png`
