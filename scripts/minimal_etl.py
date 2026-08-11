from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.parse
import urllib.request
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "minimal_etl"
OUT_DIR = ROOT / "data" / "processed" / "minimal_etl"
REPORT_DIR = ROOT / "reports"
ORANGE_BOOK_DIR = ROOT / "data" / "raw" / "orange_book"

ACTIVE_STATUSES = {
    "RECRUITING",
    "ACTIVE_NOT_RECRUITING",
    "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
}

NON_DISEASE_CONDITIONS = {
    "healthy",
    "healthy volunteers",
    "healthy volunteer",
}

INTERVENTION_ALIASES = {
    "sirolimus": ["rapamycin"],
}

DRUGS = [
    {"key": "metformin", "name": "metformin", "chembl_id": "CHEMBL1431", "approved_terms": ["type 2 diabetes mellitus"], "orange_ingredient_contains": ["METFORMIN"], "max_trials": 2},
    {"key": "sirolimus", "name": "sirolimus", "chembl_id": "CHEMBL413", "approved_terms": ["malignant perivascular epithelioid cell tumor"], "orange_ingredient_contains": ["SIROLIMUS"], "max_trials": 2},
    {"key": "thalidomide", "name": "thalidomide", "chembl_id": "CHEMBL468", "approved_terms": ["multiple myeloma", "erythema nodosum leprosum"], "orange_ingredient_contains": ["THALIDOMIDE"], "max_trials": 2},
    {"key": "minoxidil", "name": "minoxidil", "chembl_id": "CHEMBL802", "approved_terms": ["hair regrowth", "top of the scalp"], "orange_ingredient_contains": ["MINOXIDIL"], "max_trials": 2},
    {"key": "sildenafil", "name": "sildenafil", "chembl_id": "CHEMBL192", "approved_terms": ["erectile dysfunction", "pulmonary arterial hypertension"], "orange_ingredient_contains": ["SILDENAFIL"], "max_trials": 2},
    {"key": "aspirin", "name": "aspirin", "chembl_id": "CHEMBL25", "approved_terms": ["minor aches and pains", "fever"], "orange_ingredient_contains": ["ASPIRIN"], "max_trials": 2},
    {"key": "methotrexate", "name": "methotrexate", "chembl_id": "CHEMBL34259", "approved_terms": ["acute lymphoblastic leukemia", "mycosis fungoides", "non-hodgkin lymphomas", "rheumatoid arthritis", "polyarticular juvenile idiopathic arthritis", "psoriasis"], "orange_ingredient_contains": ["METHOTREXATE"], "max_trials": 2},
    {"key": "propranolol", "name": "propranolol", "chembl_id": "CHEMBL27", "approved_terms": ["hypertension", "angina pectoris", "atrial fibrillation", "migraine", "essential tremor", "infantile hemangioma"], "orange_ingredient_contains": ["PROPRANOLOL"], "max_trials": 2},
    {"key": "naltrexone", "name": "naltrexone", "chembl_id": "CHEMBL19019", "approved_terms": ["alcohol dependence", "opioid dependence"], "orange_ingredient_contains": ["NALTREXONE"], "max_trials": 2},
    {"key": "ketamine", "name": "ketamine", "chembl_id": "CHEMBL742", "approved_terms": ["diagnostic and surgical procedures", "induction of anesthesia"], "orange_ingredient_contains": ["KETAMINE"], "max_trials": 2},
    {"key": "colchicine", "name": "colchicine", "chembl_id": "CHEMBL107", "approved_terms": ["gout", "familial mediterranean fever"], "orange_ingredient_contains": ["COLCHICINE"], "max_trials": 2},
    {"key": "hydroxychloroquine", "name": "hydroxychloroquine", "chembl_id": "CHEMBL1535", "approved_terms": ["malaria", "lupus erythematosus", "rheumatoid arthritis"], "orange_ingredient_contains": ["HYDROXYCHLOROQUINE"], "max_trials": 2},
    {"key": "doxycycline", "name": "doxycycline", "chembl_id": "CHEMBL1200699", "approved_terms": ["acne", "rosacea", "malaria", "adult periodontitis"], "orange_ingredient_contains": ["DOXYCYCLINE"], "max_trials": 2},
    {"key": "atorvastatin", "name": "atorvastatin", "chembl_id": "CHEMBL1487", "approved_terms": ["hyperlipidemia", "coronary heart disease"], "orange_ingredient_contains": ["ATORVASTATIN"], "max_trials": 2},
    {"key": "losartan", "name": "losartan", "chembl_id": "CHEMBL191", "approved_terms": ["hypertension", "diabetic nephropathy"], "orange_ingredient_contains": ["LOSARTAN"], "max_trials": 2},
    {"key": "spironolactone", "name": "spironolactone", "chembl_id": "CHEMBL1393", "approved_terms": ["heart failure", "hypertension", "edema", "hyperaldosteronism"], "orange_ingredient_contains": ["SPIRONOLACTONE"], "max_trials": 2},
    {"key": "finasteride", "name": "finasteride", "chembl_id": "CHEMBL710", "approved_terms": ["benign prostatic hyperplasia", "male pattern hair loss"], "orange_ingredient_contains": ["FINASTERIDE"], "max_trials": 2},
    {"key": "topiramate", "name": "topiramate", "chembl_id": "CHEMBL220492", "approved_terms": ["epilepsy", "migraine"], "orange_ingredient_contains": ["TOPIRAMATE"], "max_trials": 2},
    {"key": "gabapentin", "name": "gabapentin", "chembl_id": "CHEMBL940", "approved_terms": ["postherpetic neuralgia", "epilepsy"], "orange_ingredient_contains": ["GABAPENTIN"], "max_trials": 2},
    {"key": "pregabalin", "name": "pregabalin", "chembl_id": "CHEMBL1059", "approved_terms": ["diabetic peripheral neuropathy", "postherpetic neuralgia", "fibromyalgia", "epilepsy"], "orange_ingredient_contains": ["PREGABALIN"], "max_trials": 2},
    {"key": "amitriptyline", "name": "amitriptyline", "chembl_id": "CHEMBL629", "approved_terms": ["depression"], "orange_ingredient_contains": ["AMITRIPTYLINE"], "max_trials": 2},
    {"key": "bupropion", "name": "bupropion", "chembl_id": "CHEMBL894", "approved_terms": ["major depressive disorder", "seasonal affective disorder", "smoking cessation"], "orange_ingredient_contains": ["BUPROPION"], "max_trials": 2},
    {"key": "mifepristone", "name": "mifepristone", "chembl_id": "CHEMBL1276308", "approved_terms": ["hypercortisolism", "termination of pregnancy"], "orange_ingredient_contains": ["MIFEPRISTONE"], "max_trials": 2},
    {"key": "misoprostol", "name": "misoprostol", "chembl_id": "CHEMBL606", "approved_terms": ["gastric ulcers"], "orange_ingredient_contains": ["MISOPROSTOL"], "max_trials": 2},
    {"key": "tamoxifen", "name": "tamoxifen", "chembl_id": "CHEMBL83", "approved_terms": ["breast cancer", "ductal carcinoma in situ"], "orange_ingredient_contains": ["TAMOXIFEN"], "max_trials": 2},
    {"key": "raloxifene", "name": "raloxifene", "chembl_id": "CHEMBL81", "approved_terms": ["osteoporosis", "breast cancer"], "orange_ingredient_contains": ["RALOXIFENE"], "max_trials": 2},
    {"key": "anastrozole", "name": "anastrozole", "chembl_id": "CHEMBL1399", "approved_terms": ["breast cancer"], "orange_ingredient_contains": ["ANASTROZOLE"], "max_trials": 2},
    {"key": "letrozole", "name": "letrozole", "chembl_id": "CHEMBL1444", "approved_terms": ["breast cancer"], "orange_ingredient_contains": ["LETROZOLE"], "max_trials": 2},
    {"key": "imatinib", "name": "imatinib", "chembl_id": "CHEMBL941", "approved_terms": ["chronic myeloid leukemia", "gastrointestinal stromal tumors"], "orange_ingredient_contains": ["IMATINIB"], "max_trials": 2},
    {"key": "rituximab", "name": "rituximab", "chembl_id": "CHEMBL1201576", "approved_terms": ["non-hodgkin lymphoma", "chronic lymphocytic leukemia", "rheumatoid arthritis", "granulomatosis with polyangiitis"], "orange_ingredient_contains": ["RITUXIMAB"], "max_trials": 2},
    {"key": "bevacizumab", "name": "bevacizumab", "chembl_id": "CHEMBL1201583", "approved_terms": ["metastatic colorectal cancer", "non-squamous non-small cell lung cancer", "glioblastoma", "renal cell carcinoma", "cervical cancer", "ovarian cancer"], "orange_ingredient_contains": ["BEVACIZUMAB"], "max_trials": 2},
    {"key": "tocilizumab", "name": "tocilizumab", "chembl_id": "CHEMBL1237022", "approved_terms": ["rheumatoid arthritis", "giant cell arteritis", "cytokine release syndrome"], "orange_ingredient_contains": ["TOCILIZUMAB"], "max_trials": 2},
    {"key": "baricitinib", "name": "baricitinib", "chembl_id": "CHEMBL2105759", "approved_terms": ["rheumatoid arthritis", "alopecia areata", "COVID-19"], "orange_ingredient_contains": ["BARICITINIB"], "max_trials": 2},
    {"key": "ruxolitinib", "name": "ruxolitinib", "chembl_id": "CHEMBL1789941", "approved_terms": ["myelofibrosis", "polycythemia vera", "graft-versus-host disease", "atopic dermatitis"], "orange_ingredient_contains": ["RUXOLITINIB"], "max_trials": 2},
    {"key": "semaglutide", "name": "semaglutide", "chembl_id": "CHEMBL2108724", "approved_terms": ["type 2 diabetes mellitus", "obesity"], "orange_ingredient_contains": ["SEMAGLUTIDE"], "max_trials": 2},
    {"key": "empagliflozin", "name": "empagliflozin", "chembl_id": "CHEMBL2107830", "approved_terms": ["type 2 diabetes mellitus", "heart failure", "chronic kidney disease"], "orange_ingredient_contains": ["EMPAGLIFLOZIN"], "max_trials": 2},
]

