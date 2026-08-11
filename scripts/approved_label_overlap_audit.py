"""Audit final repurposing signals against complete DailyMed label inventories."""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed" / "minimal_etl"
RAW_DIR = ROOT / "data" / "raw" / "full_label_overlap"
REPORT_DIR = ROOT / "reports"
LEDGER_PATH = DATA_DIR / "approved_label_overlap_ledger_gate5.json"
sys.path.insert(0, str(ROOT / "scripts"))
from minimal_etl import extract_indication_sections  # noqa: E402

# Controlled phrase sets make the audit conservative: a match means an indication
# section explicitly mentions the queried investigational condition/family.
CONDITION_TERMS = {
    "ischemic stroke": (r"ischemic stroke", r"\bstroke\b"),
    "coronary artery disease": (r"coronary artery disease", r"coronary heart disease"),
    "tinnitus": (r"\btinnitus\b",),
    "chronic periodontitis": (r"\bperiodontitis\b",),
    "cough": (r"\bcough\b",),
    "cardiovascular diseases": (r"cardiovascular disease", r"cardiovascular risk"),
    "osteoarthritis knee": (r"osteoarthritis",),
    "hiv infectious disease": (r"\bhiv\b", r"human immunodeficiency"),
    "traumatic brain injury": (r"traumatic brain injury",),
    "pancreatic ductal adenocarcinoma": (r"pancreatic (ductal )?(adenocarcinoma|cancer)",),
    "endometriosis": (r"\bendometriosis\b",),
    "aging": (r"\baging\b", r"\bageing\b"),
}


def key(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def fetch_json(url: str, path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.load(response)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def fetch_xml(setid: str, path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"
    with urllib.request.urlopen(url, timeout=60) as response:
        text = response.read().decode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def all_spls(drug: str) -> list[dict[str, Any]]:
    page = 1
    rows = []
    while True:
        url = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?" + urllib.parse.urlencode({"drug_name": drug, "pagesize": "100", "page": str(page)})
        payload = fetch_json(url, RAW_DIR / key(drug) / f"spls_page_{page}.json")
        rows.extend(payload.get("data", []))
        metadata = payload.get("metadata", {})
        if page >= int(metadata.get("total_pages", 1)):
            return rows
        page += 1


def inspect_label(drug: str, condition: str, item: dict[str, Any]) -> dict[str, Any] | None:
    setid = item.get("setid")
    if not setid:
        return None
    xml = fetch_xml(setid, RAW_DIR / key(drug) / "labels" / f"{setid}.xml")
    patterns = [re.compile(pattern, re.I) for pattern in CONDITION_TERMS[condition]]
    hits = []
    for section in extract_indication_sections(xml):
        text = section["text"]
        if any(pattern.search(text) for pattern in patterns):
            hits.append({"section": section["title"], "text": text[:800]})
    if not hits:
        return None
    return {
        "setid": setid,
        "title": item.get("title"),
        "published_date": item.get("published_date"),
        "url": f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={setid}",
        "matches": hits,
    }


def main() -> None:
    source = json.loads((DATA_DIR / "repurposing_signals_gate5.json").read_text(encoding="utf-8"))
    checks = {}
    for signal in source["signals"]:
        drug = signal["drug"]
        condition = key(signal["investigational_use"])
        checks[(drug, condition)] = signal

    audit_rows = []
    for (drug, condition), signal in sorted(checks.items()):
        if condition not in CONDITION_TERMS:
            raise ValueError(f"No controlled overlap matcher configured for {condition}")
        items = all_spls(drug)
        matches = []
        failures = []
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = {executor.submit(inspect_label, drug, condition, item): item.get("setid") for item in items}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        matches.append(result)
                except Exception as exc:  # pragma: no cover - reported as audit failure.
                    failures.append(f"{futures[future]}: {exc}")
        audit_rows.append({
            "drug": drug,
            "investigational_use": signal["investigational_use"],
            "nct_id": signal["nct_id"],
            "label_records_scanned": len(items),
            "overlap_found": bool(matches),
            "matches": sorted(matches, key=lambda row: row["setid"]),
            "fetch_failures": failures,
        })
        print(f"{drug} -> {signal['investigational_use']}: {len(items)} labels, {len(matches)} overlaps, {len(failures)} failures", flush=True)

    failures = [row for row in audit_rows if row["fetch_failures"]]
    overlaps = [row for row in audit_rows if row["overlap_found"]]
    result = {
        "scope": "All DailyMed SPL records returned by drug_name across every API page; only indication/purpose sections were searched.",
        "checks": audit_rows,
        "summary": {"signals_checked": len(audit_rows), "overlaps_found": len(overlaps), "fetch_failure_checks": len(failures)},
    }
    out = DATA_DIR / "approved_label_overlap_audit_gate5.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    ledger = load_json(LEDGER_PATH) if LEDGER_PATH.exists() else {"scope": result["scope"], "checks": {}}
    for row in audit_rows:
        ledger["checks"][f"{key(row['drug'])}::{key(row['investigational_use'])}"] = row
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Gate 5 Full Approved-Label Overlap Audit", "", result["scope"], "", f"Signals checked: {len(audit_rows)}", f"Confirmed approved-label overlaps: {len(overlaps)}", f"Checks with fetch failures: {len(failures)}", ""]
    for row in audit_rows:
        status = "OVERLAP" if row["overlap_found"] else "clean"
        lines.append(f"- {row['drug']} -> {row['investigational_use']} ({row['nct_id']}): {status}; {row['label_records_scanned']} SPLs scanned")
        for match in row["matches"]:
            lines.append(f"  - DailyMed setid {match['setid']} | {match['url']}")
        for failure in row["fetch_failures"]:
            lines.append(f"  - fetch failure: {failure}")
    (REPORT_DIR / "approved_label_overlap_audit_gate5.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
