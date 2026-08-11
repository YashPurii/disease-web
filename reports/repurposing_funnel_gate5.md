# Gate 5 Repurposing Signals Funnel

## Ranking

Score = trial phase (0-40) + active status (0-12) + ClinicalTrials.gov last-update recency (0-12). This is a screening priority score, not evidence of efficacy, safety, or commercial value.

- Phase: Phase 4=40; Phase 2/3=35; Phase 3=30; Phase 2=20; Phase 1/2=15; Phase 1=10; N/A=8; Early Phase 1=5.
- Status: Recruiting=12; Active, not recruiting=8; Not yet recruiting=4.
- Recency: updated <=1 year=12; <=3 years=8; <=6 years=4; older=1; unavailable=0.

## Two-Tier Threshold Policy

Disease signals require a score of at least 44. Mapped research_condition signals require 25 because aging/life-stage trials are expected to be sparse and an Early Phase 1 study should not automatically conceal a conceptually important screened signal such as sirolimus -> Aging.

The categories are not on equal evidentiary footing: a research_condition result is explicitly labeled, has a lower inclusion threshold, and must never be compared as though it had disease-level evidence. This wording is required in the Gate 8/README narrative.

## Anchor Audit

- Aspirin: no primary indication is distinguished in the retained OTC labels. Available purposes are pain relief, fever reduction, and minor aches/pains; Fever is not presented as a primary indication.
- Doxycycline: no primary indication is distinguished. Available labels cover rickettsial, sexually transmitted, respiratory, bacterial, ophthalmic, anthrax, penicillin-alternative, amebiasis/acne, malaria-prophylaxis, and adult periodontitis adjunctive treatment. The original eight-SPL retrieval was incomplete; the widened future ETL query will cover up to 100 results.
- Verified correction: doxycycline -> Chronic Periodontitis was removed because DailyMed setid b3cd7b44-db40-4ce5-895e-d4c85a0068ae already labels doxycycline hyclate for adult periodontitis adjunctive treatment.

## Trial Arm Verification

- NCT07634341 has one active-comparator arm containing a local chitosan nanoparticle formulation loaded with both doxycycline and atorvastatin, after scaling/root planing. It is a combination-therapy trial, not two independent single-drug arms. Remaining signals retain `trial_arm_type=combination` plus both partner drugs so the evidence cannot be read as independent support.

## Funnel

- Raw different-condition pairs: 93
- After indication-difference filter: 22
- After active-status and phase requirement: 22
- After per-drug/NCT duplicate collapse: 21
- Final signals after conservative score threshold: 9
- Distinct drugs represented: 9
- Top four drugs account for 4/9 signals (44%). No four-drug majority.

## Removed Pairs

