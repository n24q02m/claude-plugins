## 2026-03-27 - [MEDIUM] Insecure Shell Execution Mode and Non-Portable Emptiness Checks
**Vulnerability:** Shell scripts lacked `set -euo pipefail` causing potential unbounded variable expansions, ignored pipe errors, and silently failing commands, leading to unpredictable or insecure states. Also, `[ "$(ls -A "$dir" 2>/dev/null)" ]` was used to check for directory emptiness, which can cause unexpected behavior depending on `ls` aliases and parsing.
**Learning:** For predictable execution and avoiding security risks due to unbound variables or hidden pipe failures, shell scripts must fail securely on the first error. Standard checking with `ls` is brittle.
**Prevention:** Always enforce strict execution mode by adding `set -euo pipefail` at the top of all shell scripts. To check if a directory is not empty in a POSIX/portable way, use the pattern: `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` to avoid alias/parsing issues and improve portability.## 2026-04-04 - Secure GitHub Actions Version Sync
**Vulnerability:** Python Code Injection via Environment Variable in cd.yml
**Learning:** To prevent command injection when updating JSON files in GitHub Actions using Python, avoid shell variable expansion within the Python command string. Instead, export the variables to the environment and access them via `os.environ` within a Python script passed to the interpreter via stdin (`python3 - <<'EOF'`).
**Prevention:** Always use `os.environ` and heredocs for inline Python scripts in workflows.

## 2026-04-04 - Consolidated Plugin Metadata Sync
**Vulnerability:** Python Code Injection via Environment Variable in cd.yml
**Learning:** Consolidating the synchronization of multiple configuration files (e.g., `plugin.json` and `gemini-extension.json`) into a single secure Python script improves consistency and ensures all relevant metadata fields (like `version`) are correctly updated across the marketplace.
**Prevention:** Maintain a unified sync logic for all configuration files to ensure versioning consistency.
