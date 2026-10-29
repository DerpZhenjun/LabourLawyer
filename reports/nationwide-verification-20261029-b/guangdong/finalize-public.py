"""Build bounded discovery records and hash an explicit, public-only allowlist.

No network, browser, Word, databases, candidate import or product configuration.
Run after human/agent visual review; never converts discovery into a verified guide.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAMP = datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def source(folder, purpose):
    path = HERE / folder / "public-source.json"
    value = read(path)
    return {"capture": folder, "url": value["url"], "captured_at": value["captured_at"],
            "sha256": sha(path), "purpose": purpose}


common = {
    "record_type": "locality_discovery_only",
    "checked_at": STAMP,
    "browser": {"tool": "Agent Browser", "version": "0.38.2", "session": "gd-oct29b"},
    "target_service": "劳动人事争议仲裁申请",
    "guide_status": "not_found_in_checked_sources",
    "verified_guide": False,
    "service_code": None,
    "current_materials": {"status": "unverified", "items": None},
    "current_handling_modes": {"status": "unverified", "items": None},
    "current_time_limit": {"status": "unverified", "value": None},
    "current_fee": {"status": "unverified", "value": None},
    "current_online_auth_requirement": "unverified",
    "candidate_import_allowed": False,
    "generation": {"status": "not_implemented", "adapter_key": None, "entrypoint": None},
    "limits": [
        "未找到仅限本批已检查入口，不代表官方未提供或当地没有该服务。",
        "全站搜索展示10条相关结果，无目标条目不证明完整目录中不存在。",
        "省级同名申请仲裁审查确认、计量仲裁、劳动监察均不能替代本区普通仲裁申请指南。",
        "部门办事窗口不能自动认定为劳动仲裁收件窗口。",
        "未进入在线申报、实名认证或验证码；未保存cookies、SSO或raw HAR。",
    ],
}

for locality, code, name, org in [
    ("chancheng", "440604", "禅城区", "699751106"),
    ("nanhai", "440605", "南海区", "734134585"),
]:
    own_branch = "own-branch-empty-response" if locality == "chancheng" else "own-branch"
    identity_capture = "rsj" if locality == "chancheng" else "rsj-initial"
    identity = read(HERE / locality / identity_capture / "public-source.json")
    record = {**common,
        "region": {"province": "广东省", "city": "佛山市", "district": name, "code": code},
        "authority": {"name": f"佛山市{name}人力资源和社会保障局", "org_code": org,
                      "org_code_kind": "official_portal_branch_orgCode_not_service_code",
                      "branch_url": f"https://www.gdzwfw.gov.cn/portal/v2/branch-hall?orgCode={org}",
                      "identity_status": "verified_official_department_link_and_branch_heading",
                      "own_website_url": identity["url"], "own_website_captured_at": identity["captured_at"],
                      "own_website_capture_sha256": sha(HERE / locality / identity_capture / "public-source.json")},
        "checked_sources": [
            source(f"{locality}/{own_branch}", "各区官网人社部门真实链接到本区办事大厅，核对机关名称"),
            source(f"{locality}/branch-search-arbitration", "本区部门大厅原生搜索仲裁，0事项仅为本次筛选结果"),
            source(f"{locality}/global-search-own-region-loaded", "原生区域选择本区，记录省级同名结果的适用地区"),
            source(f"{locality}/global-search-own-level", "原生勾选仅显示本级，目标仲裁申请未在展示10结果内定位"),
        ],
        "template_status": "historical_source" if locality == "chancheng" else "not_found_in_checked_sources",
        "current_template_applicability": "unverified",
        "original_attachment_count": 6 if locality == "chancheng" else 0,
    }
    if locality == "chancheng":
        record["checked_sources"] += [
            source("chancheng/download-directory", "人社下载中心第一页"),
            source("chancheng/download-directory-page2", "33条两页目录的第二页，发现历史仲裁附件通知"),
            source("chancheng/own-material-notice", "本区历史附件发布正文及六个真实DOC链接"),
            source("chancheng/agencies", "2026-03-25本区仲裁机构联系方式表，仅作为机构信息"),
        ]
        record["historical_source"] = {"publication_date": "2015-02-11 14:33:51",
            "title": "仲裁申请书、保证书及授权委托书（含样表）", "classification_review": "content-review.json",
            "source_url": "https://www.chancheng.gov.cn/rsj/zxfw/xzzx/content/post_723175.html",
            "current_validity_explicitly_confirmed": False,
            "note": "公开原件保留历史样式；授权委托书预印二○一一年。未认定为现行要求，未据此制作可生成候选。"}
        record["capture_label_note"] = "own-branch-empty-response为初次导航错误后的目录名，实际保存的是随后加载成功的本区249事项大厅，不能引用目录名声称官方故障。"
    else:
        record["additional_checked_sources"] = [
            {"url": "https://www.nanhai.gov.cn/fsnhrsj/gkmlpt/index", "observation": "公开目录有案件送达公告，未将案件公告当作指南或空白模板；相关原始页面不列入公开白名单。"},
            {"url": "https://www.nanhai.gov.cn/fsnhrsj/gkmlpt/search?keywords=%E4%BB%B2%E8%A3%81&order=0&position=title",
             "observation": "原生检索页面仅见搜索标题，无结果行或总数，等待后仍如此；不解释成零项。"},
        ]
    write(HERE / locality / "discovery.json", record)

manifest = read(HERE / "chancheng/downloads/manifest.json")
notes = [
    ["blank_application", 3, "空白当事人（含第三人）、四项请求、事实理由及签名日期副本份数；原件保留三页。"],
    ["sample_application", 3, "红色张三和X占位及请求、事实理由填写指引；样例不作为空白生成模板。"],
    ["blank_declaration", 1, "保证书含禅城区劳动人事争议仲裁委员会及联系地址真实性等声明，待填签名联系信息。"],
    ["sample_declaration", 1, "保证书样式含红色张三、X占位地址电话及邮编528000。"],
    ["blank_authorization", 1, "空白授权委托书含两名代理人，预印日期二○一一年，历史适用性未知。"],
    ["sample_authorization", 1, "红色张三、李四和X占位授权样例。"],
]
review = []
for index, (item, (classification, pages, observation)) in enumerate(zip(manifest, notes), 1):
    original = ROOT / item["file"]
    assert sha(original) == item["sha256"]
    images = sorted((HERE / "chancheng/qa/originals").glob(f"{index:02}-*.png"))
    assert len(images) == pages
    review.append({"file": item["file"], "original_name": item["original_name"],
        "sha256": sha(original), "classification": classification, "historical_publication_date": "2015-02-11",
        "current_applicability": "unverified", "visual_qa": "all_pages_viewed",
        "page_count": pages, "observation": observation,
        "pdf": f"chancheng/qa/originals/{index:02}.pdf",
        "page_images": [p.relative_to(HERE).as_posix() for p in images]})
write(HERE / "chancheng/content-review.json", {
    "reviewed_at": STAMP, "note": "此复核追加于原始下载清单；原清单下载时visual_qa=pending保留不覆盖。",
    "files": review, "total_original_files": 6, "total_pages_viewed": 10,
})

isolation = read(HERE / "qa/original-tasks-word-instance-isolation.json")
assert isolation["completed"] == 6 and isolation["new_pid_verified"]
assert all(i["matches_new_instance"] for i in isolation["document_window_pid_checks"])
assert isolation["after"] == isolation["before"]
write(HERE / "qa/public-isolation-summary.json", {
    "method": isolation["method"], "completed": 6, "new_pid_verified": True,
    "all_six_document_window_pids_matched_new_instance": True,
    "macro_security": 3, "link_updates_disabled": True,
    "before_word_process_count": len(isolation["before"]), "after_word_process_count": len(isolation["after"]),
    "own_instance_exited": isolation["new_instance_pid"] not in isolation["after"],
    "original_files_sha256_unchanged": True,
    "raw_proof_excluded": "原始本机路径/PID操作回执不列入公开包，仅保留此摘要。",
})

# Deliberate finite list: no recursive-public-all rule and no raw case-notice pages.
capture_folders = [
    "chancheng/own-material-notice", "chancheng/agencies", "chancheng/download-directory",
    "chancheng/download-directory-page2", "chancheng/own-branch-empty-response",
    "chancheng/branch-search-arbitration", "chancheng/global-search-own-region-loaded", "chancheng/global-search-own-level",
    "nanhai/own-branch", "nanhai/branch-search-arbitration",
    "nanhai/global-search-own-region-loaded", "nanhai/global-search-own-level",
]
paths = [HERE / folder / filename for folder in capture_folders
         for filename in ["public-source.json", "page.txt", "page.png", "provenance.json"]]
paths += [ROOT / item["file"] for item in manifest]
paths += list((HERE / "chancheng/qa/originals").glob("*.pdf"))
paths += list((HERE / "chancheng/qa/originals").glob("*.png"))
paths += [HERE / p for p in ["chancheng/downloads/manifest.json", "chancheng/content-review.json",
          "chancheng/discovery.json", "nanhai/discovery.json", "qa/public-isolation-summary.json",
          "FINAL-REPORT.md", "finalize-public.py", "render-isolated.ps1"]]
paths += [ROOT / "scripts/collect-guangdong-oct29b.py"]
for path in paths:
    assert path.is_file(), path
    # Source code contains the detector literals themselves; scan captured data.
    if path.suffix in {".json", ".txt", ".md"}:
        content = path.read_text(encoding="utf8")
        assert not any(marker in content.lower() for marker in ["set-cookie:", "bearer eyj", '"cookies":', '"accesstoken":']), path
for folder in capture_folders:
    provenance = read(HERE / folder / "provenance.json")
    for filename, expected in provenance["sha256"].items():
        assert sha(HERE / folder / filename) == expected
records = [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(set(paths))]
write(HERE / "PUBLIC-WHITELIST.json", {
    "created_at": STAMP, "scope": "只允许精确清单文件；未列出项不得自动打包或提交。",
    "excluded": ["cookies/SSO/rawHAR/auth state（本批未采集）", "目录和首页中无关案件公告的原始捕获",
                 "初始加载中或失败诊断捕获", "原始本机Word操作任务和PID回执"],
    "files": records, "file_count": len(records),
})
print(json.dumps({"public_files": len(records), "originals_sha_passed": 6,
                  "original_pages_reviewed": 10, "verified_guides_added": 0,
                  "generation_adapters_added": 0, "status": "discovery_records_complete"}))
