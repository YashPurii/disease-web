from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed" / "minimal_etl"
REPORT_DIR = ROOT / "reports"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def node_type(node: dict[str, Any]) -> str:
    if node["kind"] == "research_condition":
        return "research_condition"
    if node["kind"] == "disease":
        category = node.get("attributes", {}).get("node_category")
        return "research_condition" if category == "research_condition" else "disease"
    if node["kind"] == "target":
        return "gene/target"
    return node["kind"]


def citation_label(edge: dict[str, Any]) -> str:
    c = edge.get("citation", {})
    if c.get("nct_id"):
        return f"ClinicalTrials.gov {c['nct_id']}"
    if c.get("setid"):
        ob = c.get("orange_book", {})
        ob_label = f"; Orange Book {ob.get('appl_type', '')} {ob.get('appl_no', '')}" if ob else ""
        return f"DailyMed setid {c['setid']}{ob_label}"
    if c.get("target_id") and c.get("disease_id"):
        return f"Open Targets {c['target_id']} / {c['disease_id']}"
    if c.get("chembl_id"):
        refs = c.get("references") or []
        ref_label = ""
        if refs:
            ref = refs[0]
            ids = ref.get("ids") or []
            ref_label = f"; {ref.get('source')} {', '.join(ids[:2])}" if ids else f"; {ref.get('source')}"
        return f"Open Targets {c['chembl_id']}{ref_label}"
    if c.get("class_id"):
        return f"RxClass {c['class_id']}"
    return c.get("source", "citation present")


