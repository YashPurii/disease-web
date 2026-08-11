# Gate 4 Path-Finding Slice

Graph filter: edge types are `approved_for`, `investigational_for`, `targets`, and `associated_with`. Disease nodes are included only when `pathfinding_default=true`; drug and target nodes are allowed as intermediates. Mechanism/class edges are excluded for this slice.

Filtered graph nodes: 190
Filtered graph edges: 184

## Coverage And Interpretation

This is a deliberately small, 36-drug seed slice. Most disease pairs do not connect at this coverage level; that is the expected and honest result, not a defect to conceal by loosening the filter.

The path search enumerates every shortest path in this filtered graph before displaying up to the requested limit. Therefore a reported count of one means there is exactly one shortest path in the current graph, not merely one selected example.

This dataset cannot support a general claim that any two diseases connect in three steps. The results directly contradict that framing: breast cancer and cervical cancer have no eligible evidence path here, while Type 2 Diabetes to Hypertension requires four edges.

For breast cancer and cervical cancer specifically, the full evidence-edge graph (all 380 nodes, before the disease-node default filter) still has no path using approved/investigational, drug-target, or gene-disease evidence edges. Cervical cancer currently has one such edge, to bevacizumab; breast cancer has 13, but shares no drug, target, or gene with cervical cancer in this dataset. That indicates sparse current coverage for cervical cancer, not a conclusion that the diseases lack a real biological relationship.

If mechanism/class edges are added back, two four-edge class-mediated routes appear through the broad RxClass node `ANTINEOPLASTIC,OTHER` (via letrozole or anastrozole and bevacizumab). They are intentionally excluded from this slice: a broad class label is not the same as a directly evidenced shared drug, target, or gene connection.

## Well-connected cancer pair

Query: `cervical cancer` -> `renal cell carcinoma`

Resolved endpoints:
- Source: cervical cancer | disease | disease:mondo:MONDO_0002974 | pathfinding_default=True
- Target: renal cell carcinoma | disease | disease:mondo:MONDO_0005086 | pathfinding_default=True

Shortest distance: 2 edges
Distinct shortest paths in this filtered graph: 1
Distinct shortest paths shown: 1

### Path 1

Nodes:
1. cervical cancer | disease | disease:mondo:MONDO_0002974 | pathfinding_default=True
2. bevacizumab | drug | drug:rxnorm:253337
3. renal cell carcinoma | disease | disease:mondo:MONDO_0005086 | pathfinding_default=True

Edges:
1. cervical cancer -> bevacizumab
   - edge_id=edge:56359d1e7a1663d8 | type=approved_for | source=DailyMed + FDA Orange Book | citation_id=DailyMed setid 939b5d1f-9fb2-4499-80ef-0607aa6b114e | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=939b5d1f-9fb2-4499-80ef-0607aa6b114e
2. bevacizumab -> renal cell carcinoma
   - edge_id=edge:2ed430d7b88cd909 | type=approved_for | source=DailyMed + FDA Orange Book | citation_id=DailyMed setid 939b5d1f-9fb2-4499-80ef-0607aa6b114e | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=939b5d1f-9fb2-4499-80ef-0607aa6b114e

## Plausible less-obvious chronic disease pair

Query: `Diabetes Mellitus, Type 2` -> `Hypertension`

Resolved endpoints:
- Source: Diabetes Mellitus, Type 2 | disease | disease:mesh:D003924 | pathfinding_default=True
- Target: Hypertension | disease | disease:mesh:D006973 | pathfinding_default=True

Shortest distance: 4 edges
Distinct shortest paths in this filtered graph: 1
Distinct shortest paths shown: 1

### Path 1

Nodes:
1. Diabetes Mellitus, Type 2 | disease | disease:mesh:D003924 | pathfinding_default=True
2. empagliflozin | drug | drug:rxnorm:1545653
3. Heart Failure | disease | disease:mesh:D006333 | pathfinding_default=True
4. spironolactone | drug | drug:rxnorm:9997
5. Hypertension | disease | disease:mesh:D006973 | pathfinding_default=True

Edges:
1. Diabetes Mellitus, Type 2 -> empagliflozin
   - edge_id=edge:7da66ca3300cdcd3 | type=approved_for | source=DailyMed + FDA Orange Book | citation_id=DailyMed setid 334f1b3d-5670-6685-e063-6294a90a7e47; Orange Book N 204629 | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=334f1b3d-5670-6685-e063-6294a90a7e47
2. empagliflozin -> Heart Failure
   - edge_id=edge:1059690b37890823 | type=approved_for | source=DailyMed + FDA Orange Book | citation_id=DailyMed setid 334f1b3d-5670-6685-e063-6294a90a7e47; Orange Book N 204629 | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=334f1b3d-5670-6685-e063-6294a90a7e47
3. Heart Failure -> spironolactone
   - edge_id=edge:556d880210641c2d | type=approved_for | source=DailyMed + FDA Orange Book | citation_id=DailyMed setid e61269b2-823a-49e8-b55f-ef0b8b1dbcde; Orange Book N 209478 | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=e61269b2-823a-49e8-b55f-ef0b8b1dbcde
4. spironolactone -> Hypertension
   - edge_id=edge:848c0f519996312c | type=approved_for | source=DailyMed + FDA Orange Book | citation_id=DailyMed setid e61269b2-823a-49e8-b55f-ef0b8b1dbcde; Orange Book N 209478 | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=e61269b2-823a-49e8-b55f-ef0b8b1dbcde

## Unsure / honest thin case

Query: `breast cancer` -> `cervical cancer`

Resolved endpoints:
- Source: breast cancer | disease | disease:mondo:MONDO_0007254 | pathfinding_default=True
- Target: cervical cancer | disease | disease:mondo:MONDO_0002974 | pathfinding_default=True

Result: no path found in the filtered Gate 4 graph.

Filter used: disease nodes must have `pathfinding_default=true`; raw/research-condition nodes are excluded, while drug and target nodes are allowed as intermediates.
