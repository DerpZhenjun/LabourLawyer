"""Private QA for a separately labelled official-blank-derived layout."""

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
import json

from lxml import etree

from compact_contract_experiment import LocalContractProof
from compact_proof_experiment import HEX64, checked_row, object_without_duplicates
from regional_workbook_xml import parse_xml, xml_bytes

EDIT_PROPERTIES = {
    'docProps/core.xml': {'creator', 'lastModifiedBy', 'description', 'keywords'},
    'docProps/app.xml': {'Company', 'Manager'},
    'docProps/custom.xml': None,
}


def clean_official_layout(original):
    """Preserve every member except the allowlisted editor properties."""
    output = BytesIO()
    changed = []
    with ZipFile(BytesIO(original)) as source, ZipFile(output, 'w') as target:
        members = source.namelist()
        if (len(members) != len(set(members)) or 'word/document.xml' not in members
                or source.testzip() is not None):
            raise ValueError('Not an intact official DOCX')
        for info in source.infolist():
            name = info.filename
            if (PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
                    or name.startswith(('_xmlsignatures/', 'word/comments', 'word/embeddings/', 'word/activeX/'))
                    or name.lower().endswith('.bin')):
                raise ValueError('An embedded, signed or annotated original requires separate review')
            body = source.read(info)
            if name in EDIT_PROPERTIES:
                root = parse_xml(body)
                keys = EDIT_PROPERTIES[name]
                remove = list(root) if keys is None else [field for field in root if isinstance(field.tag, str)
                                                         and etree.QName(field).localname in keys]
                if remove:
                    for field in remove:
                        root.remove(field)
                    body = xml_bytes(root)
                    changed.append(name)
            target.writestr(info, body)
    return (output.getvalue(), tuple(changed)) if changed else (original, ())


class LayoutBindings:
    def __init__(self, body, expected_pin, originals):
        if not isinstance(expected_pin, str) or not HEX64.fullmatch(expected_pin) or sha256(body).hexdigest() != expected_pin:
            raise ValueError('Unexpected layout manifest digest')
        manifest = json.loads(body, object_pairs_hook=object_without_duplicates)
        if (not isinstance(manifest, dict) or manifest.keys() != {'schema', 'rows'}
                or type(manifest['schema']) is not int or manifest['schema'] != 1
                or not isinstance(manifest['rows'], list)):
            raise ValueError('Unexpected layout manifest')
        self._layout_by_original = {}
        for row in manifest['rows']:
            if not isinstance(row, dict) or row.keys() != {'official_original_sha256', 'sanitized_layout_sha256'}:
                raise ValueError('Unexpected dual SHA binding')
            original, layout = row['official_original_sha256'], row['sanitized_layout_sha256']
            if (not isinstance(original, str) or not isinstance(layout, str)
                    or not HEX64.fullmatch(original) or not HEX64.fullmatch(layout)
                    or original == layout or original in self._layout_by_original):
                raise ValueError('Invalid original-to-layout binding')
            self._layout_by_original[original] = layout
        if (set(self._layout_by_original) != set(originals)
                or len(set(self._layout_by_original.values())) != len(originals)):
            raise ValueError('Unexpected source or layout coverage')

    def resolve(self, root, original):
        layout = self.hash_for(original)
        folder = Path(root).resolve()
        path = folder / (layout + '.docx')
        if path.is_symlink() or not path.is_file() or path.resolve().parent != folder:
            raise ValueError('Missing or unsafe sanitized layout')
        body = path.read_bytes()
        if sha256(body).hexdigest() != layout:
            raise ValueError('Sanitized layout digest differs')
        return body

    def hash_for(self, original):
        layout = self._layout_by_original.get(original)
        if layout is None:
            raise ValueError('Original is outside the approved derivative scope')
        return layout


class SanitizedContractProof(LocalContractProof):
    """Reuse the original authority and contract checks without serving original bytes."""

    def __init__(self, root, capsule_body, capsule_pin, contract_body, contract_pin, layout_body, layout_pin):
        super().__init__(root, capsule_body, capsule_pin, contract_body, contract_pin)
        originals = {row['original_sha256'] for row in self._capsule.rows.values()}
        self._layouts = LayoutBindings(layout_body, layout_pin, originals)

    def read(self, request):
        key = checked_row(request)
        if self._capsule.rows.get(key) != request:
            raise ValueError('Request does not match the pinned official original binding')
        layout = self._layouts.resolve(self._root, request['original_sha256'])
        return deepcopy(self._contracts[key]), layout

    def derivative_sha256(self, original):
        return self._layouts.hash_for(original)
