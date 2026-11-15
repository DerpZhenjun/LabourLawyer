"""Shared XML operations for header-preserving regional workbooks."""

from re import sub
from unicodedata import category

from lxml import etree


NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def plain_line(value: str) -> str:
    if any(category(char).startswith("C") or category(char) in {"Zl", "Zp"}
           or ord(char) in {0xFFFE, 0xFFFF} for char in value):
        raise ValueError("每个单元格请填写一行文字")
    return value.strip()


def parse_xml(data: bytes):
    return etree.fromstring(data, parser=etree.XMLParser(resolve_entities=False, no_network=True))


def xml_bytes(element) -> bytes:
    return etree.tostring(element, encoding="UTF-8", xml_declaration=True, standalone=True)


def spreadsheet_tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def set_cell(cell, value: str | int) -> None:
    if value == "":
        return
    if isinstance(value, int):
        cell.set("t", "n")
        etree.SubElement(cell, spreadsheet_tag("v")).text = str(value)
    else:
        cell.set("t", "inlineStr")
        axis = etree.SubElement(cell, spreadsheet_tag("is"))
        text = etree.SubElement(axis, spreadsheet_tag("t"))
        # Excel treats _xNNNN_ as an escape even in explicitly textual cells.
        text.text = sub(r"_x[0-9A-Fa-f]{4}_", lambda match: "_x005F_" + match[0][1:], value)


def scrub_metadata(payload: bytes, remove_all: bool) -> bytes:
    root = parse_xml(payload)
    for field in tuple(root):
        if remove_all or etree.QName(field).localname in {"creator", "lastModifiedBy"}:
            root.remove(field)
    return xml_bytes(root)