MESH_LABEL_ALIASES = {
    "hr+/her2- advanced/metastatic breast cancer": "Breast Cancer",
    "hr+/her2- advanced metastatic breast cancer": "Breast Cancer",
    "advanced/metastatic breast cancer": "Breast Cancer",
    "metastatic breast cancer": "Breast Cancer",
    "breast cancer": "Breast Cancer",
    "non-hodgkin lymphomas": "Lymphoma, Non-Hodgkin",
    "non-hodgkin lymphoma": "Lymphoma, Non-Hodgkin",
    "lymphoblastic lymphoma": "Precursor Cell Lymphoblastic Leukemia-Lymphoma",
    "malignant perivascular epithelioid cell tumor": "PEComa",
    "perivascular epithelioid cell tumor": "PEComa",
    "type 2 diabetes mellitus": "Diabetes Mellitus, Type 2",
    "rheumatoid arthritis": "Arthritis, Rheumatoid",
    "psoriasis": "Psoriasis",
    "acute lymphoblastic leukemia": "Precursor Cell Lymphoblastic Leukemia-Lymphoma",
    "mycosis fungoides": "Mycosis Fungoides",
    "polyarticular juvenile idiopathic arthritis": "Arthritis, Juvenile",
    "endometriosis": "Endometriosis",
    "polycystic ovary syndrome": "Polycystic Ovary Syndrome",
    "depression": "Depression",
    "multiple myeloma": "Multiple Myeloma",
    "plaque psoriasis": "Psoriasis",
    "ischemic heart disease": "Myocardial Ischemia",
    "stroke": "Stroke",
}


