"""Thin CLI wrapper around ``extract(action="agent")`` for the research-topic skill.

Usage:

    python run.py "your research question" [--max-urls N] [--synthesis-model M]
                                            [--token-budget T]

Prints progress markers to stderr and the synthesised Markdown answer
+ source list to stdout. Intended for skill invocation; production MCP
callers should hit the tool directly.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


def _emit_progress(stage: str, detail: str = "") -> None:
    suffix = f" -- {detail}" if detail else ""
    print(f"[research-topic] {stage}{suffix}", file=sys.stderr, flush=True)


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the wet research-topic skill.")
    parser.add_argument("query", help="Research question to answer.")
    parser.add_argument(
        "--max-urls",
        type=int,
        default=5,
        help="Number of search hits to extract + cite (default 5, cap 20).",
    )
    parser.add_argument(
        "--synthesis-model",
        default=None,
        help="Override LLM model for synthesis (e.g. gemini-3-flash-preview).",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=10000,
        help="Max prompt tokens for the synthesis call (default 10000).",
    )
    args = parser.parse_args(argv)

    if len(args.query) > 2000:
        parser.error("query exceeds maximum length of 2000 characters.")
    if not (1 <= args.max_urls <= 20):
        parser.error("max-urls must be between 1 and 20.")
    if args.synthesis_model and len(args.synthesis_model) > 100:
        parser.error("synthesis-model exceeds maximum length of 100 characters.")
    if not (1 <= args.token_budget <= 100000):
        parser.error("token-budget must be between 1 and 100000.")

    _emit_progress("starting", f"query={args.query!r} max_urls={args.max_urls}")

    # Lazy import so the script imports cheaply when -h is used.
    from wet_mcp.sources.agent_orchestrator import run_agent

    _emit_progress("searching + extracting + synthesising")
    result = await run_agent(
        query=args.query,
        max_urls=args.max_urls,
        synthesis_model=args.synthesis_model,
        token_budget=args.token_budget,
    )

    if isinstance(result, str):
        # Error path: print the error to stderr + non-zero exit so callers
        # can detect the failure deterministically.
        _emit_progress("error", result)
        print(result, file=sys.stderr)
        return 1

    _emit_progress("done", f"sources={len(result.get('sources', []))}")
    print(result.get("markdown", ""))
    print()
    print("## Sources")
    for src in result.get("sources", []):
        print(f"- [{src.get('index')}] {src.get('title')} -- {src.get('url')}")
    print()
    print("## Per-URL metadata")
    print(json.dumps(result.get("per_url_metadata", []), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
