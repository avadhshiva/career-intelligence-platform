# Career Agent Platform (Phase 5)

Experimental workspace for the **agentic career platform**. The canonical deterministic
`career_intelligence_engine/` at the repository root remains **frozen** and unchanged.
This folder is an isolated copy-plus-orchestration layer for agent workflows.

## Separation of concerns

| Layer | Location | Status |
|-------|----------|--------|
| Deterministic intelligence engine | `career_intelligence_engine/` (embedded copy) | Stable baseline — ontology, scoring, calibration, matching, explainability, benchmarks, tests, Streamlit UI, APIs |
| Agent orchestration | `agents/`, `workflows/`, `orchestration/` | Phase 5 experimental |
| Human-in-the-loop | `agents/human_review_agent.py`, `memory/` | Scaffold |
| Browser automation | `browser/` | Future — not implemented |
| Application lifecycle | `applications/`, `memory/` | Scaffold — no auto-apply |

**Rules:** Do not modify `canonical_unified_pipeline` logic, ontology scoring behavior, or
benchmark fixtures in the embedded engine. Browser automation and auto-apply are out of scope
for Phase 5.

## Architecture

```
Resume Engine (deterministic)
        ↓
Job Discovery (agent)
        ↓
JD Matching (embedded JobMatchEngine)
        ↓
Human Review Queue
        ↓
Resume Tailoring (agent scaffold)
        ↓
Future Browser Automation
```

### Data flow

1. **Resume Engine** — `CareerIdentityEngine` parses resume text into a `CandidateProfile` with calibrated role-family scoring and explainability.
2. **Job Discovery** — `JobDiscoveryAgent` ingests JD text via `JobDescriptionParser` and capability vectors (no external APIs).
3. **JD Matching** — `JobMatchEngine` produces deterministic `JobMatchResult` with gates, gaps, and fit summary.
4. **Human Review Queue** — `HumanReviewAgent` + `ApplicationMemory` persist approve / reject / defer decisions.
5. **Resume Tailoring** — `ResumeTailoringAgent` placeholder; must preserve deterministic explainability on replay.
6. **Future Browser Automation** — `browser/` reserved for Playwright/LinkedIn adapters (credentials in `.env` only).

## Directory layout

```
career_agent_platform/
├── career_intelligence_engine/   # Embedded copy of frozen engine
├── agents/
│   ├── job_discovery_agent.py
│   ├── human_review_agent.py
│   └── resume_tailoring_agent.py
├── workflows/
│   └── recommendation_pipeline.py
├── orchestration/
├── browser/
├── memory/
│   └── application_memory.py
├── applications/
│   └── application_queue.py
├── monitoring/
├── configs/
├── logs/
├── requirements_agentic.txt
├── .env.example
├── run_agent_platform.ps1
└── README.md
```

## Quick start

From the repository root (or this folder):

```powershell
cd career_agent_platform
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements_agentic.txt
copy .env.example .env
.\run_agent_platform.ps1
```

The startup script:

- Activates `venv` (platform or parent)
- Sets `PYTHONPATH` to this folder
- Initializes JSON queue storage under `applications/data/`
- Launches the embedded Streamlit UI (`career_intelligence_engine/app/ui.py`)

## Running tests (embedded engine)

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest career_intelligence_engine/tests -q
```

## Configuration

Copy `.env.example` to `.env`:

| Variable | Purpose |
|----------|---------|
| `LINKEDIN_EMAIL` | Future LinkedIn automation |
| `LINKEDIN_PASSWORD` | Future LinkedIn automation |
| `OPENAI_API_KEY` | Future LLM tailoring / outreach |
| `PLAYWRIGHT_BROWSER_PATH` | Optional Playwright browser binary |

## Roadmap (TODO)

### Browser automation

- [ ] Playwright session manager under `browser/`
- [ ] LinkedIn job search adapter (read-only discovery first)
- [ ] Respect robots/ToS and explicit user consent gates
- [ ] No auto-submit in initial release

### Recruiter outreach

- [ ] Outreach templates with human approval
- [ ] Thread tracking in `memory/`
- [ ] Integration with review queue status

### Application memory

- [ ] Enrich `ApplicationMemory` with outcome tracking (interview, offer, rejection)
- [ ] Link queue items to tailored resume versions
- [ ] Export audit trail for compliance

### Learning loop

- [ ] Feedback from human decisions into recommendation ranking (offline only)
- [ ] Preserve deterministic replay for any learned weights
- [ ] A/B harness against benchmark fixtures

### Analytics dashboard

- [ ] `monitoring/` metrics for pipeline latency and match distribution
- [ ] Streamlit or separate dashboard for queue funnel
- [ ] Snapshot comparison with `benchmarks/` regression suite

## Example pipeline (Python)

```python
from workflows.recommendation_pipeline import RecommendationPipeline, PipelineInput

pipeline = RecommendationPipeline()
out = pipeline.run(
    PipelineInput(
        resume_text="...",
        jobs=[{
            "job_id": "job-001",
            "title": "Senior TPM",
            "company": "Example Corp",
            "jd_text": "...",
        }],
    )
)
```

## License & safety

Phase 5 scaffolds **do not** auto-apply to jobs, scrape behind login without user action,
or alter benchmark snapshots. All matching remains deterministic and explainable via the
embedded engine.
