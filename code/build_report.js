const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, ImageRun, BorderStyle
} = require("docx");

const results = JSON.parse(fs.readFileSync("/home/claude/catchphish/outputs/results.json", "utf8"));

function h(text, level) {
  return new Paragraph({ text, heading: level, spacing: { before: 240, after: 120 } });
}
function p(text, opts = {}) {
  return new Paragraph({ children: [new TextRun({ text, ...opts })], spacing: { after: 120 } });
}
function bullet(text) {
  return new Paragraph({ text, bullet: { level: 0 }, spacing: { after: 60 } });
}

function cell(text, opts = {}) {
  return new TableCell({
    width: { size: opts.width || 2000, type: WidthType.DXA },
    shading: opts.header ? { type: ShadingType.CLEAR, fill: "1F6FEB", color: "auto" } : undefined,
    children: [new Paragraph({
      children: [new TextRun({ text, bold: !!opts.header, color: opts.header ? "FFFFFF" : "000000" })],
    })],
  });
}

function resultsTable(tierResults) {
  const models = Object.keys(tierResults);
  const header = new TableRow({
    children: [
      cell("Model", { header: true, width: 2400 }),
      cell("Accuracy", { header: true, width: 1600 }),
      cell("Precision", { header: true, width: 1600 }),
      cell("Recall", { header: true, width: 1600 }),
      cell("F1-Score", { header: true, width: 1600 }),
      cell("ROC-AUC", { header: true, width: 1600 }),
    ],
  });
  const rows = models.map((m) => {
    const r = tierResults[m];
    return new TableRow({
      children: [
        cell(m, { width: 2400 }),
        cell(String(r.accuracy), { width: 1600 }),
        cell(String(r.precision), { width: 1600 }),
        cell(String(r.recall), { width: 1600 }),
        cell(String(r.f1), { width: 1600 }),
        cell(String(r.roc_auc), { width: 1600 }),
      ],
    });
  });
  return new Table({
    width: { size: 10800, type: WidthType.DXA },
    columnWidths: [2400, 1600, 1600, 1600, 1600, 1600],
    rows: [header, ...rows],
  });
}

const shapImage = fs.readFileSync("/home/claude/catchphish/outputs/shap_summary.png");

