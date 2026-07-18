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

Future logging must exclude full user text by default. Any diagnostic mode that
can expose text must be explicit, temporary, and documented.

## Persistence

Future persistence must remain local and ignored by Git. Schema migrations must
be additive, testable, and safe for existing local data.
