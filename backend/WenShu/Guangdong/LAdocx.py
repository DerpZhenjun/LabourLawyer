"""Fill the official four-page Guangdong worker arbitration application."""

from __future__ import annotations

from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE
from WenShu.template_fill import fill_date_runs, replace_text, set_cell_text, set_paragraph_text


def _write_cell(cell, text: str, *, size: int = 11, align=WD_ALIGN_PARAGRAPH.LEFT):
    set_cell_text(cell, text)


def _write_if(cell, value, *, size: int = 11, align=WD_ALIGN_PARAGRAPH.LEFT):
    if str(value or "").strip():
        _write_cell(cell, value, size=size, align=align)


def _split_text(value: str, width: int = 32, limit: int = 22) -> list[str]:
    text = str(value or "").replace("\r", "").strip()
    lines: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        while len(paragraph) > width:
            cut = width
            punctuation = max(paragraph.rfind(mark, max(0, width - 10), width + 1) for mark in "，。；！？")
            if punctuation >= max(0, width - 10):
                cut = punctuation + 1
            while 1 < cut < len(paragraph) and paragraph[cut - 1].isascii() and paragraph[cut - 1].isalnum() and paragraph[cut].isascii() and paragraph[cut].isalnum():
                cut -= 1
            lines.append(paragraph[:cut])
            paragraph = paragraph[cut:]
        if paragraph:
            lines.append(paragraph)
    if len(lines) > limit:
        raise ValueError("事情经过内容过长，请压缩到约900字以内")
    return lines


