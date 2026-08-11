# Disease Web Source Probe

Generated: 2026-06-30 10:59:56 UTC

This checkpoint verifies live access and records real sample outputs before any graph or UI work.

## Summary

| Source | Status | HTTP | Sample |
| --- | --- | ---: | --- |
| ClinicalTrials.gov API v2 | go | 200 | `data\raw\source_probe\clinicaltrials_metformin_cancer_sample.json` |
| RxNorm / RxClass APIs | go | 200 | `data\raw\source_probe\rxnorm_rxclass_metformin_sample.json` |
| DailyMed API | go | 200 | `data\raw\source_probe\dailymed_metformin_spls_sample.json` |
| FDA Orange Book bulk data | manual |  | `data\raw\source_probe\orange_book_products_sample.json` |
| MeSH descriptor lookup and XML download | go | 200 | `data\raw\source_probe\mesh_diabetes_lookup_sample.json` |
| Open Targets Platform GraphQL | go | 200 | `data\raw\source_probe\open_targets_egfr_sample.json` |
| DisGeNET static downloads | risk | 200 | `data\raw\source_probe\disgenet_homepage_head.txt` |

## ClinicalTrials.gov API v2

URL: https://clinicaltrials.gov/api/v2/studies?query.intr=metformin&query.cond=cancer&pageSize=3&format=json

Status: **go**
Sample file: `data\raw\source_probe\clinicaltrials_metformin_cancer_sample.json`

Findings:
- Returned 3 sample studies.
- NCT01954732 | WITHDRAWN | PHASE1 | conditions=['Stage IA Pancreatic Cancer', 'Stage IB Pancreatic Cancer', 'Stage IIA Pancreatic Cancer'] | interventions=['metformin hydrochloride', 'pharmacological study']
- NCT03378297 | COMPLETED | EARLY_PHASE1 | conditions=['Ovarian Cancer'] | interventions=['Metformin', 'Acetylsalicylic acid', 'Olaparib']
- NCT05279768 | COMPLETED | PHASE1, PHASE2 | conditions=['Polycystic Ovary Syndrome'] | interventions=['UC-MSCs', 'Secretomes', 'UC-MSCs and Secretomes']
- Important: ClinicalTrials search can still return false positives; ETL must verify the drug is explicitly listed as an intervention.

Next step: Use API v2 as the investigational-use backbone, but create drug edges only after post-filtering named interventions through RxNorm normalization and active trial statuses.

## RxNorm / RxClass APIs

URL: https://rxnav.nlm.nih.gov/REST/rxcui.json?name=metformin

Status: **go**
Sample file: `data\raw\source_probe\rxnorm_rxclass_metformin_sample.json`

Findings:
- RxNorm ingredient lookup for metformin returned RxCUI=6809.
- RxClass returned 313 class records for RxCUI=6809.
- ATC: -> Combinations of oral blood glucose lowering drugs
- ATCPROD: -> Combinations of oral blood glucose lowering drugs
- VA:has_VAClass -> ORAL HYPOGLYCEMIC AGENTS,ORAL
- ATCPROD: -> Combinations of oral blood glucose lowering drugs
- VA:has_VAClass_extended -> ORAL HYPOGLYCEMIC AGENTS,ORAL

Next step: Use RxNorm for ingredient canonicalization and RxClass for class/mechanism-style edges where classes are populated.

## DailyMed API

URL: https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=metformin&pagesize=3

Status: **go**
Sample file: `data\raw\source_probe\dailymed_metformin_spls_sample.json`

