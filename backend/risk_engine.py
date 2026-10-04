"""Loads CatchPhish models and produces risk plus explainable factors."""
import os, warnings, joblib, numpy as np, shap
warnings.filterwarnings('ignore')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
_tier1 = joblib.load(os.path.join(MODELS_DIR, 'tier1_models.pkl'))
_tier2 = joblib.load(os.path.join(MODELS_DIR, 'tier2_models.pkl'))
_features = joblib.load(os.path.join(MODELS_DIR, 'feature_lists.pkl'))
LEXICAL_HOST_FEATURES, CONTENT_FEATURES = _features['lexical_host'], _features['content']
_xgb1, _xgb2 = _tier1['XGBoost'], _tier2['XGBoost']
_explainer1, _explainer2 = shap.TreeExplainer(_xgb1), shap.TreeExplainer(_xgb2)


def risk_tier(proba_legit: float, low=.35, high=.65):
    score = round((1 - proba_legit) * 100, 1)
    return ('Safe' if proba_legit >= high else 'Dangerous' if proba_legit <= low else 'Suspicious'), score


def _reason_text(name, value):
    if name == 'IsHTTPS': return 'the URL uses HTTPS' if float(value) == 1 else 'the URL does not use HTTPS'
    if name == 'DomainLength': return 'the domain is unusually long' if float(value) >= 35 else 'the domain length is unusual'
    if name == 'URLLength': return 'the URL is unusually long' if float(value) >= 120 else 'the URL length is unusual'
    labels = {
        'TLDLegitimateProb': 'the top-level domain has low historical legitimacy',
        'HasObfuscation': 'the URL contains obfuscation markers', 'NoOfObfuscatedChar': 'the URL contains encoded characters',
        'IsDomainIP': 'the host is an IP address instead of a domain name', 'LetterRatioInURL': 'the URL has an unusual letter-to-character ratio',
        'DegitRatioInURL': 'the URL has an unusual digit-to-character ratio', 'SpacialCharRatioInURL': 'the URL has an unusual special-character ratio',
        'NoOfOtherSpecialCharsInURL': 'the URL contains unusual special characters', 'ObfuscationRatio': 'the URL contains encoded characters',
        'NoOfQMarkInURL': 'the URL contains query parameters', 'NoOfEqualsInURL': 'the URL contains assignment-style query data',
        'HasPasswordField': 'the page contains a password field', 'HasExternalFormSubmit': 'a form submits to another domain',
        'NoOfURLRedirect': 'the URL redirects through other locations', 'DomainTitleMatchScore': 'the page title does not closely match the domain',
    }
    return labels.get(name, name)


def _top_reasons(shap_row, names, values, top_n=5):
    pairs = sorted(zip(names, shap_row, values), key=lambda x: abs(x[1]), reverse=True)
    out = []
    for name, impact, value in pairs[:top_n]:
        direction = 'lowers risk' if impact > 0 else 'raises risk'
        out.append({'feature': name, 'value': round(float(value), 4), 'impact': round(float(impact), 4),
                    'direction': direction, 'text': _reason_text(name, value)})
    return out


def explanation_headline(tier, reasons, heuristic_reasons=None, lookalike=None):
    parts = []
    if lookalike and lookalike.get('flagged'): parts.append(lookalike['reason'])
    for item in heuristic_reasons or []:
        if item.get('direction') == 'raises risk': parts.append(item['text'])
    for item in reasons:
        if item.get('direction') == 'raises risk' and item.get('text') not in parts: parts.append(item['text'])
        if len(parts) >= 3: break
    if not parts: parts = ['the model found no strong phishing indicators']
    prefix = 'Blocked because' if tier == 'Dangerous' else 'Flagged because' if tier == 'Suspicious' else 'Considered safe because'
    return prefix + ' ' + '; '.join(parts[:3]) + '.'


def score_fast(feature_dict):
    x = np.array([[feature_dict[f] for f in LEXICAL_HOST_FEATURES]])
    legit = float(_xgb1.predict_proba(x)[0][1]); tier, score = risk_tier(legit)
    reasons = _top_reasons(_explainer1.shap_values(x)[0], LEXICAL_HOST_FEATURES, x[0])
    return {'tier': tier, 'risk_score': score, 'proba_legit': round(legit, 4), 'reasons': reasons,
            'reason_headline': explanation_headline(tier, reasons), 'model': 'XGBoost (Tier-1 Fast)'}


def score_deep(feature_dict):
    all_features = LEXICAL_HOST_FEATURES + CONTENT_FEATURES
    x = np.array([[feature_dict[f] for f in all_features]])
    legit = float(_xgb2.predict_proba(x)[0][1]); tier, score = risk_tier(legit)
    reasons = _top_reasons(_explainer2.shap_values(x)[0], all_features, x[0], top_n=8)
    return {'tier': tier, 'risk_score': score, 'proba_legit': round(legit, 4), 'reasons': reasons,
            'reason_headline': explanation_headline(tier, reasons), 'model': 'XGBoost (Tier-2 Deep)'}
