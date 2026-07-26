# Certificate Category Follow-up Design

- Task ID: `CHAT-CERTIFICATE-FOLLOWUP-001`
- Status: Review
- Human decision authority: Q-CHAT-FOLLOWUP-001=A, accepted by user `ㅇㅋ 진행해`
- Product surface: local/private `/api/v1/chat`, `/chat`
- Source authority: SFR-002/SFR-005, `KB_GUIDE.md`, D-024, ADR-0004/0009/0010

## 1. Goal

When a citizen asks a generic certificate request such as `증명서 발급해야해`, the system must
recognize the supported certificate category without guessing a specific certificate. It returns
a certificate-specific FOLLOWUP. Selecting one option must lead to the existing ACTIVE-only
retrieval and grounded answer path instead of repeating the four-category question.

## 2. Approved citizen behavior

The certificate-specific prompt is:

> 어떤 증명서를 발급하려고 하시나요?

The options are bounded to the five approved certificate KB topics:

1. 주민등록등본 발급
2. 주민등록초본 발급
3. 등본과 초본의 차이
4. 주민등록표 열람
5. 무인민원발급기 이용

The user may select an option or type a different question. Each selected label is itself a safe,
supported certificate query that the deterministic classifier and ACTIVE KB retrieval can
understand.

## 3. Non-goals

- Do not answer a generic certificate question by choosing one KB automatically.
- Do not add family relation, school, medical or other unsupported certificates.
- Do not add an LLM classification or generation call.
- Do not change the public OpenAPI response shape or add a DB enum/migration.
- Do not persist a FOLLOWUP as a failed question.
- Do not change the 15-minute signed context architecture.
- Do not implement admin candidate authoring or first region entry in this slice; they follow as
  separately testable vertical slices.

## 4. Considered approaches

### A. Server-owned category-aware FOLLOWUP — selected

The classifier returns `CERTIFICATE_ISSUANCE + followup_required=true`; the service selects a
server-owned certificate option set; the Web uses response intent for the prompt.

Advantages:

- The API meaning is correct at the source.
- All clients receive the same bounded options.
- The existing OpenAPI already permits a supported intent in FOLLOWUP.
- No client label sniffing or LLM is required.

Cost:

- Classification invariant, service branching, server response labels and Web prompt tests change
  together.

### B. Add `증명서` as a normal high-score intent term and retrieve immediately — rejected

This is smaller but may select an arbitrary KB when the citizen has not identified a certificate.
It violates “모르면 지어내지 않는다”.

### C. Keep the server UNKNOWN response and special-case it in the Web — rejected

This hides the loop in one client while server events, context and other consumers still describe
the question as UNKNOWN. It also couples behavior to Korean display text.

## 5. Classification design

### 5.1 Priority

The deterministic decision order remains:

1. personal lookup policy
2. legal judgment policy
3. existing specific supported-intent score
4. explicit out-of-scope term when no supported score exists
5. generic certificate category cue
6. unknown four-category FOLLOWUP

This order preserves `졸업증명서`, `재학증명서`, `성적증명서`, `건강진단서` and `진단서` as
OUT_OF_SCOPE. It also preserves `납세증명서` as LOCAL_TAX and `인감증명` as a specific
certificate query.

### 5.2 Outcome invariant

`ClassificationOutcome` permits `followup_required=true` when:

- `fallback_reason is None`, and
- `intent` is UNKNOWN or one of the four supported intents.

Policy fallback outcomes can never request FOLLOWUP. A supported category FOLLOWUP is not a
SUCCESS classification and must not enter retrieval until the citizen provides a specific option.

### 5.3 Generic cue

The bounded generic cue is compact text containing `증명서` after no specific supported score and
no explicit out-of-scope term matched. It is not added to the normal weighted intent terms because
that would incorrectly capture unsupported compound terms such as `졸업증명서`.

## 6. Service and response design

The service handles `outcome.followup_required` before retrieval:

- UNKNOWN uses the existing four-category options and UNKNOWN context.
- CERTIFICATE_ISSUANCE uses the five certificate options and certificate context.
- Both write only a text-free FOLLOWUP interaction event.
- Neither creates a failed-question row.

The context token for the certificate FOLLOWUP carries:

- `last_intent=CERTIFICATE_ISSUANCE`
- the existing selected region, if any
- `answer_status=FOLLOWUP`

The response builder keeps internal option IDs and server-owned Korean labels. The public
`followup_options: string[]` contract remains unchanged.

## 7. Web design

`FollowupCard` receives the typed response intent in addition to options.

- `CERTIFICATE_ISSUANCE` displays `어떤 증명서를 발급하려고 하시나요?`
- an all-region option list keeps the existing region prompt
- every other FOLLOWUP keeps `어떤 것부터 안내해 드릴까요?`

The selected-summary view uses the same prompt as the pre-selection view. Prompt selection must
depend on the typed response intent, not on substring inspection of option labels.

`ChatScreen` continues to:

- issue a new UUID idempotency key for the selected option
- pass the FOLLOWUP context token
- keep the transcript only in React state
- send the selected server label as the next question

## 8. Error and privacy behavior

- Malformed or empty server option lists remain rejected by the response builder.
- Provider calls remain zero for the FOLLOWUP itself.
- FOLLOWUP event `masked_question` remains null.
- Raw question text is not added to logs, context tokens or failed-question storage.
- Idempotency replay reissues a memory-only context token with the supported certificate intent.
- If a selected option lacks ACTIVE grounding, the existing `INSUFFICIENT_GROUNDING` policy applies;
  the implementation must not invent an answer.

## 9. Test design and acceptance criteria

### API classification

- `증명서 발급해야해` → `CERTIFICATE_ISSUANCE`, followup true, fallback null.
- unsupported `졸업증명서 발급` → OUT_OF_SCOPE.
- specific `주민등록등본 발급` → certificate, followup false.
- `납세증명서 발급` → local tax, followup false.

### API service/response

- generic certificate response is FOLLOWUP with certificate intent and exactly five approved labels.
- repository ACTIVE KB and office reads are zero for the initial category FOLLOWUP.
- interaction event is FOLLOWUP, certificate intent, masked text null.
- selecting every option can reach the existing classifier/retrieval path without returning the
  same category FOLLOWUP.
- unknown generic questions still return the existing four categories.

### Web

- certificate FOLLOWUP announces the certificate-specific prompt before and after selection.
- unknown FOLLOWUP retains the generic prompt.
- region FOLLOWUP retains the region prompt.
- clicking a certificate option sends that option with the response context token.
- keyboard access and 390px/430px no-overflow behavior remain intact.

### Area gates

- API focused classification/service/response tests
- Web `FollowupCard` and `chat-screen` tests
- API full test suite
- Web lint, typecheck and full test suite
- contract generation check and contract tests
- repository docs, package and secret checks

## 10. Version and rollback

Implementation is expected to advance application, Web and test versions. API/shared-contract
versions remain unchanged unless implementation proves the current schema cannot represent the
approved behavior.

Rollback is a code revert. There is no DB migration, data rewrite, provider state or deployment
rollback.
