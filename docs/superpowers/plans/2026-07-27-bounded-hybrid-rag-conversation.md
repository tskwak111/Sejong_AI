# Bounded Hybrid RAG Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Execution status (2026-07-27 KST):** 사용자가 계획과 Subagent-Driven 구현을 명시 승인했다.
Tasks 1~9의 local/offline 구현·task-scoped 독립 검토·area/version gate는 `e0b5bc2`까지
완료했다. Task 10 runner는 `5130b1e`에서 독립 review를 통과했고 actual은 정확히 한 번 실행해
20 selected·skip 0·11 provider-free·9 outbound 뒤 strict accepted usage/provider match 0으로
FAIL했다. 아래 checkbox는 실행 명세를 보존하기 위한 것이며 live status 권위는 이 문단,
`TASKS.md`, D-104/D-105와 구현 노트다. Task 11 final gate/Draft PR만 Pending이다.

**Goal:** 현재 ACTIVE/OFFICIAL KB 최대 20건만 사용해 일상어 paraphrase와 후속질문을 정확한 top-1 공식 안내로 연결하고, 근거가 없거나 모호한 질문은 route별 안전 FOLLOWUP/FALLBACK으로 닫는다.

**Architecture:** PII·personal/legal/privacy gate 뒤 request-local ACTIVE snapshot과 versioned non-factual coverage metadata의 교집합으로 runtime catalog를 만든다. exact approved example, unique lexical, signed context facet은 서버가 먼저 판정하고, 그 밖의 안전한 질문만 Upstage가 closed `route+intent+topic_id+coverage_id+pending_slot`을 제안한다. 서버가 membership·intent·coverage·ACTIVE/OFFICIAL을 다시 검증하고 typed grounding evidence가 있을 때만 한 KB를 사용한다. 사실·출처·기관·저장·후보·승인은 계속 서버 소유다.

**Tech Stack:** Python 3.12.13, FastAPI 0.139.0, Pydantic 2.13.4, httpx 0.28.1, PostgreSQL 17/Supabase CLI 2.109.1 patched runner, Node 24.12.0, pnpm 11.13.0, Next.js 16.2.10, React 19.2.7, Vitest 4.1.10, Playwright existing harness.

## Global Constraints

- 새 production dependency, DB migration, public response field, official `.2` byte 변경은 0이다.
- 시민 질문 원문·raw provider payload·context token·secret·DSN을 DB·문서·로그에 저장하거나 출력하지 않는다.
- provider 호출은 deterministic PII redaction과 personal/legal/privacy/policy gate 뒤에만 가능하다.
- 시민 검색은 current request의 ACTIVE/OFFICIAL `KnowledgeRecord` projection만 사용한다.
- runtime catalog는 1~20건일 때만 provider에 전달한다. 0건 또는 21건 이상이면 outbound 0이다.
- provider 입력은 masked question 최대 1,024자, topic별 승인 예시 최대 2개, 전체 보수적 입력 추정 최대 4,096 token이다.
- provider는 answer, fact, source, office, storage, candidate, confidence를 반환하지 못한다.
- SUCCESS는 한 KB와 한 source만 사용한다. score-zero 첫 record와 invalid topic의 조용한 대체 선택을 금지한다.
- local interactive cap은 classifier 80, generator 100, combined 160, concurrency 1, request당 최대 2회, 3초/8초, hard wall 12초, retry 0, VAT 포함 USD 0.20이다.
- 기존 20/30/40·USD 0.05 actual evidence와 synthetic profile은 역사적 결과로 보존한다.
- `[db.seed].enabled=false`를 유지한다. actual DB reset·`.2` seed·19→20 재승인 흐름은 이번 구현에 필요하지 않으며 자동 실행하지 않는다.
- `UPSTAGE_CLASSIFIER_MODE=false` 또는 `UPSTAGE_GROUNDED_CHAT_MODE=false`인 lane의 outbound는 0이다.
- 실제 provider 실행은 offline/area gate 통과 뒤 PII-free 고정 20건으로 한 번만 수행한다.
- public/remote deploy와 admin 공개 활성화는 하지 않는다.
- 자동 merge는 하지 않는다.

---

## File Responsibility Map

| Unit | Files | Responsibility |
|---|---|---|
| Retrieval metadata | `data/retrieval/topic-coverage.v1.json`, `data/retrieval/README.md` | 사실이 아닌 topic coverage 경계 |
| Runtime catalog | new `chat/topic_catalog.py` | ACTIVE/OFFICIAL intersection, max-20 catalog |
| Closed selector | `llm/classifier_contracts.py`, `classifier_prompt.py`, `upstage_classifier.py` | source-free topic+coverage 제안 |
| Deterministic selection | `chat/retrieval.py`, `chat/grounding.py` | exact/unique lexical/typed evidence |
| Chat orchestration | `chat/service.py`, `chat/response.py`, `local.py` | request snapshot, route, persistence, top-1 answer |
| Signed context | `chat/context.py` | DOMAIN/TOPIC_CHOICE와 ACTIVE topic revalidation |
| Behavioral contract | `contracts/*`, generated TypeScript, API/Web fixtures | 같은 public field 안의 option/copy 동기화 |
| Citizen Web | `chat-screen.tsx`, `RegionSelect.tsx`, `FollowupCard.tsx`, `AnswerCard.tsx` | 상시 지역 선택, 새 대화 유지, 관련 질문 |
| Provider budget | `llm/limits.py`, `settings.py`, `upstage_chat.py`, `.env.example` | 80/100/160과 USD 0.20 pre-reservation |
| UAT | `hybrid-rag-uat.v1.json`, API/runner/E2E tests | 48 offline + 20 actual subset |
| Governance | ADR/spec/decisions/TASKS/manifest/notes/reports | 승인·버전·검증·롤백 계보 |

---

### Task 1: Publish and validate the versioned topic coverage catalog

**Files:**
- Create: `data/retrieval/topic-coverage.v1.json`
- Create: `data/retrieval/README.md`
- Create: `apps/api/src/sejong_ai_api/chat/topic_catalog.py`
- Create: `apps/api/tests/chat/test_topic_catalog.py`
- Modify: `apps/api/tests/test_architecture.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class TopicCoverage:
    topic_id: str
    intent: Intent
    coverage_id: str
    coverage_label: str

@dataclass(frozen=True, slots=True)
class RuntimeTopic:
    record: KnowledgeRecord
    coverage: TopicCoverage

@dataclass(frozen=True, slots=True)
class TopicCatalog:
    topics: tuple[RuntimeTopic, ...]

    @property
    def provider_eligible(self) -> bool: ...
    def find(self, topic_id: str) -> RuntimeTopic | None: ...

def load_topic_coverage(path: Path) -> tuple[TopicCoverage, ...]: ...
def build_topic_catalog(
    records: Sequence[KnowledgeRecord],
    coverage: Sequence[TopicCoverage],
) -> TopicCatalog: ...
```

