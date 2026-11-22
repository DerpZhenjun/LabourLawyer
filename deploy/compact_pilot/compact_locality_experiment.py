"""Read-only locality endpoints for the private compact pilot."""

from fastapi import HTTPException, Query

from compact_catalogue_experiment import digest, labels
from compact_http_experiment import create_test_app
import json


SCOPE_MESSAGE = '仅提供本次试点已核对的 18 个地区。目录行本身不表示当地文书已获核验。'


def create_locality_app(proof, bindings, guides, areas, *, layout_hash=None):
    app = create_test_app(proof, bindings, layout_hash=layout_hash)
    by_locality = {labels(guide): guide for guide in guides}
    prefix = '/api/regional-guides'

    @app.get(prefix + '/lookup')
    def lookup(province: str = Query(max_length=30), city: str = Query(max_length=80),
               district: str = Query(max_length=80), case_scope: str | None = None, xlsx: bool = False):
        if case_scope is not None:
            raise HTTPException(404, '试点尚未提供这一案件类型的指南。')
        locality = (province, city, district)
        if locality in by_locality:
            return by_locality[locality]
        return {
            'province': province, 'city': city, 'district': district, 'source_id': None,
            'templates': [], 'materials': [], 'fields': {}, 'sections': {}, 'channel': {},
            'verification_status': 'unverified', 'message': SCOPE_MESSAGE,
        }

    @app.get(prefix + '/areas')
    def list_areas(province: str = Query(max_length=30), city: str = Query('', max_length=80),
                   xlsx: bool = False):
        level = 4 if city else 3
        items = []
        for row in areas:
            if row['province'] != province or row['level'] != level or (city and row['city'] != city):
                continue
            matched = by_locality.get(labels(row))
            items.append({
                **row, 'region_code': row['code'], 'can_generate': matched is not None,
                'source_id': matched['source_id'] if matched else None,
                'verification_status': matched['verification_status'] if matched else 'unverified',
            })
        return {'items': items, 'scope': SCOPE_MESSAGE, 'directory_is_not_guide_coverage': True}

    @app.get(prefix + '/inventory')
    def inventory():
        fields = ('province', 'city', 'district', 'region_code', 'source_id', 'verification_status')
        return {
            'items': [{**{field: guide[field] for field in fields}, 'can_generate': True} for guide in guides],
            'coverage': [], 'scope': SCOPE_MESSAGE,
        }

    @app.get(prefix + '/versions')
    def versions(province: str = Query(max_length=30), city: str = Query(max_length=80),
                 district: str = Query(max_length=80), case_scope: str | None = None):
        guide = by_locality.get((province, city, district))
        if not guide or case_scope is not None:
            return {'items': []}
        content_hash = digest(json.dumps(guide, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
        return {'items': [{'content_hash': content_hash, 'verified_at': guide['verified_at']}]}

    return app
