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

CSV uploads are read into a bounded, expiring in-memory workspace. The batch
workflow creates no upload directory, temporary file, database, automatic
export, or history. Responses use `Cache-Control: no-store`. Users explicitly
initiate each export; exported CSV includes original text and must be protected
as private local data. Spreadsheet-formula-like text is escaped on export.

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

## Persistence

Future persistence must remain local and ignored by Git. Schema migrations must
be additive, testable, and safe for existing local data.
