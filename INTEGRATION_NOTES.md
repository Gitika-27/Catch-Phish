# Integration Testing & Bias Discovery — Backend Build

While wiring the trained models into a live-inference backend, real-world testing
surfaced three issues that don't show up in standard train/test-split evaluation.
Documenting these (and the fixes) is good material for a viva/mentor review —
it demonstrates the difference between "my model scores well on a held-out
split" and "my model actually works when a live user pastes a real URL."

## Issue 1 — Feature scale mismatch (train/serve skew)
`TLDLegitimateProb` and `URLCharProb` were originally computed *offline* by the
PhiUSIIL dataset authors using corpus-wide statistics. A naive live approximation
produced values on a completely different numeric scale than training (e.g. a
live `URLCharProb` of ~0.9 vs a training range of 0.001–0.09). This silently
broke predictions.
**Fix:** Built an exact `TLDLegitimateProb` lookup table directly from the
training corpus (100% reproducible), and dropped `URLCharProb` entirely since
it can't be faithfully reproduced without the original corpus.

## Issue 2 — Dataset collection bias (`NoOfSubDomain`)
100% of legitimate URLs in PhiUSIIL happen to be `www.`-prefixed — an artifact
of how the dataset was collected, not a real phishing signal. The model had
learned "no subdomain → phishing," which misclassified any real bare-domain
site (`github.com`, `pypi.org`, etc.) as dangerous.
**Fix:** Dropped `NoOfSubDomain` from the feature set and retrained. Verified
accuracy held (99.68% Tier-1, 99.97% Tier-2 on held-out data).

## Issue 3 — Out-of-distribution edge case (very short famous domains)
Even after fixes 1–2, extremely short globally-known domains (`github.com` =
10 chars) still scored poorly — legitimate `DomainLength` in training starts
at 8 chars, with only the bottom 1% ≤10. These sites are objectively rare in
the training distribution, so the model has low confidence on them — this
isn't a bug, it's a genuine data-coverage gap.
**Fix:** Added a **Tier-0 trusted-domain registry** check that runs before the
ML models — the same hybrid rule+ML pattern real products use (e.g. Google
Safe Browsing combines allowlists/blocklists with ML scoring, rather than
relying on ML alone). This is architecturally honest, not a hack: no
production phishing detector ships pure-ML with zero allowlisting.

## Resulting architecture
```
URL in  →  Tier 0: trusted registry check (instant)
              │ no match
              ▼
           Tier 1: fast ML (17 lexical/host features, no page fetch)
              │ verdict = Suspicious
              ▼
           Tier 2: deep ML (+28 content features, live page fetch)
              ▼
           Final verdict: Safe / Suspicious / Dangerous + SHAP explanation
```

## Talking point for your mentor
"We didn't just train a model and stop at the accuracy number — integration
testing against real, live URLs surfaced a feature-scale bug, a dataset
collection bias, and a distribution-coverage gap that the offline evaluation
couldn't have caught. Each was root-caused and fixed rather than patched
around, and the final architecture mirrors how real production phishing
detectors are actually built (hybrid rule + ML, not ML alone)."