def slug(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return clean or hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def norm_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def canonical_condition_label(label: str) -> tuple[str, str]:
    lower = norm_text(label)
    alias_key = label.lower().strip()
    if alias_key in MESH_LABEL_ALIASES:
        return MESH_LABEL_ALIASES[alias_key], "alias"
    if "breast cancer" in lower:
        return "Breast Cancer", "cancer_phrase_rule"
    return label, "identity"


def mesh_tree_numbers(mesh_id: str) -> list[str]:
    url = f"https://id.nlm.nih.gov/mesh/{mesh_id}.json"
    try:
        payload = fetch_json(url, f"mesh_descriptor_{mesh_id}.json")
    except Exception:
        return []
    tree_values = payload.get("treeNumber", [])
    if isinstance(tree_values, str):
        tree_values = [tree_values]
    trees = []
    for value in tree_values:
        if isinstance(value, str):
            trees.append(value.rsplit("/", 1)[-1])
    return trees


def is_mesh_disease_tree(tree_numbers: list[str]) -> bool:
    # MeSH C is Diseases; F03 is Mental Disorders. Non-disease MeSH concepts like Aging live elsewhere.
    return any(tree.startswith("C") or tree.startswith("F03") for tree in tree_numbers)


def mondo_exact_lookup(label: str) -> dict[str, Any]:
    url = "https://www.ebi.ac.uk/ols4/api/search?" + urllib.parse.urlencode(
        {"q": label, "ontology": "mondo", "exact": "true", "rows": "30"}
    )
    try:
        payload = fetch_json(url, f"mondo_exact_{slug(label)}.json")
    except Exception as exc:  # noqa: BLE001
        return {"mapped": False, "label": label, "error": str(exc)}
    wanted = norm_text(label)
    for doc in payload.get("response", {}).get("docs", []):
        candidates = [doc.get("label", "")] + doc.get("exact_synonyms", [])
        for candidate in candidates:
            if norm_text(candidate) == wanted:
                return {
                    "mapped": True,
                    "label": doc.get("label", label),
                    "mondo_id": doc.get("short_form"),
                    "obo_id": doc.get("obo_id"),
                    "iri": doc.get("iri"),
                    "matched_text": candidate,
                    "url": doc.get("iri"),
                }
    return {"mapped": False, "label": label, "num_found": payload.get("response", {}).get("numFound", 0)}


def stable_id(prefix: str, *parts: str) -> str:
    body = "|".join(parts)
    return f"{prefix}:{hashlib.sha1(body.encode('utf-8')).hexdigest()[:16]}"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def fetch_json(url: str, cache_name: str | None = None, *, method: str = "GET", body: bytes | None = None) -> Any:
    if cache_name:
        cache_path = RAW_DIR / cache_name
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                cache_path.unlink(missing_ok=True)
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": "DiseaseWebMinimalETL/0.1",
            "Content-Type": "application/json" if body else "application/x-www-form-urlencoded",
        },
        method=method,
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read())
            if cache_name:
                write_json(RAW_DIR / cache_name, payload)
            return payload
        except Exception as exc:  # noqa: BLE001 - external APIs have occasional transient failures.
            last_error = exc
            if attempt == 2:
                break
            time.sleep(2 * (attempt + 1))
    raise last_error


def fetch_bytes(url: str, cache_name: str | None = None) -> bytes:
    if cache_name:
        cache_path = RAW_DIR / cache_name
        if cache_path.exists():
            return cache_path.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": "DiseaseWebMinimalETL/0.1"})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
            if cache_name:
                cache_path = RAW_DIR / cache_name
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(payload)
            return payload
        except Exception as exc:  # noqa: BLE001 - external APIs have occasional transient failures.
            last_error = exc
            if attempt == 2:
                break
            time.sleep(2 * (attempt + 1))
    raise last_error


@dataclass
class GraphBuilder:
    nodes: dict[str, dict[str, Any]]
    edges: dict[str, dict[str, Any]]

    def add_node(self, node_id: str, kind: str, label: str, **attrs: Any) -> dict[str, Any]:
        node = self.nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label, "attributes": {}})
        node["attributes"].update({k: v for k, v in attrs.items() if v not in (None, "", [], {})})
        return node

    def add_edge(
        self,
        edge_type: str,
        source_id: str,
        target_id: str,
        source: str,
        citation: dict[str, Any],
        confidence: float | None = None,
        **attrs: Any,
    ) -> dict[str, Any]:
        edge_id = stable_id("edge", edge_type, source_id, target_id, json.dumps(citation, sort_keys=True))
        edge = {
            "id": edge_id,
            "type": edge_type,
            "source_id": source_id,
            "target_id": target_id,
            "source": source,
            "confidence": confidence,
            "citation": citation,
            "attributes": {k: v for k, v in attrs.items() if v not in (None, "", [], {})},
        }
        self.edges[edge_id] = edge
        return edge


def rxnorm_exact_rxcui(name: str) -> str | None:
    url = "https://rxnav.nlm.nih.gov/REST/rxcui.json?" + urllib.parse.urlencode({"name": name})
    payload = fetch_json(url, f"rxnorm_exact_{slug(name)}.json")
    ids = payload.get("idGroup", {}).get("rxnormId", [])
    return ids[0] if ids else None


def rxnorm_ingredient_for_rxcui(rxcui: str) -> dict[str, str] | None:
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json?" + urllib.parse.urlencode({"tty": "IN"})
    payload = fetch_json(url, f"rxnorm_related_in_{rxcui}.json")
    for group in payload.get("relatedGroup", {}).get("conceptGroup", []):
        for concept in group.get("conceptProperties", []) or []:
            if concept.get("tty") == "IN" and concept.get("rxcui"):
                return {"rxcui": concept["rxcui"], "name": concept.get("name", "")}
    return None


