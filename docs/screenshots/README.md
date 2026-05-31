# Screenshot index — Job Intelligence

Portfolio and README assets for recruiter-facing review. Use **fictional** demo data from `career_agent_platform/demo/public/` only.

---

## Required captures

| File | Page | What to show | Used in |
|------|------|--------------|---------|
| `01-overview.png` | **Overview** (`Home.py`) | Sidebar navigation (all five pages), journey rail, version `0.5.1` | Root README, portfolio deck |
| `02-recommendations.png` | **Recommendations** | Ranked match cards with separate **Fit** and **Confidence** chips; identity card visible | Root README |
| `03-market.png` | **Market opportunities** | Populated company/role-family snapshot (**after** generating recs in same session) | Root README |
| `04-workspace.png` | **Application workspace** | Approved job selected, package hero, tab strip (resume / cover letter / prep) | Root README |
| `05-dashboard.png` | **Career cockpit** | Pipeline count, intelligence tiles, recent package expander | Root README |

---

## Capture procedure

1. From `career_agent_platform/`: `streamlit run Home.py`
2. Follow [demo_walkthrough.md](../demo_walkthrough.md) steps 1–7.
3. Save PNGs to this folder with exact filenames above.
4. Verify README image links render on GitHub.

**Important:** Step 3 for `03-market.png` requires **Generate recommendations** in the same session before opening Market — otherwise the screenshot will show empty-state guidance only (valid but weaker for portfolio).

---

## Privacy checklist

- [ ] No real names, employers, or emails in frame
- [ ] No machine-specific paths in window title or file dialogs
- [ ] Sample resume from `demo/public/sample_resume.txt` only
- [ ] Normal mode or explicit demo banner if using `CAREER_AGENT_DEMO_MODE=1`

---

## Repository status (2026-05-31)

| File | On disk | Portfolio quality | Notes |
|------|---------|-------------------|-------|
| `01-overview.png` | Yes | Good | Sidebar, journey rail, version caption |
| `02-recommendations.png` | Yes | Good | Ranked cards, Fit/Confidence chips |
| `03-market.png` | Yes | Good | Populated market snapshot |
| `04-workspace.png` | Yes | Good | Approved job selector, package CTA |
| `05-dashboard.png` | Yes | Fair | Pipeline visible; intelligence tiles may show empty state (DEF-001) — re-capture after in-session generate for best portfolio impression |

**Before public GitHub publish:** Confirm all five PNGs are **git-tracked** (not just on disk locally) so README embeds do not 404. Re-capture `05-dashboard.png` with profile populated if presenting to recruiters.

---

## Related documentation

- [demo_walkthrough.md](../demo_walkthrough.md) — step-by-step expected outcomes
- [recruiter_demo_script.md](../recruiter_demo_script.md) — 5-minute presenter script
- [demo_script.md](../demo_script.md) — extended talking points
- [RELEASE_REPORT.md](../RELEASE_REPORT.md) — validation evidence