const doc = new Document({
  sections: [
    {
      properties: { page: { size: { width: 12240, height: 15840 } } },
      children: [
        new Paragraph({
          children: [new TextRun({ text: "CatchPhish", bold: true, size: 56, color: "1F6FEB" })],
          spacing: { after: 60 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "Real-Time URL Classification through Feature Engineering & ML", size: 28 })],
          spacing: { after: 60 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "PBL Progress Report — Month 1 & Month 2", italics: true, size: 24, color: "555555" })],
          spacing: { after: 60 },
        }),
        new Paragraph({
          children: [new TextRun({ text: "Gitika Omprakash (210425243069) & P. Ashvika (210425243179), AIDS-A, CIT", size: 22 })],
          spacing: { after: 400 },
        }),

        h("1. Novelty Statement", HeadingLevel.HEADING_1),
        p("Prior work identified in the literature survey (Sahingoz et al. 2019; Zieni et al. 2023; Das Guptta et al. 2024; Tamal et al. 2024) consistently trades off feature richness against real-time speed, and none provide interpretable, tiered decision output. CatchPhish addresses this gap with three additions:"),
        bullet("Two-Tier Detection Architecture — a Tier-1 fast model using only lexical + host-based features available instantly, before the page is fetched, followed by a Tier-2 deep model using webpage content features, invoked only when Tier-1 is uncertain."),
        bullet("Confidence-Tiered Risk Scoring — output is Safe / Suspicious / Dangerous with a 0–100 risk score rather than a brittle binary label."),
        bullet("Explainable Detection (SHAP) — every prediction can be traced to the specific URL characteristics that drove it, addressing the 'black box' criticism common to ML-based phishing detectors."),
        p("We also identified and explicitly corrected a data-leakage artifact: the PhiUSIIL dataset's URLSimilarityIndex feature equals exactly 100.0 for 100% of legitimate URLs, which alone yields perfect (and unrealistic) accuracy. All headline results below exclude this feature from the fast-path model for an honest evaluation; a reference run with it is included to document the artifact transparently."),

        h("2. Dataset", HeadingLevel.HEADING_1),
        p("PhiUSIIL Phishing URL Dataset (Prasad & Chandra, 2024): 134,850 legitimate and 100,945 phishing URLs, 54 features spanning lexical, host-based and content-based categories, zero missing values. A stratified subsample of 60,000 rows was used for training in this development phase for compute efficiency; the full 235,795-row dataset is available for the final Colab run before Review 3."),

        h("3. Feature Engineering", HeadingLevel.HEADING_1),
        p("Features were split by acquisition cost/latency:"),
        bullet("Tier 1 — Lexical + Host (21 features, instant): URL length, domain length, subdomain count, digit/letter/special-char ratios, obfuscation indicators, HTTPS usage, TLD legitimacy probability, etc."),
        bullet("Tier 2 — + Content-based (28 additional features, requires page fetch): line-of-code count, title-domain match score, redirect/popup/iframe counts, password/hidden-field presence, form submission target, image/CSS/JS counts, etc."),

        h("4. Model Training & Results", HeadingLevel.HEADING_1),
        p("Four base classifiers (Logistic Regression, Random Forest, XGBoost, SVM) plus a stacking ensemble meta-learner were trained and compared for each tier.", { bold: true }),
        p("Tier 1 — Fast / Realistic (lexical + host only, no leakage feature):"),
        resultsTable(results.tier1_fast_lexical_host),
        new Paragraph({ text: "", spacing: { after: 200 } }),
        p("Tier 2 — Deep (lexical + host + content-based features):"),
        resultsTable(results.tier2_deep_full),
        new Paragraph({ text: "", spacing: { after: 200 } }),
        p("Reference run — Tier 1 features + URLSimilarityIndex included, Random Forest (demonstrates leakage artifact):"),
        resultsTable({ "Random Forest (with leaky feature)": results.reference_with_leaky_feature }),
        new Paragraph({ text: "", spacing: { after: 200 } }),
        p("The Stacking Ensemble is the best-performing model in both tiers, and is adopted as CatchPhish's production model. The Tier-1 fast path alone achieves 99.7% accuracy with zero page-fetch latency, validating the two-tier design.", { bold: true }),

        h("5. Explainability (SHAP)", HeadingLevel.HEADING_1),
        p("SHAP (SHapley Additive exPlanations) was applied to the Tier-1 XGBoost model to identify which URL characteristics drive each prediction. IsHTTPS, count of special characters, letter ratio, and domain length emerged as the top global predictors — consistent with known phishing patterns (lack of HTTPS, unusual character density, and abnormally long or short domains)."),
        new Paragraph({
          children: [new ImageRun({ data: shapImage, transformation: { width: 500, height: 333 }, type: "png" })],
          spacing: { after: 120 },
        }),
        p("Figure 1: SHAP summary plot — feature impact on Tier-1 model output (1,000 test samples)."),

        h("6. Risk-Tiering Logic", HeadingLevel.HEADING_1),
        p("Rather than a hard 0/1 cutoff, predicted probability P(legitimate) is mapped to three actionable tiers:"),
        bullet("P(legit) ≥ 0.65 → Safe"),
        bullet("0.35 < P(legit) < 0.65 → Suspicious — Tier-2 deep check triggered automatically"),
        bullet("P(legit) ≤ 0.35 → Dangerous"),
        p("On a 10-sample held-out demonstration, all tiered predictions matched ground-truth labels."),

        h("7. Next Steps (Month 3, pre-Review 3)", HeadingLevel.HEADING_1),
        bullet("Build the real-time inference API (FastAPI/Flask) wrapping the two-tier + risk-scoring logic."),
        bullet("Build a minimal Chrome extension that calls the API on page navigation and shows the risk tier + top SHAP reasons as a popup."),
        bullet("Re-run final training on the full 235,795-row dataset (Colab) for the Review 3 headline numbers."),
        bullet("Stress-test against obfuscated/typosquatted URLs not in the original dataset to check real-world generalization."),
        bullet("Write final documentation, user manual, and prepare the demo video."),

        h("8. Artifacts Produced This Session", HeadingLevel.HEADING_1),
        bullet("data/PhiUSIIL.csv — full dataset (235,795 rows)"),
        bullet("notebooks/01_eda.py, 02_pipeline.py, 03_explainability_and_risk.py — full reproducible pipeline"),
        bullet("models/tier1_models.pkl, tier2_models.pkl — trained models (5 each, incl. stacking ensemble)"),
        bullet("models/risk_tier.py — reusable risk-scoring function"),
        bullet("outputs/results.json, feature_importance_shap.csv, shap_summary.png"),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("/home/claude/catchphish/outputs/CatchPhish_Progress_Report.docx", buf);
  console.log("done");
});