def normalize_intervention_to_ingredient(intervention_name: str, canonical_name: str, canonical_rxcui: str) -> dict[str, Any]:
    url = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json?" + urllib.parse.urlencode(
        {"term": intervention_name, "maxEntries": "3"}
    )
    payload = fetch_json(url, f"rxnorm_approx_{slug(intervention_name)}.json")
    candidates = payload.get("approximateGroup", {}).get("candidate", [])
    for candidate in candidates:
        rxcui = candidate.get("rxcui")
        if not rxcui:
            continue
        if rxcui == canonical_rxcui:
            return {
                "matched": True,
                "method": "rxnorm_approx_exact_ingredient",
                "matched_rxcui": canonical_rxcui,
                "candidate": candidate,
            }
        ingredient = rxnorm_ingredient_for_rxcui(rxcui)
        if ingredient and ingredient.get("rxcui") == canonical_rxcui:
            return {
                "matched": True,
                "method": "rxnorm_approx_then_related_ingredient",
                "matched_rxcui": canonical_rxcui,
                "candidate": candidate,
                "ingredient": ingredient,
            }
    if re.search(rf"\b{re.escape(canonical_name)}\b", intervention_name, flags=re.I):
        return {
            "matched": True,
            "method": "literal_named_drug_with_rxnorm_canonical",
            "matched_rxcui": canonical_rxcui,
            "note": "Approximate RxNorm result did not resolve cleanly to ingredient; accepted because the named DRUG intervention contains the canonical RxNorm ingredient label.",
        }
    return {"matched": False, "method": "no_rxnorm_ingredient_match", "candidates": candidates[:3]}


def rxclass_edges(graph: GraphBuilder, drug_id: str, drug_name: str, rxcui: str) -> None:
    url = "https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?" + urllib.parse.urlencode({"rxcui": rxcui})
    payload = fetch_json(url, f"rxclass_{rxcui}.json")
    seen: set[str] = set()
    for item in payload.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
        concept = item.get("rxclassMinConceptItem", {})
        class_name = concept.get("className")
        class_id = concept.get("classId") or class_name
        if not class_name or class_name in seen:
            continue
        # Keep the class slice compact and preferably interpretable.
        source = item.get("relaSource", "RxClass")
        if source not in {"VA", "ATC", "MeSH", "MESHPA"} and len(seen) >= 2:
            continue
        seen.add(class_name)
        mechanism_id = f"mechanism:rxclass:{slug(class_id)}"
        graph.add_node(
            mechanism_id,
            "mechanism",
            class_name,
            source="RxClass",
            class_id=class_id,
            relation=item.get("rela"),
            relation_source=source,
        )
        graph.add_edge(
            "in_class_of",
            drug_id,
            mechanism_id,
            "RxClass",
            {
                "source": "RxClass API",
                "url": url,
                "rxcui": rxcui,
                "class_id": class_id,
            },
            confidence=None,
            relation=item.get("rela"),
            relation_source=source,
        )
        if len(seen) >= 3:
            break


def load_orange_book_products() -> list[dict[str, str]]:
    path = ORANGE_BOOK_DIR / "products.txt"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    with path.open("r", encoding="latin-1", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="~"))


def find_orange_product(products: list[dict[str, str]], drug: dict[str, Any]) -> dict[str, str] | None:
    needles = drug["orange_ingredient_contains"]
    candidates = []
    for index, row in enumerate(products):
        ingredient = (row.get("Ingredient") or "").upper()
        if not any(needle in ingredient for needle in needles):
            continue
        exact_or_salt = ";" not in ingredient
        active = row.get("Type") != "DISCN"
        reference = row.get("RLD") == "Yes" or row.get("RS") == "Yes"
        nda = row.get("Appl_Type") == "N"
        candidates.append((not active, not exact_or_salt, not reference, not nda, index, row))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[:5])
    return candidates[0][-1]


def extract_indication_sections(xml_bytes: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    ns = {"hl7": "urn:hl7-org:v3"}
    sections: list[dict[str, str]] = []
    for section in root.findall(".//hl7:section", ns):
        title_el = section.find("hl7:title", ns)
        title = " ".join("".join(title_el.itertext()).split()) if title_el is not None else ""
        title_upper = title.upper()
        is_rx_indication = "INDICATIONS AND USAGE" in title_upper or re.match(r"^1(?:\.\d+)*\.?\s", title)
        is_otc_use = title_upper in {"USES", "PURPOSE", "ACTIVE INGREDIENT AND PURPOSE"}
        if not (is_rx_indication or is_otc_use):
            continue
        text_el = section.find("hl7:text", ns)
        text = " ".join("".join(text_el.itertext()).split()) if text_el is not None else ""
        if text:
            sections.append({"title": title, "text": text})
    return sections


COMBINATION_TITLE_TOKENS = {
    "ACETAMINOPHEN",
    "CAFFEINE",
    "DIPHENHYDRAMINE",
    "PHENYLEPHRINE",
    "CHLORPHENIRAMINE",
    "DEXTROMETHORPHAN",
    "GUAIFENESIN",
}


def dailymed_title_score(title: str, drug_name: str) -> int:
    title_upper = (title or "").upper()
    product_part = title_upper.split("[")[0]
    drug_upper = drug_name.upper()
    score = 0
    if product_part.startswith(drug_upper):
        score -= 20
    if f"({drug_upper})" in product_part:
        score -= 10
    if any(token in product_part and token != drug_upper for token in COMBINATION_TITLE_TOKENS):
        score += 50
    if " WITH " in product_part:
        score += 5
    return score


def dailymed_label_matches(drug: dict[str, Any]) -> list[dict[str, Any]]:
    if not drug["approved_terms"]:
        return []
    url = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?" + urllib.parse.urlencode(
        {"drug_name": drug["name"], "pagesize": "100"}
    )
    payload = fetch_json(url, f"dailymed_spls_{drug['key']}_page100.json")
    items = list(enumerate(payload.get("data", [])))
    items.sort(key=lambda pair: (dailymed_title_score(pair[1].get("title") or "", drug["name"]), pair[0]))
    matches: list[dict[str, Any]] = []
    matched_terms: set[str] = set()
    for _item_index, item in items:
        setid = item.get("setid")
        if not setid:
            continue
        xml_url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"
        xml_bytes = fetch_bytes(xml_url, f"dailymed_label_{drug['key']}_{setid}.xml")
        for section in extract_indication_sections(xml_bytes):
            lower_text = section["text"].lower()
            for term in drug["approved_terms"]:
                if term in matched_terms or term.lower() not in lower_text:
                    continue
                matches.append(
                    {
                        "term": term,
                        "setid": setid,
                        "title": item.get("title"),
                        "published_date": item.get("published_date"),
                        "section_title": section["title"],
                        "section_text": section["text"],
                        "url": f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={setid}",
                    }
                )
                matched_terms.add(term)
        if matched_terms == set(drug["approved_terms"]):
            break
    return matches


