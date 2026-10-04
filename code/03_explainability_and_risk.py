"""
SHAP explainability for the Tier-1 (fast) XGBoost model + confidence-tiered risk scoring.
This is the "explainable, tiered real-time" novelty layer.
"""
import pandas as pd
import numpy as np
import joblib
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

LEXICAL_HOST_FEATURES = [
    'URLLength', 'DomainLength', 'IsDomainIP', 'TLDLength', 'NoOfSubDomain',
    'CharContinuationRate', 'TLDLegitimateProb', 'URLCharProb',
    'HasObfuscation', 'NoOfObfuscatedChar', 'ObfuscationRatio',
    'NoOfLettersInURL', 'LetterRatioInURL', 'NoOfDegitsInURL', 'DegitRatioInURL',
    'NoOfEqualsInURL', 'NoOfQMarkInURL', 'NoOfAmpersandInURL',
    'NoOfOtherSpecialCharsInURL', 'SpacialCharRatioInURL', 'IsHTTPS'
]

df_full = pd.read_csv("../data/PhiUSIIL.csv")
df, _ = train_test_split(df_full, train_size=60000, stratify=df_full['label'], random_state=42)
X1 = df[LEXICAL_HOST_FEATURES].copy()
y = df['label'].copy()
X1_train, X1_test, y_train, y_test = train_test_split(X1, y, test_size=0.2, stratify=y, random_state=42)

tier1_models = joblib.load("../models/tier1_models.pkl")
xgb_model = tier1_models['XGBoost']

# ---- SHAP explainability ----
explainer = shap.TreeExplainer(xgb_model)
sample = X1_test.sample(n=1000, random_state=42)
shap_values = explainer.shap_values(sample)

plt.figure()
shap.summary_plot(shap_values, sample, show=False, plot_size=(9, 6))
plt.tight_layout()
plt.savefig("../outputs/shap_summary.png", dpi=140)
plt.close()

# mean |SHAP| per feature -> global importance table
mean_abs_shap = np.abs(shap_values).mean(axis=0)
importance_df = pd.DataFrame({
    'feature': X1_test.columns,
    'mean_abs_shap': mean_abs_shap
}).sort_values('mean_abs_shap', ascending=False)
importance_df.to_csv("../outputs/feature_importance_shap.csv", index=False)
print(importance_df.head(10).to_string(index=False))

# ---- Confidence-tiered risk scoring ----
def risk_tier(proba_legit, low=0.35, high=0.65):
    """
    proba_legit: model's predicted probability that URL is legitimate (class 1)
    Returns a human-facing risk tier + numeric phishing risk score (0-100).
    Tuned so the 'Suspicious' band is where Tier-2 deep check should trigger.
    """
    risk_score = round((1 - proba_legit) * 100, 1)
    if proba_legit >= high:
        tier = "Safe"
    elif proba_legit <= low:
        tier = "Dangerous"
    else:
        tier = "Suspicious - deep check recommended"
    return tier, risk_score

# Demonstrate on 10 held-out test URLs
demo_idx = X1_test.sample(10, random_state=1).index
demo_X = X1_test.loc[demo_idx]
demo_proba = xgb_model.predict_proba(demo_X)[:, 1]
demo_true = y_test.loc[demo_idx]

print("\n--- Sample tiered risk output (Tier 1 fast path) ---")
for i, (idx, p, actual) in enumerate(zip(demo_idx, demo_proba, demo_true)):
    tier, score = risk_tier(p)
    print(f"URL row {idx}: P(legit)={p:.3f} -> Risk={score}/100 -> Tier: {tier}  (actual label: {'legit' if actual==1 else 'phishing'})")

# Save the risk_tier function's logic as reusable module
with open("../models/risk_tier.py", "w") as f:
    f.write('''def risk_tier(proba_legit, low=0.35, high=0.65):
    risk_score = round((1 - proba_legit) * 100, 1)
    if proba_legit >= high:
        tier = "Safe"
    elif proba_legit <= low:
        tier = "Dangerous"
    else:
        tier = "Suspicious - deep check recommended"
    return tier, risk_score
''')

print("\nSaved: outputs/shap_summary.png, outputs/feature_importance_shap.csv, models/risk_tier.py")
