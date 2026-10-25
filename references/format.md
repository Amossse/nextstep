# Plan format

Regular UTF-8 JSON file, at most 128 KiB; an optional UTF-8 BOM is accepted. Pipes and other nonregular inputs are refused. UTF-16/32 is rejected rather than auto-detected. Exactly these top-level fields:

- `title`: plan name, non-empty text, at most 120 characters.
- `goal`: desired outcome and relevant uncertainty, at most 1,000 characters.
- `language`: `en` or `zh`; controls interface language.
- `steps`: 1–12 step objects.

Exactly these fields per step:

- `id`: unique lowercase identifier, `[a-z][a-z0-9-]{0,31}`.
- `title`: non-empty short label, at most 80 characters.
- `action`: bounded proposed action, at most 2,000 characters.
- `done_when`: observable completion criterion, at most 1,000 characters.
- `depends_on`: at most 3 unique existing step IDs. No cycles or self-dependency.

All fields are plain text. HTML, commands and URLs remain inert text; the viewer does not execute them. Newlines/tabs are allowed; other control characters are rejected. The renderer orders prerequisites before dependents. IDs and full content determine the plan fingerprint; changing content makes old progress incompatible.

Browser progress format: `version: 1`, `plan_id: <SHA-256 of canonical validated plan>`, and an ordered `steps` array with `id`, `status` (`pending`, `done`, `blocked`) and `reason`. Only blocked records may have a non-empty reason, limited to 1,000 characters. A done step requires all dependencies to be done. Import is bounded and validated; it never executes the notes. Progress export includes no plan text except blocker notes and IDs, but is still private.