Findings:
- DailyMed returned 3 SPL records for metformin sample query.
- setid=25be863d-490c-47f6-9ad3-c828dc43fbf0 | title=METFORMIN HYDROCHLORIDE TABLET, FILM COATED [QUALLENT PHARMACEUTICALS HEALTH LLC] | published=Jun 29, 2026
- setid=552ad61d-bafd-478d-e063-6294a90a02f9 | title=METFORMIN HYDROCHLORIDE TABLET [UNIT DOSE SOLUTIONS, INC.] | published=Jun 29, 2026
- setid=552df462-6dcb-e6f2-e063-6294a90aacfe | title=METFORMIN HCL TABLET [UNIT DOSE SOLUTIONS, INC.] | published=Jun 29, 2026
- Fetched one label detail XML for setid=25be863d-490c-47f6-9ad3-c828dc43fbf0.

Next step: Use SPL set IDs to fetch labels and extract indication/mechanism sections with conservative parsing.

## FDA Orange Book bulk data

URL: https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files

Status: **manual**
Sample file: `data\raw\source_probe\orange_book_products_sample.json`

Findings:
- Manual EOBZIP extraction found: products.txt, patent.txt, and exclusivity.txt.
- File sizes: products=7,441,149 bytes, patent=1,205,960 bytes, exclusivity=72,983 bytes.
- Products.txt columns: ['Ingredient', 'DF;Route', 'Trade_Name', 'Applicant', 'Strength', 'Appl_Type', 'Appl_No', 'Product_No', 'TE_Code', 'Approval_Date', 'RLD', 'RS', 'Type', 'Applicant_Full_Name'].
- Products.txt parsed 48,381 product rows.
- BUDESONIDE | BUDESONIDE | A | 215328
- BUDESONIDE | UCERIS | N | 205613
- MINOCYCLINE HYDROCHLORIDE | AMZEEQ | N | 212379
- AZELAIC ACID | AZELAIC ACID | A | 210928
- BETAMETHASONE VALERATE | BETAMETHASONE VALERATE | A | 215832

Risks / blockers:
- Known limitation: automated FDA bulk/search fetches hit bot/challenge protection in this environment. Treat Orange Book refresh as a manual monthly download step.

Next step: Use the manually downloaded monthly EOBZIP files in data/raw/orange_book for approved product grounding. Do not attempt to automate FDA AccessData fetches until a supported API, mirror, or challenge-free bulk URL is confirmed.

## MeSH descriptor lookup and XML download

URL: https://id.nlm.nih.gov/mesh/lookup/descriptor?label=Diabetes+Mellitus&match=exact&limit=5

Status: **go**
Sample file: `data\raw\source_probe\mesh_diabetes_lookup_sample.json`

Findings:
- Descriptor lookup returned 1 records.
- http://id.nlm.nih.gov/mesh/D003920 | Diabetes Mellitus
- 2026 descriptor XML HEAD status=200, size=312952703 bytes.

Next step: Use MeSH XML/RDF for disease and pharmacologic-action categories; do not use retired ASCII files.

## Open Targets Platform GraphQL

URL: https://api.platform.opentargets.org/api/v4/graphql

Status: **go**
Sample file: `data\raw\source_probe\open_targets_egfr_sample.json`

Findings:
- Target EGFR (ENSG00000146648) returned associated disease rows.
- non-small cell lung carcinoma | score=0.8525670184292347
- lung adenocarcinoma | score=0.7744435748658476
- cancer | score=0.7369034999647346

Next step: Use bounded GraphQL queries for demo-scale target/disease/drug enrichment; use downloads later if broad coverage becomes necessary.

## DisGeNET static downloads

URL: https://www.disgenet.com/

Status: **risk**
Sample file: `data\raw\source_probe\disgenet_homepage_head.txt`

Findings:
- DisGeNET homepage is reachable.

Risks / blockers:
- Direct static file access/licensing was not proven by this probe; treating as non-core until access is confirmed.

Next step: Keep out of the core build unless a direct permitted non-commercial download is confirmed by the user.

## Checkpoint Decision

Orange Book is usable for this build via the manually downloaded monthly EOBZIP files in data/raw/orange_book.

Known limitation: Orange Book refresh is a manual pipeline step for now because automated FDA fetches hit bot/challenge protection. Do not include DisGeNET in the core pipeline yet.
