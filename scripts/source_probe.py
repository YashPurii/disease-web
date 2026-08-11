from __future__ import annotations

import gzip
import io
import json
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "source_probe"
REPORT_DIR = ROOT / "reports"


@dataclass
class ProbeResult:
    name: str
    status: str
    source_url: str
    http_status: int | None = None
    sample_file: str | None = None
    findings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_step: str | None = None


def write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path.relative_to(ROOT))


def write_json(path: Path, payload: Any) -> str:
    return write_text(path, json.dumps(payload, indent=2, sort_keys=True))


def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 45,
) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "DiseaseWebSourceProbe/0.1",
            **(headers or {}),
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def safe_text(data: bytes, limit: int = 6000) -> str:
    return data[:limit].decode("utf-8", errors="replace")


def probe_clinicaltrials() -> ProbeResult:
    params = urllib.parse.urlencode(
        {
            "query.intr": "metformin",
            "query.cond": "cancer",
            "pageSize": "3",
            "format": "json",
        }
    )
    url = f"https://clinicaltrials.gov/api/v2/studies?{params}"
    result = ProbeResult(
        name="ClinicalTrials.gov API v2",
        status="go",
        source_url=url,
        next_step=(
            "Use API v2 as the investigational-use backbone, but create drug edges only after "
            "post-filtering named interventions through RxNorm normalization and active trial statuses."
        ),
    )
    status, body, _headers = fetch(url)
    result.http_status = status
    if status != 200:
        result.status = "blocked"
        result.blockers.append(f"Expected HTTP 200, got {status}.")
        result.sample_file = write_text(RAW_DIR / "clinicaltrials_error.txt", safe_text(body))
        return result

    payload = json.loads(body)
    sample_path = RAW_DIR / "clinicaltrials_metformin_cancer_sample.json"
    result.sample_file = write_json(sample_path, payload)
    studies = payload.get("studies", [])
    result.findings.append(f"Returned {len(studies)} sample studies.")
    for study in studies[:3]:
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        arms = protocol.get("armsInterventionsModule", {})
        conditions = protocol.get("conditionsModule", {}).get("conditions", [])
        interventions = [
            item.get("name")
            for item in arms.get("interventions", [])
            if item.get("name")
        ]
        result.findings.append(
            " | ".join(
                [
                    ident.get("nctId", "unknown NCT"),
                    status_module.get("overallStatus", "unknown status"),
                    ", ".join(design.get("phases", []) or ["phase not listed"]),
                    f"conditions={conditions[:3]}",
                    f"interventions={interventions[:3]}",
                ]
            )
        )
    result.findings.append(
        "Important: ClinicalTrials search can still return false positives; ETL must verify the drug is explicitly listed as an intervention."
    )
    return result


def probe_rxnorm_rxclass() -> ProbeResult:
    name = urllib.parse.quote("metformin")
    rxnorm_url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={name}"
    result = ProbeResult(
        name="RxNorm / RxClass APIs",
        status="go",
        source_url=rxnorm_url,
        next_step="Use RxNorm for ingredient canonicalization and RxClass for class/mechanism-style edges where classes are populated.",
    )
    status, body, _headers = fetch(rxnorm_url)
    result.http_status = status
    if status != 200:
        result.status = "blocked"
        result.blockers.append(f"RxNorm rxcui lookup returned HTTP {status}.")
        result.sample_file = write_text(RAW_DIR / "rxnorm_error.txt", safe_text(body))
        return result

    rxnorm_payload = json.loads(body)
    rxcui = (
        rxnorm_payload.get("idGroup", {})
        .get("rxnormId", [None])[0]
    )
    result.findings.append(f"RxNorm ingredient lookup for metformin returned RxCUI={rxcui}.")
    combined: dict[str, Any] = {"rxnorm": rxnorm_payload}
    if rxcui:
        rxclass_url = (
            "https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?"
            + urllib.parse.urlencode({"rxcui": rxcui})
        )
        class_status, class_body, _headers = fetch(rxclass_url)
        combined["rxclass_http_status"] = class_status
        if class_status == 200:
            class_payload = json.loads(class_body)
            combined["rxclass"] = class_payload
            classes = class_payload.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
            result.findings.append(f"RxClass returned {len(classes)} class records for RxCUI={rxcui}.")
            for info in classes[:5]:
                rxclass = info.get("rxclassMinConceptItem", {})
                rela = info.get("rela", "unknown relation")
                source = info.get("relaSource", "unknown source")
                result.findings.append(
                    f"{source}:{rela} -> {rxclass.get('className', 'unknown class')}"
                )
        else:
            result.status = "partial"
            result.blockers.append(f"RxClass lookup returned HTTP {class_status}.")
            combined["rxclass_error"] = safe_text(class_body)
    result.sample_file = write_json(RAW_DIR / "rxnorm_rxclass_metformin_sample.json", combined)
    return result


