from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed" / "minimal_etl"
REPORT_DIR = ROOT / "reports"

ALLOWED_EDGE_TYPES = {"approved_for", "investigational_for", "targets", "associated_with"}
ALLOWED_INTERMEDIATE_KINDS = {"drug", "target"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def citation_id(edge: dict[str, Any]) -> str:
    citation = edge.get("citation") or {}
    if citation.get("nct_id"):
        return citation["nct_id"]
    if citation.get("setid"):
        orange = citation.get("orange_book") or {}
        orange_label = ""
        if orange.get("appl_no"):
            orange_label = f"; Orange Book {orange.get('appl_type', '').strip()} {orange.get('appl_no')}"
        return f"DailyMed setid {citation['setid']}{orange_label}"
    if citation.get("chembl_id"):
        refs = citation.get("references") or []
        if refs:
            first = refs[0]
            ids = first.get("ids") or []
            if ids:
                return f"Open Targets {citation['chembl_id']}; {first.get('source')} {', '.join(ids[:2])}"
        return f"Open Targets {citation['chembl_id']}"
    if citation.get("target_id") and citation.get("disease_id"):
        return f"Open Targets {citation['target_id']} / {citation['disease_id']}"
    if citation.get("class_id"):
        return f"RxClass {citation['class_id']}"
    return citation.get("source", "citation present")


def citation_url(edge: dict[str, Any]) -> str | None:
    citation = edge.get("citation") or {}
    return citation.get("url")


def node_allowed(node: dict[str, Any]) -> bool:
    attrs = node.get("attributes", {})
    return node["kind"] in ALLOWED_INTERMEDIATE_KINDS or bool(attrs.get("pathfinding_default"))


def build_graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> tuple[nx.Graph, dict[str, dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
    node_by_id = {node["id"]: node for node in nodes}
    allowed_nodes = {node["id"] for node in nodes if node_allowed(node)}
    graph = nx.Graph()
    for node_id in allowed_nodes:
        graph.add_node(node_id)

    edge_lookup: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        if edge["type"] not in ALLOWED_EDGE_TYPES:
            continue
        source_id = edge["source_id"]
        target_id = edge["target_id"]
        if source_id not in allowed_nodes or target_id not in allowed_nodes:
            continue
        graph.add_edge(source_id, target_id)
        edge_lookup[tuple(sorted((source_id, target_id)))].append(edge)
    return graph, node_by_id, edge_lookup


def resolve_disease(label_or_id: str, nodes: list[dict[str, Any]]) -> str:
    exact_id = [node for node in nodes if node["id"] == label_or_id]
    if exact_id:
        node = exact_id[0]
        if not node.get("attributes", {}).get("pathfinding_default"):
            raise ValueError(f"Node is not pathfinding_default=true: {label_or_id}")
        return node["id"]

    matches = [
        node for node in nodes
        if node["label"].lower() == label_or_id.lower()
        and node.get("attributes", {}).get("pathfinding_default")
    ]
    if not matches:
        raise ValueError(f"No pathfinding_default disease node found for {label_or_id!r}")
    if len(matches) > 1:
        # Prefer MeSH for exact user labels when both MeSH and MONDO aliases exist; otherwise stable by id.
        matches.sort(key=lambda node: (0 if node["id"].startswith("disease:mesh:") else 1, node["id"]))
    return matches[0]["id"]


def format_node(node_id: str, node_by_id: dict[str, dict[str, Any]]) -> str:
    node = node_by_id[node_id]
    attrs = node.get("attributes", {})
    parts = [node["label"], node["kind"], node_id]
    if node["kind"] == "disease":
        parts.append(f"pathfinding_default={attrs.get('pathfinding_default')}")
    return " | ".join(str(part) for part in parts)


def path_edges(path: list[str], edge_lookup: dict[tuple[str, str], list[dict[str, Any]]]) -> list[list[dict[str, Any]]]:
    rows = []
    for source_id, target_id in zip(path, path[1:]):
        rows.append(sorted(edge_lookup[tuple(sorted((source_id, target_id)))], key=lambda edge: (edge["type"], citation_id(edge), edge["id"])))
    return rows


def find_paths(graph: nx.Graph, source_id: str, target_id: str, max_paths: int = 5) -> tuple[int | None, int, list[list[str]]]:
    if source_id not in graph or target_id not in graph:
        return None, 0, []
    try:
        distance = nx.shortest_path_length(graph, source_id, target_id)
    except nx.NetworkXNoPath:
        return None, 0, []
    all_paths = list(nx.all_shortest_paths(graph, source_id, target_id))
    return distance, len(all_paths), all_paths[:max_paths]


def run_pair(name: str, source_label: str, target_label: str, graph: nx.Graph, nodes: list[dict[str, Any]], node_by_id: dict[str, dict[str, Any]], edge_lookup: dict[tuple[str, str], list[dict[str, Any]]]) -> list[str]:
    source_id = resolve_disease(source_label, nodes)
    target_id = resolve_disease(target_label, nodes)
    distance, total_shortest_paths, paths = find_paths(graph, source_id, target_id)
    lines = [f"## {name}", "", f"Query: `{source_label}` -> `{target_label}`", "", "Resolved endpoints:", f"- Source: {format_node(source_id, node_by_id)}", f"- Target: {format_node(target_id, node_by_id)}", ""]
    if distance is None:
        lines.extend([
            "Result: no path found in the filtered Gate 4 graph.",
            "",
            "Filter used: disease nodes must have `pathfinding_default=true`; raw/research-condition nodes are excluded, while drug and target nodes are allowed as intermediates.",
            "",
        ])
        return lines

    lines.extend([
        f"Shortest distance: {distance} edges",
        f"Distinct shortest paths in this filtered graph: {total_shortest_paths}",
        f"Distinct shortest paths shown: {len(paths)}",
        "",
    ])
    for index, path in enumerate(paths, start=1):
        lines.extend([f"### Path {index}", "", "Nodes:"])
        for step, node_id in enumerate(path, start=1):
            lines.append(f"{step}. {format_node(node_id, node_by_id)}")
        lines.extend(["", "Edges:"])
        for step, edge_group in enumerate(path_edges(path, edge_lookup), start=1):
            source_id = path[step - 1]
            target_id = path[step]
            lines.append(f"{step}. {node_by_id[source_id]['label']} -> {node_by_id[target_id]['label']}")
            for edge in edge_group:
                url = citation_url(edge)
                url_label = f" | {url}" if url else ""
                lines.append(
                    f"   - edge_id={edge['id']} | type={edge['type']} | source={edge['source']} | citation_id={citation_id(edge)}{url_label}"
                )
        lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate 4 path-finding slice over the real Disease Web graph.")
    parser.add_argument("--max-paths", type=int, default=5)
    args = parser.parse_args()

    nodes = load_json(DATA_DIR / "nodes.json")
    edges = load_json(DATA_DIR / "edges.json")
    graph, node_by_id, edge_lookup = build_graph(nodes, edges)

    pairs = [
        ("Well-connected cancer pair", "cervical cancer", "renal cell carcinoma"),
        ("Plausible less-obvious chronic disease pair", "Diabetes Mellitus, Type 2", "Hypertension"),
        ("Unsure / honest thin case", "breast cancer", "cervical cancer"),
    ]

    lines = [
        "# Gate 4 Path-Finding Slice",
        "",
        "Graph filter: edge types are `approved_for`, `investigational_for`, `targets`, and `associated_with`. Disease nodes are included only when `pathfinding_default=true`; drug and target nodes are allowed as intermediates. Mechanism/class edges are excluded for this slice.",
        "",
        f"Filtered graph nodes: {graph.number_of_nodes()}",
        f"Filtered graph edges: {graph.number_of_edges()}",
        "",
        "## Coverage And Interpretation",
        "",
        "This is a deliberately small, 36-drug seed slice. Most disease pairs do not connect at this coverage level; that is the expected and honest result, not a defect to conceal by loosening the filter.",
        "",
        "The path search enumerates every shortest path in this filtered graph before displaying up to the requested limit. Therefore a reported count of one means there is exactly one shortest path in the current graph, not merely one selected example.",
        "",
        "This dataset cannot support a general claim that any two diseases connect in three steps. The results directly contradict that framing: breast cancer and cervical cancer have no eligible evidence path here, while Type 2 Diabetes to Hypertension requires four edges.",
        "",
        "For breast cancer and cervical cancer specifically, the full evidence-edge graph (all 380 nodes, before the disease-node default filter) still has no path using approved/investigational, drug-target, or gene-disease evidence edges. Cervical cancer currently has one such edge, to bevacizumab; breast cancer has 13, but shares no drug, target, or gene with cervical cancer in this dataset. That indicates sparse current coverage for cervical cancer, not a conclusion that the diseases lack a real biological relationship.",
        "",
        "If mechanism/class edges are added back, two four-edge class-mediated routes appear through the broad RxClass node `ANTINEOPLASTIC,OTHER` (via letrozole or anastrozole and bevacizumab). They are intentionally excluded from this slice: a broad class label is not the same as a directly evidenced shared drug, target, or gene connection.",
        "",
    ]
    for name, source, target in pairs:
        lines.extend(run_pair(name, source, target, graph, nodes, node_by_id, edge_lookup))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / "pathfinding_gate4.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
