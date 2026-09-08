---
title: fastretrieval
description: Multi-model Python retrieval runtime for dense, sparse, late-interaction, image embeddings, and reranking with ONNX and optional GGUF support.
---

[fastretrieval](https://github.com/n24q02m/fastretrieval) is the Python retrieval
runtime used by Wet, Mnemo, and Better Code Review Graph. It is a library, not an
MCP server or a marketplace plugin: it has no MCP endpoint, relay, credential
form, or transport configuration.

## Package and capabilities

The [PyPI package](https://pypi.org/project/fastretrieval/) requires Python 3.11
or newer. ONNX Runtime is included; GGUF uses the optional `llama-cpp-python`
backend. Runtime inference does not require PyTorch.

| Capability | Public facade | Package extra |
|---|---|---|
| Dense text embeddings | `TextEmbedding` | None for ONNX; `gguf` for GGUF |
| Cross-encoder and yes/no-logit reranking | `TextCrossEncoder` | None for ONNX; `gguf` for GGUF |
| Sparse text embeddings | `SparseTextEmbedding` | None |
| Late-interaction text embeddings | `LateInteractionTextEmbedding` | None |
| Image embeddings | `ImageEmbedding` | `image` |
| Late-interaction multimodal embeddings | `LateInteractionMultimodalEmbedding` | `image` |

`fastretrieval[all]` includes both `gguf` and `image`. Model availability is
specific to each facade's registry; a facade does not imply that every model
family is bundled. Custom models use the public `CustomModelSpec` and
`CustomRerankerSpec` contracts. The repository also provides a conversion CLI
with `onnx`, `gguf`, `verify`, and `card` commands; its conversion dependencies
are separate from the inference package.

## Defaults and supported models

`TextEmbedding()` defaults to `n24q02m/Qwen3-Embedding-0.6B-ONNX`. Its registered
output size is 1024, with model-specific Matryoshka truncation available at
embedding time. There is no universal 768-dimensional library contract.
`TextCrossEncoder` requires an explicit `model_name`; a consumer's chosen
reranker is not a package-wide constructor default.

The installed package is authoritative for supported models and dimensions.
These registry queries do not instantiate a model or download weights:

```python
from fastretrieval import TextCrossEncoder, TextEmbedding

embedding_models = TextEmbedding.list_supported_models()
reranker_models = TextCrossEncoder.list_supported_models()
embedding_size = TextEmbedding.get_embedding_size(
    "n24q02m/Qwen3-Embedding-0.6B-ONNX"
)
```

See the [supported-model reference](https://github.com/n24q02m/fastretrieval#supported-models)
and [usage examples](https://github.com/n24q02m/fastretrieval#usage) for model
identifiers, backend selection, and custom-model registration.

## Cache and consumer contracts

- `FASTRETRIEVAL_CACHE_PATH` overrides the model cache directory.
- `FASTRETRIEVAL_MAX_INPUT_LENGTH` overrides the maximum accepted input length.
- `define_cache_dir()` is the public cache-location helper; an explicit path
  overrides environment configuration.
- Legacy `QWEN3_EMBED_*` environment names are deprecated compatibility inputs,
  not the package name. `FASTRETRIEVAL_*` takes precedence.

Local inference can run without provider API keys after the selected model
artifacts are available. Initial downloads still require network access unless
those artifacts have already been provisioned. Cloud completion, embedding,
and rerank selection belongs to each consuming server, not to Fastretrieval.

Wet, Mnemo, and CRG must keep their model identity, query/document embedding
behavior, and stored vector dimensions consistent. Changing a model or output
size requires the consumer to rebuild affected vectors rather than mix
incompatible vector spaces. See each server's setup reference:

- [Wet](/servers/wet-mcp/setup/)
- [Mnemo](/servers/mnemo-mcp/setup/)
- [Better Code Review Graph](/servers/better-code-review-graph/setup/)
