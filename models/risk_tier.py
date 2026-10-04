def risk_tier(proba_legit, low=0.35, high=0.65):
    risk_score = round((1 - proba_legit) * 100, 1)
    if proba_legit >= high:
        tier = "Safe"
    elif proba_legit <= low:
        tier = "Dangerous"
    else:
        tier = "Suspicious - deep check recommended"
    return tier, risk_score
