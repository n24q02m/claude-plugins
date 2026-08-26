"""Atomic, auditable locks for workspace-relative channel paths.

Path locks are coordination metadata only.  They never execute a process,
assign a model, or infer that a task should be started.  Each lock is a
human-readable JSON record under ``<channel>/locks`` and every mutation emits a
normal Agent Chat message event.
"""

from __future__ import annotations

import base64
import contextlib
import datetime as _dt
import json
import math
import ntpath
import os
import posixpath
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Mapping

import chat


LOCKS_DIRNAME = "locks"
TRANSACTION_FILENAME = ".path-lock-transaction.json"
MUTATION_LOCK_FILENAME = ".path-locks.lock"
TRANSACTION_PHASES = {"prepared", "applied", "published"}
DEFAULT_LOCK_SECONDS = 300.0
LOCK_FIELDS = (
    "lock_id",
    "channel",
    "owner",
    "paths",
    "expires_at",
    "locked_at",
    "updated_at",
    "previous_owner",
    "previous_expires_at",
    "recovery_reason",
)
_PATH_FIELDS = ("normalized_path", "display_path", "kind")
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


class PathLockError(chat.AgentChatError):
    """Stable machine-readable path-lock error."""

    def __init__(self, code: str, message: str, **details: Any):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class LockedPath:
    """One requested path and its canonical workspace-relative spelling."""

    normalized_path: str
    display_path: str
    kind: str = "file"

    def __post_init__(self) -> None:
        if not isinstance(self.normalized_path, str) or not self.normalized_path:
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD", "normalized_path must be non-empty text"
            )
        if any(_is_forbidden_text_character(char) for char in self.normalized_path):
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                "normalized_path contains a forbidden control character",
            )
        if self.normalized_path != _platform_casefold(self.normalized_path):
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                "normalized_path is not in the platform canonical case",
                normalized_path=self.normalized_path,
            )
        if (
            self.normalized_path != "."
            and (
                self.normalized_path.startswith("/")
                or "\\" in self.normalized_path
                or ":" in self.normalized_path
                or any(
                    part in {"", ".", ".."}
                    for part in self.normalized_path.split("/")
                )
            )
        ) or ".." in self.normalized_path.split("/"):
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD", "normalized_path is not workspace-relative"
            )
        if (
            not isinstance(self.display_path, str)
            or not self.display_path
            or any(_is_forbidden_text_character(char) for char in self.display_path)
        ):
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD", "display_path must be safe non-empty text"
            )
        if self.kind not in {"file", "directory"}:
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD", "path kind must be file or directory"
            )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LockedPath":
        if not isinstance(data, Mapping):
            raise PathLockError("PATH_LOCK_INVALID_RECORD", "lock path must be an object")
        unknown = sorted(set(data) - set(_PATH_FIELDS))
        missing = [field for field in _PATH_FIELDS if field not in data]
        if unknown:
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                "lock path contains unknown fields",
                fields=unknown,
            )
        if missing:
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                "lock path is missing required fields",
                fields=missing,
            )
        return cls(
            normalized_path=data["normalized_path"],
            display_path=data["display_path"],
            kind=data["kind"],
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "normalized_path": self.normalized_path,
            "display_path": self.display_path,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class PathLockRecord:
    """The active lock record stored in one ``locks/*.json`` file."""

    lock_id: str
    channel: str
    owner: str
    paths: tuple[LockedPath, ...]
    expires_at: str
    locked_at: str
    updated_at: str
    previous_owner: str | None = None
    previous_expires_at: str | None = None
    recovery_reason: str | None = None

    def __post_init__(self) -> None:
        _validate_identity(self.lock_id, "lock_id", "PATH_LOCK_INVALID_LOCK_ID")
        _validate_identity(self.channel, "channel", "PATH_LOCK_INVALID_CHANNEL")
        _validate_identity(self.owner, "owner", "PATH_LOCK_INVALID_OWNER")
        if not self.paths:
            raise PathLockError("PATH_LOCK_INVALID_RECORD", "lock must contain at least one path")
        for path in self.paths:
            if not isinstance(path, LockedPath):
                raise PathLockError("PATH_LOCK_INVALID_RECORD", "lock paths are malformed")
        _timestamp(self.expires_at, field="expires_at")
        _timestamp(self.locked_at, field="locked_at")
        _timestamp(self.updated_at, field="updated_at")
        if self.previous_owner is not None:
            _validate_identity(
                self.previous_owner, "previous_owner", "PATH_LOCK_INVALID_OWNER"
            )
        if self.previous_expires_at is not None:
            _timestamp(self.previous_expires_at, field="previous_expires_at")
        if self.recovery_reason is not None:
            _validate_reason(self.recovery_reason)
        recovery_fields = (
            self.previous_owner,
            self.previous_expires_at,
            self.recovery_reason,
        )
        if any(value is not None for value in recovery_fields) and not all(
            value is not None for value in recovery_fields
        ):
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                "previous owner, expiry, and recovery reason must be recorded together",
            )
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PathLockRecord":
        if not isinstance(data, Mapping):
            raise PathLockError("PATH_LOCK_INVALID_RECORD", "lock record must be an object")
        actual = set(data)
        required = set(LOCK_FIELDS[:7])
        expiry_aliases = {"lease_expires_at", "previous_lease_expires_at"}
        if "expires_at" not in actual and "lease_expires_at" in actual:
            required.remove("expires_at")
        missing = [field for field in required if field not in actual]
        unknown = sorted(actual - set(LOCK_FIELDS) - expiry_aliases)
        if missing:
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                "lock record is missing required fields",
                fields=missing,
            )
        if unknown:
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                "lock record contains unknown fields",
                fields=unknown,
            )
        if (
            "expires_at" in actual
            and "lease_expires_at" in actual
            and data["expires_at"] != data["lease_expires_at"]
        ):
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                "expires_at and lease_expires_at aliases disagree",
            )
        if (
            "previous_expires_at" in actual
            and "previous_lease_expires_at" in actual
            and data["previous_expires_at"] != data["previous_lease_expires_at"]
        ):
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                "previous expiry aliases disagree",
            )
        raw_paths = data["paths"]
        if not isinstance(raw_paths, list):
            raise PathLockError("PATH_LOCK_INVALID_RECORD", "lock paths must be an array")
        expiry = data.get("expires_at", data.get("lease_expires_at"))
        previous_expiry = data.get(
            "previous_expires_at", data.get("previous_lease_expires_at")
        )
        return cls(
            lock_id=data["lock_id"],
            channel=data["channel"],
            owner=data["owner"],
            paths=tuple(LockedPath.from_dict(item) for item in raw_paths),
            expires_at=expiry,
            locked_at=data["locked_at"],
            updated_at=data["updated_at"],
            previous_owner=data.get("previous_owner"),
            previous_expires_at=previous_expiry,
            recovery_reason=data.get("recovery_reason"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "lock_id": self.lock_id,
            "channel": self.channel,
            "owner": self.owner,
            "paths": [path.to_dict() for path in self.paths],
            "expires_at": self.expires_at,
            "locked_at": self.locked_at,
            "updated_at": self.updated_at,
            "previous_owner": self.previous_owner,
            "previous_expires_at": self.previous_expires_at,
            "recovery_reason": self.recovery_reason,
        }
    @property
    def lease_expires_at(self) -> str:
        """Task4-compatible spelling for the active lease expiry."""

        return self.expires_at

    @property
    def previous_lease_expires_at(self) -> str | None:
        """Task4-compatible spelling for the prior lease expiry."""

        return self.previous_expires_at


# Friendly aliases for callers that use the noun "lock" rather than "path".
LockRecord = PathLockRecord
PathLockPath = LockedPath


def _is_forbidden_text_character(value: str) -> bool:
    codepoint = ord(value)
    return codepoint < 0x20 or 0x7F <= codepoint <= 0x9F or 0xD800 <= codepoint <= 0xDFFF


def _validate_identity(value: Any, field: str, code: str) -> str:
    if not isinstance(value, str) or not value or not _ID_RE.fullmatch(value):
        raise PathLockError(code, f"{field} must be a safe identity")
    if any(_is_forbidden_text_character(char) for char in value):
        raise PathLockError(code, f"{field} contains a forbidden control character")
    return value


def _validate_reason(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PathLockError("PATH_LOCK_INVALID_REASON", "recovery reason must not be empty")
    if any(_is_forbidden_text_character(char) for char in value):
        raise PathLockError(
            "PATH_LOCK_INVALID_REASON",
            "recovery reason contains a forbidden control character",
        )
    return value


def _timestamp(value: Any, *, field: str) -> str:
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise PathLockError(
                "PATH_LOCK_INVALID_TIMESTAMP", f"{field} needs a UTC offset"
            )
        return value.isoformat(timespec="microseconds")
    if not isinstance(value, str):
        raise PathLockError(
            "PATH_LOCK_INVALID_TIMESTAMP", f"{field} must be an ISO-8601 string"
        )
    try:
        _parse_timestamp(value)
    except (TypeError, ValueError) as error:
        raise PathLockError(
            "PATH_LOCK_INVALID_TIMESTAMP", f"{field} must be an ISO-8601 string"
        ) from error
    return value


def _parse_timestamp(value: str) -> _dt.datetime:
    parse_value = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    parsed = _dt.datetime.fromisoformat(parse_value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp needs an offset")
    return parsed


def _is_expired(expires_at: str, now: _dt.datetime) -> bool:
    return _parse_timestamp(expires_at) <= now


def _validate_duration(value: Any) -> float:
    if isinstance(value, bool):
        raise PathLockError("PATH_LOCK_INVALID_DURATION", "lock duration must be positive")
    try:
        seconds = float(value)
    except (TypeError, ValueError) as error:
        raise PathLockError(
            "PATH_LOCK_INVALID_DURATION", "lock duration must be positive"
        ) from error
    if not math.isfinite(seconds) or seconds <= 0:
        raise PathLockError("PATH_LOCK_INVALID_DURATION", "lock duration must be positive")
    return seconds


def _platform_casefold(value: str) -> str:
    return value.casefold() if os.name == "nt" else value


def _path_error(message: str, *, path: Any = None) -> PathLockError:
    details = {} if path is None else {"path": path}
    return PathLockError("PATH_LOCK_INVALID_PATH", message, **details)


def _storage_error(operation: str, error: BaseException) -> PathLockError:
    return PathLockError(
        "PATH_LOCK_STORAGE_ERROR",
        f"{operation} failed: {error}",
        operation=operation,
        cause=type(error).__name__,
    )


def _display_parts(display_path: Any) -> list[str]:
    if not isinstance(display_path, str) or not display_path:
        raise _path_error("path must be a non-empty string", path=display_path)
    if any(_is_forbidden_text_character(char) for char in display_path):
        raise _path_error("path contains a forbidden control character", path=display_path)

    # Use both path grammars so a Windows absolute path cannot be smuggled into
    # a POSIX worker, and vice versa.  On Windows backslashes are separators;
    # on POSIX they are rejected as ambiguous rather than treated as a name.
    portable = display_path.replace("\\", "/") if os.name == "nt" else display_path
    if os.name != "nt" and "\\" in display_path:
        raise _path_error("backslashes are not valid portable separators", path=display_path)
    if (
        posixpath.isabs(portable)
        or ntpath.isabs(display_path)
        or ntpath.splitdrive(display_path)[0]
        or portable.startswith("/")
    ):
        raise _path_error("absolute paths are not allowed", path=display_path)
    if ":" in portable:
        raise _path_error("path names may not contain ':'", path=display_path)

    raw_parts = portable.split("/")
    if any(part == ".." for part in raw_parts):
        raise _path_error("parent traversal is not allowed", path=display_path)
    if os.name == "nt":
        reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{index}" for index in range(1, 10)),
            *(f"LPT{index}" for index in range(1, 10)),
        }
        for part in raw_parts:
            if not part or part == ".":
                continue
            if part.endswith((" ", ".")):
                raise _path_error(
                    "Windows path components may not end with space or dot",
                    path=display_path,
                )
            if any(char in '<>\"|?*' for char in part):
                raise _path_error("path contains an unrepresentable Windows name", path=display_path)
            stem = part.split(".", 1)[0].upper()
            if stem in reserved:
                raise _path_error("path contains a reserved Windows name", path=display_path)
    # Collapse harmless duplicate separators and current-directory markers.
    # The original spelling remains in ``display_path`` for auditability.
    parts = [part for part in raw_parts if part not in {"", "."}]
    if not parts:
        return ["."]
    return parts


def _validate_persisted_normalized_path(value: str) -> None:
    try:
        parts = _display_parts(value)
    except PathLockError as error:
        raise PathLockError(
            "PATH_LOCK_INVALID_RECORD",
            "persisted normalized_path is not a valid workspace-relative path",
            normalized_path=value,
        ) from error
    canonical = "/".join(parts)
    if canonical != value or canonical != _platform_casefold(canonical):
        raise PathLockError(
            "PATH_LOCK_INVALID_RECORD",
            "persisted normalized_path is not platform-canonical",
            normalized_path=value,
        )


def _paths_overlap(left: str, right: str) -> bool:
    return (
        left == "."
        or right == "."
        or left == right
        or left.startswith(right + "/")
        or right.startswith(left + "/")
    )

@dataclass
class _MutationHandle:
    path: Path
    fd: int
    released: bool = False

    def release(self) -> None:
        if self.released:
            return
        try:
            os.lseek(self.fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.fd, fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            self.released = True
            try:
                os.close(self.fd)
            except OSError:
                pass



class PathLockStore:
    """Read and mutate active path locks for one declared channel workspace."""

    def __init__(
        self,
        channel: Path | str,
        root: Path | str | None = None,
        *,
        clock: Callable[[], Any] | None = None,
        mutation_timeout: float = 10.0,
        mutation_stale: float = 30.0,
    ):
        self.channel = Path(channel)
        self.root = Path(root) if root is not None else self.channel.parent
        self._clock = clock or chat.now_iso
        self._mutation_timeout = mutation_timeout
        self._mutation_stale = mutation_stale
        self._assert_inside_root(self.channel)
        if not self.channel.is_dir() or not (self.channel / "_meta.json").is_file():
            raise PathLockError(
                "PATH_LOCK_CHANNEL_NOT_FOUND",
                f"channel does not contain _meta.json: {self.channel}",
            )
        self._assert_inside_channel(self.locks_dir)

    @property
    def locks_dir(self) -> Path:
        return self.channel / LOCKS_DIRNAME
    @property
    def transaction_path(self) -> Path:
        path = self.locks_dir / TRANSACTION_FILENAME
        self._assert_inside_channel(path)
        return path

    @property
    def mutation_lock_path(self) -> Path:
        return self.channel / MUTATION_LOCK_FILENAME

    def _assert_inside_root(self, path: Path) -> None:
        try:
            path.resolve(strict=False).relative_to(self.root.resolve(strict=False))
        except (OSError, RuntimeError, ValueError, UnicodeError) as error:
            raise PathLockError(
                "PATH_LOCK_PATH_OUTSIDE_WORKSPACE",
                f"channel path escapes configured root: {path}",
                path=str(path),
            ) from error

    def _assert_inside_channel(self, path: Path) -> None:
        try:
            path.resolve(strict=False).relative_to(self.channel.resolve(strict=False))
        except (OSError, RuntimeError, ValueError, UnicodeError) as error:
            raise PathLockError(
                "PATH_LOCK_PATH_OUTSIDE_WORKSPACE",
                f"path escapes channel workspace: {path}",
                path=str(path),
            ) from error

    def _revalidate_storage(self) -> Path:
        try:
            if self.locks_dir.is_symlink() or os.path.islink(str(self.locks_dir)):
                raise PathLockError(
                    "PATH_LOCK_PATH_OUTSIDE_WORKSPACE",
                    "lock storage may not be a symlink or junction",
                    path=str(self.locks_dir),
                )
            if self.locks_dir.exists() and not self.locks_dir.is_dir():
                raise PathLockError(
                    "PATH_LOCK_STORAGE_INVALID",
                    f"lock storage is not a directory: {self.locks_dir}",
                )
            resolved = self.locks_dir.resolve(strict=False)
            resolved.relative_to(self.channel.resolve(strict=False))
        except PathLockError:
            raise
        except (OSError, RuntimeError, ValueError, UnicodeError) as error:
            raise PathLockError(
                "PATH_LOCK_PATH_OUTSIDE_WORKSPACE",
                f"lock storage containment could not be proven: {self.locks_dir}",
                path=str(self.locks_dir),
            ) from error
        return self.locks_dir

    def _revalidate_mutation_lock(self) -> Path:
        path = self.mutation_lock_path
        self._assert_inside_channel(path)
        try:
            if path.is_symlink() or os.path.islink(str(path)):
                raise PathLockError(
                    "PATH_LOCK_PATH_OUTSIDE_WORKSPACE",
                    "mutation lock may not be a symlink or junction",
                    path=str(path),
                )
            if path.exists() and not path.is_file():
                raise PathLockError(
                    "PATH_LOCK_STORAGE_INVALID",
                    f"mutation lock is not a regular file: {path}",
                )
        except PathLockError:
            raise
        except (OSError, RuntimeError, UnicodeError) as error:
            raise _storage_error("mutation lock validation", error)
        return path

    def _ensure_locks_dir(self) -> Path:
        self._revalidate_storage()
        try:
            self.locks_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise _storage_error("lock storage creation", error) from error
        self._revalidate_storage()
        return self.locks_dir

    def _acquire_mutation_lock(self) -> _MutationHandle:
        path = self._revalidate_mutation_lock()
        flags = os.O_RDWR | os.O_CREAT
        no_follow = getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(str(path), flags | no_follow, 0o600)
        except OSError as error:
            raise _storage_error("mutation lock open", error) from error
        if os.name == "nt":
            try:
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b"\0")
            except OSError as error:
                os.close(fd)
                raise _storage_error("mutation lock initialization", error) from error
        started = time.monotonic()
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._revalidate_mutation_lock()
                return _MutationHandle(path, fd)
            except PathLockError:
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise
            except OSError:
                if time.monotonic() - started > self._mutation_timeout:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                    raise PathLockError(
                        "PATH_LOCK_TIMEOUT", "could not acquire path-lock mutation lock"
                    )
                time.sleep(0.01)

    @staticmethod
    def _release_mutation_lock(lock: _MutationHandle) -> None:
        lock.release()

    @contextlib.contextmanager
    def _mutation(self):
        lock = self._acquire_mutation_lock()
        try:
            yield
        finally:
            self._release_mutation_lock(lock)

    def _lock_path(self, lock_id: str) -> Path:
        _validate_identity(lock_id, "lock_id", "PATH_LOCK_INVALID_LOCK_ID")
        self._revalidate_storage()
        path = self.locks_dir / f"{lock_id}.json"
        self._assert_inside_channel(path)
        try:
            if path.resolve(strict=False).parent != self.locks_dir.resolve(strict=False):
                raise ValueError
        except (OSError, RuntimeError, ValueError, UnicodeError) as error:
            raise PathLockError(
                "PATH_LOCK_PATH_OUTSIDE_WORKSPACE",
                f"lock record path escapes lock storage: {path}",
                path=str(path),
            ) from error
        return path

    def _read_record(self, path: Path) -> PathLockRecord:
        self._assert_inside_channel(path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise PathLockError(
                "PATH_LOCK_NOT_FOUND", f"lock record does not exist: {path.stem}"
            ) from error
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                f"could not read lock record {path.name}: {error}",
                path=str(path),
            ) from error
        record = PathLockRecord.from_dict(raw)
        for locked_path in record.paths:
            _validate_persisted_normalized_path(locked_path.normalized_path)
            parts = (
                []
                if locked_path.normalized_path == "."
                else locked_path.normalized_path.split("/")
            )
            candidate = self.channel.joinpath(*parts)
            try:
                relative = candidate.resolve(strict=False).relative_to(
                    self.channel.resolve(strict=False)
                )
            except (OSError, RuntimeError, ValueError, UnicodeError) as error:
                raise PathLockError(
                    "PATH_LOCK_INVALID_RECORD",
                    "persisted path escapes channel workspace",
                    normalized_path=locked_path.normalized_path,
                ) from error
            actual = _platform_casefold(relative.as_posix() or ".")
            if actual != locked_path.normalized_path:
                raise PathLockError(
                    "PATH_LOCK_INVALID_RECORD",
                    "persisted normalized_path does not match channel canonical path",
                    normalized_path=locked_path.normalized_path,
                )
        if record.channel != self.channel.name:
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                f"lock channel {record.channel!r} does not match {self.channel.name!r}",
                path=str(path),
            )
        if path.stem != record.lock_id:
            raise PathLockError(
                "PATH_LOCK_INVALID_RECORD",
                f"lock id does not match filename {path.name!r}",
                path=str(path),
            )
        return record

    def _read_all(self) -> list[PathLockRecord]:
        self._assert_no_pending_transaction()
        self._revalidate_storage()
        if not self.locks_dir.exists():
            return []
        if not self.locks_dir.is_dir():
            raise PathLockError(
                "PATH_LOCK_STORAGE_INVALID",
                f"lock storage is not a directory: {self.locks_dir}",
            )
        records: list[PathLockRecord] = []
        for path in sorted(self.locks_dir.glob("*.json"), key=lambda item: item.name):
            if path.name.startswith((".", "_")):
                continue
            records.append(self._read_record(path))
        return records

    def list(self) -> list[PathLockRecord]:
        with self._mutation():
            return self._read_all()

    def load(self, lock_id: str) -> PathLockRecord:
        with self._mutation():
            path = self._lock_path(lock_id)
            return self._read_record(path)

    def normalize_paths(self, paths: Iterable[str]) -> tuple[LockedPath, ...]:
        if paths is None:
            raise _path_error("at least one path is required")
        if isinstance(paths, (str, bytes)):
            paths = [paths]  # type: ignore[list-item]
        normalized: list[LockedPath] = []
        for display_path in paths:
            parts = _display_parts(display_path)
            try:
                candidate = self.channel.joinpath(*parts)
                resolved_channel = self.channel.resolve(strict=False)
                resolved = candidate.resolve(strict=False)
                relative = resolved.relative_to(resolved_channel)
            except UnicodeError as error:
                raise _path_error(
                    "path contains malformed Unicode", path=display_path
                ) from error
            except (OSError, RuntimeError, ValueError) as error:
                raise PathLockError(
                    "PATH_LOCK_PATH_OUTSIDE_WORKSPACE",
                    f"requested path escapes channel workspace: {display_path}",
                    path=display_path,
                ) from error
            canonical = relative.as_posix()
            if not canonical:
                raise _path_error("path must name a workspace entry", path=display_path)
            canonical = _platform_casefold(canonical)
            kind = "directory" if resolved.is_dir() else "file"
            item = LockedPath(
                normalized_path=canonical,
                display_path=display_path,
                kind=kind,
            )
            if any(_paths_overlap(item.normalized_path, old.normalized_path) for old in normalized):
                raise PathLockError(
                    "PATH_LOCK_CONFLICT",
                    "requested paths overlap within one lock request",
                    paths=[entry.to_dict() for entry in (*normalized, item)],
                )
            normalized.append(item)
        if not normalized:
            raise _path_error("at least one path is required")
        return tuple(normalized)

    def _conflicts(
        self,
        requested: Iterable[LockedPath],
        records: Iterable[PathLockRecord],
        *,
        ignore_lock_id: str | None = None,
    ) -> list[PathLockRecord]:
        result: list[PathLockRecord] = []
        for record in records:
            if ignore_lock_id is not None and record.lock_id == ignore_lock_id:
                continue
            if any(
                _paths_overlap(left.normalized_path, right.normalized_path)
                for left in requested
                for right in record.paths
            ):
                result.append(record)
        return result

    @staticmethod
    def _conflict_details(records: Iterable[PathLockRecord], now: _dt.datetime) -> list[dict[str, Any]]:
        return [
            {
                "lock_id": record.lock_id,
                "owner": record.owner,
                "expires_at": record.expires_at,
                "expired": _is_expired(record.expires_at, now),
                "paths": [path.to_dict() for path in record.paths],
            }
            for record in records
        ]

    def check(
        self,
        paths: Iterable[str],
        *,
        owner: str | None = None,
        ignore_lock_id: str | None = None,
    ) -> list[PathLockRecord]:
        """Return active or stale records that overlap ``paths``.

        Expired records remain visible until explicitly recovered or released;
        callers must not silently treat stale coordination metadata as free.
        """

        requested = self.normalize_paths(paths)
        if owner is not None:
            _validate_identity(owner, "owner", "PATH_LOCK_INVALID_OWNER")
        with self._mutation():
            return self._conflicts(
                requested, self._read_all(), ignore_lock_id=ignore_lock_id
            )

    def _raise_conflict(
        self,
        conflicts: list[PathLockRecord],
        now: _dt.datetime,
        *,
        operation: str,
    ) -> None:
        details = self._conflict_details(conflicts, now)
        if any(item["expired"] for item in details):
            raise PathLockError(
                "PATH_LOCK_RECOVERY_REQUIRED",
                f"{operation} overlaps an expired lock; recover it explicitly",
                conflicts=details,
            )
        raise PathLockError(
            "PATH_LOCK_CONFLICT",
            f"{operation} overlaps an active lock",
            conflicts=details,
        )

    @staticmethod
    def _json_bytes(record: PathLockRecord) -> bytes:
        return (
            json.dumps(
                record.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                separators=(",", ": "),
            )
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        try:
            fd = os.open(str(directory), os.O_RDONLY)
        except (OSError, ValueError):
            return
        try:
            try:
                os.fsync(fd)
            except OSError:
                pass
        finally:
            os.close(fd)

    def _write_exclusive(self, path: Path, record: PathLockRecord) -> bool:
        directory = self._ensure_locks_dir()
        self._assert_inside_channel(path)
        payload = self._json_bytes(record)
        temporary: Path | None = None
        fd = -1
        try:
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{path.stem}.", suffix=".tmp", dir=str(directory)
            )
            temporary = Path(temporary_name)
            self._assert_inside_channel(temporary)
            self._revalidate_storage()
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                try:
                    os.fsync(stream.fileno())
                except OSError:
                    pass
            fd = -1
            self._revalidate_storage()
            try:
                os.link(str(temporary), str(path))
            except FileExistsError as error:
                raise PathLockError(
                    "PATH_LOCK_CONFLICT", f"lock id already exists: {record.lock_id}"
                ) from error
            except OSError as error:
                self._revalidate_storage()
                raise _storage_error("atomic lock publish", error) from error
            self._revalidate_storage()
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            temporary = None
            self._fsync_directory(directory)
            return True
        except PathLockError:
            raise
        except (OSError, UnicodeError) as error:
            raise _storage_error("exclusive lock write", error) from error
        finally:
            if fd != -1:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass

    def _write_atomic(self, path: Path, record: PathLockRecord) -> bool:
        directory = self._ensure_locks_dir()
        self._assert_inside_channel(path)
        temporary: Path | None = None
        fd = -1
        try:
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{path.stem}.", suffix=".tmp", dir=str(directory)
            )
            temporary = Path(temporary_name)
            self._assert_inside_channel(temporary)
            self._revalidate_storage()
            with os.fdopen(fd, "wb") as stream:
                stream.write(self._json_bytes(record))
                stream.flush()
                try:
                    os.fsync(stream.fileno())
                except OSError:
                    pass
            fd = -1
            self._revalidate_storage()
            os.replace(temporary, path)
            temporary = None
            self._revalidate_storage()
            self._fsync_directory(directory)
            return True
        except PathLockError:
            raise
        except (OSError, UnicodeError) as error:
            raise _storage_error("atomic lock replace", error) from error
        finally:
            if fd != -1:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass

    def _restore_bytes(self, path: Path, previous: bytes | None) -> None:
        self._assert_inside_channel(path)
        if previous is None:
            try:
                path.unlink()
                self._revalidate_storage()
                self._fsync_directory(path.parent)
            except FileNotFoundError:
                return
            except (OSError, UnicodeError) as error:
                raise _storage_error("lock rollback removal", error) from error
            return
        directory = self._ensure_locks_dir()
        temporary: Path | None = None
        fd = -1
        try:
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{path.stem}.rollback.", suffix=".tmp", dir=str(directory)
            )
            temporary = Path(temporary_name)
            self._assert_inside_channel(temporary)
            self._revalidate_storage()
            with os.fdopen(fd, "wb") as stream:
                stream.write(previous)
                stream.flush()
                try:
                    os.fsync(stream.fileno())
                except OSError:
                    pass
            fd = -1
            self._revalidate_storage()
            os.replace(temporary, path)
            temporary = None
            self._revalidate_storage()
            self._fsync_directory(directory)
        except PathLockError:
            raise
        except (OSError, UnicodeError) as error:
            raise _storage_error("lock rollback restore", error) from error
        finally:
            if fd != -1:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
    def _post_event(
        self,
        event: str,
        record: PathLockRecord,
        *,
        actor: str | None,
        previous: PathLockRecord | None = None,
        transaction_id: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        sender = actor or record.owner
        _validate_identity(sender, "actor", "PATH_LOCK_INVALID_OWNER")
        payload: dict[str, Any] = {
            "event": event,
            "lock_id": record.lock_id,
            "channel": record.channel,
            "owner": record.owner,
            "paths": [path.to_dict() for path in record.paths],
            "expires_at": record.expires_at,
            "lease_expires_at": record.lease_expires_at,
            "updated_at": record.updated_at,
        }
        if previous is not None:
            payload.update(
                {
                    "previous_owner": previous.owner,
                    "previous_expires_at": previous.expires_at,
                    "previous_lease_expires_at": previous.lease_expires_at,
                }
            )
        if transaction_id is not None:
            _validate_identity(
                transaction_id, "transaction_id", "PATH_LOCK_TRANSACTION_INVALID"
            )
            payload["transaction_id"] = transaction_id
        if details:
            payload.update(details)
        body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        args = SimpleNamespace(
            channel=self.channel.name,
            sender=sender,
            to="all",
            title=f"{event} {record.lock_id}",
            reply=None,
            status=event,
            body=body,
            body_file=None,
        )
        try:
            chat.cmd_post(self.channel.parent, args)
        except (chat.AgentChatError, OSError, UnicodeError) as error:
            raise PathLockError(
                "PATH_LOCK_AUDIT_FAILED",
                f"path lock audit event could not be written: {error}",
                event=event,
                lock_id=record.lock_id,
                transaction_id=transaction_id,
            ) from error


    @staticmethod
    def _encode_bytes(value: bytes | None) -> str | None:
        if value is None:
            return None
        return base64.b64encode(value).decode("ascii")

    @staticmethod
    def _decode_bytes(value: Any) -> bytes | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_INVALID",
                "transaction bytes must be base64 text",
            )
        try:
            return base64.b64decode(value.encode("ascii"), validate=True)
        except (ValueError, UnicodeError) as error:
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_INVALID",
                "transaction bytes are not valid base64",
            ) from error

    def _atomic_write_payload(self, path: Path, payload: bytes) -> None:
        directory = self._ensure_locks_dir()
        temporary: Path | None = None
        fd = -1
        try:
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{path.stem}.", suffix=".tmp", dir=str(directory)
            )
            temporary = Path(temporary_name)
            self._assert_inside_channel(temporary)
            self._revalidate_storage()
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                try:
                    os.fsync(stream.fileno())
                except OSError:
                    pass
            fd = -1
            self._revalidate_storage()
            try:
                os.replace(temporary, path)
            except OSError as error:
                self._revalidate_storage()
                raise _storage_error("transaction publish", error) from error
            temporary = None
            self._revalidate_storage()
            self._fsync_directory(directory)
        except PathLockError:
            raise
        except (OSError, UnicodeError) as error:
            raise _storage_error("transaction write", error) from error
        finally:
            if fd != -1:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
    def _write_transaction(self, transaction: Mapping[str, Any]) -> None:
        payload = (
            json.dumps(
                transaction,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                separators=(",", ": "),
            )
            + "\n"
        ).encode("utf-8")
        self._atomic_write_payload(self.transaction_path, payload)

    def _read_transaction(self) -> dict[str, Any] | None:
        path = self.transaction_path
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_INVALID",
                f"could not read transaction marker: {error}",
                path=str(path),
            ) from error
        required = {
            "version",
            "transaction_id",
            "phase",
            "operation",
            "event",
            "target",
            "before",
            "after",
            "actor",
        }
        if (
            not isinstance(raw, dict)
            or raw.get("version") not in {1, 2}
            or raw.get("phase") not in TRANSACTION_PHASES
            or not required.issubset(raw)
            or not isinstance(raw.get("transaction_id"), str)
            or not _ID_RE.fullmatch(raw["transaction_id"])
            or raw.get("operation") not in {"lock", "unlock", "recover"}
            or not isinstance(raw.get("target"), str)
            or not isinstance(raw.get("actor"), str)
        ):
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_INVALID",
                "transaction marker has an unsupported shape",
                path=str(path),
            )
        target = raw["target"].replace("\\", "/")
        target_parts = target.split("/")
        if len(target_parts) == 1:
            target_name = target_parts[0]
        elif len(target_parts) == 2 and target_parts[0] == LOCKS_DIRNAME:
            target_name = target_parts[1]
        else:
            target_name = ""
        if (
            not target_name.endswith(".json")
            or not _ID_RE.fullmatch(target_name[:-5])
        ):
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_INVALID",
                "transaction target is not a lock record filename",
                target=raw["target"],
            )
        _validate_identity(raw["actor"], "actor", "PATH_LOCK_INVALID_OWNER")
        self._decode_bytes(raw["before"])
        self._decode_bytes(raw["after"])
        if raw.get("previous_bytes") is not None:
            self._decode_bytes(raw["previous_bytes"])
        if raw.get("next_bytes") is not None:
            self._decode_bytes(raw["next_bytes"])
        return raw

    def _remove_transaction(self) -> None:
        try:
            self.transaction_path.unlink()
            self._fsync_directory(self.transaction_path.parent)
        except FileNotFoundError:
            return
        except (OSError, UnicodeError) as error:
            raise _storage_error("transaction cleanup", error) from error

    def _set_transaction_phase(self, phase: str) -> None:
        if phase not in TRANSACTION_PHASES:
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_INVALID", f"unsupported transaction phase: {phase}"
            )
        transaction = self._read_transaction()
        if transaction is None:
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_INVALID", "transaction marker is missing"
            )
        transaction["phase"] = phase
        self._write_transaction(transaction)

    def _assert_no_pending_transaction(self) -> None:
        pending = self._read_transaction()
        if pending is not None:
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_PENDING",
                "a previous path-lock mutation needs explicit recovery",
                transaction_id=pending["transaction_id"],
                operation=pending["operation"],
                phase=pending["phase"],
            )
    def _audit_event_exists_for_transaction(self, transaction_id: Any) -> bool:
        if not isinstance(transaction_id, str) or not transaction_id:
            return False
        marker = f'"transaction_id": "{transaction_id}"'
        try:
            message_paths = chat.message_files(self.channel)
        except (OSError, UnicodeError):
            return False
        for path in message_paths:
            try:
                if marker in path.read_text(encoding="utf-8"):
                    return True
            except (OSError, UnicodeError):
                continue
        return False

    def _transaction_for(
        self,
        *,
        operation: str,
        event: str,
        path: Path,
        before: bytes | None,
        after: bytes | None,
        actor: str,
    ) -> dict[str, Any]:
        self._assert_inside_channel(path)
        if path.parent.resolve(strict=False) != self.locks_dir.resolve(strict=False):
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_INVALID",
                "transaction target is outside lock storage",
                path=str(path),
            )
        return {
            "version": 1,
            "transaction_id": uuid.uuid4().hex,
            "phase": "prepared",
            "operation": operation,
            "event": event,
            "target": path.name,
            "before": self._encode_bytes(before),
            "after": self._encode_bytes(after),
            "actor": actor,
        }

    def _run_transaction(
        self,
        *,
        operation: str,
        event: str,
        path: Path,
        before: bytes | None,
        after: bytes | None,
        actor: str,
        apply: Callable[[], bool],
        record: PathLockRecord,
        previous: PathLockRecord | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> PathLockRecord:
        self._assert_no_pending_transaction()
        transaction = self._transaction_for(
            operation=operation,
            event=event,
            path=path,
            before=before,
            after=after,
            actor=actor,
        )
        self._write_transaction(transaction)
        publish_succeeded = False
        audit_published = False
        before_apply = None
        snapshot_error = None
        try:
            try:
                if path.exists():
                    before_apply = path.read_bytes()
                else:
                    before_apply = None
            except Exception as read_error:
                snapshot_error = read_error
                raise PathLockError(
                    "PATH_LOCK_AUDIT_ROLLBACK_FAILED",
                    f"path lock mutation target could not be snapshotted: {read_error}",
                    transaction_pending=True,
                    transaction_id=transaction["transaction_id"],
                    readback_error=str(read_error),
                ) from read_error
            apply_result = apply()
            publish_succeeded = apply_result is not False
            self._set_transaction_phase("applied")
            self._post_event(
                event,
                record,
                actor=actor,
                previous=previous,
                transaction_id=transaction["transaction_id"],
                details=details,
            )
            audit_published = True
            self._set_transaction_phase("published")
            self._remove_transaction()
        except Exception as error:
            if audit_published:
                raise PathLockError(
                    "PATH_LOCK_TRANSACTION_CLEANUP_FAILED",
                    f"path lock mutation is audited but transaction cleanup failed: {error}",
                    transaction_pending=True,
                    transaction_id=transaction["transaction_id"],
                    operation=operation,
                ) from error
            read_failed = False
            read_error = None
            try:
                if path.exists():
                    current_on_disk = path.read_bytes()
                else:
                    current_on_disk = None
            except Exception as e:
                read_failed = True
                read_error = e
                current_on_disk = None

            if read_failed:
                raise PathLockError(
                    "PATH_LOCK_AUDIT_ROLLBACK_FAILED",
                    f"path lock mutation failed and target state could not be verified: {read_error}",
                    transaction_pending=True,
                    transaction_id=transaction["transaction_id"],
                    original_error=str(error),
                    readback_error=str(read_error),
                ) from read_error

            if snapshot_error is not None:
                raise PathLockError(
                    "PATH_LOCK_AUDIT_ROLLBACK_FAILED",
                    "path lock mutation snapshot failed; pending recovery is required",
                    transaction_pending=True,
                    transaction_id=transaction["transaction_id"],
                    original_error=str(error),
                    snapshot_error=str(snapshot_error),
                    readback_error=None,
                ) from snapshot_error

            has_mutated = publish_succeeded or (current_on_disk != before_apply)
            if has_mutated:
                try:
                    self._restore_bytes(path, before)
                    self._remove_transaction()
                except Exception as rollback_error:
                    raise PathLockError(
                        "PATH_LOCK_AUDIT_ROLLBACK_FAILED",
                        f"path lock mutation failed and rollback failed: {rollback_error}",
                        transaction_pending=True,
                        transaction_id=transaction["transaction_id"],
                        original_error=str(error),
                        rollback_error=str(rollback_error),
                    ) from rollback_error
            else:
                try:
                    self._remove_transaction()
                except Exception:
                    pass
            if isinstance(error, PathLockError):
                raise
            if isinstance(error, (OSError, UnicodeError)):
                raise _storage_error("path lock mutation", error) from error
            raise PathLockError(
                "PATH_LOCK_AUDIT_FAILED",
                f"path lock audit failed: {error}",
                event=event,
                lock_id=record.lock_id,
            ) from error
        return record

    def recover_pending(
        self,
        *,
        actor: str = "recovery",
        publication_resolution: str | None = None,
    ) -> None:
        _validate_identity(actor, "actor", "PATH_LOCK_INVALID_OWNER")
        if publication_resolution not in {None, "rollback", "published"}:
            raise PathLockError(
                "PATH_LOCK_TRANSACTION_INVALID",
                f"unsupported publication resolution: {publication_resolution!r}",
            )
        with self._mutation():
            transaction = self._read_transaction()
            if transaction is None:
                return
            phase = transaction["phase"]
            if publication_resolution is not None:
                if phase not in {"applied", "published"}:
                    raise PathLockError(
                        "PATH_LOCK_TRANSACTION_INVALID",
                        "publication resolution applies only to applied or published transactions",
                    )
                phase = (
                    "published"
                    if publication_resolution == "published"
                    else "prepared"
                )
            elif phase in {"applied", "published"} and (
                phase == "published"
                or self._audit_event_exists_for_transaction(
                    transaction["transaction_id"]
                )
            ):
                phase = "published"
            target = transaction["target"]
            target_name = target.replace("\\", "/").split("/")[-1]
            target_path = self._lock_path(target_name[:-5])
            before = self._decode_bytes(transaction["before"])
            after = self._decode_bytes(transaction["after"])
            try:
                if phase == "published":
                    current = target_path.read_bytes() if target_path.exists() else None
                    if current != after:
                        raise PathLockError(
                            "PATH_LOCK_TRANSACTION_INVALID",
                            "published transaction does not match lock state",
                            transaction_id=transaction["transaction_id"],
                        )
                    self._remove_transaction()
                    return
                self._restore_bytes(target_path, before)
                self._remove_transaction()
            except PathLockError:
                raise
            except Exception as error:
                raise PathLockError(
                    "PATH_LOCK_AUDIT_ROLLBACK_FAILED",
                    f"pending path-lock recovery failed: {error}",
                    transaction_pending=True,
                    transaction_id=transaction["transaction_id"],
                ) from error
    def _now(self, value: Any = None) -> _dt.datetime:
        candidate = self._clock() if value is None else value
        if isinstance(candidate, _dt.datetime):
            if candidate.tzinfo is None or candidate.utcoffset() is None:
                raise PathLockError(
                    "PATH_LOCK_INVALID_TIMESTAMP", "clock must include a UTC offset"
                )
            return candidate
        if not isinstance(candidate, str):
            raise PathLockError(
                "PATH_LOCK_INVALID_TIMESTAMP", "clock must return an ISO-8601 string"
            )
        try:
            return _parse_timestamp(candidate)
        except (TypeError, ValueError) as error:
            raise PathLockError(
                "PATH_LOCK_INVALID_TIMESTAMP", "clock must return an ISO-8601 string"
            ) from error

    def _expiry(self, now: _dt.datetime, lease_seconds: Any) -> str:
        seconds = _validate_duration(lease_seconds)
        try:
            return (now + _dt.timedelta(seconds=seconds)).isoformat(timespec="microseconds")
        except (OverflowError, ValueError) as error:
            raise PathLockError(
                "PATH_LOCK_INVALID_DURATION",
                "lock duration is outside the supported timestamp range",
            ) from error

    def lock(
        self,
        owner: str,
        paths: Iterable[str],
        lease_seconds: float = DEFAULT_LOCK_SECONDS,
        *,
        actor: str | None = None,
        now: Any = None,
        ttl: float | None = None,
    ) -> PathLockRecord:
        _validate_identity(owner, "owner", "PATH_LOCK_INVALID_OWNER")
        if ttl is not None:
            lease_seconds = ttl
        requested = self.normalize_paths(paths)
        with self._mutation():
            self._assert_no_pending_transaction()
            current_now = self._now(now)
            conflicts = self._conflicts(requested, self._read_all())
            if conflicts:
                self._raise_conflict(conflicts, current_now, operation="lock request")
            updated_at = _timestamp(current_now, field="updated_at")
            record = PathLockRecord(
                lock_id=uuid.uuid4().hex,
                channel=self.channel.name,
                owner=owner,
                paths=requested,
                expires_at=self._expiry(current_now, lease_seconds),
                locked_at=updated_at,
                updated_at=updated_at,
            )
            path = self._lock_path(record.lock_id)
            return self._run_transaction(
                operation="lock",
                event="path.locked",
                path=path,
                before=None,
                after=self._json_bytes(record),
                actor=actor or owner,
                record=record,
                apply=lambda: self._write_exclusive(path, record),
            )

    def _find_target(self, target: str) -> tuple[Path, PathLockRecord]:
        self._revalidate_storage()
        if isinstance(target, str) and _ID_RE.fullmatch(target):
            path = self._lock_path(target)
            if path.exists():
                return path, self._read_record(path)
        try:
            requested = self.normalize_paths([target])[0]
        except PathLockError:
            raise PathLockError(
                "PATH_LOCK_NOT_FOUND", f"lock record does not exist: {target}"
            )
        matches: list[tuple[Path, PathLockRecord]] = []
        for path in self.locks_dir.glob("*.json") if self.locks_dir.exists() else []:
            record = self._read_record(path)
            if any(item.normalized_path == requested.normalized_path for item in record.paths):
                matches.append((path, record))
        if not matches:
            raise PathLockError("PATH_LOCK_NOT_FOUND", f"lock record does not exist: {target}")
        if len(matches) > 1:
            raise PathLockError(
                "PATH_LOCK_CONFLICT",
                f"path target matches multiple lock records: {target}",
                lock_ids=[record.lock_id for _, record in matches],
            )
        return matches[0]

    def unlock(
        self,
        target: str,
        owner: str,
        *,
        actor: str | None = None,
    ) -> PathLockRecord:
        _validate_identity(owner, "owner", "PATH_LOCK_INVALID_OWNER")
        with self._mutation():
            self._assert_no_pending_transaction()
            path, record = self._find_target(target)
            if record.owner != owner:
                raise PathLockError(
                    "PATH_LOCK_OWNER_MISMATCH",
                    f"lock {record.lock_id} belongs to {record.owner}",
                    lock_id=record.lock_id,
                    owner=owner,
                    current_owner=record.owner,
                )
            try:
                previous = path.read_bytes()
            except (OSError, UnicodeError) as error:
                raise _storage_error("lock read for unlock", error) from error

            def apply() -> bool:
                try:
                    path.unlink()
                    self._fsync_directory(path.parent)
                    return True
                except (OSError, UnicodeError) as error:
                    raise _storage_error("lock removal", error) from error

            return self._run_transaction(
                operation="unlock",
                event="path.lock.unlocked",
                path=path,
                before=previous,
                after=None,
                actor=actor or owner,
                record=record,
                apply=apply,
            )

    def recover(
        self,
        target: str,
        owner: str,
        reason: str,
        lease_seconds: float = DEFAULT_LOCK_SECONDS,
        *,
        actor: str | None = None,
        now: Any = None,
        ttl: float | None = None,
    ) -> PathLockRecord:
        _validate_identity(owner, "owner", "PATH_LOCK_INVALID_OWNER")
        _validate_reason(reason)
        if ttl is not None:
            lease_seconds = ttl
        with self._mutation():
            self._assert_no_pending_transaction()
            path, previous = self._find_target(target)
            current_now = self._now(now)
            if not _is_expired(previous.expires_at, current_now):
                raise PathLockError(
                    "PATH_LOCK_NOT_STALE",
                    f"lock {previous.lock_id} is still active",
                    lock_id=previous.lock_id,
                    owner=previous.owner,
                    expires_at=previous.expires_at,
                )
            conflicts = self._conflicts(
                previous.paths, self._read_all(), ignore_lock_id=previous.lock_id
            )
            if conflicts:
                self._raise_conflict(conflicts, current_now, operation="recovery request")
            updated_at = _timestamp(current_now, field="updated_at")
            recovered = PathLockRecord(
                lock_id=previous.lock_id,
                channel=previous.channel,
                owner=owner,
                paths=previous.paths,
                expires_at=self._expiry(current_now, lease_seconds),
                locked_at=updated_at,
                updated_at=updated_at,
                previous_owner=previous.owner,
                previous_expires_at=previous.expires_at,
                recovery_reason=reason,
            )
            try:
                old_bytes = path.read_bytes()
            except (OSError, UnicodeError) as error:
                raise _storage_error("lock read for recovery", error) from error
            return self._run_transaction(
                operation="recover",
                event="path.lock.recovered",
                path=path,
                before=old_bytes,
                after=self._json_bytes(recovered),
                actor=actor or owner,
                record=recovered,
                previous=previous,
                details={
                    "previous_owner": previous.owner,
                    "previous_expires_at": previous.expires_at,
                    "recovery_reason": reason,
                },
                apply=lambda: self._write_atomic(path, recovered),
            )


# Module-level wrappers keep the public API easy to use from tests and clients.
def lock_paths(
    channel: Path | str,
    owner: str,
    paths: Iterable[str],
    *,
    root: Path | str | None = None,
    lease_seconds: float = DEFAULT_LOCK_SECONDS,
    actor: str | None = None,
    now: Any = None,
    ttl: float | None = None,
) -> PathLockRecord:
    return PathLockStore(channel, root=root).lock(
        owner, paths, lease_seconds, actor=actor, now=now, ttl=ttl
    )


def check_paths(
    channel: Path | str,
    paths: Iterable[str],
    *,
    root: Path | str | None = None,
    owner: str | None = None,
    ignore_lock_id: str | None = None,
) -> list[PathLockRecord]:
    return PathLockStore(channel, root=root).check(
        paths, owner=owner, ignore_lock_id=ignore_lock_id
    )


def unlock_paths(
    channel: Path | str,
    target: str,
    owner: str,
    *,
    root: Path | str | None = None,
    actor: str | None = None,
) -> PathLockRecord:
    return PathLockStore(channel, root=root).unlock(target, owner, actor=actor)


def recover_paths(
    channel: Path | str,
    target: str,
    owner: str,
    reason: str,
    *,
    root: Path | str | None = None,
    lease_seconds: float = DEFAULT_LOCK_SECONDS,
    actor: str | None = None,
    now: Any = None,
    ttl: float | None = None,
) -> PathLockRecord:
    return PathLockStore(channel, root=root).recover(
        target,
        owner,
        reason,
        lease_seconds,
        actor=actor,
        now=now,
        ttl=ttl,
    )
def recover_pending(
    channel: Path | str,
    *,
    root: Path | str | None = None,
    actor: str = "recovery",
    publication_resolution: str | None = None,
) -> None:
    PathLockStore(channel, root=root).recover_pending(
        actor=actor, publication_resolution=publication_resolution
    )


# Short aliases mirror the command names without shadowing PathLockStore methods.
lock = lock_paths
check = check_paths
unlock = unlock_paths
recover = recover_paths


__all__ = [
    "DEFAULT_LOCK_SECONDS",
    "LOCKS_DIRNAME",
    "LockRecord",
    "LockedPath",
    "PathLockError",
    "PathLockPath",
    "PathLockRecord",
    "PathLockStore",
    "check",
    "check_paths",
    "lock",
    "lock_paths",
    "recover",
    "recover_paths",
    "recover_pending",
    "unlock",
    "unlock_paths",
]
