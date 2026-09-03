#!/usr/bin/env python3
"""Focused contract tests for the portable harness adapter manifest schema."""

from __future__ import annotations

import functools
import ipaddress
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse


# Caching compiled regexes saves a massive amount of overhead during JSON schema validation.
# Because the same JSON schemas are evaluated repeatedly and the schemas use static regex
# patterns, calling re.search directly recompiles (or looks up in internal cache which
# is still slow compared to a bound method call on a compiled object).
@functools.lru_cache(maxsize=128)
def _compile_pattern(pattern: str) -> re.Pattern:
    return re.compile(pattern)


SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "harness-adapter.schema.json"
)


_TYPE_NAMES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _resolve_ref(root: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise AssertionError(f"Unsupported schema reference: {ref}")
    current = root
    for part in ref[2:].split("/"):
        current = current[part]
    return current


def _validate_json(
    instance, schema: dict, root: dict, path: str = "$", *, resolve=True
) -> list[str]:
    """Validate the JSON Schema subset used by the contract, without extra deps."""
    if resolve and "$ref" in schema:
        return _validate_json(instance, _resolve_ref(root, schema["$ref"]), root, path)

    errors: list[str] = []

    if "allOf" in schema:
        for index, subschema in enumerate(schema["allOf"]):
            errors.extend(_validate_json(instance, subschema, root, path))

    if "anyOf" in schema:
        branches = [
            _validate_json(instance, subschema, root, path)
            for subschema in schema["anyOf"]
        ]
        if not any(not branch_errors for branch_errors in branches):
            errors.append(f"{path}: does not match any allowed schema")

    if "oneOf" in schema:
        branches = [
            _validate_json(instance, subschema, root, path)
            for subschema in schema["oneOf"]
        ]
        if sum(not branch_errors for branch_errors in branches) != 1:
            errors.append(f"{path}: must match exactly one schema")

    if "not" in schema and not _validate_json(instance, schema["not"], root, path):
        errors.append(f"{path}: matches a forbidden schema")

    if "if" in schema:
        condition_matches = not _validate_json(instance, schema["if"], root, path)
        branch = schema.get("then" if condition_matches else "else")
        if branch is not None:
            errors.extend(_validate_json(instance, branch, root, path))

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected {schema['const']!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']!r}")

    expected_type = schema.get("type")
    if expected_type:
        expected = _TYPE_NAMES[expected_type]
        # bool is an int subclass, so keep JSON Schema's type distinction.
        if expected_type == "integer":
            valid_type = isinstance(instance, int) and not isinstance(instance, bool)
        elif expected_type == "number":
            valid_type = isinstance(instance, (int, float)) and not isinstance(
                instance, bool
            )
        else:
            valid_type = isinstance(instance, expected)
        if not valid_type:
            return errors + [f"{path}: expected type {expected_type}"]

    if isinstance(instance, dict):
        for required in schema.get("required", []):
            if required not in instance:
                errors.append(f"{path}: missing required property {required!r}")

        properties = schema.get("properties", {})
        for name, subschema in properties.items():
            if name in instance:
                errors.extend(
                    _validate_json(instance[name], subschema, root, f"{path}.{name}")
                )

        if schema.get("additionalProperties") is False:
            for name in instance:
                if name not in properties:
                    errors.append(
                        f"{path}: additional property {name!r} is not allowed"
                    )

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: expected at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: expected at most {schema['maxItems']} items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(instance):
                errors.extend(
                    _validate_json(item, item_schema, root, f"{path}[{index}]")
                )

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: expected at least {schema['minLength']} characters")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: expected at most {schema['maxLength']} characters")
        if (
            "pattern" in schema
            and _compile_pattern(schema["pattern"]).search(instance) is None
        ):
            errors.append(f"{path}: does not match required pattern")

    return errors


_SECRET_LITERAL = re.compile(
    r"(?:"
    r"sk-[A-Za-z0-9][A-Za-z0-9_-]{19,}|"
    r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20,}|"
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]+ PRIVATE KEY-----|"
    r"(?:password|secret|api[_-]?key|access[_-]?token|bearer)\s*[:=]\s*\S+"
    r")",
    re.IGNORECASE,
)
_TRAVERSAL = re.compile(r"(?:^|[/\\])\.\.(?:[/\\]|$)")
_ABSOLUTE_PATH = re.compile(r"(?:^[A-Za-z]:[/\\])|(?:^[/\\])|(?:^\\\\)|(?:^~[/\\])")


