"""Dispatch to audited official template field bindings."""
from pathlib import Path
from WenShu.exact_template_fill import fill_application, fill_evidence


def generate_application(data: dict, template_docx: str | Path):
    folder = Path(template_docx).parent.name
    if folder == 'ShanXiSheng':
        from WenShu.Shanxi.application import fill_application as fill_shanxi
        return fill_shanxi(data,template_docx)
    if folder == 'GuangDongSheng':
        from WenShu.Guangdong.LAdocx import generate_LAdocx
        return generate_LAdocx(data, template_docx)
    if folder == 'ZheJiangSheng':
        from WenShu.Zhejiang.LAdocx import generate_LAdocx
        return generate_LAdocx(data, template_docx)
    return fill_application(data, template_docx)


def generate_evidence(data: dict, template_docx: str | Path):
    return fill_evidence(data, template_docx)
