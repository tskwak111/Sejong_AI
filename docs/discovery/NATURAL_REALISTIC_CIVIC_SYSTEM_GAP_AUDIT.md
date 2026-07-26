# 자연스러운 대화·현실형 민원 시스템 격차 감사

- Task: `CHAT-REALISTIC-USABILITY-AUDIT-001`
- Date: 2026-07-27 KST
- Status: Discovery complete / product target decision pending
- Branch/Base: `codex/ACTUAL-P0-UX-GAPS-001` / `13632cb`
- Safety: 시민 질문 원문, 비밀, DSN, provider call, DB read/write 없음

## 1. 결론

현재 시스템은 **local/private에서 실행 가능한 공식 KB 기반 민원 안내 MVP**다. 네 분야의
ACTIVE KB 검색, 서버 결합 출처, 안전 폴백, 기관 카드, 실패 질문과 별도 승인 루프는 실제
구조로 존재한다. 반면 “자연스러운 챗봇”과 “현실에서 운영 가능한 서비스” 사이에는 서로 다른
두 종류의 격차가 있다.

1. **대화 품질 격차:** 개인정보 오탐, 작은 용어표 중심 분류, 얕은 구조화 문맥, 제한된 KB
   때문에 정상 한국어가 막히거나 확인 질문이 반복된다.
2. **운영 준비 격차:** 실제 인증, 일반 후보 작성, 범위 확대 검토, 데이터 갱신 운영,
   rate limit·백업·공개 배포가 아직 local MVP 경계 밖이다.

LLM을 더 넓게 붙이는 것만으로 두 격차가 해결되지는 않는다. 권고 순서는 **개인정보 오탐
교정 → hybrid route 분류 → 구조화 대화 문맥 → KB/검색 품질 → 운영 workflow → public
hardening**이다.

## 2. 현재 구현에서 이미 되는 것

| 영역 | 확인된 현재 상태 | 근거 |
|---|---|---|
| 시민 답변 | PII-safe supported 질문을 ACTIVE/OFFICIAL KB에 연결하고 출처를 서버가 결합 | `chat/service.py`, `retrieval.py`, `response.py`, ADR-0023 |
| 생성형 답변 | local/private에서 grounded 조건을 모두 통과한 경우만 Upstage를 사용하고 전체 검증 실패 시 공식 template | `llm/upstage_chat.py`, `llm/prompt.py`, D-075 |
| 개인정보 | 원문 DB 미저장, provider 전 마스킹, 안전한 문자열을 만들 수 없으면 fail closed | `privacy/redaction.py`, ADR-0004 |
| 짧은 문맥 | 15분 서명 token에 마지막 intent·지역·응답 상태·서버 option ID만 저장 | `chat/context.py`, ADR-0010 |
| 공식 데이터 | 승인된 immutable `.2`, 초기 19 ACTIVE 뒤 별도 승인으로 20번째 ACTIVE | DATA-SEED lineage, MVP-001 |
| 관리자 loop | 실패 사유 확인, 후보 작성·제출, 다른 승인자의 승인/반려, ACTIVE 전환 capability | `admin/service.py`, DB migration/pgTAP |
| 기관 안내 | OFFICIAL office 3개와 mapping 10개를 직접 지역 선택과 intent로 조회 가능 | OFFICE-API-001 |
| 로컬 신뢰성 | `/ready=200`, API/Web/DB 계약·테스트와 local demo 증거 | DEMO-001, 관련 test report |

이 표는 공개 운영, 실제 민원 신청·조회, production 인증 또는 기관 연계를 의미하지 않는다.

## 3. 자연스러운 대화를 막는 격차

| ID | 우선도 | 확인된 격차 | 시민에게 보이는 영향 | 권고 |
|---|---|---|---|---|
| N-01 | P0 | 일반 한국어를 사람 이름으로 보는 PII contextual-name 오탐 | 민원/비민원 분류 전에 개인정보 재질문으로 막힘 | fail-closed 유지, negative corpus와 문맥 규칙을 TDD로 교정 |
| N-02 | P0 | 네 intent 용어표와 고정 OOS term만 있는 결정론적 분류 | 새 표현, 비민원, 범위 밖 행정 민원이 UNKNOWN/FOLLOWUP으로 섞임 | Q-CLASS-001/002의 bounded hybrid classifier와 closed route 구현 |
| N-03 | P0 | generic 증명서 질문이 분야 4개를 다시 묻는 기존 FOLLOWUP | 이미 증명서라고 말했는데 같은 수준의 질문을 반복 | 승인된 증명서 5개 category FOLLOWUP 계획 통합 |
| N-04 | P0 | context v1이 마지막 intent·지역 중심이며 topic/요청 slot을 보존하지 않음 | “그럼 비용은?”, “온라인도 돼?” 같은 생략형 후속 질문이 불안정 | raw history 없이 server-issued topic·pending slot·dialog act를 담는 context v2 설계 |
| N-05 | P0 | 키워드·metadata 검색, embedding off, 공식 KB 20건 | 표현 다양성과 복합 질문의 recall이 낮음 | 먼저 synonym/query rewrite·구조화 field retrieval, 측정 후에만 embedding 재결정 |
| N-06 | P1 | 만족/불만족 UI가 탭 메모리에서 끝나고 API가 없음 | 실제 품질 개선 지표로 연결되지 않음 | 원문 없이 request 결과 ID+닫힌 reason code만 받는 feedback 계약 검토 |
| N-07 | P1 | 시민 최초 지역 선택 진입점이 화면에 없음 | 기관 endpoint가 있어도 기관 카드 도달성이 낮음 | `/chat` 상단 직접 읍·면·동 선택과 변경 동선 구현 |
| N-08 | P1 | 새 대화/주제 전환이 명시적 control로 드러나지 않음 | token 만료나 주제 변경 때 문맥을 예측하기 어려움 | “새 대화”, “이전 주제 계속”, token 만료 안내를 명시 |

