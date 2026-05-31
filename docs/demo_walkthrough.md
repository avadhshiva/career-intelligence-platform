# Demo walkthrough — Job Intelligence (recruiter & portfolio)

**Release:** `0.5.1`  
**Duration:** 12–15 minutes  
**Prerequisites:** Python 3.11+, dependencies from repo root `requirements.txt`, `PYTHONPATH` set to `career_agent_platform/`

```powershell
cd career_agent_platform
$env:PYTHONPATH = (Get-Location).Path
streamlit run Home.py
```

Use **fictional** demo data only: `demo/public/sample_resume.txt` and **Load sample job feed**.

---

## 1. Open Overview

**Navigation:** Sidebar → **Overview** (`Home.py`)

**Actions**

1. Start the app and confirm no red exception boxes.
2. Read the reviewer journey rail and version caption (`0.5.1`).
3. Open **Engineering notes** expander if present — scope boundary (no auto-apply, deterministic path).

**Expected outcomes**

| Check | Expected |
|-------|----------|
| Sidebar | Five pages: Overview, Recommendations, Market opportunities, Application workspace, Career cockpit |
| Version | Matches `career_agent_platform/version.py` |
| Errors | None on load |
| Messaging | Human-in-the-loop workflow; JSON persistence; no database |

**Screenshot:** `docs/screenshots/01-overview.png`

---

## 2. Upload Resume

**Navigation:** Sidebar → **Recommendations**

**Actions**

1. Paste contents of `demo/public/sample_resume.txt` (or upload a sanitized PDF).
2. Confirm **resume identity card** (role family, experience band, skills summary).
3. Do **not** use real PII in public recordings.

**Expected outcomes**

| Check | Expected |
|-------|----------|
| Identity card | Populated role family and skills from parsed resume |
| Active resume | Canonical marker written under `data/` (normal mode) |
| Errors | None; validation only if resume empty |

**Screenshot:** Capture after identity card visible (often combined with step 3).

---

## 3. Generate Recommendations

**Navigation:** Stay on **Recommendations**

**Actions**

1. Enable **Load sample job feed** if no job descriptions are cached.
2. Click **Generate recommendations** (or **Regenerate ranked recommendations**).
3. Review ranked match cards: Fit %, Confidence %, priority badge, brief, strengths/gaps.
4. Optional: expand **Details (explainability)** and **Recommendation governance** (hash, ontology version).

**Expected outcomes**

| Check | Expected |
|-------|----------|
| Card count | Multiple ranked roles from sample feed |
| Metrics | Fit and Confidence render as **separate chips** (not concatenated text) |
| Determinism | Same resume + same JDs → same scores on re-run |
| Persistence | Queue rows and `parsed_profile` written to disk (required for Market/Cockpit after restart) |
| URLs | No `example.com`, `currentJobId`, or synthetic listing IDs in cards |

**Screenshot:** `docs/screenshots/02-recommendations.png`

**Demo risk (DEF-001):** Skipping this step before Market/Cockpit leaves intelligence sections empty after cold restart. Always generate in-session before steps 5 and 7.

---

## 4. Approve Roles

**Navigation:** Stay on **Recommendations** → queue tabs

**Actions**

1. Approve **at least two** strong-fit roles (avoid LOW_MATCH / gated roles).
2. Optionally reject or archive one weak fit to show queue hygiene.
3. Open **Review queue** expander — confirm Pending / Approved counts update.

**Expected outcomes**

| Check | Expected |
|-------|----------|
| Approved count | ≥ 2 roles in Approved tab |
| Workspace handoff | Approved roles available on Application workspace selector |
| Disk | `applications/data/review_queue.json` updated (normal mode) |
| Demo mode | If `CAREER_AGENT_DEMO_MODE=1`, writes blocked and banner shown |

---

## 5. Review Market Opportunities

**Navigation:** Sidebar → **Market opportunities**

**Actions**

1. Visit **after** step 3 in the **same browser session** (or after successful generate with `parsed_profile` on disk).
2. Review company/role-family alignment and skill-gap sections.
3. If curated feed is shown: open **Search on LinkedIn** for 2–3 listings — confirm real search URLs.

**Expected outcomes**

| Check | Expected |
|-------|----------|
| Profile | Market snapshot populated when `career_profile` or canonical `parsed_profile` exists |
| Empty state | Clear guidance + link back to Recommendations if profile missing |
| Links | LinkedIn search URLs only; no placeholder domains |
| Errors | None |

**Screenshot:** `docs/screenshots/03-market.png` (repopulated view preferred over empty-state)

---

## 6. Generate Application Package

**Navigation:** Sidebar → **Application workspace**

**Actions**

1. Select an **approved** role from the queue dropdown.
2. Click **Generate application package**.
3. Browse tabs: tailored resume, cover letter, recruiter messages, interview prep.
4. Export PDF or TXT — confirm header includes `Match scores: Fit: X% · Confidence: Y%`.

**Expected outcomes**

| Check | Expected |
|-------|----------|
| Hero | Fit/Confidence chips, positioning paragraph, strengths/gaps |
| Artifacts | Non-empty tailored content per tab |
| Export | Labeled match scores in export body |
| Persistence | Package file under `applications/data/application_packages/` |
| URLs | No `example.com` or broken apply links in package |

**Screenshot:** `docs/screenshots/04-workspace.png`

---

## 7. Open Career Cockpit

**Navigation:** Sidebar → **Career cockpit** (`Application_Dashboard.py`)

**Actions**

1. Review intelligence tiles (role family, dimensions, market fit, readiness) — requires profile from step 3.
2. Compare **pipeline package count** with Application workspace saved packages.
3. Expand a recent package — why matched / gaps narrative.

**Expected outcomes**

| Check | Expected |
|-------|----------|
| Counts | Pipeline total reconciles with workspace (known low-severity duplicate list possible — DEF-002) |
| Intelligence | Tiles populated when profile available; empty state otherwise |
| Errors | None |
| Navigation | All sidebar links work from this page |

**Screenshot:** `docs/screenshots/05-dashboard.png`

---

## Optional: persistence proof (2 min)

1. Stop Streamlit (`Ctrl+C`).
2. Restart `streamlit run Home.py`.
3. Confirm queue, approvals, packages, and profile restore without demo-data resurrection in normal mode.

---

## Quick reference

| Step | Page | Must-see proof |
|------|------|----------------|
| 1 | Overview | Navigation + version |
| 2 | Recommendations | Resume identity |
| 3 | Recommendations | Ranked deterministic cards |
| 4 | Recommendations | ≥ 2 approvals |
| 5 | Market opportunities | Fit snapshot (same session) |
| 6 | Application workspace | Package + export |
| 7 | Career cockpit | Reconciled counts |

**Related docs:** [demo_script.md](demo_script.md) (presenter talking points) · [RELEASE_REPORT.md](RELEASE_REPORT.md) (defects & validation) · [DEVELOPER.md](DEVELOPER.md) (troubleshooting)
