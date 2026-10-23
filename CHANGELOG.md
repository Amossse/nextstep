# Changelog

## Unreleased

- Decode plan files explicitly as UTF-8 with optional BOM, instead of JSON's automatic UTF-16/32 detection. Reject other encodings before rendering an output; cover non-ASCII plans and the preserved UTF-8/BOM paths.

- Cover a competing output created after staging but before atomic publication: refuse replacement, preserve the competing file and source plan, and clean the staging file. Runtime behavior is unchanged.

- Cover a two-input action-map join in Chromium: blocking one independent prerequisite lets the other proceed but does not unlock the join; undo guards and reload preserve the remaining branch. Runtime behavior is unchanged.

- Stage all installation resources before publishing the new Skill directory. A copy failure cleans its staging directory and leaves no partial final installation, so an unchanged retry can succeed; cover standalone rendering after retry.

- Cover the previously untested English browser flow: keyboard completion, required blocker note, reload, portable export/import and final completion. Runtime behavior is unchanged; no user-effectiveness claim is made.

- Supersede pending progress imports when a newer file is selected; a slow older read cannot overwrite the newer result or clear its messages/input. Cover the read-order race in Chromium and refresh the fictional HTML/CSP hash.

- Decode imported progress as strict UTF-8; malformed bytes are rejected without silently replacing blocker text or changing existing progress. Update the fictional HTML and CSP hash, with a browser regression.

- Check that progress remains exportable when browser storage fails and resumes in a separate browser context, including after reload. Runtime behavior is unchanged.

- Preserve rejected browser-local progress even after user actions; keep new progress in memory/export until a valid import is explicitly confirmed.
- Cover cancelled and confirmed recovery imports in Chromium acceptance tests and refresh the fictional HTML example and its CSP hash.

- Reject duplicate JSON fields at any depth before validating or rendering a plan.
- Add CLI regressions for conflicting plan titles and nested completion criteria; no output is created on rejection.

## 0.1.0 — 2026-10-08

- Original portable Skill and standard-library offline HTML/SVG renderer.
- Dependency-gated next action, user completion, blockers and resumption.
- Fingerprint-bound progress export/import, keyboard controls and text equivalent.
- Bilingual documentation, fictional learning example, no-clobber output and safety checks.

No auto-execution, medical efficacy claim, reminder, account or cloud sync.
