# M9.2-A — Source intake decision register

## Version, authority and decision boundary

Register version **1.0.0**; primary-source access date **2026-10-10**.
Research reviewer role: Codex. Rights/approval reviewer role: repository owner,
with qualified advice or rightsholder clarification where necessary.

The owner-approved [evidence contract](V2_M9_EVIDENCE_CONTRACT.md) and
[evaluation protocol](V2_M9_EVALUATION_PROTOCOL.md) remain authoritative.
This register is a feasibility assessment, not a legal opinion, source approval,
permission request, acquisition instruction or executed evaluation. Only policy,
license and API documentation were consulted; no feedback records or dataset
payloads were retrieved, imported or inspected for this assessment.

**Every candidate is PENDING.** Owner approval must identify the actual source
version and proposed use and must have a defensible third-party rights basis;
an owner decision cannot create missing rights. Public availability, a working
API, a code license or an aggregator's dataset license tag does not establish
permission to research, annotate, infer on or redistribute feedback.

No source has an approved date frame, product/repository list, collection
configuration or eligible count. Provider/API identities below are concrete
candidate routes, not executable approved source frames. The approved targets
remain 60 authentic English software/app-experience records per channel (180
total), with 20 independently double-labeled IDs per channel. No smaller sample,
synthetic substitution or channel redefinition is proposed.

## Stable candidate decisions

| Candidate ID | Original channel and provider | Proposed route | Disposition | Owner decision/date/evidence |
| --- | --- | --- | --- | --- |
| SRC-APP-01 | Public app/product reviews; Valve Steam | Official app review API, restricted to owner-approved software/application products | PENDING | Not provided |
| SRC-ISSUE-01 | Technical support/issue feedback; original feedback contributors on GitHub | Official REST issues API for an explicitly licensed/authorized repository set | PENDING | Not provided |
| SRC-COMM-01 | Software/community discussion; Stack Exchange contributors | Official Stack Exchange API for a specifically approved software-use community/frame | PENDING | Not provided |
| SRC-COMM-02 | Software/community discussion; Reddit contributors | Separate permitted research arrangement and official access, only if obtained | PENDING | Not provided |
| SRC-DIRECT-01 | Any of the three channels, preserving original origin | Owner-controlled original feedback with documented author permissions/consent | PENDING | Not provided |

These are original hosting/publishing platforms. None is an endorsement of a
Kaggle, Hugging Face or other repackaged collection. An upstream mirror would
require a new stable candidate ID, original collection method/version, complete
rights chain and privacy review; this work does not assess or acquire one.

## SRC-APP-01 — Steam application reviews