The JSON contains exactly the governed IDs:

```text
KB-CERT-01..05
KB-MOVE-01..05
KB-TAX-01..05
KB-WASTE-01..05
```

`KB-WASTE-03` metadata exists but appears in the runtime catalog only when the current DB projection
contains its approved ACTIVE/OFFICIAL record.

- [ ] **Step 1: Write RED metadata and intersection tests**

Cover exact schema version, `data_kind=NON_FACTUAL_RETRIEVAL_METADATA`, 20 unique topic IDs,
supported intent, uppercase bounded coverage ID, non-empty label, missing/extra key rejection,
duplicate rejection, inactive/non-`KnowledgeRecord` exclusion, deterministic ID ordering and
runtime sizes 0/1/20/21.

```python
catalog = build_topic_catalog(records, coverage)
assert tuple(topic.record.public_id for topic in catalog.topics) == (
    "KB-CERT-01",
    "KB-MOVE-01",
)
assert catalog.provider_eligible is True
assert build_topic_catalog([], coverage).provider_eligible is False
```

- [ ] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_topic_catalog.py `
  apps/api/tests/test_architecture.py `
  -q
```

Expected: import/file-not-found failures for the new catalog artifacts.

- [ ] **Step 3: Write the 20 non-factual coverage descriptors**

Use one stable coverage ID per topic. Labels describe included and excluded subject boundaries but
contain no fee, deadline, source URL, office, legal conclusion or free-form answer. The five waste
coverage IDs are:

```text
GENERAL_BULKY_DISPOSAL
PAYMENT_STICKER_CHANGE_REFUND
BED_FRAME_APPROVED_FEE
MATTRESS_APPROVED_FEE
COLLECTION_DAY_CONTACT
```

Use parallel bounded names for certificate, move and tax records. Document explicitly that this
file is retrieval metadata, not official administrative data.

- [ ] **Step 4: Implement the strict loader and runtime intersection**

Use `json.loads(path.read_text(encoding="utf-8"))`, exact key sets, no coercion, ID regex
`[A-Z0-9][A-Z0-9._-]{0,63}`, sorted tuples and a 20-topic hard maximum. Accept only
`KnowledgeRecord`, which is already the repository ACTIVE/OFFICIAL projection.

- [ ] **Step 5: Run GREEN and architecture guard**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_topic_catalog.py `
  apps/api/tests/test_architecture.py `
  -q
apps/api/.venv/Scripts/python.exe -m ruff check `
  apps/api/src/sejong_ai_api/chat/topic_catalog.py `
  apps/api/tests/chat/test_topic_catalog.py
apps/api/.venv/Scripts/python.exe -m mypy `
  apps/api/src/sejong_ai_api/chat/topic_catalog.py
```

- [ ] **Step 6: Commit Slice 1 catalog**

```powershell
git add data/retrieval `
  apps/api/src/sejong_ai_api/chat/topic_catalog.py `
  apps/api/tests/chat/test_topic_catalog.py `
  apps/api/tests/test_architecture.py
git commit -m "feat(chat): add governed active topic catalog"
```

---

### Task 2: Extend the closed classifier to topic and coverage selection

**Files:**
- Modify: `apps/api/src/sejong_ai_api/llm/classifier_contracts.py`
- Modify: `apps/api/src/sejong_ai_api/llm/classifier_prompt.py`
- Modify: `apps/api/src/sejong_ai_api/llm/upstage_classifier.py`
- Modify: `apps/api/src/sejong_ai_api/chat/classification.py`
- Modify: `apps/api/src/sejong_ai_api/chat/service.py`
- Modify: `apps/api/src/sejong_ai_api/local.py`
- Modify: `apps/api/tests/llm/test_classifier_contracts.py`
- Modify: `apps/api/tests/llm/test_prompt.py`
- Modify: `apps/api/tests/llm/test_upstage_classifier.py`
- Modify: `apps/api/tests/chat/test_classification.py`
- Modify: `apps/api/tests/test_local.py`

**Interfaces:**

```python
class ClassifierRoute(str, Enum):
    SUPPORTED = "SUPPORTED"
    NO_TOPIC_MATCH = "NO_TOPIC_MATCH"
    CIVIC_SCOPE_GAP = "CIVIC_SCOPE_GAP"
    NON_CIVIC = "NON_CIVIC"
    NEEDS_FOLLOWUP = "NEEDS_FOLLOWUP"

class PendingSlot(str, Enum):
    DOMAIN = "DOMAIN"
    TOPIC_CHOICE = "TOPIC_CHOICE"
    CERTIFICATE_KIND = "CERTIFICATE_KIND"
    REGION = "REGION"
    WASTE_ITEM = "WASTE_ITEM"

@dataclass(frozen=True, slots=True)
class ClassifierDecision:
    route: ClassifierRoute
    intent: Intent | None
    topic_id: str | None
    coverage_id: str | None
    pending_slot: PendingSlot | None

class QuestionClassifierPort(Protocol):
    async def classify(
        self,
        question: SafeQuestion,
        catalog: TopicCatalog,
    ) -> ClassifierDecision | None: ...
```

- [ ] **Step 1: Add strict combination RED tests**

The exact JSON keys become:

```python
{
    "route",
    "intent",
    "topic_id",
    "coverage_id",
    "pending_slot",
}
```

Test all approved combinations and reject unknown keys, free text, confidence, mismatched
topic/coverage, `SUPPORTED` without all three required values, `NO_TOPIC_MATCH` without intent,
scope/non-civic with any extra value, `DOMAIN` with intent, and topic-specific slots without intent.

- [ ] **Step 2: Add prompt/catalog RED tests**

Assert the prompt includes only:

```json
{
  "masked_question": "안전한 질문",
  "topic_catalog": [
    {
      "topic_id": "KB-WASTE-01",
      "intent": "BULKY_WASTE",
      "service_name": "대형폐기물 배출신청 절차",
      "coverage_id": "GENERAL_BULKY_DISPOSAL",
      "coverage_label": "일반 가구류 배출 절차",
      "approved_examples": ["대형폐기물은 어떻게 신청하나요?"]
    }
  ]
}
```