def probe_dailymed() -> ProbeResult:
    params = urllib.parse.urlencode({"drug_name": "metformin", "pagesize": "3"})
    url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?{params}"
    result = ProbeResult(
        name="DailyMed API",
        status="go",
        source_url=url,
        next_step="Use SPL set IDs to fetch labels and extract indication/mechanism sections with conservative parsing.",
    )
    status, body, _headers = fetch(url)
    result.http_status = status
    if status != 200:
        result.status = "blocked"
        result.blockers.append(f"DailyMed SPL search returned HTTP {status}.")
        result.sample_file = write_text(RAW_DIR / "dailymed_error.txt", safe_text(body))
        return result
    payload = json.loads(body)
    result.sample_file = write_json(RAW_DIR / "dailymed_metformin_spls_sample.json", payload)
    data = payload.get("data", [])
    result.findings.append(f"DailyMed returned {len(data)} SPL records for metformin sample query.")
    for item in data[:3]:
        result.findings.append(
            f"setid={item.get('setid')} | title={item.get('title')} | published={item.get('published_date')}"
        )
    if data and data[0].get("setid"):
        setid = data[0]["setid"]
        label_url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"
        label_status, label_body, _headers = fetch(label_url)
        if label_status == 200:
            write_text(
                RAW_DIR / "dailymed_metformin_label_sample.xml",
                label_body.decode("utf-8", errors="replace")[:250000],
            )
            result.findings.append(f"Fetched one label detail XML for setid={setid}.")
        else:
            result.status = "partial"
            result.blockers.append(f"DailyMed label detail fetch for setid={setid} returned HTTP {label_status}.")
    return result


def probe_orange_book() -> ProbeResult:
    local_dir = ROOT / "data" / "raw" / "orange_book"
    products_path = local_dir / "products.txt"
    patent_path = local_dir / "patent.txt"
    exclusivity_path = local_dir / "exclusivity.txt"
    url = "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files"
    result = ProbeResult(
        name="FDA Orange Book bulk data",
        status="manual",
        source_url=url,
        next_step=(
            "Use the manually downloaded monthly EOBZIP files in data/raw/orange_book for approved product grounding. "
            "Do not attempt to automate FDA AccessData fetches until a supported API, mirror, or challenge-free bulk URL is confirmed."
        ),
    )

    missing = [
        str(path.relative_to(ROOT))
        for path in (products_path, patent_path, exclusivity_path)
        if not path.exists()
    ]
    if missing:
        result.status = "blocked"
        result.blockers.append(f"Missing expected manual Orange Book files: {', '.join(missing)}.")
        return result

    import csv

    result.findings.append(
        "Manual EOBZIP extraction found: products.txt, patent.txt, and exclusivity.txt."
    )
    result.findings.append(
        f"File sizes: products={products_path.stat().st_size:,} bytes, "
        f"patent={patent_path.stat().st_size:,} bytes, exclusivity={exclusivity_path.stat().st_size:,} bytes."
    )

    sample_rows: list[dict[str, str]] = []
    product_count = 0
    with products_path.open("r", encoding="latin-1", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="~")
        result.findings.append(f"Products.txt columns: {reader.fieldnames}.")
        for row in reader:
            product_count += 1
            if len(sample_rows) < 8:
                sample_rows.append(
                    {
                        "Ingredient": row.get("Ingredient", ""),
                        "Trade_Name": row.get("Trade_Name", ""),
                        "Appl_Type": row.get("Appl_Type", ""),
                        "Appl_No": row.get("Appl_No", ""),
                    }
                )
    result.findings.append(f"Products.txt parsed {product_count:,} product rows.")
    result.sample_file = write_json(RAW_DIR / "orange_book_products_sample.json", sample_rows)
    for row in sample_rows[:5]:
        result.findings.append(
            f"{row['Ingredient']} | {row['Trade_Name']} | {row['Appl_Type']} | {row['Appl_No']}"
        )

    result.blockers.append(
        "Known limitation: automated FDA bulk/search fetches hit bot/challenge protection in this environment. Treat Orange Book refresh as a manual monthly download step."
    )
    return result

