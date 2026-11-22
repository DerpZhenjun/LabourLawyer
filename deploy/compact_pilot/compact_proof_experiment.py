"""Private experiment for exact scope and deduplicated-original checks.

The caller's independently pinned digest is a precondition. This module does
not advertise or substitute for provider proof, release authorisation, or
signature verification on the public distribution channel.
"""
from hashlib import sha256
from pathlib import Path
import json
import re

SCHEMA='PILOT_QA_EXPERIMENT_ONLY'
FIELDS={'region_code','kind','source_id','template_id','version','original_sha256','contract_id'}
HEX64=re.compile('[0-9a-f]{64}')


def checked_row(row):
    if not isinstance(row,dict) or row.keys()!=FIELDS:
        raise ValueError('Unexpected proof row schema')
    if (any(not isinstance(row[k],str) for k in FIELDS-{'version'})
            or type(row['version']) is not int or row['version']<1):
        raise ValueError('Invalid proof row fields')
    if (not re.fullmatch('[0-9]{6}',row['region_code'])
            or not re.fullmatch('[0-9a-f]{24}',row['source_id'])
            or not re.fullmatch('[A-Za-z0-9_-]{1,96}(?::[A-Za-z0-9_-]{1,31})?',row['template_id'])
            or row['kind'] not in {'application','evidence'}
            or not HEX64.fullmatch(row['original_sha256'])
            or not HEX64.fullmatch(row['contract_id'])):
        raise ValueError('Invalid scope binding')
    return row['region_code'],row['kind']


def object_without_duplicates(pairs):
    obj={}
    for name,value in pairs:
        if name in obj:
            raise ValueError('Duplicate capsule field')
        obj[name]=value
    return obj


class Capsule:
    def __init__(self,data,expected_sha256):
        if not isinstance(expected_sha256,str) or not HEX64.fullmatch(expected_sha256):
            raise ValueError('The expected digest must be pinned independently')
        if not isinstance(data,bytes) or sha256(data).hexdigest()!=expected_sha256:
            raise ValueError('Unexpected capsule digest')
        obj=json.loads(data,object_pairs_hook=object_without_duplicates)
        if (not isinstance(obj,dict) or set(obj)!={'schema','rows'} or obj['schema']!=SCHEMA
                or not isinstance(obj['rows'],list) or not obj['rows']):
            raise ValueError('Unexpected capsule schema')
        self.rows={}
        for row in obj['rows']:
            key=checked_row(row)
            if key in self.rows:
                raise ValueError('Duplicate locality and kind')
            self.rows[key]=row

    def resolve(self,root,request):
        key=checked_row(request)
        if self.rows.get(key)!=request:
            raise ValueError('Request does not match the pinned binding')
        root=Path(root).resolve()
        path=root/(request['original_sha256']+'.docx')
        if path.is_symlink() or path.resolve().parent!=root or not path.is_file():
            raise ValueError('Missing or out-of-scope original')
        body=path.read_bytes()
        if sha256(body).hexdigest()!=request['original_sha256']:
            raise ValueError('Original hash differs from the binding')
        return body
