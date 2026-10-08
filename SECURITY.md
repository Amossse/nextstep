# Safety and privacy

Only fictional original samples are public. Real plans, sources, progress files and screenshots may
contain sensitive data; keep them outside the checkout. Do not attach them to public issues.

The helper and viewer have no network client, telemetry, remote font or API key. Model inference is
the host's responsibility and may be remote. Neither local rendering nor CSP makes private input safe
to publish. LocalStorage and exported notes are not encrypted or authenticated.

JSON fields are plain text; script-breaking characters are escaped and DOM updates use textContent.
State imports are bounded, bound to a content fingerprint and checked for dependency consistency.
CSP only allows the bundled script by hash and denies network connections. Generated HTML must not
be hand-edited to add untrusted JavaScript. Anyone can forge a valid completion record; it is not evidence.

Filesystem symlink checks and atomic no-clobber writes prevent common accidents, not hostile race attacks.
Rendering uses an in-memory bounded plan. Installation I/O failure can leave a partial new folder;
review it rather than overwriting or deleting an existing installation. There is no automatic cleanup.

No medical benefit is asserted. Plan correctness, safety-critical decisions and real task completion
need human review. Keyboard/mobile checks are not a comprehensive accessibility certification.

Report a vulnerability using GitHub's private vulnerability reporting when available; otherwise open a
sanitized issue describing the class of failure without secrets, private material or exploit payloads
targeting third parties. No response-time guarantee is promised.
