#!/usr/bin/env python3
"""Tests for scripts/generate_ide_manifests.py and generated manifests."""

from __future__ import annotations

import json
import sys
import tempfile
import tomllib
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

import generate_ide_manifests as gen
import test_harness_adapter_schema as adapter_schema


class GenerateIdeManifestsTests(unittest.TestCase):
    def test_repo_manifests_are_valid_and_in_sync(self):
        rendered = gen.render_all()
        expected_files = {
            "claude-code.json",
            "cursor.json",
            "windsurf.json",
            "vscode.json",
            "gemini-cli.json",
            "opencode.json",
            "codex.toml",
            "harness-adapters.json",
        }
        self.assertEqual(set(rendered.keys()), expected_files)

        for name in expected_files:
            if name.endswith(".json"):
                parsed = json.loads(rendered[name])
                self.assertIsInstance(parsed, dict)
            else:
                parsed = tomllib.loads(rendered[name])
                self.assertIn("mcp_servers", parsed)

        claude_payload = json.loads(rendered["claude-code.json"])
        self.assertIn("skret", claude_payload["mcpServers"])
        self.assertEqual(len(claude_payload["mcpServers"]), 8)

        # Check all manifests on disk match generated output.
        self.assertEqual(gen.sync_manifests(check=True), [])

        # Validate every generated harness-adapters row against the contract schema.
        schema = json.loads(adapter_schema.SCHEMA_PATH.read_text(encoding="utf-8"))
        adapters_payload = json.loads(rendered["harness-adapters.json"])
        self.assertEqual(len(adapters_payload["adapters"]), 8 * 6)
        for row in adapters_payload["adapters"]:
            with self.subTest(product=row["product"]["id"], harness=row["harness"]):
                self.assertEqual(
                    adapter_schema._validate_json(row, schema, schema),
                    [],
                )
                self.assertEqual(adapter_schema._security_errors(row), [])

    def test_synthetic_stdio_and_http_plugins_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mp_dir = root / ".claude-plugin"
            mp_dir.mkdir(parents=True)
            mp_path = mp_dir / "marketplace.json"
            mp_path.write_text(
                json.dumps(
                    {
                        "plugins": [
                            {"name": "stdio-bare", "source": "./plugins/stdio-bare"},
                            {"name": "stdio-env", "source": "./plugins/stdio-env"},
                            {"name": "http-srv", "source": "./plugins/http-srv"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            plugins_spec = {
                "stdio-bare": {
                    "name": "stdio-bare",
                    "version": "1.0.0",
                    "mcpServers": {
                        "stdio-bare": {"command": "bare-bin", "args": ["mcp"]}
                    },
                },
                "stdio-env": {
                    "name": "stdio-env",
                    "version": "2.0.0",
                    "repository": "https://github.com/n24q02m/stdio-env",
                    "userConfig": {
                        "api_key": {"type": "string"},
                        "mode": {"type": "string", "default": "auto"},
                    },
                    "mcpServers": {
                        "stdio-env": {
                            "command": "env-bin",
                            "args": ["--serve"],
                            "env": {
                                "API_KEY": "${user_config.api_key}",
                                "MODE": "${user_config.mode}",
                                "STATIC_FLAG": "1",
                            },
                        }
                    },
                },
                "http-srv": {
                    "name": "http-srv",
                    "version": "3.0.0",
                    "userConfig": {
                        "endpoint": {"type": "string", "default": "https://api.example.invalid/mcp"},
                        "token": {"type": "string", "default": "ignored-for-headers"},
                    },
                    "mcpServers": {
                        "http-srv": {
                            "type": "http",
                            "url": "${user_config.endpoint}",
                            "headers": {"Authorization": "Bearer ${user_config.token}"},
                        }
                    },
                },
            }
            for plugin_name, manifest in plugins_spec.items():
                pdir = root / "plugins" / plugin_name / ".claude-plugin"
                pdir.mkdir(parents=True)
                (pdir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")

            out_dir = root / "out"
            # Missing directory -> check detects all 8 drifted
            missing = gen.sync_manifests(
                marketplace_path=mp_path, output_dir=out_dir, check=True
            )
            self.assertEqual(len(missing), 8)

            # CLI write mode
            stdout = StringIO()
            with mock.patch.object(sys, "stdout", stdout):
                rc = gen.main(
                    ["--marketplace", str(mp_path), "--output-dir", str(out_dir)]
                )
            self.assertEqual(rc, 0)
            self.assertIn("Generated 8 IDE manifest files", stdout.getvalue())

            # Verify substitutions in vscode, opencode, windsurf, gemini-cli, codex, harness-adapters
            vscode = json.loads((out_dir / "vscode.json").read_text(encoding="utf-8"))
            self.assertEqual(vscode["servers"]["stdio-env"]["type"], "stdio")
            self.assertEqual(
                vscode["servers"]["stdio-env"]["env"]["API_KEY"], "${env:API_KEY}"
            )
            self.assertEqual(vscode["servers"]["stdio-env"]["env"]["MODE"], "auto")
            self.assertEqual(
                vscode["servers"]["http-srv"]["headers"]["Authorization"],
                "Bearer ${env:TOKEN}",
            )

            windsurf = json.loads((out_dir / "windsurf.json").read_text(encoding="utf-8"))
            self.assertEqual(
                windsurf["mcpServers"]["http-srv"]["serverUrl"],
                "https://api.example.invalid/mcp",
            )
            gemini = json.loads((out_dir / "gemini-cli.json").read_text(encoding="utf-8"))
            self.assertEqual(
                gemini["mcpServers"]["http-srv"]["httpUrl"],
                "https://api.example.invalid/mcp",
            )
            opencode = json.loads((out_dir / "opencode.json").read_text(encoding="utf-8"))
            self.assertEqual(opencode["mcp"]["stdio-bare"]["type"], "local")
            self.assertEqual(
                opencode["mcp"]["stdio-env"]["environment"]["API_KEY"], "{env:API_KEY}"
            )
            self.assertEqual(opencode["mcp"]["http-srv"]["type"], "remote")

            codex = tomllib.loads((out_dir / "codex.toml").read_text(encoding="utf-8"))
            self.assertEqual(codex["mcp_servers"]["http-srv"]["bearer_token_env_var"], "TOKEN")
            self.assertEqual(codex["mcp_servers"]["stdio-env"]["env"]["API_KEY"], "${API_KEY}")

            # CLI check mode when clean
            stdout = StringIO()
            with mock.patch.object(sys, "stdout", stdout):
                rc = gen.main(
                    [
                        "--check",
                        "--marketplace",
                        str(mp_path),
                        "--output-dir",
                        str(out_dir),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn("up to date", stdout.getvalue())

            # Mutate one file -> --check returns 1
            (out_dir / "codex.toml").write_text("stale\n", encoding="utf-8")
            stderr = StringIO()
            with mock.patch.object(sys, "stderr", stderr):
                rc = gen.main(
                    [
                        "--check",
                        "--marketplace",
                        str(mp_path),
                        "--output-dir",
                        str(out_dir),
                    ]
                )
            self.assertEqual(rc, 1)
            self.assertIn("codex.toml", stderr.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
