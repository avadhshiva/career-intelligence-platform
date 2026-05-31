# Developer guide

Setup, troubleshooting, and persistence debugging for local development.

## Prerequisites

- Python 3.11+ recommended (3.10+ typically works)
- PowerShell or bash
- No database, Docker, or API keys required for the default path

## Fresh clone setup

```powershell
git clone <your-repo-url> JobIntelligence
cd JobIntelligence/career_agent_platform
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r ..\requirements.txt
copy ..\.env.example .env
$env:PYTHONPATH = (Get-Location).Path
streamlit run Home.py
```

**PYTHONPATH** must be `career_agent_platform` (the folder containing `Home.py`). The startup script sets this automatically:

```powershell
.\run_agent_platform.ps1
```

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `PYTHONPATH` | Yes | Must point to `career_agent_platform` |
| `CAREER_AGENT_LOG_LEVEL` | No | `DEBUG`, `INFO` (default), `WARNING` |
| `OPENAI_API_KEY` | No | Future LLM features only |
| `LINKEDIN_*` | No | Future browser automation only |

Copy `.env.example` from the repo root to `career_agent_platform/.env` if you use `python-dotenv` in future scripts. Streamlit does not require `.env` for core flows.

## Running tests

```powershell
cd career_agent_platform
$env:PYTHONPATH = (Get-Location).Path
pytest tests -q
pytest career_intelligence_engine/tests -q
```

- **Platform:** 95 tests — CI gate for UI/persistence orchestration.
- **Engine benchmarks:** 4 known failures — see [benchmark_drift_notes.md](benchmark_drift_notes.md).

## Startup troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| `ModuleNotFoundError: career_intelligence_engine` | `PYTHONPATH` not set | `cd career_agent_platform`; set `PYTHONPATH` to that directory |
| `ModuleNotFoundError: recommendation_engine` | Running from repo root | Run Streamlit from `career_agent_platform/` |
| Streamlit shows wrong/old pages | Wrong cwd | `streamlit run Home.py` only from platform root |
| Port already in use | Previous Streamlit still running | Stop other process or `streamlit run --server.port 8502 Home.py` |
| Blank Market Opportunities | No `career_profile` / canonical save failed | Re-run **Generate recommendations**; check logs for `canonical_resume_persist_failed` |
| Empty recommendations after restart | Queue repair removed bad rows | Check `applications/data/review_queue.json`; re-generate |
| Packages missing in workspace | No approved queue rows | Approve on Recommendations first |

## Restart and persistence debug tips

1. Enable debug logs: `$env:CAREER_AGENT_LOG_LEVEL = "DEBUG"`.
2. Watch for ops events: `queue_restore`, `profile_restore`, `canonical_resume_persisted`.
3. Inspect files (local only, gitignored):
   - `data/active_resume.json` — last resume id
   - `data/resumes/<id>.json` — must include `parsed_profile`
   - `applications/data/review_queue.json` — embedded `recommendation` blobs
4. **Market/Cockpit empty after restart** but queue has cards → canonical persist did not run or failed; re-upload resume and regenerate.
5. Purge demo noise: app calls `purge_demo_entries()` once per session for `sample_` / `preview_` prefixes.

## Dual engine layout

| Path | Role |
|------|------|
| `career_intelligence_engine/` (repo root) | Canonical engine source + benchmark tests |
| `career_agent_platform/career_intelligence_engine/` | Embedded copy for `PYTHONPATH` isolation |

Platform runtime uses the **embedded** copy. Keep them in sync when developing engine changes.

## Determinism

Matching does not use random seeds. Same resume text + same JD text → same scores. See [benchmark_drift_notes.md](benchmark_drift_notes.md) for known test expectation drift, not runtime nondeterminism.

## Public demo data

See [career_agent_platform/demo/public/README.md](../career_agent_platform/demo/public/README.md).

## Diagrams

- [architecture_diagram.md](architecture_diagram.md)
- [persistence_diagram.md](persistence_diagram.md)