Assert at most two examples, max 1,024 masked-question chars, no facts/source/office/fee/caution,
catalog sizes 0 and 21 reject without transport, and conservative total estimate above 4,096
rejects.

**Implemented internal serialization note (controller-approved during Task 2):** the semantic
fields above are unchanged, but the provider-bound `topic_catalog` uses one exact six-column header
(`topic_id`, `intent`, `service_name`, `coverage_id`, `coverage_label`, `approved_examples`) plus
deterministically ordered row arrays. Repeating those six JSON keys for all 19/20 topics made the
real governed catalog exceed the conservative 4,096 input bound. The columnar form preserves every
topic and value without truncation or sampling and keeps the real 20-topic, 1,024-character-question
payload at 4,094/4,096. This is an internal prompt encoding only; the provider output schema, public
API, DB and official-data contracts are unchanged.

- [ ] **Step 3: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py `
  apps/api/tests/llm/test_prompt.py `
  apps/api/tests/llm/test_upstage_classifier.py `
  apps/api/tests/chat/test_classification.py `
  apps/api/tests/test_local.py `
  -q
```

- [ ] **Step 4: Implement the closed parser and prompt**

Add:

```python
def estimate_classifier_input_upper_bound(
    messages: tuple[dict[str, str], ...],
) -> int:
    return sum(len(message["content"]) for message in messages)
```

This intentionally overestimates Korean token use. The adapter checks `<= 4096` before ledger
reservation. `build_classifier_messages` receives the immutable `TopicCatalog` and serializes all
eligible topics; it never truncates or samples the catalog.

- [ ] **Step 5: Update the provider and local lazy port**

Change `QuestionClassifier.classify`, `_LazyQuestionClassifier.classify` and the service protocol
to accept the same request-local catalog. Preserve one POST, timeout 3 seconds, retry 0, JSON mode,
value-free exceptions and `None` on every provider/contract failure.

- [ ] **Step 6: Run classifier GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py `
  apps/api/tests/llm/test_prompt.py `
  apps/api/tests/llm/test_upstage_classifier.py `
  apps/api/tests/chat/test_classification.py `
  apps/api/tests/test_local.py `
  -q
apps/api/.venv/Scripts/python.exe -m ruff check `
  apps/api/src/sejong_ai_api/llm `
  apps/api/src/sejong_ai_api/chat/classification.py `
  apps/api/tests/llm
apps/api/.venv/Scripts/python.exe -m mypy `
  apps/api/src/sejong_ai_api/llm `
  apps/api/src/sejong_ai_api/chat/classification.py
```

- [ ] **Step 7: Commit the closed selector contract**

```powershell
git add apps/api/src/sejong_ai_api/llm `
  apps/api/src/sejong_ai_api/chat/classification.py `
  apps/api/src/sejong_ai_api/chat/service.py `
  apps/api/src/sejong_ai_api/local.py `
  apps/api/tests/llm `
  apps/api/tests/chat/test_classification.py `
  apps/api/tests/test_local.py
git commit -m "feat(llm): select bounded topic coverage"
```

---

### Task 3: Replace boolean grounding with typed evidence

**Files:**
- Modify: `apps/api/src/sejong_ai_api/chat/retrieval.py`
- Modify: `apps/api/src/sejong_ai_api/chat/grounding.py`
- Modify: `apps/api/tests/chat/test_retrieval.py`
- Modify: `apps/api/tests/chat/test_grounding.py`

**Interfaces:**

```python
class GroundingEvidenceKind(str, Enum):
    EXACT_APPROVED_EXAMPLE = "EXACT_APPROVED_EXAMPLE"
    UNIQUE_LEXICAL_MATCH = "UNIQUE_LEXICAL_MATCH"
    VALIDATED_SEMANTIC_COVERAGE = "VALIDATED_SEMANTIC_COVERAGE"
    VALIDATED_CONTEXT_FACET = "VALIDATED_CONTEXT_FACET"

@dataclass(frozen=True, slots=True)
class GroundingEvidence:
    kind: GroundingEvidenceKind
    topic_id: str
    coverage_id: str | None
    matched_tokens: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class TopicSelection:
    topic: RuntimeTopic
    evidence: GroundingEvidence

def select_deterministic_topic(
    question: SafeQuestion,
    intent: Intent,
    catalog: TopicCatalog,
) -> TopicSelection | None: ...

def validate_semantic_selection(
    decision: ClassifierDecision,
    catalog: TopicCatalog,
) -> TopicSelection | None: ...
```

`evaluate_grounding` becomes:

```python
def evaluate_grounding(
    question: SafeQuestion,
    intent: Intent,
    selection: TopicSelection | None,
) -> GroundingDecision: ...
```

- [ ] **Step 1: Write exact/unique/zero/invalid RED tests**

Test exact example, one unique strong service/example overlap, tied top-two, no intent anchor,
score zero, semantic catalog membership, coverage mismatch, intent mismatch, inactive absence,
context facet, topic mismatch and record-specific negative details.

```python
assert select_deterministic_topic(
    safe("주소이전 신고는 어디에서 하나요?"),
    Intent.MOVE_IN_RESIDENT_REGISTRATION,
    catalog,
).evidence.kind is GroundingEvidenceKind.UNIQUE_LEXICAL_MATCH

assert select_deterministic_topic(
    safe("못 쓰는 냉장고를 버릴 때 신고해야 하나요?"),
    Intent.BULKY_WASTE,
    catalog,
) is None
```

- [ ] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_retrieval.py `
  apps/api/tests/chat/test_grounding.py `
  -q
```

- [ ] **Step 3: Implement deterministic and semantic selectors**

Exact approved example always wins within the stated intent. Unique lexical requires:

1. at least one `service_or_example_overlap`;
2. at least one existing intent anchor;
3. the first ranking tuple is strictly greater than the second;
4. the record is a topic in the request catalog.

Never return a record when every score is zero. `validate_semantic_selection` requires exact
topic ID, coverage ID and intent equality against the current catalog.

- [ ] **Step 4: Implement typed grounding validation**

Remove `allow_contextual_detail: bool`. Grounding accepts only a `TopicSelection`, verifies the
selected topic record category and evidence topic/coverage, preserves record-specific negative
detail checks and exposes server-owned facts only from `selection.topic.record`.

