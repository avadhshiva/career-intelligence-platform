# Recruiter demo script — Job Intelligence

**Release:** `0.5.1`  
**Duration:** 5 minutes  
**Audience:** Recruiters, hiring managers, technical program leaders

---

## Before you start

### Setup (30 seconds — do this before the meeting)

```powershell
cd career_agent_platform
$env:PYTHONPATH = (Get-Location).Path
streamlit run Home.py
```

Open the app in a **single browser tab**. Use fictional demo data only.

| Item | Value |
|------|-------|
| Sample resume | Paste contents of `demo/public/sample_resume.txt` |
| Job feed | Enable **Load sample job feed** checkbox |
| Demo mode | Leave **off** (normal persistence) unless presenting on a shared machine — then set `CAREER_AGENT_DEMO_MODE=1` |

### Critical rule (DEF-001)

Always **generate recommendations in the same session** before visiting Market Opportunities or Career Cockpit. Skipping this step leaves intelligence sections empty.

---

## Demo flow overview

```
Overview (30s)
    → Recommendations: resume + generate (90s)
    → Approve 2 roles (45s)
    → Market Opportunities (45s)
    → Application Workspace (60s)
    → Career Cockpit (30s)
```

---

## Step 1 — Overview (30 seconds)

### Navigation

Sidebar → **Overview** (default landing page)

### What to click

1. Glance at the sidebar — confirm five pages visible.
2. Optionally expand **Engineering notes** expander.

### What to say

> "This is Job Intelligence — a human-in-the-loop career platform I built to unify resume analysis, explainable job ranking, approval gates, and application package generation. Everything persists across restarts using JSON files, no database required. The matching engine is fully deterministic — same resume and same jobs always produce the same scores."

### Expected outcome

| Check | Expected |
|-------|----------|
| Sidebar | Five pages: Overview, Recommendations, Market opportunities, Application workspace, Career cockpit |
| Version | Caption shows `0.5.1` |
| Errors | No red exception boxes |
| Journey rail | Visible workflow steps |

---

## Step 2 — Recommendations: resume + generate (90 seconds)

### Navigation

Sidebar → **Recommendations**

### What to click

1. Paste `demo/public/sample_resume.txt` into the resume text area (or upload if prepared).
2. Confirm the **resume identity card** appears (role family, experience, skills).
3. Check **Load sample job feed**.
4. Click **Generate recommendations** (or **Regenerate ranked recommendations**).
5. Scroll through ranked match cards.
6. Optional: expand **Details (explainability)** on one card.
7. Optional: expand **Recommendation governance** — point to hash and ontology version.

### What to say

> "I paste a resume and the engine parses it into a structured career profile — role family, skills, experience band. Then I load a sample job feed and generate ranked matches. Each card shows Fit and Confidence as separate metrics, plus a brief, strengths, and gaps. This is deterministic — if I run it again with the same inputs, I get identical scores. No LLM variance in the ranking path."

> "The governance panel logs a recommendation hash and ontology version after every generation — so I can audit exactly what scoring baseline was used."

### Expected outcome

| Check | Expected |
|-------|----------|
| Identity card | Role family and skills populated |
| Card count | Multiple ranked roles from sample feed |
| Metrics | Fit % and Confidence % as **separate chips** (not concatenated) |
| Brief | One-line summary per role |
| Strengths/gaps | Visible on each card |
| URLs | No `example.com`, preview IDs, or synthetic job links |
| Errors | None |

---

## Step 3 — Approve roles (45 seconds)

### Navigation

Stay on **Recommendations** → queue tabs at bottom

### What to click

1. Select **Pending** tab.
2. Click **Approve** on **at least two** strong-fit roles (avoid LOW_MATCH badges).
3. Optionally **Reject** one weak fit to show queue hygiene.
4. Switch to **Approved** tab — confirm count ≥ 2.

### What to say

> "Nothing moves to application generation without explicit human approval. I approve the roles I'm genuinely interested in — the rest stay pending or get rejected. This is intentional governance: the system recommends, but the human decides."

### Expected outcome

| Check | Expected |
|-------|----------|
| Approved count | ≥ 2 roles in Approved tab |
| Pending | Decreased after approvals |
| Workspace handoff | Approved roles will appear in Application workspace dropdown |

---

## Step 4 — Market Opportunities (45 seconds)

### Navigation

Sidebar → **Market opportunities**

### What to click

1. Review the market snapshot section (company/role-family fit percentages).
2. Scroll to skill-gap guidance if visible.
3. If curated feed cards appear: click **Search on LinkedIn** on one listing — confirm it opens a real LinkedIn search URL.

### What to say

> "Market Opportunities builds a fit snapshot from the same parsed profile — no external APIs, all in-process. It shows which companies and role families align with my background and where skill gaps exist. Listing links go to real LinkedIn search URLs, not placeholder domains."

