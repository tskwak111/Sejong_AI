# IMP-20260727-022 — 제한형 Hybrid RAG 방향 확정

- Date/Time (KST): 2026-07-27T14:40:35+09:00
- Task ID: Q-RAG-001
- Type: decision
- Status: Decision-only / Done
- Author/Agent: Codex
- Branch: codex/LOCAL-RUN-GUIDE-001
- Base commit: 940d1df
- Related plan/ADR/RFP: D-096, A-064, ADR-0025,
  `IMP-20260727-021-실측-대화-검색-분류-후속질문-격차-진단.md`

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 `Q-RAG-001: A`로 제한형 Hybrid RAG 방향을 확정했다.

### Acceptance Criteria

- 선택을 결정 로그와 모호성 레지스터에 기록한다.
- ACTIVE/OFFICIAL-only, PII 선행, server-owned source를 유지한다.
- 아직 결정하지 않은 UX·provider cap·exact grounding을 확정했다고 과장하지 않는다.
- 제품 코드·DB·공식 데이터·provider actual call은 변경하지 않는다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자/PM이 A 결정, Codex가 결정 문서화 |
| When — 언제 | 2026-07-27 KST |
| Where — 어디서 | decision log, ambiguity register, discovery note, implementation note |
| What — 무엇을 | lexical-only 검색을 제한형 Hybrid RAG로 개선하는 아키텍처 방향 |
| Why — 왜 | 자연어 intent가 맞아도 올바른 ACTIVE KB에 도달하지 못하는 UAT 결함 해결 |
| How — 어떻게 | allowlisted ACTIVE/OFFICIAL topic 제안 + server validation·grounding |
| How much — 어느 정도 | 결정 문서 4개, 제품 코드/DB/data/provider 호출 0 |

## 3. 시작 전 상태

- 관련 파일: `docs/decisions/DECISION_LOG.md`, `docs/11_AMBIGUITY_REGISTER.md`,
  IMP-021, IMP-022, INDEX
- 기존 동작: classifier는 intent를 제안하지만 prompt가 `topic_id=null`을 강제하고 실제 KB 선택은
  lexical overlap만 사용한다.
- 발견한 충돌/부채: ADR-0025의 server authority는 유지되지만 open paraphrase에서 retrieval
  recall이 낮다.
- Git 상태: main `940d1df`; 문서는 격리 branch `codex/LOCAL-RUN-GUIDE-001`에 작성했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-RAG-001 | A/Blocker | 자연어 검색 방식 | A / 제한형 Hybrid RAG | prompt·topic selection·grounding·tests |
| Q-UX-REGION-001 | B/High | 지역 선택 표시·유지 | Pending | Web/context/E2E |
| Q-UX-CERT-001 | B/High | 증명서 FOLLOWUP 계층 | Pending | followup options/contract/Web |
| Q-COST-001 | A/Blocker | 긴 UAT session provider cap UX | Pending | 비용·운영·fallback |

## 5. 설계 결정과 대안

### 선택

서버가 제공한 ACTIVE/OFFICIAL allowlisted topic catalog 안에서만 bounded classifier가
`topic_id`를 제안하고, 서버가 intent·status·data class·grounding을 다시 검증한다.

### 이유

- 현재 20개 KB 규모에 충분하다.
- 새 dependency·embedding·migration 없이 자연어 recall을 개선할 수 있다.
- 모델이 출처·저장·candidate·승인 권한을 갖지 않는다.

### 고려했지만 선택하지 않은 대안

- synonym table만 확장: 새 표현에서 반복 실패한다.
- vector/embedding RAG: 현재 규모에는 비용·운영 복잡도가 과하다.
- 자유 생성: 공식 근거 원칙을 위반한다.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| Decision log | D-096 추가 | 인간 아키텍처 방향 기록 |
| Ambiguity register | A-064 Resolved 추가 | blocker 해소 |
| IMP-021 | Q-RAG 상태 갱신 | 진단과 결정 정합성 |
| IMP-022/INDEX | 요청별 결정 노트·색인 | 저장소 규칙 준수 |

### 데이터 흐름/상태 변화

현재는 문서 결정만 기록했다. future 설계 목표는 PII redaction→policy gate→allowlisted topic
proposal→server validation→ACTIVE retrieval/grounding→generated/template→server source다.

### 오류·빈 상태·롤백

exact classifier failure/cap UX는 아직 Pending이다. 문서 롤백은 D-096/A-064/IMP-021 갱신과
IMP-022/INDEX 행을 되돌리는 것이다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.9
- application: 0.11.1-classifier-runtime
- web: 0.7.0-natural-dialogue
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.3.1-hybrid-classifier
- test_suite: 1.9.2-classifier-runtime
- documentation: 2.25.1

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.11.1-classifier-runtime | 동일 | 코드 변경 없음 |
| Web | 0.7.0-natural-dialogue | 동일 | 코드 변경 없음 |
| API | 4.0.0-draft | 동일 | 공개 계약 변경 없음 |
| DB schema | 0.5.0-local | 동일 | migration 없음 |
| Official data | 0.1.0-initial.2 + local 20th | 동일 | data write 없음 |
| Mock data | 0.0.0-not-populated | 동일 | mock 없음 |
| Prompt set | 0.3.1-hybrid-classifier | 동일 | 상세 설계 전 prompt 변경 없음 |
| Test suite | 1.9.2-classifier-runtime | 동일 | 코드 테스트 대상 없음 |
| Docs | 2.25.1 | 동일 | 결정 노트 범위, manifest bump 없음 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| recent git/decision/ambiguity 조사 | PASS | read-only | terminal |
| `python -B scripts/check_repository_docs.py` | PASS, `repository documentation check passed` | 1 | terminal |
| `git diff --check` | PASS | 1 | terminal |

### 미실행 검증과 이유

제품 코드·provider·DB는 변경하지 않아 API/Web/DB 전체 테스트와 actual 호출은 실행하지 않는다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: raw 질문·transcript 저장과 새 외부 전송 0. future에도 redaction 선행 유지.
- Security: allowlisted topic과 server validation을 비협상 경계로 기록했다.
- Accessibility: 현 결정만으로 UI 변경 없음. 지역/FOLLOWUP 설계에서 별도 검토한다.
- Performance/cost: 호출 횟수 증가는 승인하지 않았다. catalog prompt 크기·cap은 후속 설계 대상이다.

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 0.
- mock/AI 생성: 0.
- schema/lineage: 변경 0.
- verified date: 기존 record 값 유지.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 제한형 Hybrid RAG 방향은 확정됐지만 exact catalog·grounding·UX·cap은 아직 미결정이다.
- vector DB·embedding·새 production dependency·DB migration은 이번 방향에서 제외한다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- 내부 helper/module 분리는 후속 계획에서 현재 계약 안에서 자율 결정할 수 있다.

## 13. 인수인계·재현·롤백

### 재현

IMP-021의 19개 record/9개 질문 단계별 재현을 먼저 확인하고 D-096/A-064를 읽는다.

### 롤백

문서 변경만 역순으로 되돌린다. DB/data/provider rollback은 필요 없다.

### 다음 개발자 시작점

Q-UX-REGION-001부터 한 번에 하나씩 확정하고 통합 written specification을 작성한다.
## 14. 남은 위험·미해결 질문·다음 단계

- Q-UX-REGION-001, Q-UX-CERT-001, Q-COST-001.
- catalog size/field allowlist와 topic-aware grounding acceptance.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 변경 없음
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