- [ ] **Step 5: Run GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_retrieval.py `
  apps/api/tests/chat/test_grounding.py `
  -q
apps/api/.venv/Scripts/python.exe -m ruff check `
  apps/api/src/sejong_ai_api/chat/retrieval.py `
  apps/api/src/sejong_ai_api/chat/grounding.py `
  apps/api/tests/chat/test_retrieval.py `
  apps/api/tests/chat/test_grounding.py
apps/api/.venv/Scripts/python.exe -m mypy `
  apps/api/src/sejong_ai_api/chat/retrieval.py `
  apps/api/src/sejong_ai_api/chat/grounding.py
```

- [ ] **Step 6: Commit typed grounding**

```powershell
git add apps/api/src/sejong_ai_api/chat/retrieval.py `
  apps/api/src/sejong_ai_api/chat/grounding.py `
  apps/api/tests/chat/test_retrieval.py `
  apps/api/tests/chat/test_grounding.py
git commit -m "feat(chat): require typed grounding evidence"
```

---

### Task 4: Integrate request-local snapshots, routes and storage

**Files:**
- Modify: `apps/api/src/sejong_ai_api/chat/service.py`
- Modify: `apps/api/src/sejong_ai_api/chat/response.py`
- Modify: `apps/api/src/sejong_ai_api/llm/evaluation.py`
- Modify: `apps/api/src/sejong_ai_api/local.py`
- Modify: `apps/api/tests/chat/test_service.py`
- Modify: `apps/api/tests/chat/test_response.py`
- Modify: `apps/api/tests/chat/test_grounded_generation.py`
- Modify: `apps/api/tests/chat/test_official_examples.py`
- Modify: `apps/api/tests/chat/test_sample_questions_20.py`
- Modify: `apps/api/tests/llm/test_evaluation.py`
- Modify: `apps/api/tests/test_local.py`

**Interfaces:**

```python
async def _load_active_snapshot(
    self,
    intents: Sequence[Intent],
) -> tuple[KnowledgeRecord, ...]: ...

async def _select_topic(
    self,
    question: SafeQuestion,
    *,
    outcome: ClassificationOutcome,
    prior_context: ChatContext | None,
    deadline: float,
) -> TopicSelection | FollowupPlan | ClassifierDecision | None: ...
```

`ChatService` receives immutable coverage metadata at construction; the repository protocol stays
unchanged.

- [ ] **Step 1: Write route and read-count RED tests**

Cover:

- deterministic intent: one `list_active_kb(intent)` call;
- unknown safe question: four intent reads via `asyncio.gather`;
- one request reuses one snapshot for selection, grounding and response;
- semantic paraphrases select `KB-MOVE-01` and `KB-WASTE-01`;
- `NO_TOPIC_MATCH` returns `INSUFFICIENT_GROUNDING` and one safe failed row;
- `CIVIC_SCOPE_GAP` uses only the scope queue;
- `NON_CIVIC`, policy, privacy and provider failure write no interaction/failed/scope row;
- invalid topic/coverage returns provider-failure domain FOLLOWUP, not lexical success;
- generator failure returns the complete selected KB template and official source.
- every remaining production and test call site uses `TopicSelection`; the synthetic evaluator,
  official-example test and 20-sample test do not restore a record/boolean compatibility overload.

- [ ] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_service.py `
  apps/api/tests/chat/test_response.py `
  apps/api/tests/chat/test_grounded_generation.py `
  apps/api/tests/chat/test_official_examples.py `
  apps/api/tests/chat/test_sample_questions_20.py `
  apps/api/tests/llm/test_evaluation.py `
  apps/api/tests/test_local.py `
  -q
```

- [ ] **Step 3: Build and reuse the request snapshot**

For known supported intent, load only that intent. For provider/domain selection, load all four
supported intents concurrently, flatten by `public_id`, then call `build_topic_catalog`. Do not
cache beyond `_execute_once`.

Migrate the synthetic evaluator and the official/sample test helpers through the same
`TopicCatalog` → `TopicSelection` boundary. No caller may pass a bare `KnowledgeRecord` to
`evaluate_grounding`, and no permissive compatibility overload is added.

- [ ] **Step 4: Integrate the exact decision order**

```text
redaction
→ personal/legal/privacy
→ deterministic classification
→ request snapshot/catalog
→ exact/unique lexical or validated context
→ ambiguous-only provider selector
→ server validation
→ typed grounding
→ one record response
→ route-specific persistence
```

`NO_TOPIC_MATCH` carries the returned supported intent into the existing
`INSUFFICIENT_GROUNDING` response. Provider `None`, cap, timeout, invalid JSON, invalid catalog ID
or prompt bound failure returns the exact domain FOLLOWUP copy and no storage.

- [ ] **Step 5: Run Slice 2 service GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat `
  apps/api/tests/test_local.py `
  apps/api/tests/privacy `
  apps/api/tests/llm/test_architecture.py `
  -q
```

- [ ] **Step 6: Commit orchestration**

```powershell
git add apps/api/src/sejong_ai_api/chat/service.py `
  apps/api/src/sejong_ai_api/chat/response.py `
  apps/api/src/sejong_ai_api/llm/evaluation.py `
  apps/api/src/sejong_ai_api/local.py `
  apps/api/tests/chat `
  apps/api/tests/llm/test_evaluation.py `
  apps/api/tests/test_local.py
git commit -m "feat(chat): orchestrate active topic selection"
```

---

### Task 5: Implement intent-specific followups and context facets

**Files:**
- Modify: `apps/api/src/sejong_ai_api/chat/context.py`
- Modify: `apps/api/src/sejong_ai_api/chat/service.py`
- Modify: `apps/api/src/sejong_ai_api/chat/response.py`
- Modify: `apps/api/tests/chat/test_context.py`
- Modify: `apps/api/tests/chat/test_service.py`
- Modify: `apps/api/tests/chat/test_response.py`
- Modify: `contracts/openapi-v1.yaml`
- Modify: `contracts/chat-response.schema.json`
- Modify: `contracts/fixtures/chat-response/valid-followup.json`
- Modify: `packages/shared-contracts/src/generated/api.ts`
- Modify: `packages/shared-contracts/test/contract-fixtures.test.mjs`
- Modify: `apps/api/tests/test_chat_contract_fixtures.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class FollowupPlan:
    intent: Intent
    pending_slot: PendingSlot
    options: tuple[str, ...]
