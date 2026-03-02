# CrisisVerify — Architecture

## Sequence Flow

```
User → Frontend (Next.js)
     → POST /api/v1/analyze  { text, crisis_mode }
     → FastAPI Router (routes.py)
     → claim_extractor.py    → [LLM | heuristic fallback]
     → evidence_fetcher.py   → [Serper API | mock fallback]  ← per claim, concurrent
     → scoring_engine.py     + crisis_mode.py                ← per claim
     → report_generator.py   → AnalysisResponse JSON
     → Frontend renders ReportCard, ConfidenceMeter
```

## Module Responsibility Matrix

| Module | Responsibility | Dependencies |
|---|---|---|
| `api/routes.py` | HTTP contract, orchestration | All services |
| `services/claim_extractor.py` | Extract factual claims | Gemini API / heuristics |
| `services/evidence_fetcher.py` | Retrieve & weight evidence | Serper API / mock |
| `services/scoring_engine.py` | Compute credibility score | `crisis_mode.py` |
| `services/report_generator.py` | Aggregate per-claim results | None |
| `core/config.py` | Load all config/env vars | `pydantic-settings` |
| `core/crisis_mode.py` | Apply crisis-mode adjustments | `config.py` |
| `models/claim_models.py` | Domain types | pydantic |
| `models/request_models.py` | Input validation | pydantic |
| `models/response_models.py` | Output contract | pydantic |

## Data Flow

```
Raw Text (≤2000 chars)
  │
  ▼
claim_extractor.py ──► List[str]  (1–5 claims)
  │
  ├── For each claim (async concurrent):
  │     evidence_fetcher.py ─► List[Evidence]
  │       │   (source_name, url, snippet, published_date, credibility_weight)
  │       │
  │     scoring_engine.py ──► ClaimScore
  │       │   SourceWeight × Relevance × Recency × 100
  │       │   crisis_mode.py adjusts if crisis_mode=True
  │
  ▼
report_generator.py ──► AnalysisResponse
  (overall_confidence, overall_verdict, claim_results, scoring_breakdown, disclaimer)
```

## Trust Boundary Explanation

```
┌─────────────────────────────────────────────────────────────┐
│  TRUSTED ZONE                                                │
│  ┌──────────────┐    ┌──────────────────────────────────┐  │
│  │  Frontend    │◄──►│  Backend (stateless, no DB)      │  │
│  │  (Next.js)   │    │  Input validated, rate limited   │  │
│  └──────────────┘    └──────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────┘
                                  │ HTTPS
              ┌───────────────────┼────────────────────┐
              ▼                   ▼                    ▼
       Gemini API           Serper API         (No other external
       (LLM claims)         (Evidence)          connections)
       API-key auth         API-key auth
```

**Data that never leaves the backend:**
- Raw user input (logged only as character-length)
- API keys (environment variables, never in code)

**Stateless design:** No database, no persistent session, no user data stored.
