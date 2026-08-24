"""Deterministic derived state summary and non-destructive compaction for Agent Chat channels.

State records are derived summaries of channel history and structured task/lock
records.  ``state.md`` is never authoritative: compaction never deletes or
mutates authoritative messages, task records, claim records, path locks, or
read cursors.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import chat
from .path_locks import PathLockRecord, PathLockStore
from .task_model import TaskRecord
from .task_store import TaskStore


STATE_FILENAME = "state.md"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


class StateError(chat.AgentChatError):
    """Stable machine-readable state summary error."""

    def __init__(self, code: str, message: str, **details: Any):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"{code}: {message}")


class StateValidationError(StateError):
    """Raised when channel state cannot be summarized or validated."""

def _require_safe_channel(channel: str | Path, root: Path | None = None) -> tuple[Path, str, Path]:
    if isinstance(channel, Path):
        raw_str = str(channel).replace("\\", "/")
        if ".." in raw_str.split("/") or "." in raw_str.split("/"):
            raise StateValidationError("STATE_INVALID_CHANNEL", f"path traversal not allowed: '{channel}'")
        chan_path = channel
        channel_name = chan_path.name
        actual_root = Path(root) if root is not None else chan_path.parent
    else:
        channel_name = str(channel).strip()
        if not channel_name or "/" in channel_name or "\\" in channel_name or channel_name in {".", ".."}:
            raise StateValidationError("STATE_INVALID_CHANNEL", f"invalid channel name: '{channel}'")
        if not _ID_RE.fullmatch(channel_name):
            raise StateValidationError("STATE_INVALID_CHANNEL", f"invalid channel name format: '{channel}'")
        actual_root = Path(root) if root is not None else chat.root_dir(None)
        chan_path = actual_root / channel_name

    try:
        chat._check_safe_name(channel_name, "channel")
    except Exception as error:
        raise StateValidationError("STATE_INVALID_CHANNEL", str(error)) from error

    try:
        chan_path.resolve(strict=False).relative_to(actual_root.resolve(strict=False))
    except (OSError, RuntimeError, ValueError) as error:
        raise StateValidationError("STATE_INVALID_CHANNEL", f"channel path escapes root: '{channel}'") from error

    return chan_path, channel_name, actual_root


@dataclass(frozen=True)
class DecisionRecord:
    """One decision recorded in a message or task."""

    seq: int
    title: str
    author: str
    time: str
    details: str
    source: str = "message"

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "title": self.title,
            "author": self.author,
            "time": self.time,
            "details": self.details,
            "source": self.source,
        }


@dataclass(frozen=True)
class BlockerRecord:
    """One blocker identified from tasks, messages, or locks."""

    kind: str
    source_id: str
    title: str
    details: str
    author: str | None = None
    time: str | None = None
    blocking_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "source_id": self.source_id,
            "title": self.title,
            "details": self.details,
            "author": self.author,
            "time": self.time,
            "blocking_items": list(self.blocking_items),
        }


@dataclass(frozen=True)
class OwnerAssignment:
    """One owner's active task assignments and path locks."""

    owner: str
    tasks: list[dict[str, Any]] = field(default_factory=list)
    path_locks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "tasks": list(self.tasks),
            "path_locks": list(self.path_locks),
        }


@dataclass(frozen=True)
class VerificationRecord:
    """One verification evidence entry extracted from messages or completed tasks."""

    source_type: str
    source_id: str
    author: str
    time: str
    title: str
    evidence: str
    acceptance: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "author": self.author,
            "time": self.time,
            "title": self.title,
            "evidence": self.evidence,
            "acceptance": list(self.acceptance),
        }


