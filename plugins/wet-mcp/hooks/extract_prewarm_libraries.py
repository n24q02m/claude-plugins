#!/usr/bin/env python3
import sys
import re

# Tier 1 library aliases the wet-mcp registry currently knows about.
# The list mirrors tests/fixtures/libraries/tier1_libraries.json so the
# hook stays useful without a runtime DB lookup.
TIER1_LIBRARIES = {
    "fastapi",
    "pydantic",
    "starlette",
    "uvicorn",
    "react",
    "next",
    "vue",
    "svelte",
    "django",
    "flask",
    "numpy",
    "pandas",
    "polars",
    "scikit-learn",
    "pytorch",
    "tensorflow",
    "transformers",
    "langchain",
    "anthropic",
    "openai",
}

# Patterns covered:
#   from <pkg> import ...
#   import <pkg>
#   import { ... } from "<pkg>"     (JS/TS)
#   require("<pkg>")
#   from "<pkg>"
PATTERNS = [
    re.compile(r"from\s+([a-zA-Z0-9_.-]+)"),
    re.compile(r"import\s+([a-zA-Z0-9_.-]+)"),
    re.compile(r'require\("([a-zA-Z0-9_.@/-]+)"\)'),
    re.compile(r'from\s+"([a-zA-Z0-9_.@/-]+)"'),
]


def extract_libraries(text):
    candidates = []
    for pattern in PATTERNS:
        for match in pattern.finditer(text):
            candidates.append(match.group(1))

    # Mirror bash: sort -u | head -20
    unique_candidates = sorted(list(set(candidates)))
    top_candidates = unique_candidates[:20]

    hits = set()
    for raw in top_candidates:
        # normalization: lowercase
        base = raw.lower()

        # strip scoped packages if they start with @ (e.g. @org/pkg -> pkg)
        # We do this BEFORE stripping everything after slash so we can actually
        # see the slash that separates the scope from the package.
        base = re.sub(r"^@[^/]+/", "", base)

        # strip sub-imports like "react/jsx-runtime" -> "react"
        base = re.sub(r"/.*$", "", base)

        if base in TIER1_LIBRARIES:
            hits.add(base)

    return sorted(list(hits))


def main():
    try:
        text = sys.stdin.read()
    except EOFError:
        return

    if not text:
        return

    hits = extract_libraries(text)
    if hits:
        print("\n".join(hits))


if __name__ == "__main__":
    main()
