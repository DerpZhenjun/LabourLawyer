"""Read-only E Zhejiang own-source and exact publication-file checks.
Run from any directory: python path/to/source_checks.py
No network, database, application, document renderer, or model calls.
"""
from pathlib import Path
import hashlib
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
SPECS = {"fuyang": ("330111", "富阳区", 4), "jiande": ("330182", "建德市", 5)}

def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def verify_files(records):
    for r in records:
        p = ROOT / r["path"]
        assert p.is_file() and p.is_relative_to(BASE), r["path"]
        assert p.stat().st_size == r["bytes"] and sha(p) == r["sha256"], r["path"]

def run():
    results = []
    identities = []
    for name, (code, district, expected_materials) in SPECS.items():
        p = BASE / name
        g = read(p / "guide.json")
        raw = read(p / "item-response.json")["data"]["item"]
        search, page = read(p / "search.json"), read(p / "guide-dom.json")
        assert g["region_code"] == raw["jurisCode"] == code
        assert g["city"] == "杭州市" and g["district"] == district
        own = "https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=" + raw["dcode"]
        assert g["source_url"] == page["url"] == own
        assert g["service_code"] == raw["taskCode"] and g["authority"] == raw["qlDept"]
        assert g["raw_business_fields"] == raw and len(raw) == 252
        assert "websiteid=" + code + "000000" in search["url"] and district in search["text"]
        assert g["published"] is False and g["can_generate"] is False and g["candidate_web_qa"] == "NOT_RUN"
        materials = read(p / "materials-dom.json")
        assert len(g["materials"]) == len(raw["materialList"]) == expected_materials
        assert all(m["name"] in materials["text"] and m["source_url"] == own and m["region_code"] == code for m in g["materials"])
        assert [m["raw"] for m in g["materials"]] == raw["materialList"]
        for capture in ["basic-dom", "conditions-dom", "materials-dom", "flow-dom", "faq-dom", "window-dom", "law-dom"]:
            assert read(p / (capture + ".json"))["url"] == own
        boundary = read(p / "online-boundary.json")
        assert boundary["origin"] == "https://user.zjzwfw.gov.cn" and boundary["path"] == "/pc/login"
        assert boundary["login_visible"] and boundary["captcha_visible"] and not boundary["authenticated"] and not boundary["submitted"] and boundary["query_saved"] is False
        assert g["channel"]["entry_check"] == boundary
        records = read(p / "originals.json")
        blanks = [r for r in records if r["official_kind"] == "blank"]
        assert len(blanks) == 2
        for r in records:
            assert r["region_code"] == code and r["source_url"] == own and r["service_code"] == raw["taskCode"] and r["local_inner_code"] == raw["dcode"]
            m = next(x for x in raw["materialList"] if x["impleCode"] == r["material_id"])
            assert r["download_url"] == "https:" + m["blankForm" if r["official_kind"] == "blank" else "sampleForm"]
            assert r["http_status"] == 200 and r["can_generate"] is False and r["native_control_clicked"]
            if r["official_kind"] == "sample":
                assert r["public_distribution"] is False and not r.get("file")
                continue
            f = ROOT / r["file"]
            assert f.is_relative_to(p / "originals" / "blank") and sha(f) == r["sha256"] and f.stat().st_size == r["bytes"]
            assert read(f.with_suffix(".docx.source.json")) == r
            with zipfile.ZipFile(io.BytesIO(f.read_bytes())) as z:
                assert z.testzip() is None
                ET.fromstring(z.read("word/document.xml"))
        assert len([r for r in records if r["official_kind"] == "sample"]) == (1 if name == "jiande" else 0)
        assert not (p / "originals" / "sample").exists()
        for f in p.rglob("*.json"):
            text = f.read_text(encoding="utf-8-sig")
            assert not re.search(r"(?i)(?<![A-Za-z])[A-Za-z]:[\\/]|/Users/|\.runtime|DerpZhenjun|process_id|\"pid\"", text), f.name
            assert not re.search(r"(?i)__ssoSeq__|Bearer |access_token|Set-Cookie|\"cookies\"|[?&](?:sp|goto|ticket|token|signature)=", text), f.name
            assert not re.search(r"(?i)Codex|ChatGPT|OpenAI|agent-browser|node_repl", text), f.name
        manifest = p / "SOURCE-MANIFEST.json"
        if manifest.exists():
            verify_files(read(manifest)["files"])
            white = read(p / "PUBLIC-WHITELIST.json")
            verify_files(white["files"])
            actual = {f.relative_to(ROOT).as_posix() for f in p.rglob("*") if f.is_file() and f.name != "PUBLIC-WHITELIST.json"}
            assert {r["path"] for r in white["files"]} == actual
        identities.append((raw["dcode"], raw["taskCode"]))
        results.append({"region_code": code, "district": district, "status": "PASS", "raw_business_field_count": 252, "material_count": expected_materials, "public_blank_count": 2, "sample_distribution": False, "online_boundary": "login_and_captcha_only", "generation_and_page_publication": "NOT_RUN"})
    assert len(set(identities)) == 2
    white = BASE / "PUBLIC-WHITELIST.json"
    if white.exists():
        verify_files(read(white)["files"])
        actual = {f.relative_to(ROOT).as_posix() for f in BASE.rglob("*") if f.is_file() and f != white}
        assert {r["path"] for r in read(white)["files"]} == actual
    return {"scope": "source-only", "status": "PASS", "localities": results}

if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
