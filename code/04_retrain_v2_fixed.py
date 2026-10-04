"""
04_retrain_v2_fixed.py
Fixes train/serve skew + dataset bias issues discovered during backend integration:

1. TLDLegitimateProb: replaced heuristic guess with an EXACT lookup table built
   from this training data itself (same corpus = same scale, fully reproducible live).
2. URLCharProb and CharContinuationRate: DROPPED. Both are computed by the
   original dataset authors using proprietary corpus-level statistics we cannot
   reproduce at inference time on a fresh URL. Approximating them caused wildly
   out-of-distribution values, breaking predictions on real URLs.
3. NoOfSubDomain: DROPPED. Discovered that 100% of legitimate URLs in PhiUSIIL
   happen to be "www."-prefixed (a collection artifact of this specific dataset),
   so the model learned "no subdomain -> phishing" -- which misclassifies any
   real bare-domain legitimate site (github.com, pypi.org, amazon.com, etc).
   This is a spurious correlation, not a real phishing signal, so it was removed
   rather than patched around.

Result: 17 lexical/host features, all exactly reproducible live and free of the
two dataset biases identified so far (this, plus the URLSimilarityIndex leakage
found earlier).
"""
import pandas as pd
import numpy as np
import json
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import xgboost as xgb

RANDOM_STATE = 42
df_full = pd.read_csv("../data/PhiUSIIL.csv")
df, _ = train_test_split(df_full, train_size=60000, stratify=df_full['label'], random_state=42)

LEXICAL_HOST_V2 = [
    'URLLength', 'DomainLength', 'IsDomainIP', 'TLDLength',
    'TLDLegitimateProb', 'HasObfuscation', 'NoOfObfuscatedChar', 'ObfuscationRatio',
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
TARGET = 'label'

# Build exact TLD lookup from the FULL dataset (not the subsample) for max coverage
df_full['tld'] = df_full['Domain'].astype(str).str.split('.').str[-1].str.lower()
tld_lookup = df_full.groupby('tld')['TLDLegitimateProb'].mean().to_dict()
default_tld_prob = float(df_full['TLDLegitimateProb'].quantile(0.1))  # conservative default for unseen TLDs
with open("../models/tld_lookup.json", "w") as f:
    json.dump({"lookup": tld_lookup, "default": default_tld_prob}, f)
print(f"Saved TLD lookup with {len(tld_lookup)} entries, default={default_tld_prob:.4f}")

def evaluate(name, y_true, y_pred, y_proba):
    m = {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred), 4),
        "recall": round(recall_score(y_true, y_pred), 4),
        "f1": round(f1_score(y_true, y_pred), 4),
        "roc_auc": round(roc_auc_score(y_true, y_proba), 4),
    }
    print(f"--- {name} --- {m}")
    return m

def train_suite(X_train, X_test, y_train, y_test, tag):
    results = {}
    scaler = StandardScaler()
    Xtr_s, Xte_s = scaler.fit_transform(X_train), scaler.transform(X_test)

    lr = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    lr.fit(Xtr_s, y_train)
    results['LogisticRegression'] = evaluate(f"{tag}-LR", y_test, lr.predict(Xte_s), lr.predict_proba(Xte_s)[:,1])

    rf = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=RANDOM_STATE, n_jobs=-1)
    rf.fit(X_train, y_train)
    results['RandomForest'] = evaluate(f"{tag}-RF", y_test, rf.predict(X_test), rf.predict_proba(X_test)[:,1])

    xgbc = xgb.XGBClassifier(n_estimators=150, max_depth=6, learning_rate=0.1, random_state=RANDOM_STATE,
                              eval_metric='logloss', n_jobs=-1, tree_method='hist')
    xgbc.fit(X_train, y_train)
    results['XGBoost'] = evaluate(f"{tag}-XGB", y_test, xgbc.predict(X_test), xgbc.predict_proba(X_test)[:,1])

    svm_base = LinearSVC(random_state=RANDOM_STATE, max_iter=3000, dual=False)
    svm = CalibratedClassifierCV(svm_base, cv=2)
    svm.fit(Xtr_s, y_train)
    results['SVM'] = evaluate(f"{tag}-SVM", y_test, svm.predict(Xte_s), svm.predict_proba(Xte_s)[:,1])

    stack = StackingClassifier(
        estimators=[
            ('rf', RandomForestClassifier(n_estimators=80, max_depth=15, random_state=RANDOM_STATE, n_jobs=-1)),
            ('xgb', xgb.XGBClassifier(n_estimators=80, max_depth=6, random_state=RANDOM_STATE, eval_metric='logloss', n_jobs=-1, tree_method='hist')),
            ('lr', LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
        ],
        final_estimator=LogisticRegression(max_iter=1000), cv=2, n_jobs=-1
    )
    stack.fit(X_train, y_train)
    results['StackingEnsemble'] = evaluate(f"{tag}-Stack", y_test, stack.predict(X_test), stack.predict_proba(X_test)[:,1])

    models = {'LogisticRegression': lr, 'RandomForest': rf, 'XGBoost': xgbc, 'SVM': svm,
              'StackingEnsemble': stack, 'scaler': scaler}
    return results, models

print("\n=== TIER 1 v2 (skew-fixed, 19 features) ===")
X1 = df[LEXICAL_HOST_V2]
y = df[TARGET]
X1_train, X1_test, y_train, y_test = train_test_split(X1, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)
tier1_results, tier1_models = train_suite(X1_train, X1_test, y_train, y_test, "T1v2")

print("\n=== TIER 2 v2 (skew-fixed, 47 features) ===")
X2 = df[LEXICAL_HOST_V2 + CONTENT_FEATURES]
X2_train, X2_test, y_train2, y_test2 = train_test_split(X2, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)
tier2_results, tier2_models = train_suite(X2_train, X2_test, y_train2, y_test2, "T2v2")

joblib.dump(tier1_models, "../models/tier1_models.pkl")
joblib.dump(tier2_models, "../models/tier2_models.pkl")
joblib.dump({'lexical_host': LEXICAL_HOST_V2, 'content': CONTENT_FEATURES}, "../models/feature_lists.pkl")

with open("../outputs/results_v2_fixed.json", "w") as f:
    json.dump({"tier1_v2": tier1_results, "tier2_v2": tier2_results}, f, indent=2)

print("\nDone. Models + feature_lists.pkl overwritten with skew-fixed versions.")
