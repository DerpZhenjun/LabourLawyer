"""Measure QA reuse through isolated, source-bound regional HTTP entry points."""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter
from unittest.mock import patch
from xml.etree import ElementTree
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from regional_guides import RegionalStore
from regional_template_acceptance import AcceptanceStore, content_digest, template_families


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_document(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as destination:
            destination.write(body)
    except FileExistsError:
        if path.read_bytes() != body:
            raise ValueError("Existing QA document bytes changed")


def eligible_templates(guide):
    return [item for item in guide.get("templates", [])
            if item.get("can_generate") is True and item.get("official_kind") == "blank"
            and item.get("adapter") and item["adapter"] not in {
                "sichuan_combined_reference_v1", "tianfu_reference_v1"}]


def choose_regions(guides, count):
    provinces = defaultdict(list)
    for guide in guides:
        if eligible_templates(guide):
            provinces[guide["province"]].append(guide)
    for rows in provinces.values():
        rows.sort(key=lambda guide: guide["region_code"])
    chosen = []
    while provinces and len(chosen) < count:
        for province in sorted(list(provinces)):
            chosen.append(provinces[province].pop(0))
            if not provinces[province]:
                del provinces[province]
            if len(chosen) == count:
                break
    if len(chosen) != count:
        raise ValueError(f"Only {len(chosen)} regions have eligible source-bound blank templates")
    return chosen


def payload(contract, scenario):
    data = deepcopy(contract["defaults"])
    if scenario == "blank":
        return data
    for field in contract["fields"]:
        key = field["key"]
        if field["type"] == "copies":
            data[key] = "1"
        elif field["type"] == "text_list":
            limit = min(field.get("maxItems", 1), 3 if scenario == "long" else 1)
            data[key] = ["本条为虚构验收测试内容"] * limit
        elif field["type"] == "object_list":
            item = {}
            for child in field["fields"]:
                item[child["key"]] = (child["choices"][0] if child.get("choices")
                                      else "原件" if child["key"] == "originalType"
                                      else "1" if child["key"] in {"pageCount", "itemCount"}
                                      else "虚构测试材料")
            data[key] = [deepcopy(item) for _ in range(
                min(field.get("maxItems", 1), 12 if scenario == "long" else 2))]
        elif key in {"factsReason", "facts"}:
            length = min(field.get("maxLength", 300) // 2, 800 if scenario == "long" else 30)
            layout = contract["policy"].get("layout_limits", {}).get("fields", {}).get(key, {})
            if layout.get("max_lines"):
                capacity = layout.get("first_width", 0) + layout.get("later_width", 0) * (layout["max_lines"] - 1)
                if capacity:
                    length = min(length, int(capacity * .35))
            data[key] = ("本段仅用于虚构文书验收测试。" * 80)[:length]
        elif key == "applicantName":
            data[key] = "验收测试人"
        elif key == "respondentName":
            data[key] = "虚构验收测试单位"
        elif field.get("format") == "iso-date" or key in {"birthDate", "applicationDate", "submitDate"}:
            data[key] = "2000-01-01"
        elif field.get("choices"):
            data[key] = field["choices"][0]
    return data


def package_digest(body):
    """Ignore ZIP container timestamps, retaining every member's exact bytes."""
    with ZipFile(BytesIO(body)) as package:
        return content_digest({name: sha256(package.read(name)).hexdigest()
                               for name in sorted(package.namelist())})


def review_ooxml(body, destination):
    with ZipFile(BytesIO(body)) as package:
        names = package.namelist()
        if len(names) != len(set(names)) or package.testzip() is not None:
            raise ValueError("Invalid generated OOXML package")
        required = {"[Content_Types].xml", "word/document.xml"}
        if not required.issubset(names):
            raise ValueError("Generated document has no Word body")
        xml_members = [name for name in names if name.endswith((".xml", ".rels"))]
        for name in xml_members:
            ElementTree.fromstring(package.read(name))
        document = package.read("word/document.xml")
        result = {"status": "PASS", "review_type": "OOXML_STRUCTURE_ONLY",
                  "visual_approval": False, "synthetic_test_only": True,
                  "output_sha256": sha256(body).hexdigest(),
                  "package_sha256": package_digest(body), "members": len(names),
                  "xml_members": len(xml_members), "body_bytes": len(document)}
    save_json(destination, result)
    return result


def checked_response(response, status=200):
    if response.status_code != status:
        raise ValueError(f"HTTP {response.status_code}: {response.text[:280]}")
    return response


def run_mode(client, guides, mode, work, renderer):
    cache = AcceptanceStore(work / "qa.sqlite", root=ROOT)
    results = []
    started = perf_counter()
    for guide in guides:
        region_start = perf_counter()
        row = {"region_code": guide["region_code"], "province": guide["province"],
               "city": guide["city"], "district": guide["district"],
               "source_url": guide["source_url"], "source_id": guide["source_id"],
               "source_scope": "EXISTING_SEALED_OFFICIAL_SOURCE", "documents": [], "errors": []}
        params = {key: guide[key] for key in ("province", "city", "district")}
        try:
            actual = checked_response(client.get("/api/regional-guides/lookup", params=params)).json()
            if actual["source_id"] != guide["source_id"]:
                raise ValueError("Lookup returned another regional source")
            for template in eligible_templates(guide):
                for kind in template["document_types"]:
                    query = {**params, "source_id": guide["source_id"], "version": guide["version"],
                             "template_id": template["id"], "kind": kind}
                    contract_start = perf_counter()
                    contract = checked_response(client.get(
                        "/api/regional-guides/form-contract", params=query)).json()
                    contract_seconds = perf_counter() - contract_start
                    original = checked_response(client.get(
                        "/api/regional-guides/templates/" + template["id"], params=query)).content
                    if sha256(original).hexdigest() != template["sha256"]:
                        raise ValueError("Native download differs from own original")
                    stale = client.get("/api/regional-guides/form-contract", params={**query, "version": 999999})
                    if stale.status_code != 409:
                        raise ValueError("Stale regional source was accepted")
                    for scenario in ("blank", "normal", "long"):
                        sample_start = perf_counter()
                        request = {**query, "mode": "blank", "contract_id": contract["contract_id"],
                                   "data": payload(contract, scenario)}
                        generated = checked_response(client.post("/api/regional-guides/generate", json=request))
                        if (generated.headers.get("x-guide-source-id") != guide["source_id"]
                                or generated.headers.get("x-form-contract-id") != contract["contract_id"]):
                            raise ValueError("Generated download lost its own regional contract")
                        body = generated.content
                        key = content_digest({"original": template["sha256"], "scenario": scenario,
                                              "result": sha256(body).hexdigest(), "shape": {
                                                  k: contract[k] for k in ("fields", "defaults", "policy")}})
                        artifact = work / "review" / (key + ".json")
                        docx = work / "documents" / (sha256(body).hexdigest() + ".docx")
                        save_document(docx, body)

                        def reviewer(value):
                            reviewed = review_ooxml(value, artifact)
                            return {"status": reviewed["status"], "review_type": reviewed["review_type"],
                                    "visual_approval": False, "artifacts": [{
                                        "path": artifact.relative_to(ROOT).as_posix(),
                                        "sha256": sha256(artifact.read_bytes()).hexdigest()}, {
                                        "path": docx.relative_to(ROOT).as_posix(),
                                        "sha256": sha256(body).hexdigest()}]}

                        review_start = perf_counter()
                        if mode == "baseline":
                            reviewer(body)
                            acceptance = {"reused": False, "key": key}
                        else:
                            acceptance = cache.review(guide=guide, template=template, contract=contract,
                                output=body, renderer_sha256=renderer, reviewer_version="ooxml-v1",
                                scenario=scenario, reviewer=reviewer)
                        row["documents"].append({
                            "template_id": template["id"], "kind": kind, "scenario": scenario,
                            "contract_id": contract["contract_id"], "original_sha256": template["sha256"],
                            "output_sha256": sha256(body).hexdigest(), "package_sha256": package_digest(body),
                            "output": docx.relative_to(ROOT).as_posix(), "review_key": acceptance["key"],
                            "reused": acceptance["reused"], "contract_seconds": contract_seconds,
                            "review_seconds": perf_counter() - review_start,
                            "total_seconds": perf_counter() - sample_start,
                        })
        except Exception as exc:
            row["errors"].append({"type": type(exc).__name__, "message": str(exc)})
        row["seconds"] = perf_counter() - region_start
        row["state"] = "PASS" if not row["errors"] else "FAIL"
        results.append(row)
        save_json(work / (mode + "-results.json"), results)
        print(json.dumps({"mode": mode, "completed": len(results), "region": guide["region_code"],
                          "state": row["state"], "seconds": round(row["seconds"], 3)}, ensure_ascii=False), flush=True)
    durations = [item["seconds"] for item in results]
    documents = [document for row in results for document in row["documents"]]
    return {"mode": mode, "seconds": perf_counter() - started, "regions": len(results),
            "passed": sum(row["state"] == "PASS" for row in results),
            "failed": sum(row["state"] == "FAIL" for row in results),
            "documents": len(documents), "reused_reviews": sum(item["reused"] for item in documents),
            "review_seconds": sum(item["review_seconds"] for item in documents),
            "median_region_seconds": statistics.median(durations),
            "p95_region_seconds": sorted(durations)[int((len(durations) - 1) * .95)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regions", type=int, default=50)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    work = arguments.output.resolve()
    if not work.is_relative_to(ROOT / ".runtime") or work.exists():
        raise ValueError("Choose a fresh directory under this isolated worktree's .runtime")
    work.mkdir(parents=True)
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routes import regional_guides as routes

    snapshot_bytes = (ROOT / "data/public-regions/guides.json").read_bytes()
    snapshot = json.loads(snapshot_bytes)
    chosen = choose_regions(snapshot, arguments.regions)
    store = RegionalStore(work / "guides.sqlite")
    guides = [store.put_guide(guide) for guide in chosen]
    manifest = template_families([{**guide, "templates": eligible_templates(guide)} for guide in guides], ROOT)
    save_json(work / "TEMPLATE-FAMILIES.json", manifest)
    code_files = [*sorted((ROOT / "backend").rglob("*.py")),
                  *sorted((ROOT / "WenShu").rglob("*.py")), Path(__file__)]
    renderer = content_digest({path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
                               for path in code_files})
    save_json(work / "SELECTED-REGIONS.json", [{key: guide[key] for key in (
        "province", "city", "district", "region_code", "source_url", "source_id", "version")}
        for guide in guides])
    with ExitStack() as stack:
        stack.enter_context(patch.object(routes, "ROOT", ROOT))
        stack.enter_context(patch.object(routes, "store", return_value=store))
        app = FastAPI()
        app.include_router(routes.router, prefix="/api/regional-guides")
        client = stack.enter_context(TestClient(app))
        baseline = run_mode(client, guides, "baseline", work / "baseline", renderer)
        cold = run_mode(client, guides, "cold", work / "reuse", renderer)
        warm = run_mode(client, guides, "warm", work / "reuse", renderer)
    report = {"state": "PASS" if all(row["failed"] == 0 for row in (baseline, cold, warm)) else "FAIL",
              "completed_at": datetime.now(timezone.utc).isoformat(), "regions": len(guides),
              "cohort": "EXISTING_OFFICIAL_ORIGINALS", "new_coverage_regions": 0,
              "includes_first_source_discovery": False, "includes_visual_rendering": False,
              "source_snapshot_sha256": sha256(snapshot_bytes).hexdigest(),
              "renderer_sha256": renderer, "provinces": dict(Counter(row["province"] for row in guides)),
              "template_families": len(manifest["families"]), "invalid_bindings": len(manifest["invalid"]),
              "modes": [baseline, cold, warm]}
    save_json(work / "RESULT.json", report)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report["state"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