```

Public `followup_options: string[]` is unchanged.

- [ ] **Step 1: Add context/followup RED tests**

Test:

- unknown domain → `DOMAIN`;
- generic move → max four exact approved service labels;
- generic certificate → exactly `주민등록등본 발급`, `주민등록초본 발급`,
  `등본과 초본의 차이`;
- generic waste → current ACTIVE service labels, max five, including `KB-WASTE-03` only when active;
- generic tax/`재산세 일반 안내` → current five tax service labels;
- tax rate/exemption and refrigerator dedicated pickup → IG;
- `수수료`, `준비물`, `처리기간`, `어디`, `온라인` use `VALIDATED_CONTEXT_FACET` only when the
  signed topic is current ACTIVE and the record has that field;
- `취소하려면?` changes to `KB-WASTE-02`;
- an explicit new intent discards the prior topic;
- expired/invalid token behaves as no context;
- FOLLOWUP creates failed row 0.

- [ ] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_context.py `
  apps/api/tests/chat/test_service.py `
  apps/api/tests/chat/test_response.py `
  -q
corepack.cmd pnpm --filter @sejong-ai/shared-contracts test
```

- [ ] **Step 3: Extend v2 pending slots without adding free text**

Allow `DOMAIN` and `TOPIC_CHOICE` in the existing v2 signed token. Continue issuing only v2 and
reading v1/v2. Token claims remain `topic_id`, `last_intent`, `pending_slot`, `selected_region`,
`dialog_act`, nonce/times/status only.

- [ ] **Step 4: Build options from server-owned runtime topics**

Use a fixed topic-ID order per intent and return only labels whose topics are present in the
current catalog. Certificate display labels are the three approved short labels; clicking each
still sends a new request through full server validation.

- [ ] **Step 5: Synchronize behavioral examples**

Update OpenAPI/JSON Schema examples and the valid FOLLOWUP fixture. Do not change required fields,
schema branches or API version. Regenerate TypeScript and inspect that only example-level generated
changes occur.

```powershell
corepack.cmd pnpm contracts:generate
corepack.cmd pnpm contracts:check
corepack.cmd pnpm --filter @sejong-ai/shared-contracts test
```

- [ ] **Step 6: Run context and contract GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_context.py `
  apps/api/tests/chat/test_service.py `
  apps/api/tests/chat/test_response.py `
  apps/api/tests/test_chat_contract_fixtures.py `
  -q
```

- [ ] **Step 7: Commit behavioral contract and context**

```powershell
git add apps/api/src/sejong_ai_api/chat `
  apps/api/tests/chat `
  contracts `
  packages/shared-contracts
git commit -m "feat(chat): guide intent-specific followups"
```

---

### Task 6: Make region and certificate guidance natural in the Web

**Files:**
- Modify: `apps/web/src/app/chat/chat-screen.tsx`
- Modify: `apps/web/src/app/chat/chat-screen.test.tsx`
- Modify: `apps/web/src/components/citizen/RegionSelect.tsx`
- Create: `apps/web/src/components/citizen/RegionSelect.test.tsx`
- Modify: `apps/web/src/components/citizen/FollowupCard.tsx`
- Modify: `apps/web/src/components/citizen/FollowupCard.test.tsx`
- Modify: `apps/web/src/components/citizen/AnswerCard.tsx`
- Create: `apps/web/src/components/citizen/AnswerCard.test.tsx`
- Modify: `apps/web/src/lib/demo-fixtures.ts`
- Modify: `apps/web/src/lib/labels.ts`
- Modify: `apps/web/src/app/chat/contract-fixtures.test.tsx`
- Modify: `tools/web-e2e/e2e/home-chat-shell.spec.ts`

**Interfaces:**

```ts
const CERTIFICATE_RELATED_QUESTIONS = [
  "주민등록표 열람",
  "무인민원발급기 이용",
] as const;

function relatedQuestions(response: ChatResponse): readonly string[] {
  return response.sources.some((source) => source.source_id === "KB-CERT-01")
    ? CERTIFICATE_RELATED_QUESTIONS
    : [];
}
```

- [ ] **Step 1: Write Web RED tests**

Assert:

- region control is visible before and after messages;
- collapsed copy is `거주 지역 선택 · 선택사항`;
- selected copy is `<지역명> · 변경`;
- native/select-equivalent keyboard operation, visible accessible name and 44px minimum target;
- `새 대화` clears transcript/context/input/failure but preserves `selectedRegion`;
- remount/reload simulation resets region because no storage is used;
- localStorage/sessionStorage/cookie writes remain 0;
- certificate prompt is `어떤 주민등록 증명서가 필요하신가요?`;
- the first certificate options are exactly three;
- a `KB-CERT-01` SUCCESS shows two related-question buttons;
- clicking a related question sends it with the response context token and a fresh idempotency key.

- [ ] **Step 2: Run RED**

```powershell
corepack.cmd pnpm --filter @sejong-ai/web exec vitest run `
  src/app/chat/chat-screen.test.tsx `
  src/app/chat/contract-fixtures.test.tsx `
  src/components/citizen/RegionSelect.test.tsx `
  src/components/citizen/FollowupCard.test.tsx `
  src/components/citizen/AnswerCard.test.tsx
```

- [ ] **Step 3: Implement the compact always-visible region control**

Render `RegionSelect` immediately above `PrivacyNotice` for every chat state. Keep region only in
the existing `useState`; remove `setSelectedRegion(null)` from `startNewConversation`. Do not add
storage, URL params, cookies or server profile.

- [ ] **Step 4: Implement contextual certificate suggestions**

Suggestions are client navigation affordances, not answer facts. Show them only for a SUCCESS whose
server-bound source ID is `KB-CERT-01`; the click calls the existing `ask()` path so the server
reclassifies and regrounds the next question.

- [ ] **Step 5: Run Web GREEN**

```powershell
corepack.cmd pnpm --filter @sejong-ai/web lint
corepack.cmd pnpm --filter @sejong-ai/web typecheck
corepack.cmd pnpm --filter @sejong-ai/web test
corepack.cmd pnpm --filter @sejong-ai/web build
```

- [ ] **Step 6: Run the browser matrix**

```powershell
corepack.cmd pnpm --dir tools/web-e2e test -- `
  --config=playwright.config.ts `
  e2e/home-chat-shell.spec.ts
```

Expected: the region/new-conversation/certificate cases pass in `mobile-390`, `mobile-430` and
desktop with keyboard and visible focus checks.

- [ ] **Step 7: Commit citizen UX**

