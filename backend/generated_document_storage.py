"""Request-owned private download files; no database, retention sweep or startup IO."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat
import tempfile


def _identity(info):
    return info.st_dev,info.st_ino


def _directory_info(path):
    info=path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)
            or path.resolve()!=path):
        raise ValueError('Generated document directory must be a real private directory')
    return info


def _ensure_directory(path):
    if not path.exists():
        if not path.parent.exists():_ensure_directory(path.parent)
        try:path.mkdir(mode=0o700)
        except FileExistsError:pass
    return _directory_info(path)


def _output_directory():
    # Match platform_api's fallback without importing it or initializing its DB.
    data=Path(os.getenv('LABOURLAWYER_DATA_DIR',Path(__file__).parent/'data')).expanduser().resolve()
    generated=data/'generated'
    identities=[]
    for directory in (data,generated):
        identities.append((directory,_identity(_ensure_directory(directory))))
    return generated,tuple(identities)


@dataclass(frozen=True)
class GeneratedDocument:
    path: Path
    _file_identity: tuple[int,int]
    _directories: tuple

    def _check_directories(self):
        for directory,identity in self._directories:
            if _identity(_directory_info(directory))!=identity:
                raise ValueError('Generated document directory changed')

    def cleanup(self):
        """Unlink only our original file, never a replacement or another request."""
        try:
            self._check_directories()
            current=self.path.lstat()
            if stat.S_ISREG(current.st_mode) and _identity(current)==self._file_identity:
                self.path.unlink()
        except (OSError,ValueError):
            pass


def save_generated_document(document):
    directory,identities=_output_directory()
    descriptor,name=tempfile.mkstemp(prefix='document-',suffix='.docx',dir=directory)
    saved=GeneratedDocument(Path(name),_identity(os.fstat(descriptor)),identities)
    try:
        with os.fdopen(descriptor,'w+b') as stream:
            if os.name=='posix':os.fchmod(stream.fileno(),0o600)
            saved._check_directories()
            document.save(stream)
            stream.flush()
        saved._check_directories()
        return saved
    except BaseException:
        saved.cleanup()
        raise
