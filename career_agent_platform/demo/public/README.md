# Public demo artifacts

Sanitized, fictional data for reviewers cloning this repository. **Not loaded automatically** — no personal data from developer machines.

| File | Purpose |
|------|---------|
| `sample_resume.txt` | Paste into **Recommendations** or upload as `.txt` |
| `sample_job_feed.json` | Check **Load sample job feed** on Recommendations |
| `sample_recommendations.json` | Reference output shape (scores are deterministic for this resume + feed) |
| `sample_package.json` | Reference application package structure |

## Quick walkthrough (5 minutes)

1. Start the app — see root [README.md](../../README.md) or [docs/DEVELOPER.md](../../docs/DEVELOPER.md).
2. Open **Recommendations**.
3. Paste contents of `sample_resume.txt`.
4. Enable **Load sample job feed**, then **Generate recommendations**.
5. Approve one role, open **Application workspace**, generate a package.
6. Open **Market opportunities** — requires profile from step 4 (persisted to `data/resumes/` locally).

Optional UI preview without pasting: add `?preview=hero` to the Recommendations URL (uses engine test fixtures; dev-only).

## Regenerate snapshots

After intentional engine changes (not routine):

```powershell
cd career_agent_platform
$env:PYTHONPATH = (Get-Location).Path
python demo/generate_public_snapshots.py
```

Commit updated JSON only if outputs remain fictional and deterministic.
