"""Create the static data bundle consumed by the Disease Web frontend."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "minimal_etl"
OUT = ROOT / "web" / "src" / "data" / "disease-web.json"


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main() -> None:
    nodes = load("nodes.json")
    edges = load("edges.json")
    signals = load("repurposing_signals_gate5.json")
    audit = load("approved_label_overlap_audit_gate5.json")
    node_by_id = {node["id"]: node for node in nodes}
    allowed_types = {"approved_for", "investigational_for", "targets", "associated_with"}
    graph_edges = [edge for edge in edges if edge["type"] in allowed_types]
    path_nodes = [
        node for node in nodes
        if node["kind"] in {"drug", "target"} or node.get("attributes", {}).get("pathfinding_default")
    ]
    payload = {
        "summary": {
            **load("summary.json"),
            "verified_signal_count": signals["summary"]["final_signal_count"],
            "full_label_audit": audit["summary"],
        },
        "nodes": path_nodes,
        "edges": graph_edges,
        "disease_search": load("disease_search_nodes.json"),
        "signals": signals["signals"],
        "signal_summary": signals["summary"],
        "node_lookup": {node_id: node_by_id[node_id] for node_id in {node["id"] for node in path_nodes}},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
