# Gate 2 Minimal ETL Output

This is a small real graph slice. Every edge below has a source citation; no placeholder edges are emitted.

## Counts

- Nodes: 380
- Edges: 410
- Nodes by kind: `{"disease": 107, "drug": 36, "mechanism": 129, "research_condition": 54, "target": 54}`
- Condition nodes by category: `{"disease": 100, "research_condition": 61}`
- Default disease search/path-finding nodes: 100
- Excluded condition/research-condition nodes from default disease search/path-finding: 61
- Edges by type: `{"approved_for": 83, "associated_with": 17, "in_class_of": 147, "investigational_for": 104, "targets": 59}`
- Edges by source: `{"ClinicalTrials.gov": 104, "DailyMed + FDA Orange Book": 83, "Open Targets Platform": 123, "RxClass": 100}`

## Sample Edges

| Type | From | To | Source | Citation |
| --- | --- | --- | --- | --- |
| approved_for | propranolol | infantile hemangioma | DailyMed + FDA Orange Book | DailyMed b6f9dd2a-632b-87eb-70f0-b2064d7ed48a |
| approved_for | baricitinib | COVID-19 | DailyMed + FDA Orange Book | DailyMed 866e9f35-9035-4581-a4b1-75a621ab55cf |
| approved_for | methotrexate | Arthritis, Rheumatoid | DailyMed + FDA Orange Book | DailyMed 9b34b1d8-d125-41a2-9f6f-3fab67b573bd |
| approved_for | sirolimus | neoplasm with perivascular epithelioid cell differentiation | DailyMed + FDA Orange Book | DailyMed 0f9bb784-53e2-46f9-a65d-1c6c2a230eaf |
| approved_for | minoxidil | hair regrowth | DailyMed + FDA Orange Book | DailyMed 4cd1163f-76bf-8700-e063-6294a90a3688 |
| investigational_for | letrozole | breast cancer | ClinicalTrials.gov | NCT07401381 |
| investigational_for | baricitinib | Alopecia Areata | ClinicalTrials.gov | NCT06545110 |
| investigational_for | semaglutide | Obesity & Overweight | ClinicalTrials.gov | NCT07430059 |
| investigational_for | topiramate | Tinnitus | ClinicalTrials.gov | NCT06799169 |
| investigational_for | gabapentin | Heavy Drinking | ClinicalTrials.gov | NCT05443555 |
| targets | gabapentin | CACNA2D1 | Open Targets Platform | OT CHEMBL940 |
| targets | losartan | AGTR1 | Open Targets Platform | OT CHEMBL191 |
| targets | imatinib | KIT | Open Targets Platform | OT CHEMBL941 |
| targets | ruxolitinib | JAK1 | Open Targets Platform | OT CHEMBL1789941 |
| targets | letrozole | CYP19A1 | Open Targets Platform | OT CHEMBL1444 |
| in_class_of | anastrozole | Aromatase inhibitors | RxClass | RxClass L02BG |
| in_class_of | amitriptyline | Serotonin transporter inhibitor | Open Targets Platform | OT CHEMBL629 |
| in_class_of | doxycycline | Matrix metalloproteinase-1 inhibitor | Open Targets Platform | OT CHEMBL1200699 |
| in_class_of | propranolol | BETA BLOCKERS/RELATED | RxClass | RxClass CV100 |
| in_class_of | empagliflozin | Sodium/glucose cotransporter 2 inhibitor | Open Targets Platform | OT CHEMBL2107830 |
| associated_with | MT-ND6 | Leigh syndrome | Open Targets Platform | OT ENSG00000198695->MONDO_0009723 |
| associated_with | FKBP1A | breast cancer | Open Targets Platform | OT ENSG00000088832->MONDO_0007254 |
| associated_with | FKBP1A | atopic eczema | Open Targets Platform | OT ENSG00000088832->MONDO_0004980 |
| associated_with | ABCC9 | Hypertrichotic osteochondrodysplasia, Cantu type | Open Targets Platform | OT ENSG00000069431->Orphanet_1517 |
| associated_with | MT-ND6 | Leber hereditary optic neuropathy | Open Targets Platform | OT ENSG00000198695->MONDO_0010788 |

## ClinicalTrials Filtering Rule

ClinicalTrials edges require `overallStatus` to be active, an `armsInterventionsModule.interventions[]` entry with `type == DRUG`, and RxNorm ingredient normalization or an explicit literal named-drug fallback recorded in the edge attributes.

## MeSH Parsing Note

Condition normalization first tries exact/alias MeSH descriptor lookup and tags `disease` only when the descriptor is in a disease tree (`C*` or `F03*`). It then tries validated MONDO exact label/synonym matching. Remaining nodes are kept as `research_condition` with the raw source label.
Default disease search and default path-finding include only resolved MeSH/MONDO disease nodes. Raw/unmapped and phenotype/research-condition nodes remain in the graph for evidence display and repurposing signals, but are excluded from disease autocomplete/path queries unless explicitly requested later.

Minimal ETL uses the MeSH descriptor lookup API for the small slice. Full MeSH XML ingestion must use `iter_mesh_descriptors()`, which is implemented with `xml.etree.ElementTree.iterparse` and clears elements as they are yielded.
