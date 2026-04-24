"""
Cross-platform filesystem safety helpers for runtime I/O operations.

This module centralizes behavior that differs across Linux/Windows/macOS,
especially file replacement and cleanup in the presence of file locks.
"""

from __future__ import annotations

import errno
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Callable


logger = logging.getLogger("citation_linker")


class IoSafetyError(OSError):
    """Base exception for I/O safety helper failures."""


class FileLockError(IoSafetyError):
    """Raised when a path remains locked after retry attempts."""


RETRYABLE_ERRNOS = {errno.EACCES, errno.EPERM, errno.EBUSY}
RETRYABLE_WINERRORS = {5, 32, 33}


def normalize_path(path: str | os.PathLike[str]) -> Path:
    """Return normalized absolute path for consistent runtime operations."""
    return Path(path).expanduser().resolve(strict=False)


def _is_retryable_lock_error(exc: BaseException) -> bool:
    if not isinstance(exc, OSError):
        return False

    winerror = getattr(exc, "winerror", None)
    if winerror in RETRYABLE_WINERRORS:
        return True

    return exc.errno in RETRYABLE_ERRNOS


def _sleep_before_retry(attempt: int, backoff: float) -> None:
    # Exponential backoff to reduce lock contention on slower filesystems.
    time.sleep(backoff * (2 ** attempt))


def _raise_remove_error(path: Path, exc: OSError, operation: str) -> None:
    if _is_retryable_lock_error(exc):
        raise FileLockError(f"{operation} failed because file is locked: {path}") from exc
    raise IoSafetyError(f"{operation} failed for path: {path}") from exc


def safe_remove_file(
    path: str | os.PathLike[str],
    retries: int = 3,
    backoff: float = 0.1,
) -> None:
    """
    Remove file with retry handling for transient lock/permission issues.

    FileNotFound is treated as success.
    """
    target = normalize_path(path)

    for attempt in range(retries + 1):
        try:
            target.unlink()
            return
        except FileNotFoundError:
            return
        except IsADirectoryError as exc:
            raise IoSafetyError(f"Expected file but got directory: {target}") from exc
        except OSError as exc:
            if _is_retryable_lock_error(exc) and attempt < retries:
                logger.warning(
                    "Retrying file removal due to lock (attempt %s/%s): %s",
                    attempt + 1,
                    retries + 1,
                    target,
                )
                _sleep_before_retry(attempt, backoff)
                continue
            _raise_remove_error(target, exc, operation="File removal")


def _safe_remove_dir(path: Path, retries: int, backoff: float) -> None:
    for attempt in range(retries + 1):
        try:
            path.rmdir()
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            if _is_retryable_lock_error(exc) and attempt < retries:
                logger.warning(
                    "Retrying directory removal due to lock (attempt %s/%s): %s",
                    attempt + 1,
                    retries + 1,
                    path,
                )
                _sleep_before_retry(attempt, backoff)
                continue
            if exc.errno == errno.ENOTEMPTY:
                raise IoSafetyError(f"Directory not empty during removal: {path}") from exc
            _raise_remove_error(path, exc, operation="Directory removal")


def safe_rmtree(
    path: str | os.PathLike[str],
    retries: int = 3,
    backoff: float = 0.1,
) -> None:
    """
    Recursively remove tree with per-file/per-directory retry behavior.

    Missing paths are treated as success.
    """
    target = normalize_path(path)

    if not target.exists():
        return

    if target.is_file() or target.is_symlink():
        safe_remove_file(target, retries=retries, backoff=backoff)
        return

    for root, dirs, files in os.walk(target, topdown=False):
        root_path = Path(root)

        for name in files:
            safe_remove_file(root_path / name, retries=retries, backoff=backoff)

        for name in dirs:
            _safe_remove_dir(root_path / name, retries=retries, backoff=backoff)

    _safe_remove_dir(target, retries=retries, backoff=backoff)


def _replace_with_retry(temp_path: Path, target: Path, retries: int, backoff: float) -> None:
    for attempt in range(retries + 1):
        try:
            os.replace(temp_path, target)
            return
        except OSError as exc:
            if _is_retryable_lock_error(exc) and attempt < retries:
                logger.warning(
                    "Retrying atomic replace due to lock (attempt %s/%s): %s",
                    attempt + 1,
                    retries + 1,
                    target,
                )
                _sleep_before_retry(attempt, backoff)
                continue
            if _is_retryable_lock_error(exc):
                raise FileLockError(f"Atomic replace failed because target is locked: {target}") from exc
            raise IoSafetyError(f"Atomic replace failed for target: {target}") from exc


def atomic_write_bytes(
    path: str | os.PathLike[str],
    data: bytes,
    retries: int = 3,
    backoff: float = 0.1,
) -> None:
    """
    Atomically write bytes to destination path using temp-file + os.replace.
    """
    target = normalize_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as temp_file:
            temp_file.write(data)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        _replace_with_retry(temp_path, target, retries=retries, backoff=backoff)
    except Exception:
        safe_remove_file(temp_path, retries=0, backoff=backoff)
        raise


def atomic_replace_save(
    path: str | os.PathLike[str],
    save_fn: Callable[[str], None],
    retries: int = 3,
    backoff: float = 0.1,
) -> None:
    """
    Atomically save a file via callback that writes to a temporary path.

    Example:
        atomic_replace_save("out.pdf", lambda temp: pymu_doc.save(temp))
    """
    target = normalize_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    os.close(fd)
    temp_path = Path(temp_name)

    try:
        save_fn(str(temp_path))
        _replace_with_retry(temp_path, target, retries=retries, backoff=backoff)
    except Exception:
        safe_remove_file(temp_path, retries=0, backoff=backoff)
        raise
