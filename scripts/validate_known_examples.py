"""Gate 6 validation against expected repurposing keeps and exclusions."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "minimal_etl" / "repurposing_signals_gate5.json"
REPORT = ROOT / "reports" / "validation_gate6.md"

CASES = [
    ("metformin", "Endometriosis", "NCT06611501", "keep", "Cross-area disease signal should survive."),
    ("sirolimus", "Aging", "NCT06658093", "keep", "Mapped research-condition signal should survive with visible label."),
    ("baricitinib", "traumatic brain injury", "NCT06065046", "keep", "Active Phase 2 cross-area disease signal should survive."),
    ("colchicine", "pancreatic ductal adenocarcinoma", "NCT06813079", "keep", "Gout-to-pancreatic-cancer signal should survive."),
    ("atorvastatin", "Chronic Periodontitis", "NCT07634341", "keep_combination", "May survive only if explicitly labeled combination therapy."),
    ("aspirin", "Stroke", "NCT06486792", "exclude", "Must be rejected because full labels cover recurrent-stroke prevention."),
    ("doxycycline", "Chronic Periodontitis", "NCT07634341", "exclude", "Must be rejected because a DailyMed label covers adult periodontitis."),
    ("colchicine", "Cardiovascular Diseases", "NCT05633810", "exclude", "Must be rejected because LODOCO covers cardiovascular-event risk reduction."),
    ("minoxidil", "androgenetic alopecia", "NCT07563036", "exclude", "Must be rejected as a same-family label expansion."),
    ("sildenafil", "traumatic brain injury", "NCT05782244", "exclude", "Must fail closed while listed DailyMed labels are unretrievable."),
]


def norm(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    signals = data["signals"]
    removals = data["removals"]
    rows = []
    for drug, condition, nct_id, expected, rationale in CASES:
        selected = next((row for row in signals if row["drug"] == drug and row["nct_id"] == nct_id and norm(row["investigational_use"]) == norm(condition)), None)
        removed = next((row for row in removals if row["drug"] == drug and row["nct_id"] == nct_id and norm(row["investigational"]) == norm(condition)), None)
        if expected == "keep":
            passed = selected is not None
        elif expected == "keep_combination":
            passed = selected is not None and selected.get("trial_arm_type") == "combination"
        else:
            passed = selected is None and removed is not None
        rows.append({"drug": drug, "condition": condition, "nct_id": nct_id, "expected": expected, "passed": passed, "rationale": rationale, "selected": selected, "removed": removed})

    lines = ["# Gate 6 Known-Example Validation", "", "This is a pipeline-behavior check, not clinical validation. A passing exclusion is as valuable as a passing selected signal: it shows the extractor resists labeling known/near-label uses as repurposing.", ""]
    for index, row in enumerate(rows, 1):
        status = "PASS" if row["passed"] else "FAIL"
        lines.extend([f"## {index}. {status} | {row['drug']} -> {row['condition']} ({row['nct_id']})", "", f"Expected: `{row['expected']}`. {row['rationale']}"])
        if row["selected"]:
            signal = row["selected"]
            lines.extend([f"Result: selected | score {signal['ranking_score']} | {', '.join(signal['trial_phase'])} | {signal['trial_status']} | arm={signal['trial_arm_type']}", f"Approved: {signal['approved_use']} | {signal['approved_evidence']}", f"Trial: {signal['trial_url']}"])
        elif row["removed"]:
            lines.append(f"Result: excluded | {row['removed']['reason']}")
        else:
            lines.append("Result: no matching extractor record found.")
        lines.append("")
    passed = sum(row["passed"] for row in rows)
    lines[3:3] = [f"Validation result: {passed}/{len(rows)} expected outcomes passed.", ""]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(REPORT)
    print(f"{passed}/{len(rows)}")


if __name__ == "__main__":
    main()
