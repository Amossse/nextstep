# Contributing

Use original fictional inputs. Never commit real plans, exports, account data, internal URLs or logs.
Explain the user problem and smallest observable behavior change. Preserve textual equivalents,
keyboard access, no-network rendering and user-only completion. Avoid speculative services or dependencies.

Run the unittest check and, for UI changes, `python tests/browser_check.py` with development-only
Playwright/Chromium installed. Regenerate the fictional HTML after changing assets:
choose a temporary output, inspect it, then deliberately update `examples/study.html` as a generated asset.
Do not overwrite a user's generated plan. Discuss larger schema changes before implementing migration.
