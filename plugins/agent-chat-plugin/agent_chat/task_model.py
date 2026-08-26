"""Typed task records and validation for the Agent Chat task board.

The task JSON file is deliberately small and boring: one record, one stable
shape, and no derived state.  The store owns dependency-graph validation and
filesystem persistence; this module only validates an individual record and
its workspace-relative path hints.
"""

from __future__ import annotations

import datetime as _dt
import ntpath
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


TASK_FIELDS = (
    "id",
    "channel",
    "title",
    "status",
    "owner",
    "created_by",
    "depends_on",
    "files_hint",
    "acceptance",
    "lease_expires_at",
    "branch",
    "updated_at",
)

VALID_STATUSES = frozenset(
    {"open", "in_progress", "blocked", "done", "cancelled"}
)

# Same-state writes are intentionally idempotent.  ``open`` is the released
# state used by the later lease surface; ``done`` and ``cancelled`` are terminal.
STATUS_TRANSITIONS = {
    "open": frozenset({"open", "in_progress", "blocked", "cancelled"}),
    "in_progress": frozenset(
        {"in_progress", "open", "blocked", "done", "cancelled"}
    ),
    "blocked": frozenset({"blocked", "open", "in_progress", "cancelled"}),
    "done": frozenset({"done"}),
    "cancelled": frozenset({"cancelled"}),
}

_TASK_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_CHANNEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


class TaskError(Exception):
    """Base error with a public, machine-readable ``code`` attribute."""

    def __init__(self, code: str, message: str, **details: Any):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"{code}: {message}")


class TaskValidationError(TaskError):
    """Raised when a task record or state transition is invalid."""


def _error(code: str, message: str, **details: Any) -> TaskValidationError:
    return TaskValidationError(code, message, **details)


def _require_text(
    value: Any,
    field: str,
    *,
    allow_empty: bool = False,
    code: str | None = None,
) -> str:
    error_code = code or f"TASK_INVALID_{field.upper()}"
    if not isinstance(value, str):
        raise _error(error_code, f"{field} must be a string")
    if not allow_empty and not value.strip():
        raise _error(error_code, f"{field} must not be empty")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise _error(
            error_code,
            f"{field} contains a forbidden control character",
        )
    return value


def _validate_id(value: Any, field: str = "id") -> str:
    code = "TASK_INVALID_ID" if field == "id" else "TASK_INVALID_DEPENDENCY_ID"
    value = _require_text(value, field, code=code)
    if not _TASK_ID_RE.fullmatch(value):
        raise _error(
            code,
            f"{field} must contain only letters, digits, '.', '_' or '-'",
        )
    return value


def _validate_channel(value: Any) -> str:
    value = _require_text(value, "channel")
    if value in {".", ".."} or not _CHANNEL_RE.fullmatch(value):
        raise _error("TASK_INVALID_CHANNEL", "channel is not a safe channel name")
    if value.startswith((".", "_")):
        raise _error("TASK_INVALID_CHANNEL", "channel uses a reserved prefix")
    return value


def parse_timestamp(value: Any, *, field: str = "updated_at") -> str:
    """Validate an ISO-8601 timestamp carrying an explicit UTC offset."""

    if not isinstance(value, str) or not value.strip():
        raise _error("TASK_INVALID_TIMESTAMP", f"{field} must be an ISO-8601 string")
    candidate = value.strip()
    # ``datetime.fromisoformat`` accepted ``Z`` starting with Python 3.11;
    # normalize it so the stdlib API remains usable on older supported Python.
    parse_value = candidate[:-1] + "+00:00" if candidate.endswith(("Z", "z")) else candidate
    try:
        parsed = _dt.datetime.fromisoformat(parse_value)
    except (TypeError, ValueError):
        raise _error("TASK_INVALID_TIMESTAMP", f"{field} is not valid ISO-8601")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _error(
            "TASK_INVALID_TIMESTAMP",
            f"{field} must include an explicit UTC offset",
        )
    return value


def _path_error(path: Any, reason: str) -> TaskValidationError:
    return _error(
        "TASK_PATH_OUTSIDE_WORKSPACE",
        f"files_hint path is outside the channel workspace: {path!r} ({reason})",
        path=path,
    )


def validate_workspace_path(path: Any, workspace: Path | None = None) -> str:
    """Validate one workspace-relative path without rewriting its display form.

    Both POSIX and Windows separators are recognized regardless of the host
    platform.  When ``workspace`` is supplied, resolving existing symlink
    ancestors also protects paths whose final component does not exist yet.
    """

    if not isinstance(path, str) or not path or "\x00" in path:
        raise _path_error(path, "invalid path text")
    portable = path.replace("\\", "/")
    drive, _ = ntpath.splitdrive(portable)
    if drive or portable.startswith("/"):
        raise _path_error(path, "absolute paths are not allowed")
    parts = PurePosixPath(portable).parts
    if any(part == ".." for part in parts):
        raise _path_error(path, "parent traversal is not allowed")

    if workspace is not None:
        base = Path(workspace)
        try:
            base_resolved = base.resolve(strict=False)
            candidate = (base / Path(*parts)).resolve(strict=False)
            candidate.relative_to(base_resolved)
        except (OSError, RuntimeError, ValueError):
            raise _path_error(path, "resolved path escapes the workspace")
    return path


