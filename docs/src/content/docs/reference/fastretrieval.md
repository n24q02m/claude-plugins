---
title: "fastretrieval"
description: "Retrieval companion for the n24q02m MCP stack — Qwen3 embedding + reranking with a local ONNX runtime and FastRetrieval caching."
---

fastretrieval is the retrieval companion library for the n24q02m MCP stack. It
provides embedding and reranking on a local ONNX runtime (Qwen3-Embedding,
768-dim) with FastRetrieval caching, so MCP servers can run retrieval fully
offline when no cloud provider is configured.

## Facts

- Repo: `n24q02m/fastretrieval` (owned dependency companion, canonical
  inventory #14 — re-included 2026-09-02)
- Registry: PyPI `fastretrieval` (current stable `v1.2.0`)
- Runtime: Python 3.10–3.14, `uv`-managed; stdlib + ONNX dependencies only
- Embedding env: `FASTRETRIEVAL_CACHE_PATH` (legacy `QWEN3_EMBED_CACHE_PATH`
  alias still readable with a `DeprecationWarning`)

## In this section

- See the repo README for the full environment-variable reference and the
  embedding/rerank API surface.
