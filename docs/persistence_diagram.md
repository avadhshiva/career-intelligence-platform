# Persistence diagrams

How disk and session cooperate across restarts.

## Persistence restore flow (cold start)

```mermaid
flowchart TD
    Start[Streamlit process start] --> Init[_init_session on Recommendations]
    Init --> QInit[ReviewQueueManager.initialize]
    QInit --> Repair[repair_queue_store]
    Init --> CheckRecs{recommendations in session?}
    CheckRecs -->|no| LoadQ[Read review_queue.json]
    LoadQ --> RestoreRecs[RecommendationResult.from_dict per row]
    RestoreRecs --> SetRecs[session recommendations + entry_map]
    Init --> CheckProf{career_profile in session?}
    CheckProf -->|no| LoadMarker[load_active_resume_id]
    LoadMarker --> LoadCanon[CanonicalResumeStore.load]
    LoadCanon --> Validate[CandidateProfile.model_validate]
    Validate --> SetProf[session career_profile]
    CheckProf -->|yes| Ready[Pages ready]
    SetRecs --> Ready
    SetProf --> Ready
```

## Write path after generation

```mermaid
flowchart LR
    Gen[recommend_from_resume] --> Sess[session: profile + recs]
    Gen --> Canon[canonical resume JSON]
    Gen --> Marker[active_resume.json]
    Gen --> Queue[review_queue entries]
    Canon --> Mkt[Market Opportunities]
    Canon --> Cockpit[Career dashboard counts]
    Queue --> WS[Application Workspace approved list]
```

## Data ownership

```mermaid
flowchart TB
    subgraph Authoritative["Authoritative on restart"]
        Q[review_queue.json]
        CR[canonical resume files]
        AM[active_resume.json]
        PK[package JSON files]
    end

    subgraph Cache["Session cache only"]
        SR[recommendations list]
        MP[match postings cache]
    end

    Q -.->|hydrate| SR
    CR -.->|hydrate| CP[career_profile]
```

## Failure modes (documented, not auto-fixed)

```mermaid
flowchart TD
    PFail[Canonical persist fails] --> Warn[UI warning shown]
    PFail --> SessOK[In-session recs still work]
    SessOK --> Restart[After restart]
    Restart --> NoProf[Market/Cockpit may lack profile]
    QOnly[Queue without canonical] --> Cards[Cards restore]
    QOnly --> NoMkt[Market snapshot blocked]
```
