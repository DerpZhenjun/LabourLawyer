"""Bounded process-local HQ semantic Word cache; file bytes are never cached as proof.

Every call validates all 27 source + 71 Word bytes and reparse-free paths.
Only the expensive, immutable semantic Word result is memoized. Authority receipts,
current store guides/versions and request/user data are outside this module.
"""
from collections import OrderedDict
from functools import wraps
from hashlib import sha256
from pathlib import Path, PurePosixPath
from threading import RLock
import inspect, json, stat, sys, types

_MODULES=('regional_fujian_huian_quangang_nov1','hq_phase_proof','hq_word_mechanics','regional_huian_quangang_request','hq_word_semantic_cache')
_MAX_ENTRIES=4
_MAX_BYTES=1024*1024
_MAX_ENTRY_BYTES=256*1024
_LOCK=RLock()
_CACHE=OrderedDict()
_HITS=_MISSES=_HASH_READS=0

def _need(ok):
    if not ok: raise ValueError('Own HQ semantic cache binding differs')

def _read(root, name, guarded=None):
    _need(type(name) is str and name and '\\' not in name and ':' not in name)
    rel=PurePosixPath(name)
    _need(not rel.is_absolute() and rel.as_posix()==name and all(p not in ('.','..') and not p.startswith('.') for p in rel.parts))
    path=root/name
    # Deduplicate ancestors only within this one snapshot, never across calls.
    guarded=set() if guarded is None else guarded
    for p in [path,*path.parents]:
        if p in guarded: continue
        info=p.lstat()
        _need(not stat.S_ISLNK(info.st_mode) and not p.is_symlink() and not getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0))
        guarded.add(p)
    _need(path.is_file() and path.resolve()==path and path.is_relative_to(root))
    return path.read_bytes()

def _root(root):
    _need(isinstance(root,(str,Path)) and str(root).strip())
    path=Path(root).absolute()
    for p in [path,*path.parents]:
        info=p.lstat()
        _need(not p.is_symlink() and not getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0))
    _need(path.is_dir() and path.resolve()==path)
    return path

def _code(code):
    # Code objects are immutable. Explicit fields avoid marshal's runtime string
    # interning state changing its serialization after the first invocation.
    return (id(code),code.co_code.hex(),code.co_exceptiontable.hex(),
            tuple(_code(x) if isinstance(x,types.CodeType) else repr(x) for x in code.co_consts),
            code.co_names,code.co_varnames,code.co_freevars,code.co_cellvars,
            code.co_argcount,code.co_posonlyargcount,code.co_kwonlyargcount,code.co_flags)

def _function(value):
    value=getattr(value,'__func__',value)
    code=getattr(value,'__code__',None)
    closure=getattr(value,'__closure__',None)
    return (id(value), sha256(repr(_code(code)).encode('utf8')).hexdigest() if code is not None else repr(value),
            repr(getattr(value,'__defaults__',None)),repr(getattr(value,'__kwdefaults__',None)),
            tuple((id(c.cell_contents),repr(c.cell_contents)) for c in closure) if closure else ())

def _schema(value):
    if isinstance(value,dict): return tuple((repr(k),_schema(v)) for k,v in sorted(value.items(),key=lambda p:repr(p[0])))
    if isinstance(value,(tuple,list)): return tuple(_schema(v) for v in value)
    if inspect.isclass(value): return (id(value),value.__module__,value.__qualname__)
    if inspect.isfunction(value) or inspect.ismethod(value) or inspect.isbuiltin(value): return _function(value)
    return repr(value)

