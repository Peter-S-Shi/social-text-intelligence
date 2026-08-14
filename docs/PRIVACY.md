# Privacy

Social Text Intelligence is local-first. User text should remain on the user's
device unless a future, optional integration is explicitly selected and clearly
documents what leaves the device.

## Never commit

- real messages, comments, transcripts, support requests, or annotations;
- names, email addresses, account identifiers, or other personal information;
- databases, uploaded files, exports, backups, or generated reports;
- tokens, passwords, cookies, private keys, or environment files;
- model caches or weights;
- logs containing user text;
- machine-specific paths or settings.

The repository ignore rules reduce accidental exposure but are not a substitute
for reviewing staged content before every commit.

## Samples and tests

Public sample data must be synthetic, authored for this project, and free of
personal information. Real platform content is not safe merely because it is
publicly visible.

## Logging

The local Flask application uses ordinary request-line logging only and never
adds submitted text to log messages. It keeps direct input only for the current
request and response; no analysis history is created. Any future diagnostic mode
that can expose text must be explicit, temporary, and documented.

The web server binds to `127.0.0.1` by default. Normal mode may download pinned
model files from their documented sources, but inference text is not sent to a
remote model API. Offline mode requires both model revisions to be cached.
Model input is encoded locally without truncation. Text beyond either pinned
model's complete encoded-input budget is rejected before inference; the app
does not create or expose partial-text scores as if they described the whole
submission.

Every HTTP request is subject to a 3 MiB framework-level body ceiling before
form or multipart content reaches workflow logic. Declared oversized bodies are
rejected before temporary state can change; read-time enforcement covers parsed
forms and files. The fixed 413 response does not echo submitted text, filenames,
or file content and receives the same `Cache-Control: no-store` and
`Pragma: no-cache` headers as other responses. This request ceiling is separate
from the 2 MiB validated CSV payload limit.

Browser requests also remain inside an explicit loopback boundary. Only
`127.0.0.1` and `localhost` Host values are accepted. Explicit cross-origin or
`null` Origin values cannot run unsafe methods; when Origin is absent, an
existing Referer must be same-origin. Requests with neither header remain
available to local non-browser clients and still pass trusted-Host validation.
Rejected Host/Origin requests receive fixed text that does not include submitted
content, host values, filenames, or internal paths, and they run before model
inference or temporary-state mutation.

All browser responses use a self-only Content Security Policy, MIME sniffing
protection, same-origin referrer behavior, anti-framing protection, and no-store
caching. Application CSS and JavaScript remain checked-in local resources; no
CDN, wildcard source, CSP reporting service, CORS, telemetry, HSTS, TLS promise,
LAN binding, or remote deployment capability is added.

CSV uploads are read into a bounded, expiring in-memory workspace. The batch
workflow creates no upload directory, temporary file, database, automatic
export, or history. Responses use `Cache-Control: no-store`. Users explicitly
initiate each export; exported CSV includes original text and must be protected
as private local data. Spreadsheet-formula-like text is escaped on export.
Reaching the workspace limit blocks a new upload without evicting existing
work. An active synchronous analysis is retained across its normal TTL boundary
until it commits or fails; this lease remains process-memory only and creates no
background task or recovery store.

Human judgments and optional review notes share the same random-token, bounded,
expiring process-memory workspace. Continued interaction extends its lifetime,
but clearing, expiry, or process shutdown can remove unexported reviews. The app
does not create a review database, autosave file, re-import history, or background
writer, and does not add labels or notes to logs. Reviewed exports are generated
only on explicit request, use `Cache-Control: no-store`, retain original text, and
apply spreadsheet-formula protection to review notes and other user-controlled
cells. Treat exported reviewed datasets as private local data.

Insight controls and user-authored phrase/context notes use the same
random-token, bounded, expiring process-memory workspace. They create no
database, autosave, analytics history, network request, or background writer.
Clearing or expiry removes them with the batch. The application never logs
group values, phrases, notes, human labels, or exported content.

Insight export occurs only after an explicit request. Summary rows and context
notes are included; original record text and metadata are optional and model-
native scores are separately optional. Spreadsheet-formula protection covers
all user-controlled cells. Treat every insight export as private local data.

Moderation training uses a separate random-token, bounded, expiring
process-memory workspace. Built-in policy and case fixtures are synthetic.
Workspace-derived cases are created only from successfully analyzed records
after an explicit snapshot action. The snapshot may contain source text,
normalized signals, human review, context notes, and an allowlisted set of
trusted metadata; none is written to a database or background file.

Default limits are configurable and block creation rather than silently
evicting prepared cases or session attempts. Expiry, explicit whole-workspace
clearing, or process shutdown removes unexported state. Moderation exports are
explicit and use `Cache-Control: no-store`. User-derived text, signals, context
notes, and metadata are excluded by default and require separate opt-in.
Spreadsheet-formula protection applies to reasoning, reviewer notes, source
text, context, and metadata. Treat opted-in exports as private local data.

Support Triage uses its own random-token, capacity-blocking, sliding-expiry
process-memory workspace. Built-in guide and ticket resources are
project-authored synthetic fixtures. Workspace-derived tickets are copied only
after explicit record selection and preserve a literal source record or literal
bounded excerpt; decisions never write back into batch, review, insight, or
moderation state.

The default Support Triage export may include built-in synthetic text but leaves
workspace-derived source text, sentiment/emotion signals, human review, context
notes, and trusted metadata blank. Each workspace-derived context category has a
separate explicit opt-in. Formula-like user-controlled cells are escaped, every
export is explicit, and all responses use `Cache-Control: no-store`. Clearing,
expiry, or process shutdown removes unexported triage state.

## Persistence

Future persistence must remain local and ignored by Git. Schema migrations must
be additive, testable, and safe for existing local data.
