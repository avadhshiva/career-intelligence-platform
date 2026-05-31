# Architecture diagrams

Mermaid diagrams for the Career Agent Platform. Render on GitHub or any Mermaid-capable viewer.

## System layers

```mermaid
flowchart TB
    subgraph UI["Streamlit multipage UI"]
        Home[Home.py]
        Rec[Recommendations]
        Mkt[Market Opportunities]
        WS[Application Workspace]
        Dash[Application Dashboard]
    end

    subgraph Platform["career_agent_platform"]
        RE[RecommendationEngine]
        RQ[ReviewQueueManager]
        PKG[ApplicationPackageBuilder]
        CRS[CanonicalResumeStore]
        MI[MarketIntelligenceService]
    end

    subgraph Engine["career_intelligence_engine"]
        CIE[CareerIdentityEngine]
        JME[JobMatchEngine]
        ONTO[Ontology + eligibility]
    end

    subgraph Persist["JSON file persistence"]
        Resume[data/resumes/]
        Queue[applications/data/review_queue.json]
        Pkgs[application_packages/]
    end

    Home --> Rec
    Rec --> RE
    RE --> CIE
    RE --> JME
    Rec --> RQ
    Rec --> CRS
    WS --> PKG
    Mkt --> MI
    MI --> CIE
    RQ --> Queue
    CRS --> Resume
    PKG --> Pkgs
```

## Session state flow

```mermaid
flowchart LR
    subgraph Session["st.session_state (per browser tab)"]
        CP[career_profile]
        RECS[recommendations]
        EM[entry_map]
        RID[active_resume_id]
    end

    subgraph Disk["Restart-safe disk"]
        AR[data/active_resume.json]
        CR[data/resumes/id.json]
        RQ[review_queue.json]
    end

    Upload[Resume + JD ingest] --> CP
    Upload --> RECS
    Upload --> CR
    Upload --> AR
    Upload --> RQ

    Restart[App restart] --> AR
    AR --> RID
    CR --> CP
    RQ --> RECS
```

## Recommendation generation flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Recommendations page
    participant RE as RecommendationEngine
    participant EN as CareerIdentityEngine
    participant RQ as ReviewQueueManager
    participant CR as CanonicalResumeStore

    U->>UI: Resume + job descriptions
    UI->>RE: recommend_from_resume()
    RE->>EN: analyze_text + match jobs
    EN-->>RE: CandidateProfile + ranked results
    RE-->>UI: profile, recommendations
    UI->>CR: persist canonical resume
    UI->>RQ: enqueue_many()
    UI->>UI: session_state update
    U->>UI: Approve / reject
    UI->>RQ: transition state
```

## Package lifecycle

```mermaid
stateDiagram-v2
    [*] --> PendingReview: enqueue recommendation
    PendingReview --> Approved: human approve
    PendingReview --> Rejected: human reject
    Approved --> PackageGenerated: ApplicationPackageBuilder.build()
    PackageGenerated --> Applied: user marks applied
    Applied --> Archived: archive
    Rejected --> Archived: archive
```

## Market Opportunities dependency chain

```mermaid
flowchart TD
    A[Generate recommendations] --> B[career_profile in session]
    A --> C[canonical resume on disk]
    B --> D{Market page load}
    C --> D
    D -->|session hit| E[build_market_snapshot]
    D -->|session empty| F[load parsed_profile from disk]
    F --> E
    D -->|no profile| G[Prompt: run Recommendations first]
```