```powershell
git add apps/web/src tools/web-e2e/e2e/home-chat-shell.spec.ts
git commit -m "feat(web): guide bounded civic conversations"
```

---

### Task 7: Enforce the local interactive attempt and cost budget

**Files:**
- Modify: `apps/api/src/sejong_ai_api/llm/limits.py`
- Modify: `apps/api/src/sejong_ai_api/llm/settings.py`
- Modify: `apps/api/src/sejong_ai_api/llm/upstage_classifier.py`
- Modify: `apps/api/src/sejong_ai_api/llm/upstage_chat.py`
- Modify: `apps/api/src/sejong_ai_api/local.py`
- Modify: `apps/api/.env.example`
- Modify: `apps/api/tests/llm/test_limits.py`
- Modify: `apps/api/tests/llm/test_settings.py`
- Modify: `apps/api/tests/llm/test_upstage_classifier.py`
- Modify: `apps/api/tests/llm/test_upstage_chat.py`
- Modify: `apps/api/tests/test_local.py`
- Create: `docs/runbooks/UPSTAGE-HYBRID-RAG-LOCAL.md`

**Interfaces:**

```python
LOCAL_INTERACTIVE_COST_CAP_USD = Decimal("0.20")

@dataclass(slots=True)
class ProviderCostReservation:
    lane: ProviderLane
    worst_case_usd: Decimal

    def record_usage(self, usage: TokenUsage) -> None: ...

class ProviderAttemptLedger:
    def __init__(
        self,
        *,
        classifier_cap: int = 80,
        generator_cap: int = 100,
        combined_cap: int = 160,
        cost_cap_usd: Decimal = Decimal("0.20"),
        classifier_worst_case_usd: Decimal,
        generator_worst_case_usd: Decimal,
    ) -> None: ...
```

- [ ] **Step 1: Write attempt and cost RED tests**

Test classifier 80, generator 100, combined 160, concurrency one, no reset API, and:

```python
assert ledger.actual_cost_usd == Decimal("0")
async with ledger.reserve_classifier() as reservation:
    reservation.record_usage(TokenUsage(20, 0, 10))
assert ledger.actual_cost_usd == estimate_cost_usd(TokenUsage(20, 0, 10))
```

Before each reservation require:

```text
actual cumulative cost + selected lane configured worst-case <= USD 0.20
```

If usage is missing, invalid, timeout or transport failure after reservation, charge that lane's
configured worst-case on context exit. Reject the next call before transport when the inequality
would be violated.

- [ ] **Step 2: Add exact profile RED tests**

The combined local interactive profile requires:

```text
LLM_CLASSIFIER_ATTEMPT_CAP=80
LLM_GENERATOR_ATTEMPT_CAP=100
LLM_COMBINED_ATTEMPT_CAP=160
LLM_SESSION_COST_CAP_USD=0.20
```

Keep synthetic mode 30 attempts/USD 0.05 and standalone historical grounded-chat profile unchanged.
Reject duplicate, quoted, malformed or non-exact values without exposing the API key.

- [ ] **Step 3: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_limits.py `
  apps/api/tests/llm/test_settings.py `
  apps/api/tests/llm/test_upstage_classifier.py `
  apps/api/tests/llm/test_upstage_chat.py `
  apps/api/tests/test_local.py `
  -q
```

- [ ] **Step 4: Implement atomic pre-reservation**

Use one process ledger, one lock and one semaphore. The reservation owns the semaphore until actual
usage or conservative cost is recorded. There is no reset method. The exception remains the
value-free `AttemptCapReached("ATTEMPT_CAP_REACHED")`.

- [ ] **Step 5: Record provider usage inside the reservation**

Classifier and generator parse strict `usage.prompt_tokens` and `usage.completion_tokens` while the
reservation is active, call `record_usage`, then parse the closed decision/draft. Missing or invalid
usage fails closed and conservatively charges worst-case. Never include token counts or cost in the
citizen response.

- [ ] **Step 6: Wire exact local settings and runbook**

Derive worst-case amounts with the existing `estimate_cost_usd` and approved max-token values.
Update `.env.example` and the runbook with non-secret values only. Modes remain false by default.

- [ ] **Step 7: Run LLM/local GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm `
  apps/api/tests/test_local.py `
  -q
apps/api/.venv/Scripts/python.exe -m ruff check `
  apps/api/src/sejong_ai_api/llm `
  apps/api/tests/llm `
  apps/api/src/sejong_ai_api/local.py
apps/api/.venv/Scripts/python.exe -m mypy `
  apps/api/src/sejong_ai_api/llm `
  apps/api/src/sejong_ai_api/local.py
```

- [ ] **Step 8: Commit local budget**

```powershell
git add apps/api/src/sejong_ai_api/llm `
  apps/api/src/sejong_ai_api/local.py `
  apps/api/.env.example `
  apps/api/tests/llm `
  apps/api/tests/test_local.py `
  docs/runbooks/UPSTAGE-HYBRID-RAG-LOCAL.md
git commit -m "feat(llm): bound local interactive cost"
```

---

### Task 8: Freeze and execute the 48-case offline Hybrid RAG UAT

**Files:**
- Create: `apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json`
- Create: `apps/api/tests/chat/test_hybrid_rag_uat.py`
- Modify: `apps/api/tests/chat/test_official_examples.py`
- Modify: `apps/api/tests/chat/test_sample_questions_20.py`
- Modify: `scripts/tests/test_upstage_classifier_evaluation.py`
- Create: `docs/test-reports/CHAT-HYBRID-RAG-001-OFFLINE-UAT.md`

**Fixture schema:**

```json
{
  "schema_version": 1,
  "data_kind": "SYNTHETIC_CHAT_UAT",
  "cases": [
    {
      "id": "HR-001",
      "group": "PARAPHRASE_SUCCESS",
      "question": "새 집으로 옮긴 뒤 행정상 거주지를 바꾸는 절차가 궁금해요",
      "expected_route": "SUPPORTED",
      "expected_intent": "MOVE_IN_RESIDENT_REGISTRATION",
      "expected_topic_id": "KB-MOVE-01",
      "expected_provider_use": 1,
      "expected_storage": "VALUE_FREE_SUCCESS",
      "actual_subset": true
    }
  ]
}
```

- [ ] **Step 1: Create fixture validator RED**

Require exactly 48 unique IDs and group counts:

```text
PARAPHRASE_SUCCESS 20
TOPIC_DISTINCTION 8
GENERIC_FOLLOWUP 4
NO_TOPIC_GROUNDING 4
SCOPE_OR_NON_CIVIC 4
CONTEXT 4
PRIVACY_POLICY 4
```

Require exactly 20 `actual_subset=true` with counts 8/4/4/4 across paraphrase, distinction,
no-topic-or-followup and scope-or-noncivic. Privacy cases use only obvious synthetic PII-shaped
values, expect provider use 0, and reports never repeat their text.

- [ ] **Step 2: Add service-level RED assertions**

Use the real redaction, classification, catalog, retrieval, grounding and response code with a
closed fake provider. Assert route, intent, topic, outbound count and repository deltas for every
case.

- [ ] **Step 3: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_hybrid_rag_uat.py `
  apps/api/tests/chat/test_official_examples.py `
  apps/api/tests/chat/test_sample_questions_20.py `
  scripts/tests/test_upstage_classifier_evaluation.py `
  -q
```