def probe_mesh() -> ProbeResult:
    lookup_url = (
        "https://id.nlm.nih.gov/mesh/lookup/descriptor?"
        + urllib.parse.urlencode({"label": "Diabetes Mellitus", "match": "exact", "limit": "5"})
    )
    result = ProbeResult(
        name="MeSH descriptor lookup and XML download",
        status="go",
        source_url=lookup_url,
        next_step="Use MeSH XML/RDF for disease and pharmacologic-action categories; do not use retired ASCII files.",
    )
    status, body, _headers = fetch(lookup_url)
    result.http_status = status
    if status != 200:
        result.status = "partial"
        result.blockers.append(f"MeSH descriptor lookup returned HTTP {status}.")
        result.sample_file = write_text(RAW_DIR / "mesh_lookup_error.txt", safe_text(body))
    else:
        payload = json.loads(body)
        result.sample_file = write_json(RAW_DIR / "mesh_diabetes_lookup_sample.json", payload)
        result.findings.append(f"Descriptor lookup returned {len(payload)} records.")
        for item in payload[:3]:
            result.findings.append(f"{item.get('resource')} | {item.get('label')}")

    xml_url = "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.xml"
    head_status, _head_body, headers = fetch(xml_url, method="HEAD")
    result.findings.append(
        f"2026 descriptor XML HEAD status={head_status}, size={headers.get('Content-Length', 'unknown')} bytes."
    )
    if head_status >= 400:
        result.status = "partial"
        result.blockers.append(f"MeSH 2026 XML HEAD request returned HTTP {head_status}.")
    return result


def probe_open_targets() -> ProbeResult:
    url = "https://api.platform.opentargets.org/api/v4/graphql"
    query = """
    query TargetProbe($ensemblId: String!) {
      target(ensemblId: $ensemblId) {
        id
        approvedSymbol
        approvedName
        associatedDiseases(page: { index: 0, size: 3 }) {
          rows {
            score
            disease {
              id
              name
            }
          }
        }
      }
    }
    """
    body = json.dumps({"query": query, "variables": {"ensemblId": "ENSG00000146648"}}).encode("utf-8")
    result = ProbeResult(
        name="Open Targets Platform GraphQL",
        status="go",
        source_url=url,
        next_step="Use bounded GraphQL queries for demo-scale target/disease/drug enrichment; use downloads later if broad coverage becomes necessary.",
    )
    status, response_body, _headers = fetch(
        url,
        method="POST",
        headers={"Content-Type": "application/json"},
        data=body,
    )
    result.http_status = status
    if status != 200:
        result.status = "blocked"
        result.blockers.append(f"GraphQL endpoint returned HTTP {status}.")
        result.sample_file = write_text(RAW_DIR / "open_targets_error.txt", safe_text(response_body))
        return result
    payload = json.loads(response_body)
    result.sample_file = write_json(RAW_DIR / "open_targets_egfr_sample.json", payload)
    target = payload.get("data", {}).get("target")
    if not target:
        result.status = "partial"
        result.blockers.append("GraphQL response did not include target data for EGFR.")
        return result
    result.findings.append(
        f"Target {target.get('approvedSymbol')} ({target.get('id')}) returned associated disease rows."
    )
    rows = target.get("associatedDiseases", {}).get("rows", [])
    for row in rows:
        disease = row.get("disease", {})
        result.findings.append(f"{disease.get('name')} | score={row.get('score')}")
    return result