- semaglutide -> Obesity & Overweight (NCT07430059): research condition is not an in-scope mapped life-stage/aging MeSH concept
- gabapentin -> Heavy Drinking (NCT05443555): procedural, outcome, symptom, stage, or overly broad condition label
- metformin -> Pelvic Pain (NCT06611501): procedural, outcome, symptom, stage, or overly broad condition label
- colchicine -> Diabete Type 2 (NCT05633810): research condition is not an in-scope mapped life-stage/aging MeSH concept
- imatinib -> lymphoblastic leukemia, acute, with lymphomatous features (NCT04307576): same broad cancer-family indication
- thalidomide -> DS Stage II Multiple Myeloma (NCT00098475): procedural, outcome, symptom, stage, or overly broad condition label
- empagliflozin -> CAD - Coronary Artery Disease (NCT07292909): research condition is not an in-scope mapped life-stage/aging MeSH concept
- pregabalin -> Acute Pain (NCT07549490): procedural, outcome, symptom, stage, or overly broad condition label
- tocilizumab -> Multiple Myeloma Refractory (NCT07637578): procedural, outcome, symptom, stage, or overly broad condition label
- atorvastatin -> Independent Living (NCT02099123): procedural, outcome, symptom, stage, or overly broad condition label
- propranolol -> Clinical Stage II Esophageal Adenocarcinoma AJCC v8 (NCT05651594): procedural, outcome, symptom, stage, or overly broad condition label
- mifepristone -> Treatment-resistant PTSD (NCT06689254): research condition is not an in-scope mapped life-stage/aging MeSH concept
- bevacizumab -> Rhabdomyosarcoma (NCT01871766): same broad cancer-family indication
- empagliflozin -> Inflamation (NCT07292909): procedural, outcome, symptom, stage, or overly broad condition label
- finasteride -> Lower Urinary Track Symptoms (NCT06944145): procedural, outcome, symptom, stage, or overly broad condition label
- minoxidil -> androgenetic alopecia (NCT07563036): same-family or near-label expansion (alopecia)
- spironolactone -> Hypertension (HTN) (NCT07223502): research condition is not an in-scope mapped life-stage/aging MeSH concept
- misoprostol -> Postpartum Complication (NCT07353281): procedural, outcome, symptom, stage, or overly broad condition label
- amitriptyline -> Microvesicle Particles (NCT07640061): procedural, outcome, symptom, stage, or overly broad condition label
- bupropion -> Methamphetamine-dependence (NCT06233799): procedural, outcome, symptom, stage, or overly broad condition label
- ketamine -> Cardiac Surgery (NCT05268562): procedural, outcome, symptom, stage, or overly broad condition label
- tocilizumab -> Multiple Myeloma (MM) (NCT07637578): research condition is not an in-scope mapped life-stage/aging MeSH concept
- colchicine -> Cardiovascular Diseases (NCT05633810): already covered by a full DailyMed label audit: DailyMed setid ff06d68f-d65f-d097-e053-6294a90a7e5f https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=ff06d68f-d65f-d097-e053-6294a90a7e5f
- imatinib -> Philadelphia Chromosome Positive Acute Lymphoblastic Leukemia (NCT06061094): research condition is not an in-scope mapped life-stage/aging MeSH concept
- naltrexone -> Methamphetamine Abuse (NCT06233799): procedural, outcome, symptom, stage, or overly broad condition label
- tamoxifen -> Adjuvant Therapy (NCT07101159): procedural, outcome, symptom, stage, or overly broad condition label
- bupropion -> Methamphetamine Abuse (NCT06233799): procedural, outcome, symptom, stage, or overly broad condition label
- anastrozole -> Quality of Life (NCT05472792): procedural, outcome, symptom, stage, or overly broad condition label
- doxycycline -> Chronic Periodontitis (NCT07634341): already has a verified approved-use overlap: DailyMed setid b3cd7b44-db40-4ce5-895e-d4c85a0068ae: doxycycline hyclate is labeled as an adjunct to scaling/root planing for adult periodontitis
- propranolol -> Clinical Stage III Esophageal Adenocarcinoma AJCC v8 (NCT05651594): procedural, outcome, symptom, stage, or overly broad condition label
- thalidomide -> chronic lymphoproliferative disorder of NK-cells (NCT06530576): same broad cancer-family indication
- semaglutide -> Diabetes Mellitus (NCT07621419): same-family or near-label expansion (diabetes)
- finasteride -> Prostate Hyperplasia (NCT04288427): procedural, outcome, symptom, stage, or overly broad condition label
- aspirin -> Stroke (NCT06486792): already covered by a full DailyMed label audit: DailyMed setid 41386de5-5857-efab-e063-6294a90afd9c https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=41386de5-5857-efab-e063-6294a90afd9c
- rituximab -> Interstitial Lung Disease With Systemic Sclerosis (NCT06549231): research condition is not an in-scope mapped life-stage/aging MeSH concept
- tamoxifen -> Hormone Receptor Positive Tumor (NCT02592083): procedural, outcome, symptom, stage, or overly broad condition label
- sildenafil -> traumatic brain injury (NCT05782244): full DailyMed label audit incomplete for this drug; fail-closed until every listed SPL is retrievable
- tocilizumab -> Polyarticular Course Juvenile Idiopathic Arthritis (JIA) (NCT06654882): research condition is not an in-scope mapped life-stage/aging MeSH concept
- finasteride -> BPH (Benign Prostatic Hyperplasia) (NCT06944145): research condition is not an in-scope mapped life-stage/aging MeSH concept
- atorvastatin -> Disability Free Survival (NCT02099123): procedural, outcome, symptom, stage, or overly broad condition label
- minoxidil -> Androgenic Alopecia (NCT07373054): research condition is not an in-scope mapped life-stage/aging MeSH concept
- pregabalin -> Refractory Chronic Cough (NCT07288528): procedural, outcome, symptom, stage, or overly broad condition label
- ruxolitinib -> acute myeloid leukemia (NCT06128070): same broad cancer-family indication
- sirolimus -> breast cancer (NCT06957379): same broad cancer-family indication
- topiramate -> Breastfed Infants of Mothers on Select DOI (NCT03511118): procedural, outcome, symptom, stage, or overly broad condition label
- doxycycline -> Sexually Transmitted Infection (NCT07658976): procedural, outcome, symptom, stage, or overly broad condition label
- thalidomide -> DS Stage I Multiple Myeloma (NCT00098475): procedural, outcome, symptom, stage, or overly broad condition label
- metformin -> Insulin Resistance (NCT02647827): procedural, outcome, symptom, stage, or overly broad condition label
- colchicine -> Advanced Cancer (NCT06813079): procedural, outcome, symptom, stage, or overly broad condition label
- hydroxychloroquine -> Erythematotelangiectatic Rosacea (NCT07343635): research condition is not an in-scope mapped life-stage/aging MeSH concept
- amitriptyline -> Thermal Burn (NCT07640061): research condition is not an in-scope mapped life-stage/aging MeSH concept
- gabapentin -> Pain, Postoperative (NCT07047040): procedural, outcome, symptom, stage, or overly broad condition label
- gabapentin -> HIV (NCT05443555): research condition is not an in-scope mapped life-stage/aging MeSH concept
- thalidomide -> T-cell large granular lymphocyte leukemia (NCT06530576): same broad cancer-family indication
- bevacizumab -> Chronic Subdural Hematoma (NCT06510582): research condition is not an in-scope mapped life-stage/aging MeSH concept
- naltrexone -> Overdose Accidental (NCT06633900): procedural, outcome, symptom, stage, or overly broad condition label
- naltrexone -> Methamphetamine-dependence (NCT06233799): procedural, outcome, symptom, stage, or overly broad condition label
- ruxolitinib -> Precursor Cell Lymphoblastic Leukemia-Lymphoma (NCT06128070): same broad cancer-family indication
- bupropion -> Neuroticism (NCT05273996): research condition is not an in-scope mapped life-stage/aging MeSH concept
- gabapentin -> Osteoarthritis, Knee (NCT07047040): full DailyMed label audit incomplete for this drug; fail-closed until every listed SPL is retrievable
- aspirin -> Ischemic Stroke (NCT06486792): already covered by a full DailyMed label audit: DailyMed setid 41386de5-5857-efab-e063-6294a90afd9c https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=41386de5-5857-efab-e063-6294a90afd9c
- raloxifene -> Lower Urinary Track Symptoms (NCT06944145): procedural, outcome, symptom, stage, or overly broad condition label
- ketamine -> Multiple Sclerosis Fatigue (NCT05378100): research condition is not an in-scope mapped life-stage/aging MeSH concept
- spironolactone -> Alcohol Use Disorder (NCT05807139): research condition is not an in-scope mapped life-stage/aging MeSH concept
- tamoxifen -> Early-Stage Breast Carcinoma (NCT02592083): research condition is not an in-scope mapped life-stage/aging MeSH concept
- propranolol -> Inflammation (NCT06422494): procedural, outcome, symptom, stage, or overly broad condition label
- letrozole -> Adjuvant Therapy (NCT07101159): procedural, outcome, symptom, stage, or overly broad condition label
- mifepristone -> Silent Miscarriage (NCT06733727): procedural, outcome, symptom, stage, or overly broad condition label
- minoxidil -> Androgenic Alopecia (NCT07563036): research condition is not an in-scope mapped life-stage/aging MeSH concept
- raloxifene -> BPH (Benign Prostatic Hyperplasia) (NCT06944145): research condition is not an in-scope mapped life-stage/aging MeSH concept
- topiramate -> Lactating Women on Select DOI (NCT03511118): procedural, outcome, symptom, stage, or overly broad condition label
- rituximab -> Burkitt Lymphoma (NCT05270057): duplicate condition within the same drug/NCT trial; kept more specific condition
- empagliflozin -> congenital heart disease (NCT06955260): below conservative final-score threshold (42 < 44)
- hydroxychloroquine -> breast cancer (NCT03032406): below conservative final-score threshold (40 < 44)
- metformin -> Polycystic Ovary Syndrome (NCT02647827): below conservative final-score threshold (40 < 44)
- amitriptyline -> Inflammatory Bowel Diseases (NCT06261320): below conservative final-score threshold (36 < 44)
- ruxolitinib -> Hidradenitis Suppurativa (NCT07049575): below conservative final-score threshold (34 < 44)
- losartan -> frozen shoulder (NCT07513350): below conservative final-score threshold (32 < 44)
- rituximab -> B-cell non-Hodgkin lymphoma (NCT05270057): below conservative final-score threshold (30 < 44)
- aspirin -> Myocardial Ischemia (NCT05320926): below conservative final-score threshold (28 < 44)
- misoprostol -> fetal growth restriction (NCT05674487): below conservative final-score threshold (28 < 44)
- propranolol -> Diabetes Mellitus, Type 1 (NCT06422494): below conservative final-score threshold (28 < 44)
- sildenafil -> Urinary Incontinence (NCT02983461): below conservative final-score threshold (26 < 44)
- misoprostol -> Postpartum Hemorrhage (NCT07353281): below conservative final-score threshold (24 < 44)