- [ ] **Step 4: Implement the frozen 48-case corpus**

Include the user-reported move, wardrobe, waste cancel, refrigerator, certificate, young-rent,
property-tax, weather and phone-shaped move cases. Mark all text as synthetic test material, never
official data.

- [ ] **Step 5: Run offline acceptance**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_hybrid_rag_uat.py `
  apps/api/tests/chat/test_official_examples.py `
  apps/api/tests/chat/test_sample_questions_20.py `
  scripts/tests/test_upstage_classifier_evaluation.py `
  -q
```

Expected: Hybrid RAG 48/48, official approved examples 57/57, frozen classifier 60/60, skip 0.

- [ ] **Step 6: Write aggregate-only offline report**

Record group counts, route/topic matches, provider expected/actual counts and storage deltas by case
ID. Do not copy privacy case text or provider payloads.

- [ ] **Step 7: Commit UAT**

```powershell
git add apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json `
  apps/api/tests/chat/test_hybrid_rag_uat.py `
  apps/api/tests/chat/test_official_examples.py `
  apps/api/tests/chat/test_sample_questions_20.py `
  scripts/tests/test_upstage_classifier_evaluation.py `
  docs/test-reports/CHAT-HYBRID-RAG-001-OFFLINE-UAT.md
git commit -m "test(chat): freeze bounded hybrid rag UAT"
```

---

### Task 9: Run area gates and freeze implementation versions

**Files:**
- Modify: `versions/manifest.json`
- Modify: `CHANGELOG.md`
- Modify: `TASKS.md`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `docs/12_VERSIONING_AND_RELEASES.md`
- Modify: `docs/decisions/DECISION_LOG.md`
- Create via script: one implementation note per completed vertical slice
- Modify: `docs/implementation-notes/INDEX.md`
- Create: `docs/test-reports/CHAT-HYBRID-RAG-001-INTEGRATION.md`

**Version targets:**

```json
{
  "application": "0.12.0-bounded-hybrid-rag",
  "web": "0.8.0-guided-chat",
  "api": "4.0.0-draft",
  "shared_contracts": "1.0.0",
  "database_schema": "0.5.0-local",
  "official_data": "0.1.0-initial.2",
  "prompt_set": "0.4.0-topic-coverage",
  "test_suite": "2.0.0-bounded-hybrid-rag"
}
```

- [ ] **Step 1: Run API area gate**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests -q
apps/api/.venv/Scripts/python.exe -m ruff check apps/api/src apps/api/tests
apps/api/.venv/Scripts/python.exe -m mypy apps/api/src
```

- [ ] **Step 2: Run Web and contract area gate**

```powershell
corepack.cmd pnpm --filter @sejong-ai/shared-contracts generate:check
corepack.cmd pnpm --filter @sejong-ai/shared-contracts test
corepack.cmd pnpm --filter @sejong-ai/web lint
corepack.cmd pnpm --filter @sejong-ai/web typecheck
corepack.cmd pnpm --filter @sejong-ai/web test
corepack.cmd pnpm --filter @sejong-ai/web build
```

- [ ] **Step 3: Run DB regression without reset/seed**

Run current repository/SQL unit and contract checks only:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/db `
  apps/api/tests/admin `
  scripts/tests/test_supabase_tooling.py `
  -q
```

Do not run destructive local DB reset. Record the existing schema/data versions as unchanged.

- [ ] **Step 4: Update versions and grouped implementation notes**

Create notes for catalog/selector, context/Web, budget/UAT. Each note records exact commands, pass
counts, privacy/storage/source invariants, no DB/official-data change, rollback and human/AI
responsibility.

- [ ] **Step 5: Record integration evidence**

Write only observed results. Keep actual provider status Pending until Task 10.

- [ ] **Step 6: Run documentation and version checks**

```powershell
apps/api/.venv/Scripts/python.exe -B scripts/check_repository_docs.py
apps/api/.venv/Scripts/python.exe -B scripts/validate_codex_package.py
git diff --check
```

- [ ] **Step 7: Commit integration/version evidence**

```powershell
git add versions/manifest.json CHANGELOG.md TASKS.md docs
git commit -m "docs(chat): record bounded hybrid rag integration"
```

---

### Task 10: Run the approved PII-free 20-case actual selector subset

**Files:**
- Create: `scripts/run_hybrid_rag_actual.py`
- Create: `scripts/tests/test_run_hybrid_rag_actual.py`
- Create: `docs/runbooks/UPSTAGE-HYBRID-RAG-ACTUAL.md`
- Create: `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md`
- Create via script: `CHAT-HYBRID-RAG-001 actual selector 실행` implementation note
- Modify: `docs/implementation-notes/INDEX.md`

**Interfaces:**

```powershell
apps/api/.venv/Scripts/python.exe -B `
  scripts/run_hybrid_rag_actual.py `
  --fixture apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json `
  --report docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md
```

- [ ] **Step 1: Write runner/report RED tests**

Assert exact 20 allowlisted case IDs, provider-safe cases only, no privacy case, no raw question or
payload in stdout/report, no key/DSN, route/topic aggregate, exact fixture-driven outbound count,
token totals, VAT-inclusive cost and pre-reservation stop before a call that could exceed USD 0.20.

- [ ] **Step 2: Run offline runner RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  scripts/tests/test_run_hybrid_rag_actual.py `
  apps/api/tests/llm/test_upstage_classifier.py `
  apps/api/tests/llm/test_limits.py `
  -q
```

- [ ] **Step 3: Implement the bounded actual runner**

