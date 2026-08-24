"""Keep marketplace and source-authored public prose free of exact model IDs."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
PUBLIC_SOURCE_ROOTS = (ROOT / "plugins",)
MODEL_ID = re.compile(
    r"(?:"
    r"(?:gemini-(?!cli-)|grok-|claude-)[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)+|"
    r"qwen[0-9]+(?:[-_][A-Za-z0-9]+)+|"
    r"jina/[A-Za-z0-9_.-]+|cohere/[A-Za-z0-9_.-]+|openrouter/[A-Za-z0-9_.-]+"
    r")"
)


def _public_source_files() -> list[Path]:
    return sorted(
        path
        for root in PUBLIC_SOURCE_ROOTS
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in {".json", ".md", ".py"}
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
    )


def test_public_sources_use_vendor_level_model_examples() -> None:
    violations: list[str] = []
    for path in _public_source_files():
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if MODEL_ID.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")
    assert not violations, "Exact model identifiers leaked into public sources:\n" + "\n".join(violations)
