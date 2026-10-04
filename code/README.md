# CatchPhish — Setup

## 1. Get the dataset
This folder does NOT include the dataset (56 MB, too big to bundle). Download it:
```
curl -L -o data/PhiUSIIL.csv "https://raw.githubusercontent.com/elaaatif/DATA-MINING-PhiUSIIL-Phishing-URL/main/PhiUSIIL_Phishing_URL_Dataset.csv"
```
(Create a `data/` folder first if it doesn't exist.)

## 2. Set up Python environment
```
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

## 3. Run the pipeline, in order
```
python 01_eda.py                          # dataset overview
python 02_pipeline.py                     # trains all 5 models x 2 tiers, saves to models/ and outputs/
python 03_explainability_and_risk.py      # SHAP + risk tiering demo
```

Outputs land in `outputs/` (results.json, shap_summary.png, feature_importance_shap.csv).
Trained models land in `models/` (tier1_models.pkl, tier2_models.pkl, risk_tier.py).

## Folder structure expected
```
code/
  01_eda.py
  02_pipeline.py
  03_explainability_and_risk.py
  requirements.txt
data/
  PhiUSIIL.csv        <- you download this
models/               <- created automatically
outputs/               <- created automatically
```
Note: scripts currently point to `/home/claude/catchphish/...` paths — update those to relative paths (`../data/PhiUSIIL.csv` etc.) once you're running locally in VS Code.