def generate_LAdocx(data: dict, template_docx: str | Path):
    doc = Document(str(template_docx))
    if not data.get('requests') and not any(str(data.get(k,'')).strip() for k in ('applicantName','respondentName','factsReason','applicationDate')):
        return doc

    # Page 1: parties and filing details.
    if data.get("committeeName"):
        committee = str(data["committeeName"])
        suffix = "劳动人事争议仲裁委员会"
        if committee.endswith(suffix):
            replace_text(doc.paragraphs[3], "         ", committee[:-len(suffix)])
        else:
            set_paragraph_text(doc.paragraphs[3], f"致：{committee}")
    parties = doc.tables[0]
    _write_if(parties.rows[0].cells[1], data.get("applicantName", ""))
    _write_if(parties.rows[0].cells[4], data.get("gender", ""), align=WD_ALIGN_PARAGRAPH.CENTER)
    fill_date_runs(parties.rows[0].cells[7].paragraphs[0], data.get("birthDate", ""))
    _write_if(parties.rows[1].cells[1], data.get("idNumber", ""))
    _write_if(parties.rows[1].cells[7], data.get("phone", ""), align=WD_ALIGN_PARAGRAPH.CENTER)
    _write_if(parties.rows[2].cells[1], data.get("idAddress", ""))
    applicant_mailing = data.get("applicantMailingAddress") or data.get("idAddress", "")
    if applicant_mailing:
        paragraph = parties.rows[3].cells[1].paragraphs[2]
        replace_text(paragraph, "□其他：", f"☑其他：{applicant_mailing}")

    _write_if(parties.rows[4].cells[1], data.get("respondentName", ""))
    _write_if(parties.rows[5].cells[1], data.get("registeredAddress", ""))
    respondent_mailing = data.get("mailingAddress") or data.get("registeredAddress", "")
    if respondent_mailing:
        cell = parties.rows[6].cells[1]
        if respondent_mailing == data.get("registeredAddress"):
            replace_text(cell.paragraphs[0], "□", "☑")
        else:
            replace_text(cell.paragraphs[2], "□其他：", f"☑其他：{respondent_mailing}")
    _write_if(parties.rows[7].cells[2], data.get("legalRepName", ""), align=WD_ALIGN_PARAGRAPH.CENTER)
    _write_if(parties.rows[8].cells[2], data.get("legalRepPosition", ""), align=WD_ALIGN_PARAGRAPH.CENTER)
    contact_name = data.get("companyContact") or data.get("legalRepName", "")
    contact_phone = data.get("companyContactPhone") or data.get("legalRepPhone", "")
    contact = " ".join(part for part in (contact_name, contact_phone) if part)
    _write_if(parties.rows[7].cells[6], contact, align=WD_ALIGN_PARAGRAPH.CENTER)
    # The applicant signs this field by hand after printing.
    fill_date_runs(parties.rows[9].cells[6].paragraphs[0], data.get("applicationDate", ""))

    # Page 2: requests and calculation explanation.
    request_table = doc.tables[1]
    requests = [str(item).strip() for item in data.get("requests", []) if str(item).strip()]
    if len(requests)>3:
        raise ValueError("广东官方模板最多容纳3项请求，请合并相关请求或附续页")
    for index, row_index in enumerate((1, 3, 5)):
        if index < len(requests):
            number = request_table.rows[row_index].cells[0].paragraphs[0]
            if not number.text.strip():
                set_paragraph_text(number, f"{index + 1}、")
            _write_cell(request_table.rows[row_index].cells[2], requests[index])
    calculation_lines=_split_text(data.get("claimCalculation", ""), width=32, limit=8)
    for index, line in enumerate(calculation_lines):
        _write_cell(request_table.rows[16 + index].cells[1], line)
    keep={0,15,*((1,3,5)[i] for i in range(len(requests))),*range(16,16+len(calculation_lines))}
    for index,row in reversed(list(enumerate(request_table.rows))):
        if index not in keep:request_table._tbl.remove(row._tr)

    # Page 3: structured basic facts from the official form.
    facts = doc.tables[2]
    fill_date_runs(facts.rows[1].cells[1].paragraphs[0], data.get("employmentDate", ""))
    _write_if(facts.rows[1].cells[6], data.get("jobTitle", ""), align=WD_ALIGN_PARAGRAPH.CENTER)
    if data.get("signedContract"):
        for paragraph in facts.rows[1].cells[11].paragraphs:
            if data["signedContract"] in paragraph.text:
                replace_text(paragraph, "□", "☑")
    period = facts.rows[2].cells[1].paragraphs[0]
    fill_date_runs(period, data.get("contractStartDate", ""))
    fill_date_runs(period, data.get("contractEndDate", ""), occurrence=1)
    _write_if(facts.rows[3].cells[1], data.get("workAddress", ""))
    if data.get("workSchedule"):
        schedule = str(data["workSchedule"])
        cell = facts.rows[4].cells[1]
        match = re.search(r"每周工作\s*(\d+)\s*天[，,]\s*每天(?:工作)?\s*(\d+)\s*小时", schedule)
        if match:
            replace_text(cell.paragraphs[1], "□每周工作     天，每天工作     小时",
                         f"☑每周工作{match.group(1)}天，每天工作{match.group(2)}小时")
        else:
            replace_text(cell.paragraphs[3], "□其他：", f"☑其他：{schedule}")
    if data.get("attendanceRequired"):
        for paragraph in facts.rows[5].cells[1].paragraphs:
            if data["attendanceRequired"] in paragraph.text:
                replace_text(paragraph, "□", "☑")
    _write_if(facts.rows[5].cells[4], data.get("attendanceMethod", ""), align=WD_ALIGN_PARAGRAPH.CENTER)
    for cell, value in ((facts.rows[5].cells[7], data.get("salaryPaymentMethod")),
                        (facts.rows[5].cells[10], data.get("salaryReceiptRequired"))):
        selected = str(value or "").replace("不需要签收", "不需签收")
        for paragraph in cell.paragraphs:
            if selected and selected in paragraph.text:
                replace_text(paragraph, "□", "☑")
    _write_if(facts.rows[6].cells[1], data.get("startingSalary", ""), align=WD_ALIGN_PARAGRAPH.CENTER)
    _write_if(facts.rows[6].cells[6], data.get("salaryAdjustments", ""))
    if data.get("currentlyEmployed"):
        for paragraph in facts.rows[7].cells[2].paragraphs:
            if data["currentlyEmployed"] in paragraph.text:
                replace_text(paragraph, "□", "☑")
    fill_date_runs(facts.rows[7].cells[8].paragraphs[0], data.get("departureDate", ""))
    _write_if(facts.rows[8].cells[4], data.get("departureReason", ""))
    if data.get("averageMonthlySalary"):
        paragraph = facts.rows[9].cells[8].paragraphs[0]
        paragraph.runs[0].text = str(data["averageMonthlySalary"]) + paragraph.runs[0].text

    # Keep the official ruled cells, trimming only unused writing rows.
    narrative = doc.tables[3]
    lines=_split_text(data.get("factsReason", ""))
    for index, line in enumerate(lines):
        _write_cell(narrative.rows[index + 1].cells[1], line)
    for row in list(narrative.rows)[1+len(lines):]:
        narrative._tbl.remove(row._tr)
    # Fixed row heights in the paper form can clip typed, wrapped values.
    # Retain their minimum height and all fonts, widths and borders.
    for table in doc.tables:
        for row in table.rows:
            if row.height_rule==WD_ROW_HEIGHT_RULE.EXACTLY:
                row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST
    return doc