def mesh_lookup(label: str) -> dict[str, Any]:
    query_label, normalization_method = canonical_condition_label(label)
    url = "https://id.nlm.nih.gov/mesh/lookup/descriptor?" + urllib.parse.urlencode(
        {"label": query_label, "match": "exact", "limit": "5"}
    )
    try:
        payload = fetch_json(url, f"mesh_{slug(query_label)}.json")
    except Exception as exc:  # noqa: BLE001 - ontology lookup failures become explicit unmapped nodes.
        return {
            "mapped": False,
            "label": label,
            "lookup_label": query_label,
            "normalization_method": normalization_method,
            "error": str(exc),
        }
    if payload:
        first = payload[0]
        resource = first.get("resource", "")
        mesh_id = resource.rsplit("/", 1)[-1] if resource else None
        tree_numbers = mesh_tree_numbers(mesh_id) if mesh_id else []
        return {
            "mapped": True,
            "label": first.get("label", label),
            "lookup_label": query_label,
            "normalization_method": normalization_method,
            "mesh_id": mesh_id,
            "resource": resource,
            "url": resource,
            "tree_numbers": tree_numbers,
            "is_disease_descriptor": is_mesh_disease_tree(tree_numbers),
        }
    return {
        "mapped": False,
        "label": label,
        "lookup_label": query_label,
        "normalization_method": normalization_method,
    }


def resolve_condition(label: str) -> dict[str, Any]:
    mesh = mesh_lookup(label)
    if mesh.get("mapped"):
        if mesh.get("is_disease_descriptor"):
            return {"node_category": "disease", "authority": "MeSH", "mesh": mesh, "label": mesh.get("label", label)}
        return {"node_category": "research_condition", "authority": "MeSH", "mesh": mesh, "label": mesh.get("label", label)}

    lookup_label, normalization_method = canonical_condition_label(label)
    mondo = mondo_exact_lookup(lookup_label)
    mondo["lookup_label"] = lookup_label
    mondo["normalization_method"] = normalization_method
    if mondo.get("mapped") and mondo.get("mondo_id"):
        return {"node_category": "disease", "authority": "MONDO", "mondo": mondo, "mesh": mesh, "label": mondo.get("label", lookup_label)}
    return {"node_category": "research_condition", "authority": "raw", "mesh": mesh, "mondo": mondo, "label": label}


def disease_node(graph: GraphBuilder, label: str, *, source: str = "local") -> str:
    resolved = resolve_condition(label)
    category = resolved["node_category"]
    if resolved["authority"] == "MeSH" and resolved.get("mesh", {}).get("mesh_id"):
        mesh = resolved["mesh"]
        node_id = f"disease:mesh:{mesh['mesh_id']}"
        graph.add_node(
            node_id,
            "disease",
            resolved.get("label", label),
            source="MeSH",
            node_category=category,
            mesh=mesh,
            original_label=label,
        )
        return node_id
    if resolved["authority"] == "MONDO" and resolved.get("mondo", {}).get("mondo_id"):
        mondo = resolved["mondo"]
        node_id = f"disease:mondo:{mondo['mondo_id']}"
        graph.add_node(
            node_id,
            "disease",
            resolved.get("label", label),
            source="MONDO",
            node_category=category,
            mondo=mondo,
            mesh=resolved.get("mesh"),
            original_label=label,
        )
        return node_id
    if category == "research_condition":
        node_id = f"condition:{source}:{slug(label)}"
        node_kind = "research_condition"
    else:
        node_id = f"disease:{source}:{slug(label)}"
        node_kind = "disease"
    graph.add_node(
        node_id,
        node_kind,
        label,
        source=source,
        node_category=category,
        mesh=resolved.get("mesh"),
        mondo=resolved.get("mondo"),
        original_label=label,
    )
    return node_id


def is_resolved_disease_node(node: dict[str, Any]) -> bool:
    attrs = node.get("attributes", {})
    if node.get("kind") != "disease" or attrs.get("node_category") != "disease":
        return False
    mesh = attrs.get("mesh") or {}
    mondo = attrs.get("mondo") or {}
    return bool(mesh.get("mesh_id") or mondo.get("mondo_id"))


