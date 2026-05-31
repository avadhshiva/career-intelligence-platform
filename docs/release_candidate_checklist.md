# Release candidate checklist (0.5.1)

Use this list before tagging a public technical review or demo session.

## Startup validation

- [ ] From `career_agent_platform/`: `streamlit run Home.py`
- [ ] No red exception boxes; sidebar pages load
- [ ] Home shows version `0.5.1`
- [ ] Ops log emits `app_startup` without errors

## Restart validation

- [ ] Generate recommendations with a real resume + sample feed
- [ ] Approve at least two roles (normal mode, not demo)
- [ ] Stop Streamlit completely; restart
- [ ] Queue and active resume restore; counts reconcile on Application Dashboard

## Snapshot validation

- [ ] `pytest tests/test_golden_recommendations.py -v` passes
- [ ] `python evaluation/golden/generate_golden_snapshots.py` is idempotent (re-run → same hashes)
- [ ] Golden `manifest.json` matches committed fixture IDs

## Demo-mode validation

- [ ] `CAREER_AGENT_DEMO_MODE=1 streamlit run Home.py` (or set in `.env`)
- [ ] Banner: **Demo Mode — persistence disabled**
- [ ] Recommendations and Market Intelligence still work
- [ ] `review_queue.json`, `data/resumes/`, `application_packages/` receive no new writes after generate/approve attempts
- [ ] `pytest tests/test_demo_mode.py -v` passes

## Known benchmark drift

Informational only (does not block RC if golden tests pass):

- `program_leadership_enterprise`, `cloud_transformation_lead` adjacency fixtures
- Aggregate `adjacency_hits=23/25`
- Program cluster calibration: `ai_program_management` in top-4

See [benchmark_drift_notes.md](benchmark_drift_notes.md).

## Repo hygiene checks

- [ ] No runtime JSON under `applications/data/` or `data/resumes/` in git (except `.gitkeep`)
- [ ] Golden snapshots under `evaluation/golden/` are intentional commits
- [ ] `demo/public/` artifacts regenerated via CI or `demo/generate_public_snapshots.py`
- [ ] No secrets in `.env` committed

## CI dry-run (local)

From repo root:

```powershell
cd career_agent_platform
$env:PYTHONPATH = (Get-Location).Path
python -m pytest tests -q --tb=short
$env:CAREER_AGENT_DEMO_MODE = "1"
python -m pytest tests/test_demo_mode.py -q
python evaluation/golden/generate_golden_snapshots.py
python demo/generate_public_snapshots.py
```

## Streamlit verification (full UI gate)

Follow `.cursor/rules/streamlit-verification-gate.mdc` checklist: Recommendations, Market Opportunities (5+ links), Application workspace, Career cockpit, session persistence.