def _validate_list_of_text(
    value: Any,
    field: str,
    *,
    paths: bool = False,
    workspace: Path | None = None,
) -> list[str]:
    if not isinstance(value, list):
        raise _error(f"TASK_INVALID_{field.upper()}", f"{field} must be a JSON array")
    result: list[str] = []
    for item in value:
        if paths:
            result.append(validate_workspace_path(item, workspace))
        else:
            result.append(
                _require_text(
                    item,
                    field + " item",
                    allow_empty=False,
                    code=f"TASK_INVALID_{field.upper()}",
                )
            )
    return result


def _validate_values(values: Mapping[str, Any], *, workspace: Path | None = None) -> None:
    _validate_id(values["id"])
    _validate_channel(values["channel"])
    _require_text(values["title"], "title", allow_empty=True)

    status = values["status"]
    if not isinstance(status, str) or status not in VALID_STATUSES:
        raise _error("TASK_INVALID_STATUS", f"unknown task status: {status!r}")

    owner = values["owner"]
    if owner is not None:
        _require_text(owner, "owner")
    _require_text(values["created_by"], "created_by")

    depends_on = values["depends_on"]
    if not isinstance(depends_on, list):
        raise _error("TASK_INVALID_DEPENDS_ON", "depends_on must be a JSON array")
    seen: set[str] = set()
    for dependency in depends_on:
        dependency_id = _validate_id(dependency, "dependency")
        if dependency_id in seen:
            raise _error(
                "TASK_DUPLICATE_DEPENDENCY",
                f"dependency is listed more than once: {dependency_id}",
            )
        seen.add(dependency_id)

    _validate_list_of_text(
        values["files_hint"], "files_hint", paths=True, workspace=workspace
    )
    _validate_list_of_text(values["acceptance"], "acceptance")

    lease_expires_at = values["lease_expires_at"]
    if lease_expires_at is not None:
        parse_timestamp(lease_expires_at, field="lease_expires_at")
    branch = values["branch"]
    if branch is not None:
        _require_text(branch, "branch")
    parse_timestamp(values["updated_at"], field="updated_at")


def validate_transition(old_status: str, new_status: str) -> None:
    """Validate one state-machine edge, raising a stable error on rejection."""

    if old_status not in VALID_STATUSES or new_status not in VALID_STATUSES:
        raise _error(
            "TASK_INVALID_STATUS",
            f"unknown status transition {old_status!r} -> {new_status!r}",
        )
    if new_status not in STATUS_TRANSITIONS[old_status]:
        raise _error(
            "TASK_INVALID_TRANSITION",
            f"transition {old_status!r} -> {new_status!r} is not allowed",
            old_status=old_status,
            new_status=new_status,
        )


@dataclass(frozen=True)
class TaskRecord:
    """The authoritative, JSON-serializable task record."""

    id: str
    channel: str
    title: str
    status: str
    owner: str | None
    created_by: str
    depends_on: list[str]
    files_hint: list[str]
    acceptance: list[str]
    lease_expires_at: str | None
    branch: str | None
    updated_at: str

    def __post_init__(self) -> None:
        values = {
            "id": self.id,
            "channel": self.channel,
            "title": self.title,
            "status": self.status,
            "owner": self.owner,
            "created_by": self.created_by,
            "depends_on": self.depends_on,
            "files_hint": self.files_hint,
            "acceptance": self.acceptance,
            "lease_expires_at": self.lease_expires_at,
            "branch": self.branch,
            "updated_at": self.updated_at,
        }
        _validate_values(values)
        # Freeze the record boundary while retaining JSON's documented arrays.
        object.__setattr__(self, "depends_on", list(self.depends_on))
        object.__setattr__(self, "files_hint", list(self.files_hint))
        object.__setattr__(self, "acceptance", list(self.acceptance))

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], *, workspace: Path | None = None
    ) -> "TaskRecord":
        if not isinstance(data, Mapping):
            raise _error("TASK_INVALID_RECORD", "task record must be a JSON object")
        actual = set(data)
        required = set(TASK_FIELDS)
        missing = [field for field in TASK_FIELDS if field not in actual]
        if missing:
            raise _error(
                "TASK_REQUIRED_FIELD_MISSING",
                "required task field is missing",
                fields=missing,
            )
        unknown = sorted(actual - required)
        if unknown:
            raise _error(
                "TASK_UNKNOWN_FIELD",
                "task record contains unknown fields",
                fields=unknown,
            )
        _validate_values(data, workspace=workspace)
        return cls(*(data[field] for field in TASK_FIELDS))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel,
            "title": self.title,
            "status": self.status,
            "owner": self.owner,
            "created_by": self.created_by,
            "depends_on": list(self.depends_on),
            "files_hint": list(self.files_hint),
            "acceptance": list(self.acceptance),
            "lease_expires_at": self.lease_expires_at,
            "branch": self.branch,
            "updated_at": self.updated_at,
        }


def validate_task(
    value: TaskRecord | Mapping[str, Any], *, workspace: Path | None = None
) -> TaskRecord:
    """Return a validated ``TaskRecord`` from a record or JSON mapping."""

    if isinstance(value, TaskRecord):
        _validate_values(value.to_dict(), workspace=workspace)
        return value
    return TaskRecord.from_dict(value, workspace=workspace)


# Explicit aliases make the small public surface discoverable without creating
# a second representation or a compatibility-only code path.
Task = TaskRecord
parse_task = TaskRecord.from_dict