def _iter_strings(value, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def _security_errors(row: dict) -> list[str]:
    errors: list[str] = []
    for path, value in _iter_strings(row):
        if _SECRET_LITERAL.search(value):
            errors.append(f"{path}: secret-looking literal")
        if _TRAVERSAL.search(value):
            errors.append(f"{path}: path traversal")
        if _ABSOLUTE_PATH.search(value):
            errors.append(f"{path}: absolute/private path")
        if value.lower().startswith("https://"):
            host = urlparse(value).hostname
            if host:
                host_lower = host.lower().rstrip(".")
                private_host = host_lower in {
                    "localhost",
                    "ip6-localhost",
                    "internal",
                    "private",
                    "corp",
                    "staging",
                    "workspace",
                } or any(
                    label in {"internal", "private", "corp", "staging", "workspace"}
                    for label in host_lower.split(".")
                )
                try:
                    address = ipaddress.ip_address(host_lower)
                    private_host = private_host or (
                        address.is_private
                        or address.is_loopback
                        or address.is_link_local
                        or address.is_reserved
                    )
                except ValueError:
                    private_host = private_host or any(
                        label in {"internal", "private", "corp", "staging"}
                        for label in host_lower.split(".")
                    )
                if private_host:
                    errors.append(f"{path}: private host in public reference")
    return errors


def _base_row(
    *, harness="generic-shell", layer="portable-cli", transport="none"
) -> dict:
    return {
        "product": {
            "id": "agent-chat",
            "name": "Agent Chat",
            "version": "0.2.1",
            "source_ref": "plugins/agent-chat-plugin",
        },
        "harness": harness,
        "layer": layer,
        "transport": transport,
        "verification": {
            "capability_state": "SUPPORTED",
            "installed_state": "UNVERIFIED",
            "loaded_state": "UNVERIFIED",
            "domain_verified_state": "UNVERIFIED",
            "domain_call_evidence": {
                "calls": [],
                "reason": "Task 3 validates the contract only; no runtime call was made.",
            },
        },
    }


class TestHarnessAdapterSchema(unittest.TestCase):
    def _schema(self) -> dict:
        self.assertTrue(SCHEMA_PATH.is_file(), f"Missing schema: {SCHEMA_PATH}")
        with SCHEMA_PATH.open(encoding="utf-8") as handle:
            schema = json.load(handle)
        self.assertIsInstance(schema, dict)
        return schema

    def _errors(self, row: dict) -> list[str]:
        schema = self._schema()
        return _validate_json(row, schema, schema) + _security_errors(row)

    def _schema_errors(self, row: dict) -> list[str]:
        schema = self._schema()
        return _validate_json(row, schema, schema)

    def _assert_valid(self, row: dict) -> None:
        errors = self._errors(row)
        self.assertEqual(errors, [], errors)

    def _assert_invalid(self, row: dict, message: str) -> None:
        errors = self._errors(row)
        self.assertTrue(errors, message)

    def test_schema_is_valid_json_and_declares_exact_matrix_enums(self):
        schema = self._schema()
        self.assertEqual(
            schema["properties"]["harness"]["enum"],
            [
                "claude-code",
                "codex-cli",
                "opencode",
                "cursor",
                "grok-build",
                "pi",
                "github-copilot-vscode",
                "gemini-cli",
                "generic-shell",
            ],
        )
        self.assertEqual(
            schema["properties"]["layer"]["enum"],
            [
                "functional-package",
                "portable-cli",
                "portable-skill",
                "mcp-transport",
                "harness-adapter",
                "lifecycle-hooks",
                "commands-installer",
                "documentation",
            ],
        )
        self.assertEqual(
            schema["properties"]["transport"]["enum"],
            [
                "none",
                "stdio",
                "streamable-http",
                "sse",
                "acp-stdio",
                "filesystem",
                "unknown",
            ],
        )

    def test_valid_agent_chat_portable_cli_row(self):
        row = _base_row(layer="portable-cli", transport="filesystem")
        row.update(
            {
                "endpoint_ref": "channels",
                "command": {
                    "program": "python",
                    "args": ["./chat.py", "--channel", "general"],
                },
                "env_interpolation": [
                    {"name": "AGENT_CHAT_NAME", "source": "environment"}
                ],
                "docs": [
                    "README.md",
                    "https://github.com/example/agent-chat-plugin/blob/main/README.md",
                ],
            }
        )
        self._assert_valid(row)

    def test_valid_agent_chat_portable_skill_row(self):
        row = _base_row(layer="portable-skill", transport="none")
        row.update(
            {
                "docs": [
                    "skills/agent-chat/SKILL.md",
                    "https://github.com/example/agent-chat-plugin",
                ],
                "env_interpolation": [
                    {"name": "AGENT_CHAT_ROOT", "source": "user-config"}
                ],
                "hooks": [
                    {
                        "event": "SessionStart",
                        "ref": "hooks/session-start.py",
                        "mode": "command",
                    }
                ],
            }
        )
        self._assert_valid(row)

    def test_valid_representative_mcp_stdio_row(self):
        row = _base_row(harness="claude-code", layer="mcp-transport", transport="stdio")
        row["product"] = {
            "id": "better-notion-mcp",
            "name": "Better Notion MCP",
            "version": "2.37.0-beta.3",
            "source_ref": "plugins/better-notion-mcp",
        }
        row.update(
            {
                "command": {
                    "program": "npx",
                    "args": ["-y", "@example/better-notion-mcp@2.37.0-beta.3"],
                },
                "env_interpolation": [
                    {"name": "NOTION_TOKEN", "source": "secret-store"}
                ],
                "docs": ["https://github.com/example/better-notion-mcp"],
            }
        )
        self._assert_valid(row)

    def test_rejects_real_secret_looking_literal(self):
        row = _base_row()
        row["command"] = {
            "program": "python",
            "args": ["--api-key=sk-live-abcdefghijklmnopqrstuvwxyz123456"],
        }
        self._assert_invalid(row, "A secret-looking literal must be rejected")

    def test_rejects_private_absolute_path(self):
        row = _base_row()
        row["command"] = {
            "program": "python",
            "args": [r"C:\synthetic-user\private\config.json"],
        }
        self._assert_invalid(row, "A private absolute path must be rejected")

    def test_rejects_file_uri_absolute_paths_in_schema(self):
        for file_ref in (
            "file:///C:/synthetic-user/private/config.json",
            "file:///home/synthetic-user/private/config.json",
            "file://synthetic-host/share/private.json",
        ):
            for location in ("program", "argument", "public_ref"):
                with self.subTest(file_ref=file_ref, location=location):
                    row = _base_row()
                    if location == "program":
                        row["command"] = {"program": file_ref, "args": []}
                    elif location == "argument":
                        row["command"] = {"program": "python", "args": [file_ref]}
                    else:
                        row["docs"] = [file_ref]
                    self.assertTrue(
                        self._schema_errors(row),
                        f"Schema must reject absolute file URI in {location}: {file_ref}",
                    )

    def test_rejects_file_uri_assignments_in_schema(self):
        for argument in (
            "--config=file:///C:/synthetic-user/private/config.json",
            "--config=file://synthetic-host/share/private.json",
        ):
            row = _base_row()
            row["command"] = {"program": "python", "args": [argument]}
            self.assertTrue(
                self._schema_errors(row),
                f"Schema must reject absolute file URI assignment: {argument}",
            )

    def test_rejects_assigned_tilde_absolute_path_in_schema(self):
        for argument in (
            "--config=~/private/config.json",
            "--config ~/private/config.json",
        ):
            row = _base_row()
            row["command"] = {"program": "python", "args": [argument]}
            self.assertTrue(
                self._schema_errors(row),
                f"Schema must reject assigned tilde absolute path: {argument}",
            )

    def test_rejects_uppercase_sensitive_and_reserved_hosts_in_schema(self):
        for public_ref in (
            "https://INTERNAL.example.invalid/harness-adapter",
            "https://PRIVATE.example.invalid/harness-adapter",
            "https://api.INTERNAL.example.invalid/harness-adapter",
            "https://internal.example.invalid",
            "https://api.internal/",
            "https://api.localhost/",
            "https://localhost?x=1",
            "https://api.ip6-localhost#frag",
            "https://internal?x=1",
            "https://api.internal?x=1",
            "https://owner12zone34.example.invalid#frag",
            "https://api.owner12zone34#frag",
            "https://WORKSPACE.example.invalid/harness-adapter",
            "https://owner12zone34.example.invalid/harness-adapter",
            "https://api.owner12zone34.example.invalid/harness-adapter",
            "https://CORP.example.invalid/harness-adapter",
            "https://STAGING.example.invalid/harness-adapter",
            "https://0.0.0.0/harness-adapter",
            "https://127.0.0.1/harness-adapter",
            "https://10.0.0.1/harness-adapter",
            "https://api.10.0.0.1/",
            "https://api.10.0.0.1?x=1",
            "https://api.192.0.2.1#frag",
            "https://192.168.1.1/harness-adapter",
            "https://169.254.1.1/harness-adapter",
            "https://192.0.0.1/harness-adapter",
            "https://192.0.2.1/harness-adapter",
            "https://198.18.0.1/harness-adapter",
            "https://198.51.100.2/harness-adapter",
            "https://203.0.113.10/harness-adapter",
        ):
            with self.subTest(public_ref=public_ref):
                row = _base_row()
                row["docs"] = [public_ref]
                self.assertTrue(
                    self._schema_errors(row),
                    f"Schema must reject private or reserved public host: {public_ref}",
                )

    def test_allows_public_github_path_with_digit_runs(self):
        row = _base_row()
        row["docs"] = ["https://github.com/example/v12owner34.md"]
        self._assert_valid(row)

    def test_rejects_parent_traversal(self):
        row = _base_row()
        row["product"]["source_ref"] = "plugins/../agent-chat-plugin"
        self._assert_invalid(row, "Parent traversal must be rejected")

    def test_domain_verified_requires_evidence_ref(self):
        row = _base_row()
        row["verification"]["capability_state"] = "CONFIGURABLE"
        row["verification"]["domain_verified_state"] = "DOMAIN-VERIFIED"
        row["verification"]["domain_call_evidence"] = {
            "calls": [],
            "reason": "No domain call evidence was recorded.",
        }
        self._assert_invalid(
            row, "CONFIGURABLE DOMAIN-VERIFIED without evidence must be rejected"
        )

    def test_domain_verified_accepts_evidence_ref(self):
        row = _base_row()
        row["verification"]["capability_state"] = "CONFIGURABLE"
        row["verification"]["domain_verified_state"] = "DOMAIN-VERIFIED"
        row["verification"]["domain_call_evidence"] = {
            "calls": ["https://evidence.example.invalid/harness-domain-call/row-1"],
            "reason": "Representative synthetic public domain call was captured.",
        }
        self._assert_valid(row)

    def test_all_verification_states_are_required_and_explicit(self):
        for field in (
            "capability_state",
            "installed_state",
            "loaded_state",
            "domain_verified_state",
            "domain_call_evidence",
        ):
            with self.subTest(field=field):
                row = _base_row()
                del row["verification"][field]
                self._assert_invalid(
                    row, f"Missing verification field {field} must be rejected"
                )

    def test_raw_environment_value_is_rejected(self):
        row = _base_row()
        row["env_interpolation"] = [
            {
                "name": "NOTION_TOKEN",
                "source": "secret-store",
                "value": "should-never-be-present",
            }
        ]
        self._assert_invalid(row, "Environment interpolation must not carry raw values")

    def test_invalid_harness_and_transport_values_are_rejected(self):
        for field, value in (("harness", "claude"), ("transport", "http")):
            with self.subTest(field=field):
                row = _base_row()
                row[field] = value
                self._assert_invalid(row, f"Invalid {field} must be rejected")


if __name__ == "__main__":
    unittest.main()