def main() -> None:
    nodes = load_json(DATA_DIR / "nodes.json")
    edges = load_json(DATA_DIR / "edges.json")
    summary_path = DATA_DIR / "summary.json"
    summary = load_json(summary_path) if summary_path.exists() else {}
    search_nodes_path = DATA_DIR / "disease_search_nodes.json"
    search_nodes = load_json(search_nodes_path) if search_nodes_path.exists() else []
    label = {node["id"]: node["label"] for node in nodes}

    counts_by_type = Counter(node_type(node) for node in nodes)
    counts_by_type_and_source = defaultdict(Counter)
    for node in nodes:
        counts_by_type_and_source[node_type(node)][node.get("attributes", {}).get("source", "unknown")] += 1

    requested_edge_types = {"approved_for", "investigational_for", "targets", "associated_with"}
    edge_counts_by_type = Counter(edge["type"] for edge in edges if edge["type"] in requested_edge_types)
    edge_counts_by_source = Counter(edge["source"] for edge in edges if edge["type"] in requested_edge_types)
    all_edge_counts_by_type = Counter(edge["type"] for edge in edges)
    all_edge_counts_by_source = Counter(edge["source"] for edge in edges)

    condition_nodes = [node for node in nodes if node_type(node) in {"disease", "research_condition"}]
    unresolved_conditions = []
    phenotype_conditions = []
    resolved_conditions = []
    for node in condition_nodes:
        attrs = node.get("attributes", {})
        mesh = attrs.get("mesh") or {}
        mondo = attrs.get("mondo") or {}
        if mesh.get("mesh_id") or mondo.get("mondo_id"):
            resolved_conditions.append(node)
        elif attrs.get("phenotype_id"):
            phenotype_conditions.append(node)
        else:
            unresolved_conditions.append(node)

    drug_nodes = [node for node in nodes if node["kind"] == "drug"]
    unresolved_drugs = [node for node in drug_nodes if not node.get("attributes", {}).get("rxcui")]

    disease_ids = {node["id"] for node in nodes if node_type(node) == "disease"}
    disease_connectivity = defaultdict(lambda: {"edge_count": 0, "drugs": set(), "targets": set(), "edge_types": Counter()})
    for edge in edges:
        endpoints = [edge["source_id"], edge["target_id"]]
        disease_endpoint = next((item for item in endpoints if item in disease_ids), None)
        if not disease_endpoint:
            continue
        other = edge["target_id"] if disease_endpoint == edge["source_id"] else edge["source_id"]
        bucket = disease_connectivity[disease_endpoint]
        bucket["edge_count"] += 1
        bucket["edge_types"][edge["type"]] += 1
        if other.startswith("drug:"):
            bucket["drugs"].add(other)
        if other.startswith("target:"):
            bucket["targets"].add(other)

    ranked = []
    for disease_id, bucket in disease_connectivity.items():
        ranked.append({
            "id": disease_id,
            "label": label[disease_id],
            "edge_count": bucket["edge_count"],
            "drug_count": len(bucket["drugs"]),
            "target_count": len(bucket["targets"]),
            "edge_types": dict(bucket["edge_types"]),
        })
    ranked.sort(key=lambda row: (row["edge_count"], row["drug_count"], row["target_count"], row["label"]), reverse=True)
    rich = [row for row in ranked if row["edge_count"] >= 2 or row["drug_count"] >= 1][:12]
    sparse = sorted([row for row in ranked if row["edge_count"] <= 1 and row["drug_count"] == 0], key=lambda row: row["label"])[:12]

    cited_edges = [edge for edge in edges if edge.get("citation")]
    rng = random.Random(20260710)
    sampled_edges = rng.sample(cited_edges, min(15, len(cited_edges)))
    sampled_edges.sort(key=lambda edge: (edge["type"], edge["source"], edge["id"]))

    hp_nodes = [node for node in nodes if (node.get("attributes", {}).get("phenotype_id") or "").startswith("HP_")]

    report = [
        "# Gate 3 Data Quality Report",
        "",
        "Dataset: current minimal real graph slice generated by `scripts/minimal_etl.py`.",
        "",
        "## Node Counts",
        "",
        "| Node type | Count |",
        "| --- | ---: |",
    ]
    for key in ["disease", "research_condition", "drug", "gene/target", "mechanism"]:
        if counts_by_type.get(key, 0):
            report.append(f"| {key} | {counts_by_type[key]} |")
    report.extend(["", "### Nodes By Type And Source", "", "| Node type | Source | Count |", "| --- | --- | ---: |"])
    for ntype in sorted(counts_by_type_and_source):
        for source, count in sorted(counts_by_type_and_source[ntype].items()):
            report.append(f"| {ntype} | {source} | {count} |")

    report.extend(["", "## Edge Counts", "", "Requested core edge types:", "", "| Edge type | Count |", "| --- | ---: |"])
    for key in ["approved_for", "investigational_for", "targets", "associated_with"]:
        report.append(f"| {key} | {edge_counts_by_type.get(key, 0)} |")
    report.extend(["", "Core edges by source:", "", "| Source | Count |", "| --- | ---: |"])
    for source, count in sorted(edge_counts_by_source.items()):
        report.append(f"| {source} | {count} |")
    report.extend(["", "All emitted edge types, including mechanism/class edges:", "", f"`{json.dumps(dict(all_edge_counts_by_type), sort_keys=True)}`", "", f"All emitted sources: `{json.dumps(dict(all_edge_counts_by_source), sort_keys=True)}`"])

    total_conditions = len(condition_nodes)
    report.extend([
        "",
        "## Resolution Quality",
        "",
        f"- Condition/research-condition nodes: {total_conditions}",
        f"- MeSH/MONDO-resolved condition nodes: {len(resolved_conditions)} ({len(resolved_conditions) / total_conditions:.1%})",
        f"- Phenotype-authority condition nodes kept as research_condition: {len(phenotype_conditions)} ({len(phenotype_conditions) / total_conditions:.1%})",
        f"- Unmapped raw condition nodes: {len(unresolved_conditions)} ({len(unresolved_conditions) / total_conditions:.1%})",
        f"- Drug nodes with RxNorm RxCUI: {len(drug_nodes) - len(unresolved_drugs)} / {len(drug_nodes)}",
    ])
    if phenotype_conditions:
        report.extend(["", "Phenotype-authority examples:"])
        for node in phenotype_conditions:
            attrs = node.get("attributes", {})
            report.append(f"- {node['label']} -> {attrs.get('phenotype_id')} ({attrs.get('node_category')})")
    if unresolved_conditions:
        report.extend(["", "Unmapped raw condition examples:"])
        for node in unresolved_conditions[:20]:
            attrs = node.get("attributes", {})
            report.append(f"- {node['label']} | source={attrs.get('source')} | original={attrs.get('original_label')}")
    if unresolved_drugs:
        report.extend(["", "Unresolved drug examples:"])
        for node in unresolved_drugs:
            report.append(f"- {node['label']}")

    report.extend([
        "",
        "## Disease Search / Path-Finding Default Filter",
        "",
        f"- Default disease search nodes exported: {len(search_nodes)}",
        f"- Excluded condition/research-condition nodes from default disease search/path-finding: {summary.get('excluded_from_disease_search_count', 'unknown')}",
        "- Inclusion rule: `kind == disease`, `node_category == disease`, and resolved to a MeSH or MONDO ID.",
        "- Raw/unmapped conditions and research_condition nodes stay in the graph, but are not in the default disease autocomplete/path-finding set.",
        "",
        "Sample default disease search nodes:",
    ])
    for row in search_nodes[:10]:
        authority_id = row.get("mesh_id") or row.get("mondo_id")
        report.append(f"- {row['label']} | {row['id']} | {authority_id}")

    report.extend(["", "## HP Spot Check", ""])
    if hp_nodes:
        for node in hp_nodes:
            attrs = node.get("attributes", {})
            linked = [edge for edge in edges if edge["source_id"] == node["id"] or edge["target_id"] == node["id"]]
            report.append(f"- Node: `{node['id']}` | label={node['label']} | category={attrs.get('node_category')} | phenotype_id={attrs.get('phenotype_id')}")
            for edge in linked[:3]:
                report.append(f"  Edge: {label.get(edge['source_id'], edge['source_id'])} -> {label.get(edge['target_id'], edge['target_id'])} | {edge['type']} | {citation_label(edge)} | confidence={edge.get('confidence')}")
    else:
        report.append("- No HP_* node emitted.")

    report.extend(["", "## Rich Vs Sparse Disease Coverage", "", "Rich/stronger nodes in this slice:", "", "| Disease | Edges | Connected drugs | Connected targets | Edge types |", "| --- | ---: | ---: | ---: | --- |"])
    for row in rich:
        report.append(f"| {row['label']} | {row['edge_count']} | {row['drug_count']} | {row['target_count']} | `{json.dumps(row['edge_types'], sort_keys=True)}` |")
    report.extend(["", "Sparse disease nodes in this slice:", "", "| Disease | Edges | Connected drugs | Connected targets |", "| --- | ---: | ---: | ---: |"])
    for row in sparse:
        report.append(f"| {row['label']} | {row['edge_count']} | {row['drug_count']} | {row['target_count']} |")

    report.extend(["", "## Deterministic Cited Edge Sample", "", "Sample method: `random.Random(20260710).sample(all_cited_edges, 15)`, then sorted for readability. Not hand-picked.", "", "| Type | From | To | Source | Citation |", "| --- | --- | --- | --- | --- |"])
    for edge in sampled_edges:
        report.append(f"| {edge['type']} | {label.get(edge['source_id'], edge['source_id'])} | {label.get(edge['target_id'], edge['target_id'])} | {edge['source']} | {citation_label(edge)} |")

    report.extend([
        "",
        "## Known Source Limitations",
        "",
        "- FDA Orange Book products.txt is useful for approved product/application grounding, but it is not a clean indication database.",
        "- OTC-style approved-use edges, especially aspirin and minoxidil, use DailyMed OTC label `Uses`/`Purpose` text as the indication citation; Orange Book is attached only when a matching product/application row exists.",
        "- Biologics such as rituximab, bevacizumab, and tocilizumab may lack Orange Book rows because Orange Book is CDER small-molecule/product focused; DailyMed/Open Targets evidence is still retained where available.",
    ])

    report.extend(["", "## Coverage Assessment", ""])
    if counts_by_type.get("drug", 0) < 20:
        report.append("Coverage is intentionally sparse: this slice has only 5 drug nodes, so it is enough for ETL QA but too small to judge whether cross-disease path-finding will be broadly interesting.")
        report.append("Do not treat this as demo coverage yet. The full Gate 3/full ETL pass needs a wider drug seed list before path-finding or UI work is worth starting.")
    else:
        report.append("Coverage looks broad enough for a path-finding slice, pending manual review of the sampled edges above.")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / "data_quality_gate3.md"
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()