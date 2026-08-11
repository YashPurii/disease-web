"""Gate 5: conservative, cited repurposing-signal extraction.

The scorer ranks screening signals, not biological validity or clinical promise.
Every emitted row retains one approved-use edge and one active ClinicalTrials.gov
edge.  Ranking = phase (0-40) + status (0-12) + recency (0-12).  Later trial
phases score higher; Recruiting is stronger than Active, not recruiting, which
is stronger than Not yet recruiting; recently updated records score higher.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed" / "minimal_etl"
RAW_DIR = ROOT / "data" / "raw" / "minimal_etl"
REPORT_DIR = ROOT / "reports"
OVERLAP_AUDIT_PATH = DATA_DIR / "approved_label_overlap_audit_gate5.json"
OVERLAP_AUDIT_LEDGER_PATH = DATA_DIR / "approved_label_overlap_ledger_gate5.json"
ACTIVE_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"}
TODAY = date(2026, 7, 16)
MIN_DISEASE_SIGNAL_SCORE = 44
MIN_MAPPED_RESEARCH_SIGNAL_SCORE = 25

# These labels describe procedures, trial stages, endpoints, symptoms, or broad
# descriptors rather than an investigational disease/condition suitable for this slice.
NON_INDICATION_PATTERNS = (
    "adjuvant therapy", "quality of life", "independent living", "disability free survival",
    "microvesicle", "clinical stage", "lower urinary", "prostate hyperplasia", "bph (",
    "hormone receptor positive", "early-stage breast", "breastfed", "lactating",
    "cardiac surgery", "postoperative", "heavy drinking", "overdose", "inflammation",
    "inflamation", "pelvic pain", "insulin resistance", "advanced cancer",
    "multiple myeloma refractory", "multiple myeloma (mm)", "ds stage",
    "methamphetamine", "sexually transmitted infection", "refractory chronic cough",
    "acute pain", "pain,", "silent miscarriage", "postpartum complication",
    "diagnostic", "surgical procedures", "induction of anesthesia",
)

# Canonical condition families known to be label expansions in the present 36-drug
# data slice.  A candidate is rejected if it and any approved use hit the same family.
FAMILY_TERMS = {
    "alopecia": ("alopecia", "hair regrowth", "hair loss"),
    "breast_cancer": ("breast cancer", "breast carcinoma", "ductal breast", "hormone receptor positive tumor"),
    "multiple_myeloma": ("multiple myeloma",),
    "prostate_hyperplasia": ("prostatic hyperplasia", "prostate hyperplasia", "benign prostatic", "bph"),
    "diabetes": ("diabetes", "diabete", "insulin resistance"),
    "stroke": ("stroke",),
    "hypertension": ("hypertension", "htn"),
    "obesity": ("obesity", "overweight"),
}
CANCER_TERMS = ("cancer", "carcinoma", "adenocarcinoma", "sarcoma", "leukemia", "lymphoma", "myeloma", "myelofibrosis", "lymphoproliferative", "neoplasm", "tumor")
DRUG_LABEL_ALIASES = {"sirolimus": {"rapamycin"}}
AUDIT_CONDITION_ALIASES = {"ischemic stroke": "stroke", "stroke": "stroke"}

# Verification-found approved overlap outside the original eight-SPL cache.
# Keep it here until the next full ETL run refreshes the widened DailyMed query.
VERIFIED_APPROVED_OVERLAPS = {
    ("doxycycline", "chronic periodontitis"): "DailyMed setid b3cd7b44-db40-4ce5-895e-d4c85a0068ae: doxycycline hyclate is labeled as an adjunct to scaling/root planing for adult periodontitis",
}

# DailyMed/Orange Book do not designate one primary indication for these labels.
# The output keeps the selected normalized edge but makes the ambiguity visible.
APPROVED_ANCHOR_AUDITS = {
    "aspirin": {
        "primary_designation_available": False,
        "note": "DailyMed OTC labels provide co-equal pain-reliever/fever-reducer purposes and minor-ache uses; Fever is a normalized component, not a primary indication.",
        "available_indications": "pain relief; fever reduction; minor aches and pains (headache, muscle pain, toothache, menstrual pain, arthritis/cold-related pain)",
    },
    "doxycycline": {
        "primary_designation_available": False,
        "note": "DailyMed labels list multiple co-equal antimicrobial and prophylactic indications; Malaria was a deterministic seed-term match, not a primary indication.",
        "available_indications": "rickettsial, sexually transmitted, respiratory, bacterial, ophthalmic, anthrax, penicillin-alternative, amebiasis/acne, malaria-prophylaxis, and adult periodontitis adjunctive treatment",
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def label_key(label: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in label).split())


def families(label: str) -> set[str]:
    normalized = label_key(label)
    return {family for family, terms in FAMILY_TERMS.items() if any(term in normalized for term in terms)}


def trial_dates() -> dict[str, date]:
    """Read last-posted dates from the locally retained CT.gov responses."""
    found: dict[str, date] = {}
    for path in RAW_DIR.glob("ctgov_intr_*.json"):
        for study in load_json(path).get("studies", []):
            protocol = study.get("protocolSection", {})
            nct_id = protocol.get("identificationModule", {}).get("nctId")
            status = protocol.get("statusModule", {})
            value = (
                status.get("lastUpdatePostDateStruct", {}).get("date")
                or status.get("lastUpdateSubmitDate")
                or status.get("studyFirstPostDateStruct", {}).get("date")
            )
            if nct_id and value:
                found[nct_id] = datetime.strptime(value[:10], "%Y-%m-%d").date()
    return found


def trial_arm_metadata(drug_labels: set[str]) -> dict[str, dict[str, dict[str, Any]]]:
    """Classify drug exposure per arm; study-level co-mentions are insufficient."""
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for path in RAW_DIR.glob("ctgov_intr_*.json"):
        for study in load_json(path).get("studies", []):
            protocol = study.get("protocolSection", {})
            nct_id = protocol.get("identificationModule", {}).get("nctId")
            module = protocol.get("armsInterventionsModule", {})
            interventions = [item for item in module.get("interventions", []) if item.get("type") == "DRUG"]
            if not nct_id or not interventions:
                continue
            by_arm: dict[str, set[str]] = defaultdict(set)
            names_by_drug: dict[str, list[str]] = defaultdict(list)
            explicit_combinations: set[str] = set()
            for item in interventions:
                name = item.get("name", "")
                normalized_name = label_key(name)
                components = {
                    label for label in drug_labels
                    if label in normalized_name or any(alias in normalized_name for alias in DRUG_LABEL_ALIASES.get(label, set()))
                }
                for component in components:
                    names_by_drug[component].append(name)
                if len(components) > 1:
                    explicit_combinations.update(components)
                for arm_label in item.get("armGroupLabels", []):
                    by_arm[arm_label].update(components)
            combination_by_arm = set().union(*(components for components in by_arm.values() if len(components) > 1)) if by_arm else set()
            combinations = explicit_combinations | combination_by_arm
            all_components = set(names_by_drug)
            result[nct_id] = {
                drug: {
                    "trial_arm_type": "combination" if drug in combinations else "single_drug",
                    "combination_partner_drugs": sorted(
                        next((components for components in by_arm.values() if drug in components and len(components) > 1), set())
                        or ({component for component in all_components if component in explicit_combinations} if drug in explicit_combinations else set())
                    ) if drug in combinations else [],
                    "trial_intervention_names": names_by_drug[drug],
                }
                for drug in all_components
            }
    return result


def approved_overlap_reason(drug_label: str, condition_label: str) -> str | None:
    """Fail closed on a completed full-label audit before emitting a signal."""
    normalized_condition = AUDIT_CONDITION_ALIASES.get(label_key(condition_label), label_key(condition_label))
    audit_path = OVERLAP_AUDIT_LEDGER_PATH if OVERLAP_AUDIT_LEDGER_PATH.exists() else OVERLAP_AUDIT_PATH
    if audit_path.exists():
        audit = load_json(audit_path)
        audit_rows = audit.get("checks", {})
        audit_rows = audit_rows.values() if isinstance(audit_rows, dict) else audit_rows
        for row in audit_rows:
            if label_key(row.get("drug", "")) != label_key(drug_label):
                continue
            audited_condition = AUDIT_CONDITION_ALIASES.get(
                label_key(row.get("investigational_use", "")), label_key(row.get("investigational_use", ""))
            )
            if audited_condition != normalized_condition:
                continue
            if row.get("overlap_found"):
                first = (row.get("matches") or [{}])[0]
                return f"already covered by a full DailyMed label audit: DailyMed setid {first.get('setid')} {first.get('url')}"
            if row.get("fetch_failures"):
                return "full DailyMed label audit incomplete for this drug; fail-closed until every listed SPL is retrievable"
    evidence = VERIFIED_APPROVED_OVERLAPS.get((label_key(drug_label), label_key(condition_label)))
    if evidence:
        return f"already has a verified approved-use overlap: {evidence}"
    return None


def anchor_audit(drug_label: str) -> dict[str, Any]:
    return APPROVED_ANCHOR_AUDITS.get(label_key(drug_label), {
        "primary_designation_available": None,
        "note": "No special anchor-selection limitation recorded for this drug.",
        "available_indications": None,
    })


def phase_points(phases: list[str]) -> int:
    phase_set = set(phases)
    if "PHASE4" in phase_set:
        return 40
    if "PHASE2" in phase_set and "PHASE3" in phase_set:
        return 35
    if "PHASE3" in phase_set:
        return 30
    if "PHASE2" in phase_set:
        return 20
    if "PHASE1" in phase_set and "PHASE2" in phase_set:
        return 15
    if "PHASE1" in phase_set:
        return 10
    if "EARLY_PHASE1" in phase_set:
        return 5
    if "NA" in phase_set:
        return 8
    return 0


def status_points(status: str | None) -> int:
    return {"RECRUITING": 12, "ACTIVE_NOT_RECRUITING": 8, "NOT_YET_RECRUITING": 4}.get(status, 0)


def recency_points(updated: date | None) -> int:
    if not updated:
        return 0
    age_days = (TODAY - updated).days
    if age_days <= 365:
        return 12
    if age_days <= 3 * 365:
        return 8
    if age_days <= 6 * 365:
        return 4
    return 1


def citation_text(edge: dict[str, Any]) -> str:
    citation = edge["citation"]
    if citation.get("setid"):
        orange = citation.get("orange_book") or {}
        orange_text = f"; Orange Book {orange.get('appl_type', '')} {orange.get('appl_no', '')}".rstrip()
        return f"DailyMed setid {citation['setid']}{orange_text}"
    return citation.get("source", "citation present")


def node_category(node: dict[str, Any]) -> str:
    return node.get("attributes", {}).get("node_category", "unmapped")


def is_mapped_research_condition(node: dict[str, Any]) -> bool:
    mesh = node.get("attributes", {}).get("mesh") or {}
    tree_numbers = mesh.get("tree_numbers") or []
    # In this small slice, only MeSH life-stage/aging concepts are retained as
    # non-disease investigational conditions. This keeps Aging visible without
    # promoting traits, endpoints, or ambiguous labels to clinical indications.
    return (
        node_category(node) == "research_condition"
        and bool(mesh.get("mapped") and mesh.get("mesh_id"))
        and any(tree.startswith("G07") for tree in tree_numbers)
    )


def reject_reason(approved_nodes: list[dict[str, Any]], investigational_node: dict[str, Any]) -> str | None:
    trial_label = investigational_node["label"]
    trial_key = label_key(trial_label)
    if any(pattern in trial_key for pattern in NON_INDICATION_PATTERNS):
        return "procedural, outcome, symptom, stage, or overly broad condition label"
    if node_category(investigational_node) == "research_condition" and not is_mapped_research_condition(investigational_node):
        return "research condition is not an in-scope mapped life-stage/aging MeSH concept"
    trial_families = families(trial_label)
    approved_families = set().union(*(families(node["label"]) for node in approved_nodes))
    if trial_families & approved_families:
        return f"same-family or near-label expansion ({', '.join(sorted(trial_families & approved_families))})"
    approved_keys = {label_key(node["label"]) for node in approved_nodes}
    if trial_key in approved_keys:
        return "duplicate normalized condition label"
    if any(term in trial_key for term in CANCER_TERMS) and any(
        any(term in label_key(node["label"]) for term in CANCER_TERMS) for node in approved_nodes
    ):
        return "same broad cancer-family indication"
    return None


def choose_approved_edge(edges: list[dict[str, Any]], nodes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    # Prefer a disease-labelled approved use, then a stable edge id for repeatable output.
    return sorted(edges, key=lambda edge: (node_category(nodes[edge["target_id"]]) != "disease", edge["id"]))[0]


def main() -> None:
    nodes = load_json(DATA_DIR / "nodes.json")
    edges = load_json(DATA_DIR / "edges.json")
    node_by_id = {node["id"]: node for node in nodes}
    dates = trial_dates()
    arm_metadata = trial_arm_metadata({label_key(node["label"]) for node in nodes if node["kind"] == "drug"})
    approved_by_drug: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        if edge["type"] == "approved_for" and edge.get("citation", {}).get("setid"):
            approved_by_drug[edge["source_id"]].append(edge)

    raw_pairs: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for trial_edge in edges:
        if trial_edge["type"] != "investigational_for":
            continue
        approved = approved_by_drug.get(trial_edge["source_id"], [])
        if approved and trial_edge["target_id"] not in {edge["target_id"] for edge in approved}:
            raw_pairs.append((trial_edge, approved))

    removals: list[dict[str, str]] = []
    eligible: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for trial_edge, approved in raw_pairs:
        trial_node = node_by_id[trial_edge["target_id"]]
        drug_label = node_by_id[trial_edge["source_id"]]["label"]
        reason = approved_overlap_reason(drug_label, trial_node["label"]) or reject_reason([node_by_id[edge["target_id"]] for edge in approved], trial_node)
        row = {
            "drug": drug_label,
            "investigational": trial_node["label"],
            "nct_id": trial_edge["citation"]["nct_id"],
        }
        if reason:
            row["reason"] = reason
            removals.append(row)
        else:
            eligible.append((trial_edge, approved))

    active_with_phase: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for trial_edge, approved in eligible:
        attrs = trial_edge.get("attributes", {})
        if attrs.get("status") not in ACTIVE_STATUSES:
            removals.append({"drug": node_by_id[trial_edge["source_id"]]["label"], "investigational": node_by_id[trial_edge["target_id"]]["label"], "nct_id": trial_edge["citation"]["nct_id"], "reason": "trial is not active"})
        elif not attrs.get("phases"):
            removals.append({"drug": node_by_id[trial_edge["source_id"]]["label"], "investigational": node_by_id[trial_edge["target_id"]]["label"], "nct_id": trial_edge["citation"]["nct_id"], "reason": "trial has no recorded phase"})
        else:
            active_with_phase.append((trial_edge, approved))

    # One trial can expose several aliases/subconditions. Keep one result per drug/NCT,
    # preferring a disease node and then the more specific (longer) label.
    best_by_drug_nct: dict[tuple[str, str], tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for trial_edge, approved in active_with_phase:
        key = (trial_edge["source_id"], trial_edge["citation"]["nct_id"])
        current = best_by_drug_nct.get(key)
        if current is None:
            best_by_drug_nct[key] = (trial_edge, approved)
            continue
        candidate_node = node_by_id[trial_edge["target_id"]]
        current_node = node_by_id[current[0]["target_id"]]
        candidate_key = (node_category(candidate_node) != "disease", -len(candidate_node["label"]), candidate_node["label"])
        current_key = (node_category(current_node) != "disease", -len(current_node["label"]), current_node["label"])
        if candidate_key < current_key:
            removals.append({"drug": node_by_id[current[0]["source_id"]]["label"], "investigational": current_node["label"], "nct_id": current[0]["citation"]["nct_id"], "reason": "duplicate condition within the same drug/NCT trial; kept more specific condition"})
            best_by_drug_nct[key] = (trial_edge, approved)
        else:
            removals.append({"drug": node_by_id[trial_edge["source_id"]]["label"], "investigational": candidate_node["label"], "nct_id": trial_edge["citation"]["nct_id"], "reason": "duplicate condition within the same drug/NCT trial; kept more specific condition"})

    signals = []
    for trial_edge, approved_edges in best_by_drug_nct.values():
        approved_edge = choose_approved_edge(approved_edges, node_by_id)
        trial_node = node_by_id[trial_edge["target_id"]]
        approved_node = node_by_id[approved_edge["target_id"]]
        attrs = trial_edge["attributes"]
        updated = dates.get(trial_edge["citation"]["nct_id"])
        score = phase_points(attrs.get("phases", [])) + status_points(attrs.get("status")) + recency_points(updated)
        drug_label = node_by_id[trial_edge["source_id"]]["label"]
        arm = arm_metadata.get(trial_edge["citation"]["nct_id"], {}).get(
            label_key(drug_label),
            {"trial_arm_type": "unknown", "combination_partner_drugs": [], "trial_intervention_names": []},
        )
        anchor = anchor_audit(drug_label)
        signals.append({
            "drug": drug_label,
            "approved_use": approved_node["label"],
            "approved_use_category": node_category(approved_node),
            "approved_evidence": citation_text(approved_edge),
            "approved_url": approved_edge["citation"].get("url"),
            "approved_anchor_primary_designation_available": anchor["primary_designation_available"],
            "approved_anchor_note": anchor["note"],
            "available_approved_indications": anchor["available_indications"],
            "investigational_use": trial_node["label"],
            "investigational_use_category": node_category(trial_node),
            "investigational_evidence": "ClinicalTrials.gov API v2",
            "nct_id": trial_edge["citation"]["nct_id"],
            "trial_url": trial_edge["citation"].get("url"),
            "trial_phase": attrs.get("phases", []),
            "trial_status": attrs.get("status"),
            "trial_arm_type": arm["trial_arm_type"],
            "combination_partner_drugs": arm["combination_partner_drugs"],
            "trial_intervention_names": arm["trial_intervention_names"],
            "last_update_date": updated.isoformat() if updated else None,
            "ranking_score": score,
            "score_breakdown": {"phase": phase_points(attrs.get("phases", [])), "status": status_points(attrs.get("status")), "recency": recency_points(updated)},
        })
    signals.sort(key=lambda row: (-row["ranking_score"], row["drug"], row["nct_id"]))
    score_eligible = []
    for row in signals:
        is_research = row["investigational_use_category"] == "research_condition"
        threshold = MIN_MAPPED_RESEARCH_SIGNAL_SCORE if is_research else MIN_DISEASE_SIGNAL_SCORE
        if row["ranking_score"] >= threshold:
            score_eligible.append(row)
        else:
            removals.append({
                "drug": row["drug"],
                "investigational": row["investigational_use"],
                "nct_id": row["nct_id"],
                "reason": f"below conservative final-score threshold ({row['ranking_score']} < {threshold})",
            })
    signals = score_eligible

    concentration = Counter(row["drug"] for row in signals)
    top_four = sum(count for _, count in concentration.most_common(4))
    summary = {
        "raw_different_condition_pairs": len(raw_pairs),
        "after_meaningful_difference_filter": len(eligible),
        "after_active_status_and_phase": len(active_with_phase),
        "after_duplicate_trial_condition_collapse": len(best_by_drug_nct),
        "final_signal_count": len(signals),
        "distinct_drugs": len(concentration),
        "top_four_signal_count": top_four,
        "top_four_share": top_four / len(signals) if signals else 0,
    }
    out_json = DATA_DIR / "repurposing_signals_gate5.json"
    out_json.write_text(json.dumps({"summary": summary, "signals": signals, "removals": removals}, indent=2) + "\n", encoding="utf-8")

    lines = ["# Gate 5 Repurposing Signals Funnel", "", "## Ranking", "", "Score = trial phase (0-40) + active status (0-12) + ClinicalTrials.gov last-update recency (0-12). This is a screening priority score, not evidence of efficacy, safety, or commercial value.", "", "- Phase: Phase 4=40; Phase 2/3=35; Phase 3=30; Phase 2=20; Phase 1/2=15; Phase 1=10; N/A=8; Early Phase 1=5.", "- Status: Recruiting=12; Active, not recruiting=8; Not yet recruiting=4.", "- Recency: updated <=1 year=12; <=3 years=8; <=6 years=4; older=1; unavailable=0.", "", "## Two-Tier Threshold Policy", "", "Disease signals require a score of at least 44. Mapped research_condition signals require 25 because aging/life-stage trials are expected to be sparse and an Early Phase 1 study should not automatically conceal a conceptually important screened signal such as sirolimus -> Aging.", "", "The categories are not on equal evidentiary footing: a research_condition result is explicitly labeled, has a lower inclusion threshold, and must never be compared as though it had disease-level evidence. This wording is required in the Gate 8/README narrative.", "", "## Anchor Audit", "", "- Aspirin: no primary indication is distinguished in the retained OTC labels. Available purposes are pain relief, fever reduction, and minor aches/pains; Fever is not presented as a primary indication.", "- Doxycycline: no primary indication is distinguished. Available labels cover rickettsial, sexually transmitted, respiratory, bacterial, ophthalmic, anthrax, penicillin-alternative, amebiasis/acne, malaria-prophylaxis, and adult periodontitis adjunctive treatment. The original eight-SPL retrieval was incomplete; the widened future ETL query will cover up to 100 results.", "- Verified correction: doxycycline -> Chronic Periodontitis was removed because DailyMed setid b3cd7b44-db40-4ce5-895e-d4c85a0068ae already labels doxycycline hyclate for adult periodontitis adjunctive treatment.", "", "## Trial Arm Verification", "", "- NCT07634341 has one active-comparator arm containing a local chitosan nanoparticle formulation loaded with both doxycycline and atorvastatin, after scaling/root planing. It is a combination-therapy trial, not two independent single-drug arms. Remaining signals retain `trial_arm_type=combination` plus both partner drugs so the evidence cannot be read as independent support.", "", "## Funnel", "", f"- Raw different-condition pairs: {summary['raw_different_condition_pairs']}", f"- After indication-difference filter: {summary['after_meaningful_difference_filter']}", f"- After active-status and phase requirement: {summary['after_active_status_and_phase']}", f"- After per-drug/NCT duplicate collapse: {summary['after_duplicate_trial_condition_collapse']}", f"- Final signals after conservative score threshold: {summary['final_signal_count']}", f"- Distinct drugs represented: {summary['distinct_drugs']}", f"- Top four drugs account for {summary['top_four_signal_count']}/{len(signals)} signals ({summary['top_four_share']:.0%})." + (" Concentration warning: four drugs account for more than half." if summary['top_four_share'] > 0.5 else " No four-drug majority."), "", "## Removed Pairs", ""]
    for row in removals:
        lines.append(f"- {row['drug']} -> {row['investigational']} ({row['nct_id']}): {row['reason']}")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "repurposing_funnel_gate5.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    signal_lines = ["# Gate 5 Ranked Repurposing Signals", "", "Every row joins one DailyMed/Orange Book approved-use edge to one active ClinicalTrials.gov edge. `research_condition` is intentionally not presented as a disease.", ""]
    for index, row in enumerate(signals, 1):
        phase = ", ".join(row["trial_phase"])
        signal_lines.extend([f"## {index}. {row['drug']} | score {row['ranking_score']}", "", f"- Approved use: {row['approved_use']} [{row['approved_use_category']}]", f"- Approved evidence: {row['approved_evidence']} | {row['approved_url']}", f"- Investigational use: {row['investigational_use']} [{row['investigational_use_category']}]", f"- Trial: {row['nct_id']} | {phase} | {row['trial_status']} | arm type {row['trial_arm_type']} | last update {row['last_update_date'] or 'unavailable'}", f"- Combination partners: {', '.join(row['combination_partner_drugs']) or 'none'}", f"- Approved-anchor note: {row['approved_anchor_note']}", f"- Trial evidence: {row['investigational_evidence']} | {row['trial_url']}", f"- Score breakdown: phase {row['score_breakdown']['phase']} + status {row['score_breakdown']['status']} + recency {row['score_breakdown']['recency']}", ""])
    (REPORT_DIR / "repurposing_signals_gate5.md").write_text("\n".join(signal_lines), encoding="utf-8")
    (REPORT_DIR / "gate8_readme_notes.md").write_text("# Gate 8 / README Required Note\n\nResearch-condition signals use a lower inclusion threshold (25) than disease signals (44). This deliberately retains sparse but conceptually important aging/life-stage screening evidence such as sirolimus -> Aging. The categories are not on equal evidentiary footing and must be visibly labeled and described as such in the README and UI.\n", encoding="utf-8")
    print(out_json)
    print(REPORT_DIR / "repurposing_funnel_gate5.md")
    print(REPORT_DIR / "repurposing_signals_gate5.md")


if __name__ == "__main__":
    main()

