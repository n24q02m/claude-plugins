## 2026-03-27 - [MEDIUM] Insecure Shell Execution Mode and Non-Portable Emptiness Checks
**Vulnerability:** Shell scripts lacked `set -euo pipefail` causing potential unbounded variable expansions, ignored pipe errors, and silently failing commands, leading to unpredictable or insecure states. Also, `[ "$(ls -A "$dir" 2>/dev/null)" ]` was used to check for directory emptiness, which can cause unexpected behavior depending on `ls` aliases and parsing.
**Learning:** For predictable execution and avoiding security risks due to unbound variables or hidden pipe failures, shell scripts must fail securely on the first error. Standard checking with `ls` is brittle.
**Prevention:** Always enforce strict execution mode by adding `set -euo pipefail` at the top of all shell scripts. To check if a directory is not empty in a POSIX/portable way, use the pattern: `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` to avoid alias/parsing issues and improve portability.## 2025-05-15 - Shell Command Injection in Git Commit Message
**Vulnerability:** Shell command injection in a GitHub Actions workflow via double-quoted string interpolation in a `git commit -m` command.
**Learning:** Untrusted inputs (like release tags or repo names from `repository_dispatch` payloads) can contain shell metacharacters. Even if partially validated, using them directly in a `run` block via shell expansion (`$VAR`) inside double quotes is risky.
**Prevention:**
1. Pre-define the full command string (e.g., `COMMIT_MSG`) in the `env` block using GitHub Actions expressions (`${{ }}`). This ensures the value is set as an environment variable before the shell starts.
2. Reference the environment variable in the `run` block as a shell variable (e.g., `"$COMMIT_MSG"`), ensuring it's properly quoted.
3. Use heredocs with unique, randomly generated delimiters when writing untrusted data to `$GITHUB_OUTPUT` to prevent output injection.
