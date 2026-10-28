"""Optional structured terminal telemetry; evidence and job status stay authoritative."""
import json
from contextvars import ContextVar
import os
import threading
import time
from pathlib import Path

ENV = 'LABOURLAWYER_PROGRESS_FILE'
_lock = threading.Lock()
_path = ContextVar('terminal_progress_path', default=None)


def configure(folder):
    folder = Path(folder)
    if not os.environ.get(ENV):
        _path.set(str((folder / 'progress.jsonl').resolve()))
    try:
        folder.mkdir(parents=True,exist_ok=True)
        pointer=folder/'terminal-progress.json'
        with _lock:
            temp=pointer.with_suffix('.tmp')
            temp.write_text(json.dumps({'events':os.environ.get(ENV) or _path.get()},ensure_ascii=False),'utf8')
            temp.replace(pointer)
    except OSError:pass


def province_from(paths):
    # Only infer from an actual province directory; filenames are not names.
    try:
        from province_documents import PROVINCE_DOCUMENTS
    except ImportError:
        from backend.province_documents import PROVINCE_DOCUMENTS
    return next((part for path in paths for part in reversed(Path(path).parts)
                 if part in PROVINCE_DOCUMENTS), '')


def emit(phase, state='running', **fields):
    filename = fields.pop('_file', None) or os.environ.get(ENV) or _path.get()
    if not filename:
        return False
    try:
        event = {'at': time.time(), 'pid': os.getpid(), 'phase': phase, 'state': state, **fields}
        line = (json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf8')
        with _lock:
            path = Path(filename); path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('ab', buffering=0) as output:
                output.write(line)
        return True
    except (OSError, TypeError, ValueError):
        # A terminal/logging failure must never lose acquired evidence.
        return False