def probe_disgenet() -> ProbeResult:
    url = "https://www.disgenet.com/"
    result = ProbeResult(
        name="DisGeNET static downloads",
        status="risk",
        source_url=url,
        next_step="Keep out of the core build unless a direct permitted non-commercial download is confirmed by the user.",
    )
    status, body, _headers = fetch(url)
    result.http_status = status
    result.sample_file = write_text(RAW_DIR / "disgenet_homepage_head.txt", safe_text(body, limit=3000))
    if status == 200:
        result.findings.append("DisGeNET homepage is reachable.")
    else:
        result.blockers.append(f"DisGeNET homepage returned HTTP {status}.")
    result.blockers.append(
        "Direct static file access/licensing was not proven by this probe; treating as non-core until access is confirmed."
    )
    return result


def render_report(results: list[ProbeResult]) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Disease Web Source Probe",
        "",
        f"Generated: {generated}",
        "",
        "This checkpoint verifies live access and records real sample outputs before any graph or UI work.",
        "",
        "## Summary",
        "",
        "| Source | Status | HTTP | Sample |",
        "| --- | --- | ---: | --- |",
    ]
    for result in results:
        sample = result.sample_file or ""
        lines.append(f"| {result.name} | {result.status} | {result.http_status or ''} | `{sample}` |")

    for result in results:
        lines.extend(["", f"## {result.name}", "", f"URL: {result.source_url}", "", f"Status: **{result.status}**"])
        if result.sample_file:
            lines.append(f"Sample file: `{result.sample_file}`")
        if result.findings:
            lines.extend(["", "Findings:"])
            lines.extend([f"- {finding}" for finding in result.findings])
        if result.blockers:
            lines.extend(["", "Risks / blockers:"])
            lines.extend([f"- {blocker}" for blocker in result.blockers])
        if result.next_step:
            lines.extend(["", f"Next step: {result.next_step}"])

    lines.extend(
        [
            "",
            "## Checkpoint Decision",
            "",
            "Orange Book is usable for this build via the manually downloaded monthly EOBZIP files in data/raw/orange_book.",
            "",
            "Known limitation: Orange Book refresh is a manual pipeline step for now because automated FDA fetches hit bot/challenge protection. Do not include DisGeNET in the core pipeline yet.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    probes = [
        probe_clinicaltrials,
        probe_rxnorm_rxclass,
        probe_dailymed,
        probe_orange_book,
        probe_mesh,
        probe_open_targets,
        probe_disgenet,
    ]
    results: list[ProbeResult] = []
    for probe in probes:
        try:
            results.append(probe())
        except Exception as exc:  # noqa: BLE001 - report generation should survive one bad source.
            results.append(
                ProbeResult(
                    name=probe.__name__.replace("probe_", "").replace("_", " ").title(),
                    status="blocked",
                    source_url="",
                    blockers=[f"Probe crashed: {type(exc).__name__}: {exc}"],
                )
            )

    report = render_report(results)
    report_path = REPORT_DIR / "source_probe.md"
    write_text(report_path, report)
    print(report_path)
    print()
    print(
        textwrap.dedent(
            """
            Source probe complete. Inspect reports/source_probe.md and the files in
            data/raw/source_probe/ before approving the next checkpoint.
            """
        ).strip()
    )


if __name__ == "__main__":
    main()
