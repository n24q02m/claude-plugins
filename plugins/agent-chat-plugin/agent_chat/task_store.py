"""Atomic JSON task persistence for Agent Chat channels.

Tasks are the source of truth.  Message files receive a small audit event for
each successful mutation, but loading/listing/updating never parses messages.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator, Mapping

import chat

from .task_model import (
    TASK_FIELDS,
    TaskError,
    TaskRecord,
    TaskValidationError,
    validate_task,
    validate_transition,
)


TASK_DIRNAME = "tasks"


class TaskStore:
    """Read and mutate authoritative task records below one channel folder."""

    def __init__(
        self,
        channel: Path | str,
        root: Path | str | None = None,
    ):
        self.channel = Path(channel)
        configured_root = root
        if configured_root is None:
            configured_root = os.environ.get("AGENT_CHAT_ROOT")
        self.root = Path(configured_root) if configured_root else self.channel.parent
        self._assert_inside_root(self.channel)
        if not self.channel.is_dir() or not (self.channel / "_meta.json").is_file():
            raise TaskValidationError(
                "TASK_CHANNEL_NOT_FOUND",
                f"channel does not contain _meta.json: {self.channel}",
            )
        self._assert_inside_channel(self.channel / TASK_DIRNAME)

    @property
    def tasks_dir(self) -> Path:
        return self.channel / TASK_DIRNAME

    def _assert_inside_root(self, path: Path) -> None:
        try:
            path.resolve(strict=False).relative_to(self.root.resolve(strict=False))
        except (OSError, RuntimeError, ValueError):
            raise TaskValidationError(
                "TASK_PATH_OUTSIDE_WORKSPACE",
                f"channel path escapes configured root: {path}",
            )

    def _assert_inside_channel(self, path: Path) -> None:
        try:
            path.resolve(strict=False).relative_to(self.channel.resolve(strict=False))
        except (OSError, RuntimeError, ValueError):
            raise TaskValidationError(
                "TASK_PATH_OUTSIDE_WORKSPACE",
                f"task storage path escapes channel workspace: {path}",
            )

    def _ensure_tasks_dir(self) -> Path:
        self._assert_inside_channel(self.tasks_dir)
        if self.tasks_dir.exists() and not self.tasks_dir.is_dir():
            raise TaskValidationError(
                "TASK_STORAGE_INVALID",
                f"task storage is not a directory: {self.tasks_dir}",
            )
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        return self.tasks_dir

    def _acquire_mutation_lock(
        self, timeout: float = 10.0, stale: float = 30.0
    ) -> Path:
        lock = self.channel / "_tasks.lock"
        self._assert_inside_channel(lock)
        started = time.monotonic()
        while True:
            try:
                os.mkdir(lock)
                return lock
            except FileExistsError:
                try:
                    if time.time() - lock.stat().st_mtime > stale:
                        try:
                            os.rmdir(lock)
                        except OSError:
                            pass
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() - started > timeout:
                    raise TaskValidationError(
                        "TASK_LOCK_TIMEOUT",
                        "could not acquire task mutation lock",
                    )
                time.sleep(0.01)

    @staticmethod
    def _release_mutation_lock(lock: Path) -> None:
        try:
            os.rmdir(lock)
        except OSError:
            pass

    @contextmanager
    def _mutation_lock(self) -> Iterator[None]:
        lock = self._acquire_mutation_lock()
        try:
            yield
        finally:
            self._release_mutation_lock(lock)

    def _task_path(self, task_id: str) -> Path:
        if (
            not isinstance(task_id, str)
            or not task_id
            or any(ch in task_id for ch in "/\\:")
            or task_id in {".", ".."}
            or task_id.startswith((".", "_"))
            or not all(ch.isalnum() or ch in "._-" for ch in task_id)
            or not task_id[0].isalnum()
        ):
            raise TaskValidationError(
                "TASK_INVALID_ID", f"unsafe task id: {task_id!r}"
            )
        path = self.tasks_dir / f"{task_id}.json"
        self._assert_inside_channel(path)
        return path

    def _read_path(self, path: Path) -> TaskRecord:
        self._assert_inside_channel(path)
        try:
            with path.open("r", encoding="utf-8") as stream:
                raw = json.load(stream)
        except FileNotFoundError:
            raise TaskValidationError(
                "TASK_NOT_FOUND", f"task record does not exist: {path.stem}"
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise TaskValidationError(
                "TASK_INVALID_RECORD",
                f"could not read task record {path.name}: {error}",
            )
        task = validate_task(raw, workspace=self.channel)
        if task.id != path.stem:
            raise TaskValidationError(
                "TASK_RECORD_ID_MISMATCH",
                f"task id {task.id!r} does not match filename {path.name!r}",
            )
        if task.channel != self.channel.name:
            raise TaskValidationError(
                "TASK_CHANNEL_MISMATCH",
                f"task channel {task.channel!r} does not match {self.channel.name!r}",
            )
        return task

    def _read_all(self) -> list[TaskRecord]:
        if not self.tasks_dir.exists():
            return []
        if not self.tasks_dir.is_dir():
            raise TaskValidationError(
                "TASK_STORAGE_INVALID",
                f"task storage is not a directory: {self.tasks_dir}",
            )
        records = []
        for path in sorted(self.tasks_dir.glob("*.json"), key=lambda item: item.name):
            if path.name.startswith((".", "_")):
                continue
            self._assert_inside_channel(path)
            records.append(self._read_path(path))
        return records

    def _read_snapshot(self) -> list[TaskRecord]:
        records = self._read_all()
        self._validate_graph(records)
        return records

    @staticmethod
    def _validate_graph(records: list[TaskRecord]) -> None:
        by_id: dict[str, TaskRecord] = {}
        for record in records:
            if record.id in by_id:
                raise TaskValidationError(
                    "TASK_DUPLICATE_ID", f"duplicate task id: {record.id}"
                )
            by_id[record.id] = record

        for record in records:
            for dependency in record.depends_on:
                if dependency not in by_id:
                    raise TaskValidationError(
                        "TASK_UNKNOWN_DEPENDENCY",
                        f"task {record.id} references unknown dependency {dependency}",
                        task_id=record.id,
                        dependency=dependency,
                    )

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise TaskValidationError(
                    "TASK_DEPENDENCY_CYCLE",
                    f"dependency cycle includes task {task_id}",
                    task_id=task_id,
                )
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency in by_id[task_id].depends_on:
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in sorted(by_id):
            visit(task_id)

    def validate(self, value: TaskRecord | Mapping[str, Any]) -> TaskRecord:
        task = validate_task(value, workspace=self.channel)
        if task.channel != self.channel.name:
            raise TaskValidationError(
                "TASK_CHANNEL_MISMATCH",
                f"task channel {task.channel!r} does not match {self.channel.name!r}",
            )
        return task

    @staticmethod
    def _dependency_blockers(
        task: TaskRecord, records: list[TaskRecord]
    ) -> list[str]:
        statuses = {record.id: record.status for record in records}
        return [
            dependency
            for dependency in task.depends_on
            if statuses.get(dependency) != "done"
        ]

    def dependency_statuses(self, task_id: str) -> dict[str, str]:
        """Return dependency statuses from the authoritative task snapshot."""

        path = self._task_path(task_id)
        with self._mutation_lock():
            records = self._read_snapshot()
            tasks = {record.id: record for record in records}
            task = tasks.get(path.stem)
            if task is None:
                raise TaskValidationError(
                    "TASK_NOT_FOUND", f"task record does not exist: {task_id}"
                )
            return {
                dependency: tasks[dependency].status
                for dependency in task.depends_on
            }

    def dependencies_ready(self, task_id: str) -> bool:
        """Report readiness using task records, never message text."""

        path = self._task_path(task_id)
        with self._mutation_lock():
            records = self._read_snapshot()
            tasks = {record.id: record for record in records}
            task = tasks.get(path.stem)
            if task is None:
                raise TaskValidationError(
                    "TASK_NOT_FOUND", f"task record does not exist: {task_id}"
                )
            return not self._dependency_blockers(task, records)

    def _assert_dependencies_ready(
        self, task: TaskRecord, records: list[TaskRecord]
    ) -> None:
        blockers = self._dependency_blockers(task, records)
        if blockers:
            raise TaskValidationError(
                "TASK_DEPENDENCY_NOT_READY",
                f"task {task.id} depends on unfinished tasks: {', '.join(blockers)}",
                task_id=task.id,
                dependencies=blockers,
            )



    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        """Best-effort directory durability after an atomic replace."""

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

    def _atomic_write(self, path: Path, task: TaskRecord) -> None:
        directory = path.parent
        directory.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{path.stem}.", suffix=".tmp", dir=str(directory)
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(
                    task.to_dict(),
                    stream,
                    ensure_ascii=False,
                    indent=2,
                    separators=(",", ": "),
                )
                stream.write("\n")
                stream.flush()
                try:
                    os.fsync(stream.fileno())
                except OSError:
                    pass
            os.replace(temporary, path)
            self._fsync_directory(directory)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _post_event(
        self,
        event: str,
        task: TaskRecord,
        *,
        actor: str | None,
        previous: TaskRecord | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "event": event,
            "task_id": task.id,
            "channel": task.channel,
            "status": task.status,
            "owner": task.owner,
            "lease_expires_at": task.lease_expires_at,
            "updated_at": task.updated_at,
        }
        if previous is not None:
            previous_data = previous.to_dict()
            current_data = task.to_dict()
            payload["previous_status"] = previous.status
            payload["changed_fields"] = sorted(
                field
                for field in TASK_FIELDS
                if previous_data[field] != current_data[field]
            )
        if details:
            payload.update(details)
        body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        sender = actor or task.created_by
        args = SimpleNamespace(
            channel=self.channel.name,
            sender=sender,
            to="all",
            title=f"{event} {task.id}",
            reply=None,
            status=event,
            body=body,
            body_file=None,
        )
        try:
            chat.cmd_post(self.channel.parent, args)
        except (chat.AgentChatError, OSError, UnicodeError) as error:
            raise TaskError(
                "TASK_AUDIT_FAILED",
                f"task record changed but audit event could not be written: {error}",
                event=event,
                task_id=task.id,
            )

    def create(
        self,
        task: TaskRecord | Mapping[str, Any],
        actor: str | None = None,
    ) -> TaskRecord:
        candidate = self.validate(task)
        path = self._task_path(candidate.id)
        with self._mutation_lock():
            if path.exists():
                raise TaskValidationError(
                    "TASK_ALREADY_EXISTS",
                    f"task record already exists: {candidate.id}",
                    task_id=candidate.id,
                )
            records = self._read_all()
            self._validate_graph(records + [candidate])
            if candidate.status in {"in_progress", "done"}:
                self._assert_dependencies_ready(candidate, records + [candidate])
            self._ensure_tasks_dir()
            self._atomic_write(path, candidate)
            try:
                self._post_event("task.created", candidate, actor=actor)
            except Exception as error:
                try:
                    path.unlink()
                    self._fsync_directory(path.parent)
                except Exception as rollback_error:
                    raise TaskError(
                        "TASK_AUDIT_ROLLBACK_FAILED",
                        f"could not roll back task create: {rollback_error}",
                        task_id=candidate.id,
                    ) from rollback_error
                if isinstance(error, TaskError):
                    raise
                raise TaskError(
                    "TASK_AUDIT_FAILED",
                    f"task create audit failed: {error}",
                    task_id=candidate.id,
                ) from error
        return candidate

    def load(self, task_id: str) -> TaskRecord:
        path = self._task_path(task_id)
        with self._mutation_lock():
            for record in self._read_snapshot():
                if record.id == path.stem:
                    return record
        raise TaskValidationError(
            "TASK_NOT_FOUND", f"task record does not exist: {task_id}"
        )

    def show(self, task_id: str) -> TaskRecord:
        return self.load(task_id)

    def show_with_dependencies(
        self, task_id: str
    ) -> tuple[TaskRecord, dict[str, str], bool]:
        """Return task record, dependency statuses, and readiness under one lock."""
        path = self._task_path(task_id)
        with self._mutation_lock():
            records = self._read_snapshot()
            tasks = {record.id: record for record in records}
            task = tasks.get(path.stem)
            if task is None:
                raise TaskValidationError(
                    "TASK_NOT_FOUND", f"task record does not exist: {task_id}"
                )
            statuses = {
                dependency: tasks[dependency].status
                for dependency in task.depends_on
            }
            ready = not self._dependency_blockers(task, records)
            return task, statuses, ready

    def list(self) -> list[TaskRecord]:
        with self._mutation_lock():
            return self._read_snapshot()

    def _assert_lease_update_allowed(
        self,
        current: TaskRecord,
        updates: Mapping[str, Any],
        actor: str | None,
    ) -> None:
        """Prevent generic updates from bypassing an active lease."""

        from .lease_store import LeaseError, LeaseStore, _is_expired

        leases = LeaseStore(self.channel, root=self.root)
        claim = leases._current_claim(current.id)
        if claim is None:
            leases._assert_consistent(current, None)
            return
        leases._assert_consistent(current, claim)
        _, record = claim
        now = leases._now()
        if _is_expired(record.lease_expires_at, now):
            raise LeaseError(
                "LEASE_RECOVERY_REQUIRED",
                f"expired lease for task {current.id} requires explicit recovery",
                task_id=current.id,
                previous_owner=record.owner,
                previous_lease_expires_at=record.lease_expires_at,
            )
        if actor != record.owner:
            raise LeaseError(
                "LEASE_OWNER_MISMATCH",
                f"lease for task {current.id} belongs to {record.owner}",
                task_id=current.id,
                owner=actor,
                current_owner=record.owner,
            )
        protected = {"owner", "lease_expires_at"}.intersection(updates)
        status_change = "status" in updates and updates["status"] != current.status
        if protected or status_change:
            raise LeaseError(
                "LEASE_MUTATION_REQUIRED",
                f"task {current.id} must be changed through its lease operation",
                task_id=current.id,
                protected_fields=sorted(
                    protected | ({"status"} if status_change else set())
                ),
            )
    def update(
        self,
        task_id: str,
        changes: Mapping[str, Any] | TaskRecord | None = None,
        actor: str | None = None,
        **fields: Any,
    ) -> TaskRecord:
        path = self._task_path(task_id)
        updates: dict[str, Any] = {}
        if isinstance(changes, TaskRecord):
            updates.update(changes.to_dict())
        elif changes is not None:
            if not isinstance(changes, Mapping):
                raise TaskValidationError(
                    "TASK_INVALID_UPDATE", "task update must be a mapping"
                )
            updates.update(changes)
        overlap = set(updates).intersection(fields)
        if overlap:
            raise TaskValidationError(
                "TASK_INVALID_UPDATE",
                f"duplicate update fields: {', '.join(sorted(overlap))}",
            )
        updates.update(fields)

        with self._mutation_lock():
            current = self._read_path(path)
            self._assert_lease_update_allowed(current, updates, actor)
            if "id" in updates and updates["id"] != current.id:
                raise TaskValidationError(
                    "TASK_ID_IMMUTABLE", "task id cannot be changed"
                )
            if "channel" in updates and updates["channel"] != current.channel:
                raise TaskValidationError(
                    "TASK_CHANNEL_IMMUTABLE", "task channel cannot be changed"
                )
            merged = current.to_dict()
            merged.update(updates)
            if "updated_at" not in updates:
                merged["updated_at"] = chat.now_iso()
            candidate = self.validate(merged)
            validate_transition(current.status, candidate.status)
            records = self._read_all()
            replaced = [
                candidate if record.id == task_id else record for record in records
            ]
            self._validate_graph(replaced)
            if candidate.status in {"in_progress", "done"}:
                self._assert_dependencies_ready(candidate, replaced)
            self._atomic_write(path, candidate)
            try:
                self._post_event(
                    "task.updated",
                    candidate,
                    actor=actor,
                    previous=current,
                )
            except Exception as error:
                try:
                    self._atomic_write(path, current)
                except Exception as rollback_error:
                    raise TaskError(
                        "TASK_AUDIT_ROLLBACK_FAILED",
                        f"could not roll back task update: {rollback_error}",
                        task_id=candidate.id,
                    ) from rollback_error
                if isinstance(error, TaskError):
                    raise
                raise TaskError(
                    "TASK_AUDIT_FAILED",
                    f"task update audit failed: {error}",
                    task_id=candidate.id,
                ) from error
        return candidate


# Module-level functions keep the API useful for small callers and make the
# later CLI layer independent from the store's object lifetime.
def create_task(
    channel: Path | str,
    task: TaskRecord | Mapping[str, Any],
    actor: str | None = None,
    *,
    root: Path | str | None = None,
) -> TaskRecord:
    return TaskStore(channel, root=root).create(task, actor=actor)


def load_task(
    channel: Path | str,
    task_id: str,
    *,
    root: Path | str | None = None,
) -> TaskRecord:
    return TaskStore(channel, root=root).load(task_id)


def show_task(
    channel: Path | str,
    task_id: str,
    *,
    root: Path | str | None = None,
) -> TaskRecord:
    return TaskStore(channel, root=root).show(task_id)

def show_task_with_dependencies(
    channel: Path | str,
    task_id: str,
    *,
    root: Path | str | None = None,
) -> tuple[TaskRecord, dict[str, str], bool]:
    return TaskStore(channel, root=root).show_with_dependencies(task_id)



def list_tasks(
    channel: Path | str,
    *,
    root: Path | str | None = None,
) -> list[TaskRecord]:
    return TaskStore(channel, root=root).list()


def update_task(
    channel: Path | str,
    task_id: str,
    changes: Mapping[str, Any] | TaskRecord | None = None,
    actor: str | None = None,
    *,
    root: Path | str | None = None,
    **fields: Any,
) -> TaskRecord:
    return TaskStore(channel, root=root).update(
        task_id, changes, actor=actor, **fields
    )


def dependency_statuses(
    channel: Path | str,
    task_id: str,
    *,
    root: Path | str | None = None,
) -> dict[str, str]:
    return TaskStore(channel, root=root).dependency_statuses(task_id)


def dependencies_ready(
    channel: Path | str,
    task_id: str,
    *,
    root: Path | str | None = None,
) -> bool:
    return TaskStore(channel, root=root).dependencies_ready(task_id)


__all__ = [
    "TaskError",
    "TaskRecord",
    "TaskStore",
    "TaskValidationError",
    "create_task",
    "dependencies_ready",
    "dependency_statuses",
    "list_tasks",
    "load_task",
    "show_task",
    "show_task_with_dependencies",
    "update_task",
]
