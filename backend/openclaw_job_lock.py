"""OS-owned acquisition lock, released automatically if a worker exits."""
from contextlib import contextmanager
import os
from pathlib import Path

PATH=Path(__file__).resolve().parents[1]/'.runtime/openclaw-acquisition.lock'

@contextmanager
def acquisition_lock():
    PATH.parent.mkdir(parents=True,exist_ok=True)
    stream=PATH.open('a+b');stream.seek(0)
    if PATH.stat().st_size==0:stream.write(b'0');stream.flush()
    stream.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError as exc:
        stream.close();raise RuntimeError('An OpenClaw acquisition job is already running; wait for it to finish.') from exc
    try:yield
    finally:
        stream.seek(0)
        if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        else:fcntl.flock(stream,fcntl.LOCK_UN)
        stream.close()
