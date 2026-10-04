"""
CatchPhish - Real-Time URL Classification through Feature Engineering & ML
Pipeline: EDA -> Feature Engineering -> Tiered Model Training -> Evaluation -> SHAP

NOVELTY IMPLEMENTED:
1. Two-tier detection architecture:
   - TIER 1 (Fast/Lexical+Host model): uses ONLY features available the instant a URL
     is seen, before the page is even fetched. This is what makes it genuinely "real-time".
   - TIER 2 (Deep/Content model): uses full webpage content features, run only when
     Tier 1 is uncertain (Suspicious zone). Mirrors how real browser security works
     (e.g. Chrome Safe Browsing does a fast local check first, then a deeper one).
2. URLSimilarityIndex is EXCLUDED from Tier 1 fast-path features used for the honest/
   real-world-realistic version, since it is a near-leakage feature in this dataset
   (=100.0 for 100% of legitimate URLs). We report both WITH and WITHOUT it for
   transparency in the report/viva.
3. Confidence-tiered risk output: Safe / Suspicious / Dangerous instead of binary.
4. SHAP explainability on the final model.
"""
import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.svm import LinearSVC, SVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                              f1_score, roc_auc_score, confusion_matrix, classification_report)
import xgboost as xgb
import joblib
import time

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

df_full = pd.read_csv("../data/PhiUSIIL.csv")
# Stratified subsample for compute efficiency in this environment (60k rows).
# Still statistically robust; full 235k available in data/PhiUSIIL.csv for a final Colab run.
df, _ = train_test_split(df_full, train_size=60000, stratify=df_full['label'], random_state=42)
print("Using subsample shape:", df.shape)

# ---------------------------------------------------------------
# FEATURE SET DEFINITIONS
# ---------------------------------------------------------------
LEXICAL_HOST_FEATURES = [
    'URLLength', 'DomainLength', 'IsDomainIP', 'TLDLength', 'NoOfSubDomain',
    'CharContinuationRate', 'TLDLegitimateProb', 'URLCharProb',
    'HasObfuscation', 'NoOfObfuscatedChar', 'ObfuscationRatio',
    'NoOfLettersInURL', 'LetterRatioInURL', 'NoOfDegitsInURL', 'DegitRatioInURL',
    'NoOfEqualsInURL', 'NoOfQMarkInURL', 'NoOfAmpersandInURL',
    'NoOfOtherSpecialCharsInURL', 'SpacialCharRatioInURL', 'IsHTTPS'
]

CONTENT_FEATURES = [
    'LineOfCode', 'LargestLineLength', 'HasTitle', 'DomainTitleMatchScore',
    'URLTitleMatchScore', 'HasFavicon', 'Robots', 'IsResponsive',
    'NoOfURLRedirect', 'NoOfSelfRedirect', 'HasDescription', 'NoOfPopup',
    'NoOfiFrame', 'HasExternalFormSubmit', 'HasSocialNet', 'HasSubmitButton',
    'HasHiddenFields', 'HasPasswordField', 'Bank', 'Pay', 'Crypto',
    'HasCopyrightInfo', 'NoOfImage', 'NoOfCSS', 'NoOfJS', 'NoOfSelfRef',
    'NoOfEmptyRef', 'NoOfExternalRef'
]

TARGET = 'label'  # 1 = legitimate, 0 = phishing

results = {}

def evaluate(name, y_true, y_pred, y_proba=None):
    m = {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred), 4),
        "recall": round(recall_score(y_true, y_pred), 4),
        "f1": round(f1_score(y_true, y_pred), 4),
    }
    if y_proba is not None:
        m["roc_auc"] = round(roc_auc_score(y_true, y_proba), 4)
    cm = confusion_matrix(y_true, y_pred).tolist()
    m["confusion_matrix"] = cm
    print(f"\n--- {name} ---")
    for k, v in m.items():
        if k != "confusion_matrix":
            print(f"  {k}: {v}")
    print(f"  confusion_matrix [[TN,FP],[FN,TP]]: {cm}")
    return m