### 권고 대화 문맥

원문 transcript나 사용자 사실을 저장하는 장기 memory는 권고하지 않는다. 대신 15분 서명
token을 다음과 같은 **닫힌 서버 식별자**로 확장하면 자연스러움과 개인정보 원칙을 함께
지킬 수 있다.

- `topic_id`: 서버가 선택한 현재 ACTIVE KB 주제 또는 승인된 분야 식별자
- `dialog_act`: `ANSWERED | ASKING_SLOT | CHANGING_REGION | CHANGING_TOPIC`
- `pending_slot`: `CERTIFICATE_KIND | REGION | ITEM_KIND` 같은 허용 enum
- `selected_region`, `last_intent`, `answer_status`

LLM에는 안전하게 마스킹한 **현재 질문**과 최소 구조화 context만 전달한다. 과거 질문·답변
문장, 출처 URL, 시민 프로필은 전달하거나 저장하지 않는다. retrieval과 source는 계속 서버가
결정한다.

## 4. 현실 사용성을 막는 격차

| ID | 우선도 | 확인된 격차 | 현재 위험/한계 | 현실형 안내·운영 서비스에 필요한 것 |
|---|---|---|---|---|
| R-01 | P0 | 지원 범위가 네 분야·KB 20건·기관 3곳 | 실제 시민 질문 대부분을 포괄하지 못함 | scope-gap 수요를 안전하게 계측하고 PM이 범위 확장 순서를 결정 |
| R-02 | P0 | `CIVIC_SCOPE_GAP` 정책만 있고 DB/API/admin queue 미구현 | 현재 범위 밖 행정 민원을 체계적으로 검토할 수 없음 | 별도 migration·rollback·pgTAP·API·admin queue |
| R-03 | P0 | Web actual 후보 초안이 WASTE-03 데모에 고정 | 다른 eligible 실패 질문을 운영자가 후보로 만들기 어려움 | 일반 구조화 작성 폼, source allowlist 검증, 상태 이력 연결 |
| R-04 | P1 | demo header 역할 전환이며 실제 인증이 아님 | 공개 `/admin`에서 신원·권한을 신뢰할 수 없음 | 공개 전 IdP/auth, server session, CSRF/CORS, deny-by-default role 정책 |
| R-05 | P1 | `last_verified_at`은 있으나 만료 기준·재검수 queue가 없음 | 오래된 수수료·절차가 ACTIVE로 남을 수 있음 | 분야별 freshness SLA, stale 표시/검색 제외 정책, 재승인 workflow |
| R-06 | P1 | local stack에 production TLS/rate limit/admin protection 없음 | 남용·비용 폭주·관리자 노출에 취약 | ingress rate limit, per-route quota, admin protection, abuse test |
| R-07 | P1 | 공개 운영 로그·경보·장애 지표가 확정되지 않음 | 원문을 남기지 않으면서 장애를 탐지할 운영 체계가 부족 | metadata-only metrics, reason/latency/provider-mode counters, alert/runbook |
| R-08 | P1 | local RPO/RTO 기본값은 있으나 production backup restore 증거 없음 | 실제 장애에서 복구 시간을 보장할 수 없음 | 암호화 backup, restore rehearsal, 삭제 전파, production RPO/RTO 승인 |
| R-09 | P1 | 100 VU read-only만 준비되고 chat write 부하는 보류 | 실제 동시 사용 시 DB/event/idempotency 병목을 모름 | disposable clean DB의 bounded write smoke와 p95/error 기준 |
| R-10 | P1 | 자동 접근성 테스트 외 인간 검수가 Pending | 고령층·키보드·확대 사용성 근거가 불완전 | 200% zoom, keyboard, screen reader, 실제 모바일 수동 체크 |
| R-11 | P2 | 신청·결제·상태조회·정부24/내부망 연계 없음 | 현재는 “처리”가 아니라 “안내” | 기관 계약/API, 본인인증, 동의, transaction/audit/취소/보상 설계 |

