# Validation boundaries

Only original fictional plans and temporary artifacts are used. Local checks cover schema errors,
cycles, unknown/duplicate dependencies, safe HTML embedding, standalone installation, no overwrite,
sanitized errors and symlink refusal. Real Chromium checks cover keyboard completion, blockers,
reload, progress download/import, wrong-plan rejection, dependency-safe undo, mobile width,
no-network requests and inert malicious HTML text.

Local unittest, Chromium acceptance, Node syntax checks, Ruff correctness checks (`E9,F`) and Skill
Creator format validation passed on 2026-10-08. The Chromium test runner originally attempted an
eval-based wait blocked by CSP; it was changed to locator assertions, without weakening CSP.
Screenshot review prompted a narrow routing correction so adjacent dependencies do not appear as
a shared fan-out trunk. Fixed lanes remain a small-graph simplification; the full text list is authoritative.

Release verification is reported after checks actually finish. Script/browser tests are not proof of
automatic Skill discovery or model-driven plan quality. No real user study, clinical assessment,
screen-reader certification, cross-browser storage guarantee or automatic task execution is claimed.
The real-browser suite uses Chromium; Safari/Firefox are not independently tested for this release.

Chinese publication review preserves commands, limits, privacy boundaries and status semantics.
Mechanical Chinese punctuation, em-dash and empty-phrase scan of README.zh-CN.md and LAUNCH.md:
zero findings. Commands, numeric limits and uncertainty/privacy claims were retained; no medical or
productivity efficacy statement was added. Publication directory scan found no secrets or internal identifiers.
