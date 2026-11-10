# Known issues: AsBuild Core

Defects found outside a story's scope, with the reviewer's grade. The owner fixes, accepts or drops each at every release.

| ID | Found | Grade | Issue | Status |
| --- | --- | --- | --- | --- |
| K1 | 2026-11-10, S1 re-check after D25 | Not counted by the reviewer (outside D25) | A changed protected file outside `tests/acceptance/` (for example a root `pytest.ini`) gives WAITING FOR YOU but leaves the checklist lines judged, so they can read "works" under the "Stop" headline. The acceptance run ignores conftest files and plugin autoload, which limits what such a file can change | Open |
| K2 | 2026-11-10, S1 re-check after D25 | LOW (wording) | When every line is "not judged", the receipt's footer still says "AsBuild checked only the lines on your list" | Fixed in S2 (build/S2): the footer claims nothing when no line was judged |
| K3 | 2026-11-10, first live story receipt (hevelius-ai/asbuild-demo#2) | LOW (wording) | The story receipt says "Read each new line below", but the lines are above it | Fixed in S2 (build/S2): "Read each new line above" |
