# Better Code Review Graph -- Tools Reference

better-code-review-graph (crg) builds a knowledge graph of a codebase and exposes it through 6 tools driven by an `action` parameter, plus `help` and `config__open_relay`. None of these tools wrap results as external/untrusted content.

## graph

Build and manage the code knowledge graph.

| Action | Purpose | Key parameters |
|---|---|---|
| `build` | Parse source and build the graph | `full_rebuild` (default `false`), `base` (default `HEAD~1`), `repo_root`, `roots` (federate additional repos) |
| `update` | Incremental update (alias for `build` with `full_rebuild=false`) | Same as `build` |
| `stats` | Node/edge counts, languages, embedding status | -- |
| `embed` | Compute vector embeddings for graph nodes | -- |
| `export` | Export the graph | `format` (default `graphml`; also `json-ld`, `dot`, `cypher`), `output_path` |
| `summarize` | Generate LLM summaries for Function nodes | `max_nodes` (default 500) |

## query

Query the graph for relationships, search, and impact analysis.

| Action | Purpose | Key parameters |
|---|---|---|
| `query` | Predefined graph queries | `pattern`/`target` (required): `callers_of`\|`callees_of`\|`imports_of`\|`importers_of`\|`children_of`\|`tests_for`\|`inheritors_of`\|`file_summary` |
| `search` | Search nodes by name/keyword/vector | `search_query` (required), `kind`, `limit` (default 20) |
| `impact` | Blast-radius analysis from changed files | `changed_files`, `max_depth` (default 2), `max_results` (default 500) |
| `large_functions` | Find oversized functions | `min_lines` (default 50) |
| `spot_check` | Random callsite snippets from the last `callers_of`/`callees_of`/`inheritors_of`/`importers_of` result | `n` (default 3), `context_lines` (default 2) |
| `renamed_in_diff` | Symbols whose callsite line shifted vs a base ref | `base` (default `HEAD~1`) |
| `diff` | Nodes added/removed/modified between two commits | `from_sha`, `to_sha` |

## review

Generate token-efficient review context for code changes.

| Action | Purpose | Key parameters |
|---|---|---|
| `context` (default) | Auto-detect changed files from git diff; return structural summary, impacted nodes, source snippets, review guidance | `changed_files` (auto-detected), `max_depth` (default 2), `include_source` (default `true`), `max_lines_per_file` (default 200) |
| `delta` | Wrap `query`'s `diff` action into review buckets; with `show_line_shifts`, surface renamed/moved symbols | `from_sha`, `to_sha` (required), `show_line_shifts` (default `false`) |

## security

Security scanning over the code knowledge graph.

| Action | Purpose | Key parameters |
|---|---|---|
| `scan` (default) | Run a scan over Function/Class/Method nodes; cache to disk and persist tags | `engine` (default `heuristic`; also `semgrep`) |
| `report` | Re-emit the cached scan payload | `format` (default `json`; also `sarif`) |
| `suppress` | Add/remove a rule from the persistent suppression list | `rule_id` (required), `remove` (default `false`) |
| `rule_list` | Enumerate active rules | `engine` |

## config

Server configuration, status, and credential setup.

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Show graph path, node/edge counts, backend, last-updated | -- |
| `set` | Update a runtime setting (`log_level` only) | `key`, `value` (required) |
| `cache_clear` | Wipe all computed embeddings | -- |
| `setup_status` | Show credential state and setup URL | -- |
| `setup_start` | Start relay browser setup for API keys | `force` (default `false`) |
| `setup_skip` | Set local mode, skip the relay permanently | -- |
| `setup_reset` | Clear credentials, reset to `awaiting_setup` | -- |
| `setup_complete` | Re-resolve credentials from environment variables | -- |

## help

Get full documentation for a topic.

| Parameter | Values |
|---|---|
| `topic` | `graph` (default) \| `query` \| `review` \| `config` \| `security` \| `recipes` |

## config__open_relay

Re-triggers the relay configuration form (e.g. after credential expiry). No parameters.