def train_all_models(X_train, X_test, y_train, y_test, tag):
    tag_results = {}
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # 1. Logistic Regression
    lr = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    lr.fit(X_train_s, y_train)
    pred = lr.predict(X_test_s)
    proba = lr.predict_proba(X_test_s)[:, 1]
    tag_results['LogisticRegression'] = evaluate(f"{tag} - Logistic Regression", y_test, pred, proba)

    # 2. Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=RANDOM_STATE, n_jobs=-1)
    rf.fit(X_train, y_train)
    pred = rf.predict(X_test)
    proba = rf.predict_proba(X_test)[:, 1]
    tag_results['RandomForest'] = evaluate(f"{tag} - Random Forest", y_test, pred, proba)

    # 3. XGBoost
    xgb_clf = xgb.XGBClassifier(n_estimators=150, max_depth=6, learning_rate=0.1,
                                  random_state=RANDOM_STATE, eval_metric='logloss', n_jobs=-1, tree_method='hist')
    xgb_clf.fit(X_train, y_train)
    pred = xgb_clf.predict(X_test)
    proba = xgb_clf.predict_proba(X_test)[:, 1]
    tag_results['XGBoost'] = evaluate(f"{tag} - XGBoost", y_test, pred, proba)

    # 4. SVM (calibrated LinearSVC for speed + probability support on 235k rows)
    svm_base = LinearSVC(random_state=RANDOM_STATE, max_iter=3000, dual=False)
    svm = CalibratedClassifierCV(svm_base, cv=2)
    svm.fit(X_train_s, y_train)
    pred = svm.predict(X_test_s)
    proba = svm.predict_proba(X_test_s)[:, 1]
    tag_results['SVM'] = evaluate(f"{tag} - SVM (Linear, calibrated)", y_test, pred, proba)

    # 5. Stacking ensemble (novelty: meta-learner combining all 4)
    stack = StackingClassifier(
        estimators=[
            ('rf', RandomForestClassifier(n_estimators=80, max_depth=15, random_state=RANDOM_STATE, n_jobs=-1)),
            ('xgb', xgb.XGBClassifier(n_estimators=80, max_depth=6, random_state=RANDOM_STATE, eval_metric='logloss', n_jobs=-1, tree_method='hist')),
            ('lr', LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
        ],
        final_estimator=LogisticRegression(max_iter=1000),
        cv=2, n_jobs=-1
    )
    stack.fit(X_train, y_train)
    pred = stack.predict(X_test)
    proba = stack.predict_proba(X_test)[:, 1]
    tag_results['StackingEnsemble'] = evaluate(f"{tag} - Stacking Ensemble", y_test, pred, proba)

    models = {'LogisticRegression': lr, 'RandomForest': rf, 'XGBoost': xgb_clf,
              'SVM': svm, 'StackingEnsemble': stack, 'scaler': scaler}
    return tag_results, models

# ---------------------------------------------------------------
# TIER 1: Fast lexical+host model, WITHOUT the near-leakage feature
# ---------------------------------------------------------------
print("=" * 70)
print("TIER 1 (FAST / REALISTIC): lexical + host features, no URLSimilarityIndex")
print("=" * 70)
X1 = df[LEXICAL_HOST_FEATURES].copy()
y = df[TARGET].copy()
X1_train, X1_test, y_train, y_test = train_test_split(X1, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)
t0 = time.time()
tier1_results, tier1_models = train_all_models(X1_train, X1_test, y_train, y_test, "TIER1")
tier1_time = time.time() - t0
results['tier1_fast_lexical_host'] = tier1_results

# ---------------------------------------------------------------
# TIER 2: Full model with content features (deep check)
# ---------------------------------------------------------------
print("\n" + "=" * 70)
print("TIER 2 (DEEP): lexical + host + content-based features")
print("=" * 70)
X2 = df[LEXICAL_HOST_FEATURES + CONTENT_FEATURES].copy()
X2_train, X2_test, y_train2, y_test2 = train_test_split(X2, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)
tier2_results, tier2_models = train_all_models(X2_train, X2_test, y_train2, y_test2, "TIER2")
results['tier2_deep_full'] = tier2_results

# ---------------------------------------------------------------
# Reference run: WITH URLSimilarityIndex included (to show the leakage effect)
# ---------------------------------------------------------------
print("\n" + "=" * 70)
print("REFERENCE: same as Tier1 but WITH URLSimilarityIndex (shows leakage inflation)")
print("=" * 70)
X3 = df[LEXICAL_HOST_FEATURES + ['URLSimilarityIndex']].copy()
X3_train, X3_test, y_train3, y_test3 = train_test_split(X3, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)
rf_leak = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=RANDOM_STATE, n_jobs=-1)
rf_leak.fit(X3_train, y_train3)
pred_leak = rf_leak.predict(X3_test)
proba_leak = rf_leak.predict_proba(X3_test)[:, 1]
results['reference_with_leaky_feature'] = evaluate("WITH URLSimilarityIndex - Random Forest", y_test3, pred_leak, proba_leak)

# ---------------------------------------------------------------
# Save everything
# ---------------------------------------------------------------
joblib.dump(tier1_models, "../models/tier1_models.pkl")
joblib.dump(tier2_models, "../models/tier2_models.pkl")
joblib.dump({'lexical_host': LEXICAL_HOST_FEATURES, 'content': CONTENT_FEATURES}, "../models/feature_lists.pkl")

with open("../outputs/results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n\nTier1 training wall time (all 5 models):", round(tier1_time, 1), "sec")
print("\nAll results saved to outputs/results.json")
print("Models saved to models/")