**Identity/version.** Valve Steam; candidate API version `GetAppReviews/v1`.
Product IDs, corpus snapshot/date range and retrieval configuration are UNSET.
The [current API documentation](https://partner.steamgames.com/doc/webapi/IUserReviewsService)
describes public reviews, English filtering and cursor pagination. The
[older endpoint documentation](https://partner.steamgames.com/doc/store/getreviews)
marks `/appreviews` deprecated. Anonymous API availability proves technical
accessibility, not research authorization.

**Rights evidence.** The [Steam Web API terms](https://steamcommunity.com/dev/apiterms)
(displayed update July 2010) grant a conditional application/data license and
restrict retrieval of end-user data to end-user requests. The
[Subscriber Agreement, section 6.A](https://store.steampowered.com/subscriber_agreement/?l=english)
grants Valve/affiliates UGC rights; that grant is not an automatic downstream
researcher's license. These provisions do not clearly establish this proposed
independent offline annotation/inference use. Resolve applicability to public
review text and obtain necessary permission/author-rights basis before approval.

**Proposed local use.** Only later authorized acquisition into restricted local
storage, blind human annotation and evaluation of unchanged shipped models; no
training or platform bulk harvest. Permission must cover sharing selected text
with independent human annotators and retaining a reproducibility manifest.

**Fit/limitations (research inference).** Application-use reviews plausibly fit
the review channel. Restrict to genuine software/app experience; do not silently
replace the principal domain with game criticism. English flags need later blind
screening. Helpful ranking, purchase-type defaults and platform off-topic filters
can constrain the frame; future configuration must preserve a defined eligible
frame before uniform selection and cannot pick by rating, popularity or ease.
Availability of 60 eligible lawful records is **NOT VERIFIED**.

**Privacy/public split.** Minimize account identifiers, profiles, playtime and
hardware metadata. Text can contain PII or third-party claims. Text, source IDs,
reference labels and derived summaries each remain unapproved for public release;
review separate rights, attribution and reidentification risks. Rights uncertainty
blocks even local ingestion. Priority: conditional candidate, substantial rights
clarification required.

## SRC-ISSUE-01 — GitHub original software issue feedback

**Identity/version.** GitHub official REST issues surface; specific repositories,
terms/license revision, API version header and snapshot/date range are UNSET.
[Issue API documentation](https://docs.github.com/en/rest/issues/issues)
provides repository issue access and warns that issue listings also include pull
requests. Later eligibility must exclude PRs and unrelated code/questions without
using sentiment/emotion labels or predictions.

**Rights evidence.** [GitHub Terms](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)
display effective date April 27, 2026. D.5's other-user grant concerns use through
GitHub functionality; D.6 provides contribution licensing under a repository's
license subject to separate agreements. Therefore inspect actual issue-content
coverage, notices, contributor agreements and embedded third-party material;
neither assume the code license covers everything nor ignore D.6. D.8 lawful
access and H API rules do not independently settle all local research rights.
GitHub/affiliate AI grants are not a researcher's grant. Resolve this study's
use and author's rights before approval.

**Proposed local use.** Same restricted local study and authorized human access
as SRC-APP-01. Select a clearly documented issue-content license/permission route,
with original authorship provenance; maintainer permission alone cannot license
material the maintainer does not own.

**Fit/limitations (research inference).** Experience-based bug/feature reports
can fit technical support. A developer-heavy open-source frame may be unlike
consumer app feedback. Freeze whether the unit is a standalone report or a
specified comment, minimal necessary context and cross-channel precedence before
screening/selection; do not use issue status as an appraisal label. English,
authenticity and 60 eligible lawful records are **NOT VERIFIED**.

**Privacy/public split.** Logs, credentials, usernames, screenshots, emails and
private-service details can appear in issue bodies. Exclude unsafe material under
registered rules and retain only necessary sanitized text with restricted
source mappings. All four public categories (text, IDs, labels, derivatives)
remain unapproved; attribution obligations may conflict with public pseudonyms
and require local-only release. Priority: conditional candidate after exact
repository/license scope and contributor-rights review.

## SRC-COMM-01 — Stack Exchange software-use community

**Identity/version.** Stack Exchange official API, proposed software-use community
such as Super User; exact site/date frame, API version and post/revision unit are
UNSET. The [API agreement](https://stackoverflow.com/legal/api-terms-of-use)
requires compliance with network terms and source attribution. No API request
for posts was made.

**Rights evidence.** [Public Network Terms](https://stackoverflow.com/legal/terms-of-service/public)
(displayed updated November 13, 2025), section 6, distinguish subscriber content,
platform content and API access. The [publisher's licensing help](https://stackoverflow.com/help/licensing)
identifies CC BY-SA 2.5/3.0/4.0 by contribution date and points to revision-level
license evidence. The [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)
grants conditional reproduction/adaptation rights, requires attribution and
ShareAlike when applicable, and does not license privacy/personality rights.
Confirm exact revision/license and API/network obligations; a general CC label
is not a completed source-intake decision.

**Proposed local use.** Restricted offline study under verified license/terms and
authorized annotator access. No training or republishing is proposed. This is the
strongest documented conditional licensing route among the researched community
options, not an approved or legally guaranteed source.

**Fit/limitations (research inference).** Software-use discussion may fit the
community channel, but factual troubleshooting and hardware/code questions can
be unrelated or overlap technical support. Freeze origin-based precedence and
experience eligibility; do not turn Stack Overflow coding Q&A into app reactions
by assertion. Neutral factual software experience may remain eligible under the
approved protocol. Authentic English, non-overlap and a 60-record eligible frame
are **NOT VERIFIED**.

**Privacy/public split.** Contributor names, links and embedded private logs need
minimization. Public text/IDs/labels/derivatives remain separately unapproved.
If required attribution identifies contributors and cannot meet public privacy
rules, keep record-level material restricted or obtain a suitable permission;
do not silently strip required notices. Determine whether a planned released
derivative triggers ShareAlike; do not assume that labels or aggregates inherit
or escape source obligations without review. Priority: first community route
for owner consideration, with domain/attribution feasibility unresolved.

## SRC-COMM-02 — Reddit restricted alternative

**Identity/version.** Reddit Data API; community list, access authorization and
dated arrangement UNSET. [Data API Terms](https://redditinc.com/policies/data-api-terms)
2.4 limits the user-content grant to specified app/display purposes and does not
imply other uses; 3.1 requires a separate agreement for uses not expressly
permitted. Evaluation is distinct from training, but that distinction does not
establish evaluation rights under these terms. Obtain specific research-use
authorization and necessary rightsholder permissions; no request was sent.

**Proposed use and fit (research inference).** Authentic app-use reactions might
fit the community stratum, but domain, English yield and independence are
**NOT VERIFIED**. Do not use unofficial scraped archives or evade access controls.
Privacy/takedown and author-rights burdens are significant. Local study, annotator
sharing and each public category are all unapproved. Priority: permission-dependent
fallback, not a default route.

## SRC-DIRECT-01 — Direct-permission fallback

No provider/corpus exists or has been contacted. A later owner-controlled source
must document original software/app experience, origin channel, collection dates,
author/third-party rights, prospective permission for local annotation/inference
and separate publication consent. Provider ownership alone does not confer author
rights. Do not solicit invented favorable feedback or alter the approved 60-per-
channel frame/design. Availability, authenticity and English yield are NOT VERIFIED;
privacy, retention and annotator-sharing controls remain prerequisites. Disposition
is PENDING; direct permission offers a possible rights route, not approval.

## Channel feasibility and operational prerequisites

| Approved stratum | Candidate route | Target | Current feasibility | Evidence needed before execution |
| --- | --- | ---: | --- | --- |
| Public app/product reviews | SRC-APP-01 | 60 | Conditional; rights and software-product frame unresolved | Applicable permission, fixed products/dates/configuration and later authorized eligibility ledger |
| Technical support/issue feedback | SRC-ISSUE-01 | 60 | Conditional; issue-license coverage and privacy unresolved | Exact repositories/content rights, unit/context rules and later authorized eligibility ledger |
| Software/community discussion | SRC-COMM-01; SRC-COMM-02 fallback | 60 | Conditional; source licensing route exists for first option, domain yield unverified | Site/revision license, attribution/privacy solution and later authorized eligibility ledger |

Documentation proves neither sample yield nor authentic author provenance for
individual records. Only after approval and separately authorized acquisition
can the study establish counts, dates, English eligibility, exact/near-duplicate
counts and selected pseudonyms. The later execution preregistration must freeze
source versions, frame/exclusion counts, dedup canonical-member rules, cross-channel
precedence, uniform within-channel selection, RNG/version/seeds, selected IDs,
20 dual-label IDs per channel, guide/roles and shipped evaluation configuration.
See the [annotation feasibility plan](V2_M9_2A_ANNOTATOR_FEASIBILITY.md).

For every candidate, proposed safeguards require owner approval of a named data
custodian role, authorized annotator access, protected storage, retention deadline,
deletion/backups policy and a withdrawal/takedown route. Ignored local directories
are not encryption or access control. Keep source mappings and permission/consent
records restricted; publish only separately approved safe provenance/aggregates.
Public repository material must contain no contributor names/usernames. Keep any
required attribution in a restricted manifest; this does not automatically satisfy
public attribution duties. Publication remains blocked until a compliant rights
and privacy route is approved, rather than dropping legally required credit.
Log post-freeze withdrawals against original denominators without replacements.
Redaction/normalization rules must be frozen, traceable and not selected by model
outputs; unsafe records excluded at screening remain in the count ledger.

## Required owner disposition and amendment record

Before changing any PENDING disposition, append a versioned decision containing:

1. Candidate ID, exact source/products/repositories/site, corpus dates/version,
   original collection method and rights evidence URLs/dated terms revision.
2. Responsible rights reviewer and owner decision role/date; permission/consent
   scope where needed, including third-party ownership limitations.
3. Local annotation/inference use and independent-human access authorization.
4. Separate decisions for public text, source IDs, labels and derivatives,
   attribution/license duties and privacy review. Approval of one is not all four.
5. Eligibility/channel/unit/context rules, retention/deletion/storage controls,
   contact/takedown procedure and remaining constraints.
6. Disposition `APPROVED_LOCAL_ONLY`, `APPROVED_PUBLIC`, `REJECTED` or `PENDING`,
   rationale and prospective amendment history. `APPROVED_PUBLIC` still requires
   material-specific privacy checks; it is not blanket publication authority.

Stop before ingestion if source rights remain unclear, permissions expire,
terms/access constraints conflict, contributor provenance is missing or privacy
cannot be controlled. Stop and seek a prospective owner-approved design amendment
if a channel cannot lawfully supply 60 eligible records, source overlap cannot be
resolved or independent human annotation is unavailable. Do not infer permission
from silence, accept terms on behalf of the owner, harvest opportunistically,
change the sample design or examine labels/predictions to choose alternatives.

## Research evidence log

All links above are original publisher/license-owner documentation checked on
2026-10-10. No feedback payload evidence exists. Dynamic documents must be rechecked
at approval/acquisition; later registration must retain a permitted policy
revision/digest or dated citation. A digest supplies integrity, not authorization.
Research conclusions are conditional interpretations for owner review. No source
Gate PASS, reference labels, predictions, scores, M9.3 sessions or M9.4 decision
are recorded by this register.

## Version history

| Version | Change | Owner decision |
| --- | --- | --- |
| 1.0.0 | Initial primary-source candidate and channel feasibility research | All five candidates PENDING; no source Gate approval |
