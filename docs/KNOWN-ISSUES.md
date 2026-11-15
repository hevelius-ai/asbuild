# Known issues: AsBuild Core

Defects found outside a story's scope, with the reviewer's grade. The owner fixes, accepts or drops each at every release.

| ID | Found | Grade | Issue | Status |
| --- | --- | --- | --- | --- |
| K1 | 2026-11-10, S1 re-check after D25 | Not counted by the reviewer (outside D25) | A changed protected file outside `tests/acceptance/` (for example a root `pytest.ini`) gives WAITING FOR YOU but leaves the checklist lines judged, so they can read "works" under the "Stop" headline. The acceptance run ignores conftest files and plugin autoload, which limits what such a file can change | Fixed in v0.3.1 (D41, `build/K1`): every line is unjudged |
| K2 | 2026-11-10, S1 re-check after D25 | LOW (wording) | When every line is "not judged", the receipt's footer still says "AsBuild checked only the lines on your list" | Fixed in S2 (build/S2): the footer claims nothing when no line was judged |
| K3 | 2026-11-10, first live story receipt (hevelius-ai/asbuild-demo#2) | LOW (wording) | The story receipt says "Read each new line below", but the lines are above it | Fixed in S2 (build/S2): "Read each new line above" |
| K4 | 2026-11-14, v0.3.4 release walkthrough re-check (run 5) | LOW (walker) | Right after a push, the receipt comment can still show the previous commit's verdict for a few seconds after the new check run has completed (seen once, about 12 s); it then updates. `/asbuild:verdict` reads the check run, not the comment | Open |
| K5 | 2026-11-15, AsChecked re-test (B5), proved here by running | HIGH (a false PROVEN) | pytest also reads `.pytest.ini`, `pytest.toml` and `.pytest.toml`, none of them protected, and neither pytest run pins its settings file: a build adding one could deselect the app's other tests and get PROVEN | Fixed in v0.4.0 (D50, `m1b/safety`) |
| K6 | 2026-11-15, AsChecked re-test (B4) | HIGH (a false PROVEN reported by the AI) | `/asbuild:verdict` took the newest completed check named "AsBuild" from any workflow, so one a pull request adds could post a fake PROVEN | Fixed in v0.4.0 (D50, B4-A, `m1b/safety`); the pull request's own comments and Checks list can still show such a fake (stated in the README) |
| K7 | 2026-11-15, AsChecked re-test (B6) | Not graded by a reviewer | A story pull request can carry app code; the verdict still waits for the person, but its receipt does not say app code is included | Open (release review) |
| K8 | 2026-11-15, AsChecked re-test (B7) | Not graded by a reviewer | The story's title and plain lines go into the receipt as written, so a link, image or @mention in them shows under AsBuild's note | Open (release review) |
