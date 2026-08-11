# Disease Web

Disease Web is an evidence-first screening tool for exploring disease connections through shared drugs and targets, and for reviewing active drug-repurposing signals. It is a portfolio project, not a clinical decision tool, investment thesis, or claim of drug efficacy.

The current finished slice contains 36 deliberately selected drugs, 380 nodes, 410 cited edges, and 9 audited active repurposing signals. Every displayed path edge and signal links back to its source record.

## What It Does

- **Explore paths:** choose two resolved disease concepts and inspect the shortest currently indexed route through drug and target nodes. Every route edge carries a relationship type, source, citation, and available confidence.
- **Review active signals:** compare an approved use with an active ClinicalTrials.gov use for the same drug. Each displayed signal has an approval anchor, NCT citation, trial phase/status, condition category, arm type, ranking score, and full-label overlap audit.
- **Keep uncertainty visible:** `research_condition` concepts such as Aging remain visible in signals but are not silently presented as diseases. Raw or unresolved condition strings are retained in the background data but excluded from default disease search and path endpoints.

## Evidence And Scope

| Data source | Used for |
| --- | --- |
| FDA Orange Book | Approved-drug grounding and application references |
| DailyMed | Structured label indications and full-label overlap checks |
| ClinicalTrials.gov API v2 | Active investigational uses, phase, status, NCT evidence, and intervention-arm inspection |
| Open Targets | Drug-target and gene-disease evidence edges |
| RxNorm/RxClass and MeSH | Drug normalization, mechanism classes, disease resolution, and category checks |

The Orange Book data in `data/raw/orange_book/` was manually downloaded from the FDA's official EOBZIP bulk release. FDA automation was blocked by bot/challenge protection, so a manual monthly download is a documented pipeline step. OTC monograph drugs are a known Orange Book coverage gap; where possible, their DailyMed labels provide the cited approval-purpose evidence.

## Important Limits

- A short graph route is usually caused by high-degree hub drugs. It is a property of this small graph, not a biological law or evidence that any two diseases are meaningfully connected.
- With only 36 seeded drugs, most disease pairs do not connect. A missing route can mean sparse indexing, missing seeds, or no indexed shared evidence; Disease Web does not invent a route.
- The signal list is a human-review screen, not a claimed opportunity. An active trial is not proof of efficacy, safety, approval likelihood, or commercial value.
- Combination-therapy trials are visibly labeled. They are not treated as independent single-drug evidence.
- Disease signals require a score of 44 or higher; `research_condition` signals use 25 or higher to retain sparse but potentially important aging-related research. These categories are deliberately **not** on equal evidentiary footing.
- Some unresolved DailyMed label retrievals cause the extractor to exclude a candidate rather than risk a false repurposing claim.

## Run The Finished App

```powershell
cd web
npm install
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
```

Open `http://127.0.0.1:4173`.

This workspace path contains `#`, which currently triggers a Vite/Rolldown development-server dependency-scan bug. The production bundle and `vite preview` run normally. For hot-module development, move or clone the project into a path without `#` before using `npm run dev`.

## Pipeline Artifacts

| Artifact | Contents |
| --- | --- |
| `reports/data_quality_gate3.md` | Coverage counts, resolution rates, rich/sparse diseases, and a non-hand-picked cited-edge sample |
| `reports/pathfinding_gate4.md` | Three real path queries, citations, alternative paths, and the cervical-cancer coverage-gap finding |
| `reports/repurposing_funnel_gate5.md` | Candidate funnel, removal reasons, score policy, concentration, trial-arm audit, and two-tier threshold explanation |
| `reports/approved_label_overlap_audit_gate5.md` | Systematic full approved-label overlap audit for all final signals |
| `reports/validation_gate6.md` | Ten known-example checks; all expected keep/exclude outcomes pass |
| `data/processed/minimal_etl/repurposing_signals_gate5.json` | Machine-readable final audited signal list |

## Refreshing The Slice

The ETL and analysis scripts live in `scripts/`. A data refresh must begin with the manual Orange Book download, then rerun normalization, the data-quality report, signal extractor, full-label audit, and known-example validation before replacing the frontend export. Do not treat a refresh as complete until those evidence gates are reviewed.