Load the same strict settings parser and topic catalog used by the app. Send only `actual_subset`
cases, keep concurrency one and no retry, and write aggregate evidence by fixture ID. Abort before
network on invalid exact profile, secret scan failure or offline gate failure.

- [ ] **Step 4: Preflight without displaying values**

Require:

```text
UPSTAGE_CLASSIFIER_MODE=true
UPSTAGE_GROUNDED_CHAT_MODE=true
model=solar-pro3
classifier/generator/combined=80/100/160
cost_cap_usd=0.20
```

Report key presence only. Do not use DB, Docker, remote deployment or citizen question history.

- [ ] **Step 5: Execute one actual run**

Run the command above once. Required evidence: 20 selected, skip 0, each provider response strict,
catalog-valid topic/coverage where required, deterministic/policy/privacy outbound 0, actual
outbound count equal to the fixture expectation and total cost below USD 0.20. Do not force a
provider call for a deterministic case. If any criterion fails, record FAIL and do not rerun
without a new human instruction.

- [ ] **Step 6: Restore local provider modes**

After the run, stop the process and restore both modes to false unless the human is immediately
starting an explicit foreground demo. Verify tracked files contain no key or local `.env`.

- [ ] **Step 7: Commit actual evidence**

```powershell
git add scripts/run_hybrid_rag_actual.py `
  scripts/tests/test_run_hybrid_rag_actual.py `
  docs/runbooks/UPSTAGE-HYBRID-RAG-ACTUAL.md `
  docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md `
  docs/implementation-notes docs/implementation-notes/INDEX.md
git commit -m "test(llm): record bounded hybrid rag actual"
```

---

### Task 11: Final repository verification, review and Draft PR

**Files:**
- Modify only defects proven by focused RED/GREEN tests
- Modify: final implementation note
- Modify: `CHANGELOG.md`
- Modify: `TASKS.md`
- Modify: `versions/manifest.json`
- Modify: `docs/implementation-notes/INDEX.md`

- [x] **Step 1: Run final repository gate once**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
```

If the aggregate wrapper reports a known harness-only failure, run and record every constituent
gate; do not label the wrapper PASS.

- [x] **Step 2: Run final browser matrix**

```powershell
corepack.cmd pnpm --dir tools/web-e2e test -- `
  --config=playwright.config.ts `
  e2e/home-chat-shell.spec.ts `
  e2e/admin-core-loop.spec.ts
```

Expected: citizen region/followup/suggestion and unchanged local admin core loop pass at
390px, 430px and desktop.

- [x] **Step 3: Run security, privacy and protected-diff checks**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
apps/api/.venv/Scripts/python.exe -B scripts/check_repository_docs.py
apps/api/.venv/Scripts/python.exe -B scripts/validate_codex_package.py
git diff origin/main -- data/official supabase/migrations database/rollbacks
git diff --check
```

Expected: secret/real-PII findings 0; official `.2`, migration and rollback diff 0.

- [x] **Step 4: Perform independent code review**

Use `superpowers:requesting-code-review`. Review typed boundaries, provider-zero policy paths,
request-local snapshot counts, invalid-topic failure, persistence deltas, source authority, Web
storage 0, cost pre-reservation and test realism. Fix only verified findings through a focused
RED/GREEN cycle.

- [x] **Step 5: Complete final implementation note**

Record:

- actual/offline counts and cost;
- current DB/data/public status;
- human-visible behavioral changes;
- no new dependency/migration/public field;
- exact rollback commits and provider-off switches;
- any bounded non-pass or manual Pending item.

- [x] **Step 6: Commit closeout**

```powershell
git add CHANGELOG.md TASKS.md versions/manifest.json docs
git commit -m "docs(chat): close bounded hybrid rag delivery"
```

- [x] **Step 7: Push and create Draft PR**

```powershell
git push -u origin codex/CHAT-HYBRID-RAG-001
```

Create a Draft PR to `main` with source SHA, spec/plan, user-visible changes, offline/actual
results, cost, security/DB/data boundaries and rollback. Do not merge it.

---

## Plan Self-Review

### 1. Specification coverage

- ACTIVE/OFFICIAL topic catalog and metadata: Task 1
- closed `topic_id+coverage_id` selector: Task 2
- exact/unique/semantic/context typed grounding: Task 3
- request-local snapshot, top-1 response and storage: Task 4
- generic move/certificate/waste/tax and context transitions: Task 5
- always-visible region and certificate related questions: Task 6
- 80/100/160 and USD 0.20 pre-reservation: Task 7
- 48 offline, official 57, classifier 60: Task 8
- area/version/governance gate: Task 9
- PII-free actual 20-case subset: Task 10
- final API/Web/DB/root/security/Draft PR: Task 11

Coverage gaps: none.

### 2. Placeholder scan

The plan contains exact files, type names, enum values, fixture counts, commands, expected outcomes
and commit boundaries. Ellipses in Python protocol bodies are type-stub syntax, not missing work.

### 3. Type and authority consistency

- `TopicCatalog` is built only from `KnowledgeRecord` plus non-factual metadata.
- `ClassifierDecision` and `GroundingEvidence` use the same topic and coverage IDs.
- `NO_TOPIC_MATCH` maps only to `INSUFFICIENT_GROUNDING`; scope/non-civic/policy remain separate.
- context v2 gains enum values only and no free text.
- public `followup_options` stays `string[]`; no API field or DB schema change occurs.
- selected sources and offices are server-owned and never provider-generated.
- historical provider profiles remain distinct from the local interactive profile.
- official `.2`, current migrations and current ACTIVE DB are not mutated by this implementation.

## Execution Status and Remaining Handoff

Explicit plan approval was received and `superpowers:subagent-driven-development` was used for
Tasks 1~11. The primary agent retained shared contracts, catalog types, `service.py`, provider budget
integration, versions and integration commits; independent agents implemented or reviewed bounded
non-overlapping slices. Task 10's reviewed PII-free actual subset was run exactly once and recorded
FAIL without rerun. Task 11 recorded browser 27/27, API 2,357 pass·8 local-DB skip, contracts 96/96,
Mypy 114 and zero secret/bundle/protected findings. The one final aggregate wrapper stopped at
FORMAT-API and is not PASS; after formatting, every constituent that the wrapper had not run passed
independently. Branch `codex/CHAT-HYBRID-RAG-001` was pushed and Draft PR
[#20](https://github.com/tskwak111/Sejong_AI/pull/20) was created. Human review/merge is pending;
no automatic merge is allowed.