### Expected outcome

| Check | Expected |
|-------|----------|
| Profile | Market snapshot **populated** (same session after generate) |
| Fit data | Company/role-family alignment visible |
| Links | LinkedIn search URLs only |
| Empty state | If empty: "Profile not analyzed yet" — go back and regenerate (DEF-001) |
| Errors | None |

---

## Step 5 — Application Workspace (60 seconds)

### Navigation

Sidebar → **Application workspace**

### What to click

1. Select an **approved role** from the dropdown (e.g., Enterprise Delivery Director).
2. Confirm **active resume** is shown from Recommendations handoff.
3. Click **Generate application package**.
4. Browse tabs: **Tailored resume**, **Cover letter**, **Recruiter messages**, **Interview prep**.
5. Click **Export PDF** or **Export TXT** — briefly show the header includes labeled match scores.

### What to say

> "For each approved role, I generate a full application package — tailored resume, cover letter, recruiter outreach messages, and interview prep. The export includes the Fit and Confidence scores from the original recommendation, so the narrative stays tied to the scoring evidence. Packages persist to disk — I can close the app and pick up where I left off."

### Expected outcome

| Check | Expected |
|-------|----------|
| Selector | Approved roles available in dropdown |
| Hero | Fit/Confidence chips and positioning paragraph |
| Tabs | Non-empty content in each artifact tab |
| Export | Header: `Match scores: Fit: X% · Confidence: Y%` |
| URLs | No `example.com` or broken apply links |
| Errors | None |

---

## Step 6 — Career Cockpit (30 seconds)

### Navigation

Sidebar → **Career cockpit**

### What to click

1. Review **Application pipeline** count.
2. Glance at intelligence tiles (role family, dimensions, market fit, readiness).
3. Expand one **recent package** expander — show why-matched / gaps narrative.
4. Mentally compare pipeline count with workspace saved packages.

### What to say

> "The Career Cockpit is the command center — pipeline counts, intelligence tiles from my profile, and recent package summaries. Counts reconcile with the Application workspace. This is where I'd track my active search across multiple approved roles."

### Expected outcome

| Check | Expected |
|-------|----------|
| Pipeline | Package count matches workspace (e.g., 3 packages) |
| Intelligence | Tiles populated when profile available from step 2 |
| Recent packages | Expanders with why-matched / gaps text |
| Errors | None |
| Navigation | All sidebar links work |

---

## Closing statement (15 seconds)

> "To summarize: Job Intelligence is a complete career workflow — parse, rank, approve, package, track — with deterministic scoring, human governance, restart-safe persistence, and 240-plus automated tests. It's built to demonstrate systems engineering and program discipline, not just AI prompts. Happy to walk through the architecture or test strategy in more detail."

---

## Troubleshooting during live demo

| Problem | Fix |
|---------|-----|
| Market/Cockpit empty | Go to Recommendations → enable sample feed → Regenerate → return |
| "Add at least one job description" on regenerate | Check **Load sample job feed** |
| Fit/Confidence look concatenated | Refresh page — CSS fallback should separate chips |
| Red error box | Check terminal for traceback; restart app |
| Duplicate cockpit entries | Known low-severity (DEF-002) — use package switcher in workspace |
| Persistence not working | Confirm demo mode is **off** (`CAREER_AGENT_DEMO_MODE` unset) |

---

## Optional: persistence proof (+2 minutes)

If the audience asks "does it survive a restart?":

1. Stop Streamlit (`Ctrl+C` in terminal).
2. Restart: `streamlit run Home.py`.
3. Navigate to Recommendations — confirm queue and approvals restored.
4. Navigate to Application workspace — confirm saved packages present.

> "Everything rehydrates from JSON files on disk — queue, approvals, packages, and profile. No database, no cloud dependency."

**Note:** Market/Cockpit intelligence may show empty state after cold restart if `parsed_profile` was not persisted (DEF-001). Regenerate once to repopulate.

---

## Screenshot reference

| Step | Screenshot file |
|------|-----------------|
| 1 — Overview | `docs/screenshots/01-overview.png` |
| 2 — Recommendations | `docs/screenshots/02-recommendations.png` |
| 4 — Market | `docs/screenshots/03-market.png` |
| 5 — Workspace | `docs/screenshots/04-workspace.png` |
| 6 — Cockpit | `docs/screenshots/05-dashboard.png` |

---

## Related documents

| Document | Purpose |
|----------|---------|
| [demo_walkthrough.md](demo_walkthrough.md) | Detailed 12–15 minute walkthrough with all checks |
| [interview_talking_points.md](interview_talking_points.md) | Architecture and TPM prep |
| [RELEASE_REPORT.md](RELEASE_REPORT.md) | Defect register and validation evidence |
| [DEVELOPER.md](DEVELOPER.md) | Setup and troubleshooting |
