"""Reuse an immutable proof result only within one regional HTTP request.

The first call performs the provider's complete pinned-byte verification. A new
request always starts empty, including when file sizes and timestamps match.
Template reads and all region/source/version checks remain in their providers.
"""

from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
from functools import wraps
from threading import RLock


@dataclass
class _EvidenceSession:
    results: dict = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)


_SESSION = ContextVar("regional_evidence_session", default=None)


async def evidence_validation_scope():
    token = _SESSION.set(_EvidenceSession())
    try:
        yield
    finally:
        _SESSION.reset(token)


def evidence_once(function):
    @wraps(function)
    def checked(*args, **kwargs):
        session = _SESSION.get()
        if session is None:
            return function(*args, **kwargs)
        # Preserve argument types so invalid stage=1 cannot reuse valid stage=True.
        key = (function, tuple((type(value), value) for value in args),
               tuple((name, type(value), value) for name, value in sorted(kwargs.items())))
        try:
            hash(key)
        except TypeError:
            return function(*args, **kwargs)
        with session.lock:
            if key not in session.results:
                result = function(*args, **kwargs)
                session.results[key] = deepcopy(result)
                return result
            return deepcopy(session.results[key])
    return checked