@dataclass(frozen=True)
class StateSummary:
    """The aggregate, deterministic state summary for one channel."""

    channel: str
    topic: str
    members: list[str]
    created_at: str
    last_seq: int
    decisions: list[DecisionRecord]
    open_tasks: list[TaskRecord]
    blockers: list[BlockerRecord]
    owners: dict[str, OwnerAssignment]
    path_locks: list[PathLockRecord]
    verification: list[VerificationRecord]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "topic": self.topic,
            "members": list(self.members),
            "created_at": self.created_at,
            "last_seq": self.last_seq,
            "generated_at": self.generated_at,
            "decisions": [d.to_dict() for d in self.decisions],
            "open_tasks": [t.to_dict() for t in self.open_tasks],
            "blockers": [b.to_dict() for b in self.blockers],
            "owners": {k: v.to_dict() for k, v in self.owners.items()},
            "path_locks": [lock.to_dict() for lock in self.path_locks],
            "verification": [v.to_dict() for v in self.verification],
        }

    def render_markdown(self, now: str | None = None) -> str:
        """Render the deterministic Markdown state document."""
        lines: list[str] = []

        # Header
        lines.append(f"# State: {self.channel}")
        lines.append("")

        # Section 1: Goal & Topic
        lines.append("## Goal & Topic")
        lines.append(f"- **Channel**: {self.channel}")
        topic_display = self.topic.strip() if self.topic else "(none)"
        lines.append(f"- **Topic**: {topic_display}")
        members_str = ", ".join(sorted(self.members)) if self.members else "(none)"
        lines.append(f"- **Members**: {members_str}")
        lines.append(f"- **Last Message Sequence**: #{self.last_seq:04d}")
        lines.append("")

        # Section 2: Decisions
        lines.append("## Decisions")
        if self.decisions:
            for d in sorted(self.decisions, key=lambda x: x.seq):
                lines.append(f"- `[#{d.seq:04d}]` **{d.title}** (by `{d.author}` at `{d.time}`):")
                clean_details = d.details.strip()
                if clean_details:
                    for line in clean_details.splitlines():
                        lines.append(f"  {line}")
                else:
                    lines.append("  *(no additional details)*")
        else:
            lines.append("*(none)*")
        lines.append("")

        # Section 3: Open Tasks
        lines.append("## Open Tasks")
        if self.open_tasks:
            for t in sorted(self.open_tasks, key=lambda x: x.id):
                lines.append(f"- `[{t.id}]` **{t.title}** (`{t.status}`)")
                lines.append(f"  - **Owner**: `{t.owner or 'unassigned'}`")
                lines.append(f"  - **Lease**: `{t.lease_expires_at or 'none'}`")
                deps_str = ", ".join(sorted(t.depends_on)) if t.depends_on else "none"
                lines.append(f"  - **Depends on**: `{deps_str}`")
                hints_str = ", ".join(sorted(t.files_hint)) if t.files_hint else "none"
                lines.append(f"  - **Files hint**: `{hints_str}`")
                acc_str = ", ".join(t.acceptance) if t.acceptance else "none"
                lines.append(f"  - **Acceptance**: `{acc_str}`")
        else:
            lines.append("*(none)*")
        lines.append("")

        # Section 4: Blockers
        lines.append("## Blockers")
        if self.blockers:
            for b in sorted(self.blockers, key=lambda x: (x.kind, x.source_id)):
                author_part = f" (by `{b.author}`)" if b.author else ""
                lines.append(f"- `[{b.source_id}]` **{b.title}**{author_part}: {b.details}")
        else:
            lines.append("*(none)*")
        lines.append("")

        # Section 5: Owners & Leases
        lines.append("## Owners & Leases")
        if self.owners:
            for owner in sorted(self.owners.keys()):
                assignment = self.owners[owner]
                lines.append(f"- **{owner}**:")
                if assignment.tasks:
                    for t in sorted(assignment.tasks, key=lambda x: x["id"]):
                        lease_part = f", lease expires: `{t['lease_expires_at']}`" if t.get("lease_expires_at") else ""
                        lines.append(f"  - Task `{t['id']}` (**{t['title']}**, status: `{t['status']}`{lease_part})")
                if assignment.path_locks:
                    for lock in sorted(
                        assignment.path_locks, key=lambda item: item["lock_id"]
                    ):
                        paths_str = ", ".join(sorted(lock["paths"]))
                        lines.append(
                            f"  - Path Lock `{lock['lock_id']}` (`{paths_str}`, expires: `{lock['expires_at']}`)"
                        )
        else:
            lines.append("*(none)*")
        lines.append("")

        # Section 6: Path Locks
        lines.append("## Path Locks")
        if self.path_locks:
            for lock in sorted(self.path_locks, key=lambda item: item.lock_id):
                paths_str = ", ".join(
                    sorted(
                        path.normalized_path.replace("\\", "/")
                        for path in lock.paths
                    )
                )
                lines.append(
                    f"- `[{lock.lock_id}]` `{paths_str}` (owner: `{lock.owner}`, expires: `{lock.expires_at}`)"
                )
        else:
            lines.append("*(none)*")
        lines.append("")

        # Section 7: Verification Evidence
        lines.append("## Verification Evidence")
        if self.verification:
            for v in sorted(self.verification, key=lambda x: (x.time, x.source_id)):
                if v.source_type == "message":
                    lines.append(f"- `[#{int(v.source_id):04d}]` **{v.title}** (by `{v.author}` at `{v.time}`):")
                    clean_evidence = v.evidence.strip()
                    if clean_evidence:
                        for line in clean_evidence.splitlines():
                            lines.append(f"  > {line}")
                else:
                    lines.append(f"- `[{v.source_id}]` **{v.title}** (verified by `{v.author}` at `{v.time}`):")
                    if v.acceptance:
                        lines.append(f"  - Acceptance criteria: {', '.join(v.acceptance)}")
                    if v.evidence:
                        for line in v.evidence.strip().splitlines():
                            lines.append(f"  > {line}")
        else:
            lines.append("*(none)*")
        lines.append("")

        return "\n".join(lines)