## 5. 선택 가능한 제품 접근

### A. 현실형 민원 안내 + 운영센터 고도화 — 권고

공식 안내, 자연스러운 후속 대화, 기관 연결, scope-gap 수집, 사람 승인과 운영 안전성을
완성한다. 현재 구조를 살릴 수 있고 local/private MVP에서 단계적으로 검증 가능하다.
실제 신청·상태조회는 하지 않는다는 한계는 화면과 제안서에서 정직하게 표시한다.

### B. 실제 민원 신청·상태조회 플랫폼으로 확대

시민이 서비스 안에서 본인인증, 신청, 첨부, 결제, 처리상태 확인까지 한다. 사용자 가치는
크지만 기관별 API/계약, 법무·개인정보 영향평가, 인증·권한, transaction·감사·보상,
production 배포가 필요하다. 현재 MVP의 작은 개선이 아니라 별도 사업/아키텍처다.

### C. LLM-first 광범위 답변으로 빠르게 범위 확대

KB가 없는 분야도 모델이 답하게 한다. 겉보기 범위는 넓지만 공식 근거·최신성·책임 경계를
잃어 핵심 원칙과 충돌한다. 채택하지 않는다.

## 6. 권고 개발 순서

### Slice 1 — 대화 안전성과 분류 정확도

1. PII 오탐 negative corpus와 결정론적 교정
2. hybrid closed-route classifier contract와 provider adapter
3. `NON_CIVIC`, `CIVIC_SCOPE_GAP`, `NEEDS_FOLLOWUP`, supported route별 문구
4. 증명서 category FOLLOWUP 통합
5. fixture matrix, provider-disabled/timeout/schema-invalid/cost cap test

### Slice 2 — 구조화된 자연스러운 후속 대화

1. context v2 설계·계약·만료/위조/주제 전환 테스트
2. topic·pending slot 기반 짧은 후속 질문
3. 새 대화·주제 변경·지역 선택 UI
4. raw transcript/PII/provider payload 부재 보안 gate

### Slice 3 — 실제 운영 개선 루프

1. 별도 `CIVIC_SCOPE_GAP` DB/API/admin queue
2. arbitrary eligible IG failure용 일반 후보 작성
3. 대기/승인/반려 이력과 정확한 운영 문구
4. text-free feedback reason 수집과 품질 회귀 연결

### Slice 4 — public-ready 운영 기반

제품 목표가 A로 확정된 뒤에도 실제 공개 전 별도 승인으로 인증, rate limit, source freshness,
metadata-only observability, backup/restore, write load, 접근성 수동 검수, CORS·비밀·리전·비용을
완료한다.

### Slice 5 — 실제 처리

제품 목표가 B일 때만 별도 discovery/ADR로 시작한다. 현 계획에 신청·상태조회·결제 코드를
섞지 않는다.

## 7. 완료 기준 제안

자연스러운 local/private 안내 MVP의 다음 acceptance baseline은 다음과 같다.

- fixture matrix에서 privacy false positive 0, route 기대값 전부 일치
- NON_CIVIC text/event/review row 0
- CIVIC_SCOPE_GAP은 PII-safe masked text만 별도 30일 queue에 1행
- supported 질문은 ACTIVE/OFFICIAL retrieval과 서버 결합 source 유지
- 최소 5개 생략형 후속 질문이 context v2로 올바른 topic을 유지
- provider disabled, timeout, invalid JSON에서 공식 template/fallback 100%
- classifier 1 + generator 1/request, process combined cap 40, run cost USD 0.05 이내
- 시민 원문·과거 transcript·비밀·provider raw body 저장 0

## 8. 사람 결정과 AI 내부 세부

### 사람이 반드시 결정할 것

- 안내·운영 플랫폼(A)과 실제 신청·상태조회 플랫폼(B) 중 제품 목표
- 공개 운영 시 인증/IdP, 개인정보·보관, provider, 비용, 배포와 기관 연계
- DB migration, 공개 계약, 데이터 범위 확대와 freshness 기준

### AI가 같은 계약 안에서 처리할 수 있는 것

- PII negative fixture, closed enum validator, helper 분리
- context token의 canonical encoding/validation
- deterministic fallback·timeout·invalid-schema 테스트
- UI 문구 정합성, 키보드 접근성, 내부 명명과 중복 제거

## 9. 미해결

`Q-PROD-REAL-001`이 A면 Slice 1을 첫 단일 written specification으로 작성한다. B면 현재
Slice 1은 계속 유효하지만, 실제 처리 플랫폼은 인증·기관 API·법무·transaction을 먼저
별도 discovery 해야 한다.
