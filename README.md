# CrisisVerify

> Open-source AI-assisted claim verification for high-stakes scenarios.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The Problem We Are Solving

When a major earthquake strikes and reports flood in — "Dam collapsed, 10,000 displaced" — how do first responders, journalists, and public officials know what is true?

In the first 72 hours of any crisis, misinformation does not just spread — it **accelerates**. False reports of road closures redirect aid convoys. Unverified casualty figures paralyze emergency coordination. Rumours of chemical contamination empty hospitals of staff who are needed elsewhere.

> A 2022 Reuters Institute study found that during major crisis events, false claims reach 6× more people in the first hour than corrections issued later.

There is currently no **lightweight, open-source, structured claim-verification assistant** designed for these high-stakes scenarios. CrisisVerify is that tool.

---

## What CrisisVerify Does

Accepts any text input → extracts factual claims → retrieves supporting or contradicting evidence from trusted sources → **scores credibility using a fully transparent formula** → returns a structured verification report.

**It is NOT:**
- A fact-checking authority
- A censorship tool or propaganda detector
- A mass surveillance system

**It IS:**
- A triage assistant for analysts, journalists, and crisis responders
- A system that shows exactly *how* it reached every conclusion
- A stateless, privacy-respecting, open-source tool anyone can deploy

---

## System Architecture

```
┌─────────────┐    POST /api/v1/analyze    ┌────────────────────────────────┐
│  Next.js UI │ ─────────────────────────► │        FastAPI Backend          │
│  (Port 3000)│ ◄───────────────────────── │        (Port 8000)              │
└─────────────┘    AnalysisResponse JSON   └──────────┬─────────────────────┘
                                                       │
                ┌──────────────────────────────────────┼────────────────────┐
                ▼                                      ▼                    ▼
       claim_extractor.py                  evidence_fetcher.py    scoring_engine.py
       Gemini LLM / heuristic             Serper API / mock      Formula + crisis_mode.py
                                                                            │
                                                                            ▼
                                                                   report_generator.py
                                                                   Structured JSON response
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for full data flow, module responsibility matrix, and trust boundaries.

---

## Demo Scenario

**Input text:**
> "Major dam has collapsed after earthquake in Region X, displacing an estimated 50,000 residents."

**Expected output** (no API keys, demo mode):
- Extracted claims: ["Dam has collapsed after earthquake in Region X", "50,000 residents displaced"]
- Verdict per claim: **Developing**
- Overall verdict: **Developing**
- Reasoning: Credible news sources are reporting the event but no official confirmation exists. Treat as unconfirmed.

This reflects the responsible, realistic output for a genuinely uncertain situation.

---

## Scoring Methodology

```
Credibility Score = SourceWeight × RelevanceScore × RecencyFactor × 100
```

| Component | How It's Computed |
|---|---|
| **SourceWeight** | Domain whitelist lookup (0.30 – 0.90). Configured via `core/config.py`. |
| **RelevanceScore** | Keyword overlap between claim text and evidence snippet (0.10 – 1.00). |
| **RecencyFactor** | Article age: <48h = 1.0, 2–7 days = 0.85, older/unknown = 0.60. |

**Verdict Thresholds:**
- `≥ 75` → **Verified**
- `40–74` → **Developing**
- `< 40` → **Likely False**

**Crisis Mode** raises the effective threshold by 15 points and applies up to 15% penalty for emotionally loaded language.

**Source Trust Hierarchy:**

| Source Type | Weight |
|---|---|
| Government / UN agencies | 0.90 |
| Academic institutions | 0.85 |
| Established global news media | 0.80 |
| Humanitarian NGOs | 0.75 |
| Unknown/unrecognized sources | 0.30 |

Every score in the UI includes a **full human-readable explanation** of how it was derived.

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- (Optional) [Gemini API key](https://makersuite.google.com/app/apikey) — for LLM claim extraction
- (Optional) [Serper API key](https://serper.dev) — for live evidence retrieval

The app runs fully in **demo mode with no API keys**.

```bash
git clone https://github.com/your-org/crisisverify.git
cd crisisverify

cp backend/.env.example backend/.env  # optionally add API keys

docker-compose up --build
```

- **Frontend:** http://localhost:3000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

### Run Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## ⚠ Limitations

**We believe intellectual honesty is a feature, not a bug. This section is not a disclaimer — it is a design specification.**

1. **Not a fact-checking authority.** CrisisVerify provides structured analysis, not ground truth. A score of 80 does not mean a claim is true.

2. **LLM extraction may miss implicit or embedded claims.** Gemini extracts explicitly stated facts. Inferences, implications, and culturally-specific framings may be missed.

3. **Source coverage is language-biased.** Web search APIs (Serper/Google) skew toward English-language publications. Crisis events in underserved regions may have fewer indexed sources.

4. **Recency cannot always be determined.** Many publishers do not expose publish dates via metadata. These default to the lowest recency factor (0.60) out of caution.

5. **Not immune to coordinated misinformation.** If multiple high-credibility outlets repeat the same false claim, the system may score it high. Source consensus ≠ truth.

6. **Crisis Mode detection is heuristic.** Emotional language is detected via regex patterns, not deep semantic analysis. Nuanced language may evade detection.

7. **Human review is mandatory in life-safety contexts.** This tool is a triage aid. Acting on its output alone in an emergency situation is inappropriate.

---

## Future Improvements

- Multi-language support for crisis regions (Arabic, French, Swahili)
- Direct integration with GDACS, ReliefWeb, UN OCHA data feeds
- Named entity recognition for richer claim extraction
- Confidence calibration via historical accuracy tracking
- Browser extension for real-time page analysis
- Audit log for organizational accountability (privacy-preserving)

---

## License

MIT — see [LICENSE](LICENSE).