class StateStore:
    """Derives and compacts channel state summaries deterministically."""

    def __init__(self, channel: str | Path, root: Path | None = None):
        self.channel, self.channel_name, self.root = _require_safe_channel(channel, root=root)

    def _assert_channel_exists(self) -> None:
        if not self.channel.exists() or not self.channel.is_dir():
            raise StateValidationError(
                "STATE_CHANNEL_NOT_FOUND",
                f"channel directory not found: '{self.channel_name}'",
                channel=self.channel_name,
            )

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        try:
            fd = os.open(str(directory), os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(fd)
        except OSError:
            pass
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def summarize(self, strict: bool = False, now: str | None = None) -> StateSummary:
        """Extract and aggregate all channel state from authoritative sources."""
        self._assert_channel_exists()

        # 1. Channel metadata
        meta_file = self.channel / "_meta.json"
        if not meta_file.exists():
            # Try alternate fallback meta.json
            alt_meta = self.channel / "meta.json"
            meta_file = alt_meta if alt_meta.exists() else meta_file

        topic = ""
        members: list[str] = []
        created_at = ""

        if meta_file.exists():
            try:
                content = meta_file.read_text(encoding="utf-8")
                raw_meta = json.loads(content)
                if not isinstance(raw_meta, dict):
                    if strict:
                        raise StateValidationError(
                            "STATE_INVALID_RECORD",
                            "_meta.json must be a JSON object",
                            path=str(meta_file),
                        )
                else:
                    topic = str(raw_meta.get("topic") or "")
                    raw_members = raw_meta.get("members") or []
                    if isinstance(raw_members, list):
                        members = [str(m).strip() for m in raw_members if str(m).strip()]
                    created_at = str(raw_meta.get("created_at") or "")
            except (json.JSONDecodeError, UnicodeError) as error:
                if strict:
                    raise StateValidationError(
                        "STATE_MALFORMED_SOURCE",
                        f"corrupted _meta.json: {error}",
                        path=str(meta_file),
                    ) from error

        # 2. Messages: extract decisions, blockers, verifications
        msg_files = chat.message_files(self.channel)
        last_seq = chat.max_seq(self.channel)

        decisions: list[DecisionRecord] = []
        message_blockers: list[BlockerRecord] = []
        verifications: list[VerificationRecord] = []
        completion_actors: dict[str, str] = {}

        for p in msg_files:
            seq = chat._seq_from_name(p.name) or 0
            try:
                meta = chat.parse_frontmatter(p)
                raw_text = p.read_text(encoding="utf-8")
                parts = raw_text.split("---", 2)
                body = parts[2].strip() if len(parts) >= 3 else raw_text.strip()
            except Exception as error:
                if strict:
                    raise StateValidationError(
                        "STATE_MALFORMED_SOURCE",
                        f"malformed message file {p.name}: {error}",
                        path=str(p),
                    ) from error
                continue

            author = str(meta.get("from") or "unknown")
            time_val = str(meta.get("time") or meta.get("ts") or "")
            title = str(meta.get("title") or p.stem)
            msg_type = str(meta.get("type") or "").lower()
            msg_status = str(meta.get("status") or "").lower()

            if msg_status in {"lease.completed", "task.updated"}:
                try:
                    audit_event = json.loads(body)
                except json.JSONDecodeError:
                    audit_event = None
                if (
                    isinstance(audit_event, dict)
                    and audit_event.get("event") == msg_status
                    and audit_event.get("status") == "done"
                    and isinstance(audit_event.get("task_id"), str)
                ):
                    completion_actors[audit_event["task_id"]] = author

            # Check Decision
            is_decision = (
                msg_type == "decision"
                or msg_status == "decision"
                or "decision" in meta
                or title.lower().startswith("decision:")
                or title.lower().startswith("[decision]")
                or re.search(r"^#+\s*Decision\b", body, re.IGNORECASE | re.MULTILINE) is not None
            )
            if is_decision:
                clean_title = re.sub(r"^decision:\s*", "", title, flags=re.IGNORECASE).strip()
                decisions.append(
                    DecisionRecord(
                        seq=seq,
                        title=clean_title or title,
                        author=author,
                        time=time_val,
                        details=body,
                        source=f"message:{seq:04d}",
                    )
                )

            # Check Blocker
            is_blocker = (
                msg_type in {"blocker", "blocked"}
                or msg_status in {"blocker", "blocked"}
                or "blocker" in meta
                or title.lower().startswith("blocker:")
                or title.lower().startswith("[blocker]")
                or re.search(r"^#+\s*Blocker\b", body, re.IGNORECASE | re.MULTILINE) is not None
            )
            if is_blocker:
                clean_title = re.sub(r"^blocker:\s*", "", title, flags=re.IGNORECASE).strip()
                message_blockers.append(
                    BlockerRecord(
                        kind="message",
                        source_id=f"#{seq:04d}",
                        title=clean_title or title,
                        details=body,
                        author=author,
                        time=time_val,
                    )
                )

            # Check Verification Evidence
            is_verification = (
                msg_type in {"verification", "evidence", "test"}
                or msg_status in {"verified", "verified-by", "verification"}
                or "verification" in meta
                or "evidence" in meta
                or title.lower().startswith("verification:")
                or title.lower().startswith("evidence:")
                or title.lower().startswith("[verification]")
                or re.search(r"^#+\s*(Verification|Evidence)\b", body, re.IGNORECASE | re.MULTILINE) is not None
            )
            if is_verification:
                clean_title = re.sub(r"^(verification|evidence):\s*", "", title, flags=re.IGNORECASE).strip()
                verifications.append(
                    VerificationRecord(
                        source_type="message",
                        source_id=str(seq),
                        author=author,
                        time=time_val,
                        title=clean_title or title,
                        evidence=body,
                    )
                )

        # 3. Tasks: load through the authoritative store so workspace and graph
        # validation match the task protocol rather than a second parser.
        task_store = TaskStore(self.channel, root=self.root)
        all_tasks: list[TaskRecord] = []
        open_tasks: list[TaskRecord] = []
        task_blockers: list[BlockerRecord] = []

        try:
            all_tasks = task_store.list()
        except Exception as error:
            if strict:
                raise StateValidationError(
                    "STATE_MALFORMED_SOURCE",
                    f"malformed task source: {error}",
                    channel=self.channel_name,
                ) from error

            # Lenient mode keeps valid records available while ignoring only
            # records that cannot satisfy the authoritative task contract.
            tasks_dir = self.channel / "tasks"
            if tasks_dir.exists() and tasks_dir.is_dir():
                for path in sorted(tasks_dir.glob("*.json"), key=lambda item: item.name):
                    try:
                        resolved = path.resolve(strict=False)
                        resolved.relative_to(tasks_dir.resolve(strict=False))
                        raw_task = json.loads(path.read_text(encoding="utf-8"))
                        all_tasks.append(
                            TaskRecord.from_dict(raw_task, workspace=self.channel)
                        )
                    except Exception:
                        continue

        # Map completed task IDs
        done_task_ids = {t.id for t in all_tasks if t.status == "done"}
        status_map = {t.id: t.status for t in all_tasks}

        for t in all_tasks:
            if t.status in {"open", "in_progress", "blocked"}:
                open_tasks.append(t)

            # Check task blockers
            if t.status == "blocked":
                task_blockers.append(
                    BlockerRecord(
                        kind="task_status",
                        source_id=t.id,
                        title=f"Task {t.id} blocked ({t.title})",
                        details="Task is marked with status 'blocked'",
                        author=t.owner or t.created_by,
                        time=t.updated_at,
                    )
                )
            # Check dependency blockers
            unfinished_deps = [dep for dep in t.depends_on if dep not in done_task_ids]
            if unfinished_deps:
                dep_details = ", ".join(f"{dep} (status: {status_map.get(dep, 'unknown')})" for dep in unfinished_deps)
                task_blockers.append(
                    BlockerRecord(
                        kind="task_dependency",
                        source_id=t.id,
                        title=f"Task {t.id} blocked on dependencies: {', '.join(unfinished_deps)}",
                        details=f"Unfinished dependencies: {dep_details}",
                        author=t.owner or t.created_by,
                        time=t.updated_at,
                        blocking_items=unfinished_deps,
                    )
                )

            # Check completed task verification evidence
            if t.status == "done":
                verifications.append(
                    VerificationRecord(
                        source_type="task",
                        source_id=t.id,
                        author=completion_actors.get(t.id, t.owner or t.created_by),
                        time=t.updated_at,
                        title=f"Task {t.id} completed: {t.title}",
                        evidence=f"Completed task criteria satisfied for {t.id}.",
                        acceptance=t.acceptance,
                    )
                )

        # 4. Path locks: use the validated store so storage containment,
        # symlink, record-shape, and platform normalization rules stay single
        # sourced in path_locks.py.
        lock_store = PathLockStore(self.channel, root=self.root)
        try:
            active_locks = lock_store.list()
        except Exception as error:
            if strict:
                raise StateValidationError(
                    "STATE_MALFORMED_SOURCE",
                    f"malformed path lock source: {error}",
                    channel=self.channel_name,
                ) from error
            active_locks = []
        # 5. Owners aggregation
        owners_map: dict[str, dict[str, list[Any]]] = {}

        for t in open_tasks:
            if t.owner:
                owners_map.setdefault(t.owner, {"tasks": [], "path_locks": []})
                owners_map[t.owner]["tasks"].append(
                    {
                        "id": t.id,
                        "title": t.title,
                        "status": t.status,
                        "lease_expires_at": t.lease_expires_at,
                    }
                )

        for lock in active_locks:
            if lock.owner:
                owners_map.setdefault(lock.owner, {"tasks": [], "path_locks": []})
                owners_map[lock.owner]["path_locks"].append(
                    {
                        "lock_id": lock.lock_id,
                        "paths": [
                            path.normalized_path.replace("\\", "/")
                            for path in lock.paths
                        ],
                        "expires_at": lock.expires_at,
                    }
                )

        owners: dict[str, OwnerAssignment] = {
            owner: OwnerAssignment(
                owner=owner,
                tasks=sorted(data["tasks"], key=lambda x: x["id"]),
                path_locks=sorted(data["path_locks"], key=lambda x: x["lock_id"]),
            )
            for owner, data in sorted(owners_map.items())
        }

        # Combine blockers
        all_blockers = task_blockers + message_blockers

        # Generated timestamp
        gen_time = now or chat.now_iso()

        return StateSummary(
            channel=self.channel_name,
            topic=topic,
            members=sorted(members),
            created_at=created_at,
            last_seq=last_seq,
            decisions=sorted(decisions, key=lambda x: x.seq),
            open_tasks=sorted(open_tasks, key=lambda x: x.id),
            blockers=sorted(all_blockers, key=lambda x: (x.kind, x.source_id)),
            owners=owners,
            path_locks=sorted(active_locks, key=lambda x: x.lock_id),
            verification=sorted(verifications, key=lambda x: (x.time, x.source_id)),
            generated_at=gen_time,
        )

    def render(self, strict: bool = False, now: str | None = None) -> str:
        """Extract and render deterministic Markdown state."""
        summary = self.summarize(strict=strict, now=now)
        return summary.render_markdown(now=now)

    def read_saved(self) -> str:
        """Read the currently saved state.md file from the channel directory."""
        self._assert_channel_exists()
        state_file = self.channel / STATE_FILENAME
        if not state_file.exists():
            raise StateValidationError(
                "STATE_RECORD_NOT_FOUND",
                f"saved state file not found: {state_file}",
                channel=self.channel_name,
            )
        try:
            return state_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise StateValidationError(
                "STATE_IO_ERROR",
                f"could not read state file: {error}",
                channel=self.channel_name,
            ) from error

    def compact(
        self,
        actor: str | None = None,
        audit: bool = True,
        strict: bool = False,
        now: str | None = None,
    ) -> StateSummary:
        """Derive state and atomically write state.md with an optional audit event."""
        self._assert_channel_exists()
        summary = self.summarize(strict=strict, now=now)
        rendered = summary.render_markdown(now=now)

        state_file = self.channel / STATE_FILENAME
        directory = self.channel

        # Atomic replacement via sibling temporary file
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{STATE_FILENAME}.tmp.", suffix=".tmp", dir=str(directory)
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(rendered)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
            os.replace(temporary, state_file)
            self._fsync_directory(directory)
        except (OSError, UnicodeError) as error:
            raise StateValidationError(
                "STATE_IO_ERROR",
                f"atomic write of state.md failed: {error}",
                channel=self.channel_name,
            ) from error
        finally:
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass

        # Post audit event if requested
        if audit:
            sender = actor or "system"
            audit_payload = {
                "event": "state.compacted",
                "channel": self.channel_name,
                "decisions_count": len(summary.decisions),
                "open_tasks_count": len(summary.open_tasks),
                "blockers_count": len(summary.blockers),
                "path_locks_count": len(summary.path_locks),
                "last_seq": summary.last_seq,
                "compacted_at": now or chat.now_iso(),
            }
            body = json.dumps(audit_payload, ensure_ascii=False, indent=2, sort_keys=True)
            args = SimpleNamespace(
                channel=self.channel_name,
                sender=sender,
                to="all",
                title="state.compacted",
                reply=None,
                status="state.compacted",
                body=body,
                body_file=None,
            )
            try:
                chat.cmd_post(self.root, args)
            except (chat.AgentChatError, OSError, UnicodeError) as error:
                raise StateError(
                    "STATE_AUDIT_FAILED",
                    f"state compacted but audit event could not be written: {error}",
                    channel=self.channel_name,
                ) from error

        return summary


# Module-level convenience functions
def load_state(channel: str | Path, root: Path | None = None, strict: bool = False) -> StateSummary:
    return StateStore(channel, root=root).summarize(strict=strict)


def render_state(
    channel: str | Path,
    root: Path | None = None,
    strict: bool = False,
    now: str | None = None,
) -> str:
    return StateStore(channel, root=root).render(strict=strict, now=now)


def compact_state(
    channel: str | Path,
    actor: str | None = None,
    audit: bool = True,
    root: Path | None = None,
    strict: bool = False,
    now: str | None = None,
) -> StateSummary:
    return StateStore(channel, root=root).compact(actor=actor, audit=audit, strict=strict, now=now)


__all__ = [
    "STATE_FILENAME",
    "StateError",
    "StateValidationError",
    "DecisionRecord",
    "BlockerRecord",
    "OwnerAssignment",
    "VerificationRecord",
    "StateSummary",
    "StateStore",
    "load_state",
    "render_state",
    "compact_state",
]
