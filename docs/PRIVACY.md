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

## Persistence

Future persistence must remain local and ignored by Git. Schema migrations must
be additive, testable, and safe for existing local data.