def annotate_search_flags(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for node in nodes:
        default_search = is_resolved_disease_node(node)
        node.setdefault("attributes", {})["disease_search_default"] = default_search
        node["attributes"]["pathfinding_default"] = default_search
    return nodes


def disease_search_export(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for node in nodes:
        if not node.get("attributes", {}).get("disease_search_default"):
            continue
        attrs = node.get("attributes", {})
        mesh = attrs.get("mesh") or {}
        mondo = attrs.get("mondo") or {}
        rows.append({
            "id": node["id"],
            "label": node["label"],
            "node_category": attrs.get("node_category"),
            "source": attrs.get("source"),
            "mesh_id": mesh.get("mesh_id"),
            "mondo_id": mondo.get("mondo_id"),
        })
    return sorted(rows, key=lambda row: row["label"].lower())


def opentargets_query(query: str, variables: dict[str, Any], cache_name: str) -> Any:
    url = "https://api.platform.opentargets.org/api/v4/graphql"
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    return fetch_json(url, cache_name, method="POST", body=body)


def open_targets_mechanisms(graph: GraphBuilder, drug_id: str, drug: dict[str, Any]) -> list[str]:
    query = """
    query Drug($id: String!) {
      drug(chemblId: $id) {
        id
        name
        mechanismsOfAction {
          rows {
            mechanismOfAction
            actionType
            targetName
            targets { id approvedSymbol approvedName }
            references { source ids urls }
          }
        }
      }
    }
    """
    payload = opentargets_query(query, {"id": drug["chembl_id"]}, f"opentargets_drug_{drug['chembl_id']}.json")
    drug_payload = payload.get("data", {}).get("drug")
    if not drug_payload:
        return []
    target_ids: list[str] = []
    emitted_mechanisms: set[str] = set()
    emitted_targets: set[str] = set()
    for row_index, row in enumerate(drug_payload.get("mechanismsOfAction", {}).get("rows", [])[:2]):
        mechanism = row.get("mechanismOfAction")
        if mechanism:
            mechanism_id = f"mechanism:opentargets:{slug(mechanism)}"
            graph.add_node(
                mechanism_id,
                "mechanism",
                mechanism,
                source="Open Targets",
                action_type=row.get("actionType"),
                target_name=row.get("targetName"),
            )
            if mechanism_id not in emitted_mechanisms:
                emitted_mechanisms.add(mechanism_id)
                graph.add_edge(
                    "in_class_of",
                    drug_id,
                    mechanism_id,
                    "Open Targets Platform",
                    {
                        "source": "Open Targets GraphQL mechanismsOfAction",
                        "chembl_id": drug["chembl_id"],
                        "references": row.get("references", [])[:2],
                        "url": f"https://platform.opentargets.org/drug/{drug['chembl_id']}",
                    },
                    confidence=None,
                    action_type=row.get("actionType"),
                )
        for target in row.get("targets", [])[:2]:
            ensembl_id = target.get("id")
            if not ensembl_id:
                continue
            target_id = f"target:ensembl:{ensembl_id}"
            target_ids.append(target_id)
            graph.add_node(
                target_id,
                "target",
                target.get("approvedSymbol") or target.get("approvedName") or ensembl_id,
                source="Open Targets",
                ensembl_id=ensembl_id,
                approved_symbol=target.get("approvedSymbol"),
                approved_name=target.get("approvedName"),
            )
            if target_id in emitted_targets:
                continue
            emitted_targets.add(target_id)
            graph.add_edge(
                "targets",
                drug_id,
                target_id,
                "Open Targets Platform",
                {
                    "source": "Open Targets GraphQL mechanismsOfAction",
                    "chembl_id": drug["chembl_id"],
                    "target_id": ensembl_id,
                    "references": row.get("references", [])[:2],
                    "url": f"https://platform.opentargets.org/drug/{drug['chembl_id']}",
                },
                confidence=None,
                mechanism=row.get("mechanismOfAction"),
                action_type=row.get("actionType"),
                row_index=row_index,
            )
    return target_ids


def open_targets_associated_diseases(graph: GraphBuilder, target_ids: list[str]) -> None:
    query = """
    query Target($id: String!) {
      target(ensemblId: $id) {
        id
        approvedSymbol
        associatedDiseases(page: { index: 0, size: 50 }) {
          rows {
            score
            disease { id name }
          }
        }
      }
    }
    """
    queried = 0
    emitted_hp_spot_check = False
    for target_node_id in list(dict.fromkeys(target_ids)):
        if queried >= 8:
            break
        ensembl_id = target_node_id.replace("target:ensembl:", "")
        payload = opentargets_query(query, {"id": ensembl_id}, f"opentargets_target_assoc_page50_{ensembl_id}.json")
        target = payload.get("data", {}).get("target")
        if not target:
            continue
        queried += 1
        rows = target.get("associatedDiseases", {}).get("rows", [])
        selected_rows = rows[:2]
        if not emitted_hp_spot_check:
            hp_row = next((item for item in rows if (item.get("disease", {}).get("id", "").startswith("HP_"))), None)
            if hp_row and hp_row not in selected_rows:
                selected_rows.append(hp_row)
                emitted_hp_spot_check = True
            elif hp_row:
                emitted_hp_spot_check = True
        for row in selected_rows:
            disease = row.get("disease", {})
            disease_id = disease.get("id")
            if not disease_id:
                continue
            disease_name = disease.get("name", disease_id)
            if disease_id.startswith("MONDO_"):
                category = "disease"
                disease_node_id = f"disease:mondo:{disease_id}"
                ontology_attrs = {"mondo": {"mondo_id": disease_id, "source": "Open Targets"}}
            elif disease_id.startswith(("MP_", "HP_")):
                # Mammalian Phenotype and Human Phenotype terms are phenotypes, not disease authorities.
                category = "research_condition"
                disease_node_id = f"condition:{disease_id.lower()}"
                ontology_attrs = {"phenotype_id": disease_id}
            else:
                resolved = resolve_condition(disease_name)
                category = resolved["node_category"]
                if resolved["authority"] == "MeSH" and resolved.get("mesh", {}).get("mesh_id"):
                    disease_node_id = f"disease:mesh:{resolved['mesh']['mesh_id']}"
                elif resolved["authority"] == "MONDO" and resolved.get("mondo", {}).get("mondo_id"):
                    disease_node_id = f"disease:mondo:{resolved['mondo']['mondo_id']}"
                else:
                    disease_node_id = f"condition:opentargets:{slug(disease_id)}"
                ontology_attrs = {
                    "mesh": resolved.get("mesh"),
                    "mondo": resolved.get("mondo"),
                    "original_label": disease_name,
                }
            graph.add_node(
                disease_node_id,
                "disease",
                disease_name,
                source="Open Targets",
                open_targets_disease_id=disease_id,
                node_category=category,
                **ontology_attrs,
            )
            graph.add_edge(
                "associated_with",
                target_node_id,
                disease_node_id,
                "Open Targets Platform",
                {
                    "source": "Open Targets target associatedDiseases",
                    "target_id": ensembl_id,
                    "disease_id": disease_id,
                    "url": f"https://platform.opentargets.org/evidence/{ensembl_id}/{disease_id}",
                },
                confidence=row.get("score"),
            )


def clinical_trials_edges(graph: GraphBuilder, drug_id: str, drug: dict[str, Any], canonical_rxcui: str) -> None:
    url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(
        {"query.intr": drug["name"], "pageSize": "100", "format": "json"}
    )
    payload = fetch_json(url, f"ctgov_intr_{drug['key']}.json")
    emitted_trials = 0
    for study in payload.get("studies", []):
        protocol = study.get("protocolSection", {})
        nct_id = protocol.get("identificationModule", {}).get("nctId")
        status = protocol.get("statusModule", {}).get("overallStatus")
        if not nct_id or status not in ACTIVE_STATUSES:
            continue
        design = protocol.get("designModule", {})
        interventions = protocol.get("armsInterventionsModule", {}).get("interventions", [])
        matched_interventions = []
        name_terms = [drug["name"], *INTERVENTION_ALIASES.get(drug["name"], [])]
        for intervention in interventions:
            if intervention.get("type") != "DRUG":
                continue
            name = intervention.get("name") or ""
            lower_name = name.lower()
            if not any(term.lower() in lower_name for term in name_terms):
                continue
            normalized = normalize_intervention_to_ingredient(name, drug["name"], canonical_rxcui)
            if normalized.get("matched"):
                matched_interventions.append({"name": name, "normalization": normalized})
        if not matched_interventions:
            continue
        conditions = protocol.get("conditionsModule", {}).get("conditions", [])
        if not conditions:
            continue
        emitted_conditions = 0
        for condition in conditions:
            if condition.strip().lower() in NON_DISEASE_CONDITIONS:
                continue
            disease_id = disease_node(graph, condition, source="ctgov")
            graph.add_edge(
                "investigational_for",
                drug_id,
                disease_id,
                "ClinicalTrials.gov",
                {
                    "source": "ClinicalTrials.gov API v2",
                    "nct_id": nct_id,
                    "url": f"https://clinicaltrials.gov/study/{nct_id}",
                },
                confidence=None,
                status=status,
                phases=design.get("phases", []),
                intervention_names=[item["name"] for item in matched_interventions],
                normalization=[item["normalization"] for item in matched_interventions],
            )
            emitted_conditions += 1
            if emitted_conditions >= 2:
                break
        if emitted_conditions == 0:
            continue
        emitted_trials += 1
        if emitted_trials >= drug["max_trials"]:
            break


def add_approved_edges(graph: GraphBuilder, drug_id: str, drug: dict[str, Any], orange_product: dict[str, str] | None) -> None:
    for match in dailymed_label_matches(drug):
        disease_id = disease_node(graph, match["term"], source="dailymed")
        citation = {
            "source": "DailyMed SPL label",
            "setid": match["setid"],
            "url": match["url"],
            "section_title": match["section_title"],
        }
        if orange_product:
            citation["orange_book"] = {
                "source": "FDA Orange Book EOBZIP 2026-05 products.txt",
                "ingredient": orange_product.get("Ingredient"),
                "trade_name": orange_product.get("Trade_Name"),
                "appl_type": orange_product.get("Appl_Type"),
                "appl_no": orange_product.get("Appl_No"),
                "product_no": orange_product.get("Product_No"),
                "approval_date": orange_product.get("Approval_Date"),
                "path": "data/raw/orange_book/products.txt",
            }
        graph.add_edge(
            "approved_for",
            drug_id,
            disease_id,
            "DailyMed + FDA Orange Book",
            citation,
            confidence=None,
            indication_text=match["section_text"],
            dailymed_title=match["title"],
            published_date=match.get("published_date"),
        )


def iter_mesh_descriptors(xml_path: Path):
    # Full MeSH ingestion must use this streaming pattern; do not ET.parse the 300MB+ descriptor XML.
    context = ET.iterparse(xml_path, events=("end",))
    for _event, elem in context:
        if elem.tag.endswith("DescriptorRecord"):
            yield elem
            elem.clear()


def build() -> tuple[GraphBuilder, dict[str, Any]]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    graph = GraphBuilder(nodes={}, edges={})
    products = load_orange_book_products()
    target_ids_for_association: list[str] = []
    drug_outputs: list[dict[str, Any]] = []

    for index, drug in enumerate(DRUGS, start=1):
        print(f"[{index}/{len(DRUGS)}] ETL {drug['name']}", flush=True)
        rxcui = rxnorm_exact_rxcui(drug["name"])
        if not rxcui:
            drug_outputs.append({"drug": drug["name"], "status": "skipped", "reason": "No RxNorm exact RxCUI"})
            continue
        drug_id = f"drug:rxnorm:{rxcui}"
        graph.add_node(
            drug_id,
            "drug",
            drug["name"],
            source="RxNorm",
            rxcui=rxcui,
            chembl_id=drug["chembl_id"],
        )
        orange_product = find_orange_product(products, drug)
        if orange_product:
            graph.nodes[drug_id]["attributes"]["orange_book_product"] = {
                "ingredient": orange_product.get("Ingredient"),
                "trade_name": orange_product.get("Trade_Name"),
                "appl_type": orange_product.get("Appl_Type"),
                "appl_no": orange_product.get("Appl_No"),
                "product_no": orange_product.get("Product_No"),
            }
        add_approved_edges(graph, drug_id, drug, orange_product)
        clinical_trials_edges(graph, drug_id, drug, rxcui)
        rxclass_edges(graph, drug_id, drug["name"], rxcui)
        target_ids_for_association.extend(open_targets_mechanisms(graph, drug_id, drug))
        drug_outputs.append(
            {
                "drug": drug["name"],
                "drug_id": drug_id,
                "rxcui": rxcui,
                "orange_book_product": orange_product,
            }
        )

    open_targets_associated_diseases(graph, target_ids_for_association)

    nodes = annotate_search_flags(sorted(graph.nodes.values(), key=lambda row: row["id"]))
    edges = sorted(graph.edges.values(), key=lambda row: row["id"])
    search_nodes = disease_search_export(nodes)
    write_jsonl(OUT_DIR / "nodes.jsonl", nodes)
    write_jsonl(OUT_DIR / "edges.jsonl", edges)
    write_json(OUT_DIR / "nodes.json", nodes)
    write_json(OUT_DIR / "edges.json", edges)
    write_json(OUT_DIR / "disease_search_nodes.json", search_nodes)

    summary = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes_by_kind": dict(Counter(node["kind"] for node in nodes)),
        "condition_nodes_by_category": dict(Counter(
            node.get("attributes", {}).get("node_category", "uncategorized")
            for node in nodes
            if node["kind"] in {"disease", "research_condition"}
        )),
        "edges_by_type": dict(Counter(edge["type"] for edge in edges)),
        "edges_by_source": dict(Counter(edge["source"] for edge in edges)),
        "disease_search_default_count": len(search_nodes),
        "pathfinding_default_node_count": len(search_nodes),
        "excluded_from_disease_search_count": sum(
            1
            for node in nodes
            if node["kind"] in {"disease", "research_condition"}
            and not node.get("attributes", {}).get("disease_search_default")
        ),
        "drugs": drug_outputs,
        "outputs": {
            "nodes_jsonl": str((OUT_DIR / "nodes.jsonl").relative_to(ROOT)),
            "edges_jsonl": str((OUT_DIR / "edges.jsonl").relative_to(ROOT)),
            "nodes_json": str((OUT_DIR / "nodes.json").relative_to(ROOT)),
            "edges_json": str((OUT_DIR / "edges.json").relative_to(ROOT)),
            "disease_search_nodes_json": str((OUT_DIR / "disease_search_nodes.json").relative_to(ROOT)),
        },
    }
    write_json(OUT_DIR / "summary.json", summary)
    write_report(nodes, edges, summary)
    return graph, summary


def citation_label(edge: dict[str, Any]) -> str:
    citation = edge.get("citation", {})
    if citation.get("nct_id"):
        return citation["nct_id"]
    if citation.get("setid"):
        return f"DailyMed {citation['setid']}"
    if citation.get("target_id") and citation.get("disease_id"):
        return f"OT {citation['target_id']}->{citation['disease_id']}"
    if citation.get("chembl_id"):
        return f"OT {citation['chembl_id']}"
    if citation.get("class_id"):
        return f"RxClass {citation['class_id']}"
    return citation.get("source", "citation")


def write_report(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    node_label = {node["id"]: node["label"] for node in nodes}
    lines = [
        "# Gate 2 Minimal ETL Output",
        "",
        "This is a small real graph slice. Every edge below has a source citation; no placeholder edges are emitted.",
        "",
        "## Counts",
        "",
        f"- Nodes: {summary['node_count']}",
        f"- Edges: {summary['edge_count']}",
        f"- Nodes by kind: `{json.dumps(summary['nodes_by_kind'], sort_keys=True)}`",
        f"- Condition nodes by category: `{json.dumps(summary['condition_nodes_by_category'], sort_keys=True)}`",
        f"- Default disease search/path-finding nodes: {summary['disease_search_default_count']}",
        f"- Excluded condition/research-condition nodes from default disease search/path-finding: {summary['excluded_from_disease_search_count']}",
        f"- Edges by type: `{json.dumps(summary['edges_by_type'], sort_keys=True)}`",
        f"- Edges by source: `{json.dumps(summary['edges_by_source'], sort_keys=True)}`",
        "",
        "## Sample Edges",
        "",
        "| Type | From | To | Source | Citation |",
        "| --- | --- | --- | --- | --- |",
    ]
    preferred = ["approved_for", "investigational_for", "targets", "in_class_of", "associated_with"]
    sample_edges: list[dict[str, Any]] = []
    for edge_type in preferred:
        sample_edges.extend([edge for edge in edges if edge["type"] == edge_type][:5])
    seen = set()
    for edge in sample_edges:
        if edge["id"] in seen:
            continue
        seen.add(edge["id"])
        lines.append(
            f"| {edge['type']} | {node_label.get(edge['source_id'], edge['source_id'])} | "
            f"{node_label.get(edge['target_id'], edge['target_id'])} | {edge['source']} | {citation_label(edge)} |"
        )
    lines.extend(
        [
            "",
            "## ClinicalTrials Filtering Rule",
            "",
            "ClinicalTrials edges require `overallStatus` to be active, an `armsInterventionsModule.interventions[]` entry with `type == DRUG`, and RxNorm ingredient normalization or an explicit literal named-drug fallback recorded in the edge attributes.",
            "",
            "## MeSH Parsing Note",
            "",
            "Condition normalization first tries exact/alias MeSH descriptor lookup and tags `disease` only when the descriptor is in a disease tree (`C*` or `F03*`). It then tries validated MONDO exact label/synonym matching. Remaining nodes are kept as `research_condition` with the raw source label.",
            "Default disease search and default path-finding include only resolved MeSH/MONDO disease nodes. Raw/unmapped and phenotype/research-condition nodes remain in the graph for evidence display and repurposing signals, but are excluded from disease autocomplete/path queries unless explicitly requested later.",
            "",
            "Minimal ETL uses the MeSH descriptor lookup API for the small slice. Full MeSH XML ingestion must use `iter_mesh_descriptors()`, which is implemented with `xml.etree.ElementTree.iterparse` and clears elements as they are yielded.",
            "",
        ]
    )
    (REPORT_DIR / "minimal_etl_gate2.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    _graph, summary = build()
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\nWrote {OUT_DIR / 'nodes.jsonl'}")
    print(f"Wrote {OUT_DIR / 'edges.jsonl'}")
    print(f"Wrote {REPORT_DIR / 'minimal_etl_gate2.md'}")


if __name__ == "__main__":
    main()