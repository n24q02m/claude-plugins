## 2025-05-14 - Fix broad exception handling in check-credentials hook

**Vulnerability:** Catching broad Exception in check-credentials hook could obscure unexpected bugs.
**Learning:** Replacing Exception with json.JSONDecodeError ensures specific handling of JSON errors while allowing other issues to surface.
**Prevention:** Always catch the most specific exceptions possible.
