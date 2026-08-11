# Gate 6 Known-Example Validation

This is a pipeline-behavior check, not clinical validation. A passing exclusion is as valuable as a passing selected signal: it shows the extractor resists labeling known/near-label uses as repurposing.
Validation result: 10/10 expected outcomes passed.


## 1. PASS | metformin -> Endometriosis (NCT06611501)

Expected: `keep`. Cross-area disease signal should survive.
Result: selected | score 44 | PHASE2 | RECRUITING | arm=single_drug
Approved: Diabetes Mellitus, Type 2 | DailyMed setid 25be863d-490c-47f6-9ad3-c828dc43fbf0; Orange Book A 211309
Trial: https://clinicaltrials.gov/study/NCT06611501

## 2. PASS | sirolimus -> Aging (NCT06658093)

Expected: `keep`. Mapped research-condition signal should survive with visible label.
Result: selected | score 29 | EARLY_PHASE1 | RECRUITING | arm=single_drug
Approved: neoplasm with perivascular epithelioid cell differentiation | DailyMed setid 0f9bb784-53e2-46f9-a65d-1c6c2a230eaf; Orange Book N 213478
Trial: https://clinicaltrials.gov/study/NCT06658093

## 3. PASS | baricitinib -> traumatic brain injury (NCT06065046)

Expected: `keep`. Active Phase 2 cross-area disease signal should survive.
Result: selected | score 44 | PHASE2 | RECRUITING | arm=single_drug
Approved: COVID-19 | DailyMed setid 866e9f35-9035-4581-a4b1-75a621ab55cf; Orange Book N 207924
Trial: https://clinicaltrials.gov/study/NCT06065046

## 4. PASS | colchicine -> pancreatic ductal adenocarcinoma (NCT06813079)

Expected: `keep`. Gout-to-pancreatic-cancer signal should survive.
Result: selected | score 44 | PHASE2 | RECRUITING | arm=single_drug
Approved: Gout | DailyMed setid 72984aa2-6df9-4460-9926-399ffed30e36; Orange Book N 204820
Trial: https://clinicaltrials.gov/study/NCT06813079

## 5. PASS | atorvastatin -> Chronic Periodontitis (NCT07634341)

Expected: `keep_combination`. May survive only if explicitly labeled combination therapy.
Result: selected | score 56 | PHASE4 | NOT_YET_RECRUITING | arm=combination
Approved: coronary artery disorder | DailyMed setid 303989c9-823e-4bcb-a7b3-7024fd0d3a38; Orange Book N 213260
Trial: https://clinicaltrials.gov/study/NCT07634341

## 6. PASS | aspirin -> Stroke (NCT06486792)

Expected: `exclude`. Must be rejected because full labels cover recurrent-stroke prevention.
Result: excluded | already covered by a full DailyMed label audit: DailyMed setid 41386de5-5857-efab-e063-6294a90afd9c https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=41386de5-5857-efab-e063-6294a90afd9c

## 7. PASS | doxycycline -> Chronic Periodontitis (NCT07634341)

Expected: `exclude`. Must be rejected because a DailyMed label covers adult periodontitis.
Result: excluded | already has a verified approved-use overlap: DailyMed setid b3cd7b44-db40-4ce5-895e-d4c85a0068ae: doxycycline hyclate is labeled as an adjunct to scaling/root planing for adult periodontitis

## 8. PASS | colchicine -> Cardiovascular Diseases (NCT05633810)

Expected: `exclude`. Must be rejected because LODOCO covers cardiovascular-event risk reduction.
Result: excluded | already covered by a full DailyMed label audit: DailyMed setid ff06d68f-d65f-d097-e053-6294a90a7e5f https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=ff06d68f-d65f-d097-e053-6294a90a7e5f

## 9. PASS | minoxidil -> androgenetic alopecia (NCT07563036)

Expected: `exclude`. Must be rejected as a same-family label expansion.
Result: excluded | same-family or near-label expansion (alopecia)

## 10. PASS | sildenafil -> traumatic brain injury (NCT05782244)

Expected: `exclude`. Must fail closed while listed DailyMed labels are unretrievable.
Result: excluded | full DailyMed label audit incomplete for this drug; fail-closed until every listed SPL is retrievable