def _identity_rows(verify, callbacks):
    # Hash source code AND live functions/constants/model state: neither on-disk
    # edits nor live monkeypatches may reuse a prior semantic result.
    rows=[('verifier',_function(verify))];guarded=set()
    for name in _MODULES:
        module=sys.modules[name]
        source=Path(module.__file__).absolute()
        rows.append((name,'file',sha256(_read(source.parent,source.name,guarded)).hexdigest()))
        for key,value in sorted(vars(module).items()):
            if key.startswith('__') or key in ('STAGE_SHA256','PUBLICATION_SHA256','_CACHE','_LOCK','_HITS','_MISSES','_HASH_READS'): continue
            if inspect.isfunction(value) or inspect.isbuiltin(value): rows.append((name,key,_function(value)))
            elif inspect.isclass(value):
                rows.append((name,key,id(value)))
                if hasattr(value,'model_validate'): rows.append((name,key,'base_methods',_function(value.model_validate),_function(value.model_dump)))
                if hasattr(value,'model_json_schema') and value.__name__!='BaseModel':
                    rows.append((name,key,'model',json.dumps(value.model_json_schema(),sort_keys=True),
                      _schema(value.__pydantic_core_schema__),id(value.__pydantic_validator__),id(value.__pydantic_serializer__),
                      _function(value.model_validate),_function(value.model_dump)))
            elif isinstance(value,types.ModuleType): rows.append((name,key,'module',id(value),value.__name__))
            elif type(value) in (str,int,float,bool,tuple,list,dict,type(None)):
                rows.append((name,key,repr(value)))
    for key,value in sorted(callbacks.items()): rows.append((key,_function(value)))
    from lxml import etree
    from zipfile import ZipFile
    import copy
    rows.append(('dependencies',*[_function(x) for x in (json.loads,json.dumps,etree.fromstring,etree.XMLParser,
                    ZipFile.__init__,ZipFile.read,ZipFile.open,ZipFile.namelist,ZipFile.testzip,Path.read_bytes,Path.resolve,Path.lstat,
                    Path.absolute,Path.is_file,Path.is_dir,Path.is_relative_to,Path.is_symlink,PurePosixPath.is_absolute,PurePosixPath.as_posix,copy.deepcopy)]))
    return rows

def _identity(verify,callbacks):
    return sha256(repr(_identity_rows(verify,callbacks)).encode('utf8')).hexdigest()

def _snapshot(root,pin,review,source_files):
    global _HASH_READS
    from hq_phase_proof import QA,strict_json
    _need(type(pin) is str and len(pin)==64 and type(review) is str and len(review)==64)
    names=source_files(root) # full original own-source verification, never memoized
    _need(type(names) is list and len(names)==27 and len(set(names))==27)
    manifest_name=QA+'/WORD-MANIFEST.json';guarded=set()
    raw=_read(root,manifest_name,guarded);_HASH_READS+=1
    _need(sha256(raw).hexdigest()==pin)
    manifest=strict_json(raw)
    _need(manifest['root_original_review_sha256']==review and type(manifest['files']) is dict and len(manifest['files'])==70)
    rows=[]
    for name in sorted(names):
        body=_read(root,name,guarded);_HASH_READS+=1;rows.append((name,len(body),sha256(body).hexdigest()))
    rows.append((manifest_name,len(raw),sha256(raw).hexdigest()))
    for name,p in sorted(manifest['files'].items()):
        path=QA+'/'+name;body=_read(root,path,guarded);_HASH_READS+=1;digest=sha256(body).hexdigest()
        _need(type(p['bytes']) is int and len(body)==p['bytes'] and digest==p['sha256'])
        rows.append((path,len(body),digest))
    _need(len(rows)==98 and len({r[0] for r in rows})==98)
    return sha256(repr(rows).encode('utf8')).hexdigest()

def clear():
    global _HITS,_MISSES,_HASH_READS
    with _LOCK:
        _CACHE.clear();_HITS=_MISSES=_HASH_READS=0

def info():
    with _LOCK:
        return {'entries':len(_CACHE),'bytes':sum(len(v) for v in _CACHE.values()),'hits':_HITS,'misses':_MISSES,'fresh_artifact_hash_reads':_HASH_READS,
                'max_entries':_MAX_ENTRIES,'max_bytes':_MAX_BYTES,'max_entry_bytes':_MAX_ENTRY_BYTES}

def wrap_semantic_word(verify):
    @wraps(verify)
    def checked(root,pin,root_review_sha,**callbacks):
        global _HITS,_MISSES
        # Serialize verification and insertion. Waiting callers re-snapshot only
        # AFTER obtaining the lock; failures never enter the cache.
        with _LOCK:
            base=_root(root)
            identity=_identity(verify,callbacks)
            snapshot=_snapshot(base,pin,root_review_sha,callbacks['source_files'])
            key=(str(base),pin,root_review_sha,identity,snapshot)
            if key in _CACHE:
                _need(_identity(verify,callbacks)==identity)
                body=_CACHE.pop(key);_CACHE[key]=body;_HITS+=1
                return json.loads(body) # independent mutable result for each caller
            _MISSES+=1
            result=verify(base,pin,root_review_sha,**callbacks)
            _need(_identity(verify,callbacks)==identity and _snapshot(base,pin,root_review_sha,callbacks['source_files'])==snapshot)
            body=json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')
            if len(body)<=_MAX_ENTRY_BYTES:
                _CACHE[key]=body
                while len(_CACHE)>_MAX_ENTRIES or sum(map(len,_CACHE.values()))>_MAX_BYTES: _CACHE.popitem(last=False)
            return json.loads(body)
    return checked
