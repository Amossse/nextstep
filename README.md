# NextStep

**One next action. The whole path when you need it.**

A portable Agent Skill plus an original offline action-map renderer. Turn an approved task into
small actions with dependencies and completion criteria. The browser highlights one next step;
you mark completion, record blockers and resume without rereading a wall of text.

[中文](README.zh-CN.md) · [Skill](SKILL.md) · [Security](SECURITY.md)

## Try the fictional example

Download or clone this repository, then open `examples/study.html` in a browser. No install, server,
account, CDN or network is needed for the viewer. Expand the map for the full SVG and text steps.
On narrow screens the equivalent text list replaces the SVG. JavaScript powers progress controls;
without it, the complete action list still appears.

To generate a new file with Python 3.10+ (standard library only):

```sh
git clone https://github.com/Amossse/nextstep.git
cd nextstep
python scripts/nextstep.py validate examples/study.json
python scripts/nextstep.py render examples/study.json --out ../my-action-map.html
```

Open the output file in your browser. Outputs never overwrite an existing file. Use a new filename.
Symlink components are refused; on platforms with path aliases use the physical path.

## Install the Skill

Choose a host-supported local skill root. The installer takes an explicit NEW folder named `nextstep`:

```sh
python scripts/nextstep.py install --to /physical/path/to/skills/nextstep
```

It copies only the Skill, scripts, assets and format reference, not this README, tests or demo.
Existing destinations are refused. Resources are copied into a temporary sibling before the final
directory is published. A copy failure cleans staging and leaves no partial final installation; retry
after resolving the I/O error. Parent directories may remain. This is not a filesystem-race sandbox.
The installer never removes existing files or changes global instructions. Invoke `$nextstep` or the
host's documented equivalent after refreshing Skill discovery. Local Python/file access is required;
automatic discovery on every host and chat-only agents are not promised.

Ask your Agent:

> Use nextstep to turn this task into a small action map. Propose one first action, preserve required
> dependencies and uncertainties, and give observable completion criteria. Save it locally; don't execute it.

The Agent proposes/structures the plan. The script validates and renders; it has no model client and
does not independently understand documents. See [format.md](references/format.md) for exact fields.
Human review matters: wrong prerequisites can make a plausible map misleading.

Duplicate JSON fields, including nested step fields, are rejected before rendering instead of silently keeping the last value.

## Progress you can resume

If saved browser progress is corrupt, it is preserved even when you mark new progress. Export the new in-memory state, then explicitly confirm a valid import to resume saving; cancelling an import keeps the rejected data intact.

- Only user clicks change progress. Completion is a self-report, not verified execution.
- Steps unlock when their prerequisites are marked done. Independent ready steps use stable plan order.
- Blockers require a note; unblocking returns a step to pending.
- Browser storage is best-effort for local files. Export JSON before changing browsers, moving files or
  closing a browser that cannot save. Import verifies the exact plan fingerprint and asks before replacement.
- Editing the plan creates a different fingerprint; old progress is not migrated. Undoing a prerequisite
  is refused while a direct dependent is marked done; undo from the end of the path first.

Chromium acceptance also exercises an isolated fictional English plan: keyboard completion, required blocker notes, reload, export/import and final completion. It checks the English interaction branch, not real-user effectiveness or compatibility with every browser.

There is no auto-execution, reminder, timer, account, cloud sync, analytics or medical efficacy claim.
This is an interaction aid for anyone who prefers small steps, not an ADHD diagnosis or treatment.

## Architecture, safety and limits

`User-approved source → host Agent → bounded JSON → Python validation → standalone HTML/SVG → user progress`.
The initial focus is one step; the complete path remains available. Up to 12 steps and 3 dependencies per
step keep the graph small. Larger tasks must be split deliberately rather than silently truncated.

HTML contains the full plan; progress exports contain IDs and blocker notes. Keep real artifacts private
and outside this repository. No guaranteed secret detector, encryption or authentication is included.
The host model may still process your source under its provider's privacy settings.

Imported text is rendered as text, not HTML. JSON script data is escaped, inline application code is
hash-allowed by CSP, network connections are disallowed, schema/input sizes are bounded and cycles rejected.
This is not an OS sandbox, protection from hostile local processes, or a promise that browsers/backups
erase data. New output files use restrictive permissions where POSIX supports them; Windows needs ACLs.
The content fingerprint isolates plans, but browser localStorage is not a cross-file confidentiality boundary.

## Checks and contribution

The file-budget regression accepts a complete 128 KiB UTF-8 plan with multibyte text and whitespace padding, then rejects one extra byte through both validate and render without creating output or changing the source. It checks bytes rather than character counts; runtime behavior is unchanged.

If constructing the staged output stream fails, the helper closes the still-owned descriptor before cleaning its temporary file. A fault-injection regression covers this resource lifetime and absence of a published output; it is not a guarantee for every I/O failure or process crash.

Plan files must be UTF-8 JSON (an optional UTF-8 BOM is accepted). UTF-16/32 auto-detection is no longer accepted; convert explicitly to UTF-8. Rejected encodings create no output. Browser progress imports retain their separate strict UTF-8 contract.

Plan input must be a regular file. POSIX FIFOs are opened nonblocking and refused without waiting for a writer or creating output; save a complete UTF-8 JSON file first. Windows runs the descriptor-type regression but skips the POSIX FIFO case. This is not an operating-system sandbox.

Read-side fault injection also checks descriptor closure after a rejected file type or stream-construction failure, then verifies a normal plan can still be read. This fills an error-path coverage gap without changing runtime behavior; it does not cover every filesystem failure.

A fault-injection regression creates a competing output after rendering is staged but before publication. The CLI refuses replacement, preserves the competing bytes and source plan, and cleans its staging file. This covers an important no-clobber timing boundary; runtime behavior is unchanged and hostile-process isolation is not claimed.

Chromium acceptance includes a fictional two-prerequisite join: one blocked branch does not unlock the join when the other finishes; resuming, undoing and reloading preserve dependency constraints and the independent completed branch. This expands branching-flow coverage without changing runtime behavior or measuring user effectiveness.

```sh
python -m unittest discover -s tests -v
# Optional development-only real browser check:
python -m pip install playwright
python -m playwright install chromium
python tests/browser_check.py
```

The browser check also exports progress after storage-write failure, imports it in a separate browser context, and verifies resumption after reload. It does not guarantee local-file storage across all browsers.
Progress JSON imports require valid UTF-8. Malformed bytes are refused before confirmation or replacement; re-export a valid backup rather than repairing unknown bytes by guesswork.
Selecting another progress file supersedes any earlier read still in flight. Only the latest selection may ask to replace progress; cancelled or invalid imports still preserve the current state.

Tests use fictional inputs and temporary files. CI checks Python on Linux/macOS/Windows and Chromium on
Linux. See [Actions](https://github.com/Amossse/nextstep/actions) and [validation boundaries](VALIDATION.md).
Automated acceptance is not a user study or proof of improved attention/productivity.

Inspired by the action-oriented communication of [i-have-adhd](https://github.com/ayghri/i-have-adhd)
and the restrained visual approach of [diagram-design](https://github.com/cathrynlavery/diagram-design).
Implementation, UI, instructions and fictional study example were independently written; no upstream
code, templates, illustrations, medical claims or branding are bundled. Not a fork or an upstream endorsement.

[Contribute](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [MIT](LICENSE) · [Unposted launch drafts](LAUNCH.md)

Keywords: Agent Skills, action map, next action, visual planning, offline HTML, SVG, local-first,
accessibility, Claude Code, Codex, task resumption.
