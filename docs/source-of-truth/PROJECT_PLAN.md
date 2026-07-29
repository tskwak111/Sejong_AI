# 세종 민원이음 전체 프로젝트 계획서

> **최종 제품**: 시민용 민원 AI 플랫폼 + 관리자용 AI 민원 운영센터  
> **프로젝트 기간**: 2026-07-06 ~ 2026-07-31  
> **책임 역할**: PM·Frontend·Backend·AI/Data 4개; 현재 실제 개발 협업은 사용자 owner + Frontend 팀원 1명
> **문서 버전**: v2.5.0
> **팀명·팀원·연락처·제출일**: 제출 전 직접 입력

## 1. 프로젝트 정의

> 세종 민원이음은 시민의 일상어 질문을 공식 행정 지식과 연결하고, 근거가 있는 질문은 출처와 함께 끝까지 안내하며, 근거가 부족한 질문은 개인정보를 제거한 뒤 사람이 검수·승인할 수 있는 KB 개선 후보로 전환하는 운영형 공공 AI 플랫폼이다.

### 핵심 원칙

> **모르면 지어내지 않고, 알면 끝까지 안내한다.**

### 최종 차별화

```text
시민 질문
→ 공식 KB 검색
→ 답변 또는 안전 폴백
→ 실패 질문 비식별 저장
→ 운영자 사유 확인
→ KB 후보 작성
→ 승인자 승인·반려
→ ACTIVE KB 반영
→ 동일 질문 재질의 개선
```

![대표 개선 흐름](assets/representative_flow.png)

## 2. 확정 범위

### 2.1 지원 분야

| 분야 | MVP 역할 | 대표 질문 |
| --- | --- | --- |
| 전입·주민등록 | 대표 사용자의 이사 시나리오 | 이사했는데 전입신고 어떻게 해요? |
| 증명서 발급 | 절차·수수료·기관 카드 | 등본은 어디서 발급해요? |
| 대형폐기물 | 개선 전후 회귀 시나리오 | 침대 프레임 수수료가 얼마예요? |
| 지방세 일반 안내 | 개인 조회 폴백 시연 | 내 자동차세 체납액 알려줘 |

### 2.2 우선순위 정의

| 등급 | 의미 | 이번 프로젝트 |
| --- | --- | --- |
| P0 | 대표 흐름과 인수 기준에 직접 연결 | 반드시 구현 |
| P1 | 핵심 흐름을 보조하는 확정 기능·검증 | 반드시 구현 |
| P2 | 외부 연계·고도화가 필요한 기능 | 로드맵, 미구현 |

### 2.3 실제 페이지

```text
/
- 서비스 소개·지원 분야·진입

/chat
- 질문·답변 카드·출처·후속질문·폴백
- 지역 선택·공식 기관 카드
- 쉬운 말·큰 글씨

/admin
- 실패 질문 탭
- KB 후보·승인 탭
- 품질 현황 탭
- 상세·작성·승인 모달
- 데모용 역할 전환
```

![대표 화면 와이어프레임](assets/wireframes.png)

## 3. P0 구현 목록

| ID | 기능 | 완료 기준 | 담당 |
| --- | --- | --- | --- |
| P0-01 | 자연어 질문·의도 분류 | 4개 분야·범위 밖·모호 질문을 구분 | AI/Data+BE |
| P0-02 | 공식 KB 검색 | ACTIVE KB만 검색하고 사용 source_id 반환 | AI/Data+BE |
| P0-03 | 구조화 답변·출처 | 절차·서류·기간·수수료·기관·출처 카드 | FE+BE |
| P0-04 | 후속질문 | 모호 질문 2개에 선택형 FOLLOWUP | AI/Data+FE |
| P0-05 | 4개 행정-domain 안전 폴백 | 사유·다음 행동·기관 안내·후보 적격성 | AI/Data+BE |
| P0-06 | 개인정보 마스킹 | 외부 LLM 전 마스킹, 원문 DB 미저장 | BE |
| P0-07 | 지역·기관 매칭 | 3개 지역과 공식 기관 데이터 | BE+FE |
| P0-08 | 실패 질문 목록 | masked_question·사유·상태·텍스트 만료일 표시, 만료 후 파기 빈 상태 | FE+BE |
| P0-09 | KB 후보 작성 | 근거 부족 질문만 후보 작성 가능 | FE+BE+AI/Data |
| P0-10 | 승인·반려 | 작성자 본인 승인 차단, 승인 KB 활성화 | BE+PM |
| P0-11 | 재질의 개선 | REG-01 전체 흐름 완주 | 전체 |

## 4. P1 확정 구현·검증

| 기능 | 구현 기준 |
| --- | --- |
| 쉬운 말 | 사전 기반 핵심 행정 용어 전환 |
| 큰 글씨 | 주요 본문 16px→20px, 제목 20px→24px |
| 기본 명도 대비 | 일반 본문 4.5:1 이상, 상태를 색상만으로 표현하지 않음 |
| 키보드 접근성 | 탭 순서·포커스 링·모달 닫기·포커스 복귀 |
| 실패 질문 필터 | 사유·상태·민원 유형 필터 |
| 품질 현황 | 운영 이벤트와 표본 테스트 수치를 배지로 구분 |
| 감사 이력 | 상태·행위·대상 ID·변경 필드명 저장 |
| 응답시간 | 평균·p95·오류율 측정 |
| 100명 스모크 테스트 | 캐시된 검색/고정 응답 경로, 1분, 실서비스 보증 아님 |

## 5. P2 로드맵

- 실제 GPS와 거리 계산
- 지도 API 내장
- 본인 인증과 신청 상태 조회
- 정부24·지자체·내부 행정 시스템 연계
- 다국어·음성·고령자 단계 축소 모드
- 유사 실패 질문 자동 클러스터링
- 급증 민원 탐지와 주간 리포트
- 전체 KB CRUD·버전 비교
- 다기관 SaaS·SSO·RBAC·전자결재

![5에서 10까지의 로드맵](assets/roadmap.png)

## 6. 데이터 계획

| 데이터 | 확정 수량 | 성격 | 책임 |
| --- | --- | --- | --- |
| 공식 KB | 20건 | 실제·공식 데이터 | AI/Data·Backend 작성, PM 전수 승인 |
| 공식 기관 | 3개 이상 | 실제·공개 데이터 | Backend 작성, PM 전수 승인 |
| 지역×민원 매핑 | 초기 승인 10건, staging 12건 | 팀 규칙 | Backend 작성, PM 전수 검수 |
| 표본 질문 | 20개 | 사람 확정 평가셋 | AI/Data+PM |
| 회귀 테스트 | 1개 | 개선 전후 통합 테스트 | 전체 |
| 실패 질문 mock | 20~30건 | 시연용 샘플 | AI/Data |
| 운영 이벤트 mock | 50~100건 | 시연용 샘플 | BE |
| KB 후보 mock | 5~10건 | 시연용 샘플 | AI/Data |

### 공식 데이터 책임과 완료 목표

| 담당 | 업무 |
| --- | --- |
| AI/Data | 공식 KB 작성, 형식 관리, 표본 질문 초안 |
| Backend | 공식 KB·기관 데이터 작성, 스키마·로그 필드 검증 |
| PM | 공식 KB 20건·기관 3건의 출처·표현·확인일·승인 상태와 staging 지역×민원 매핑 12건을 전수 검수하고, 초기 release 10건을 승인 |
| Frontend | 승인 데이터의 기관 표시·출처 카드 표시 QA; 공식 내용 작성·승인 권한 없음 |

완료 목표는 2026-07-20이다. PM 승인 전 레코드는 staging이며 시민 답변 검색 대상이 아니다.

Q-DATA-002=A에 따라 staging의 canonical 경로는
`data/staging/data-001/<draft-version>/`이며 KB·기관·매핑 JSON과 artifact hash에 묶인 PM
approval manifest를 분리한다. DATA-001은 authoring·validation·approval evidence까지만
소유하며, 승인 record의 immutable official release와 DB seed/import는 DATA-SEED-001에서만
수행한다. Q-DATA-003=A의 PM 최종 확인은 reviewer `PM-LOCAL-001`, confirmation
`2026-07-19T02:06:19+09:00`, current recommendation 35건 전부 채택이다. 초기 release projection은
KB 19건·기관 3건·매핑 10건이고 `KB-WASTE-03`과 거절 매핑 2건은 제외한다. WASTE-03은 개선 전후
회귀에서 별도 승인된 뒤 최종 20번째 ACTIVE가 된다.

Q-SEED-001=A에 따라 initial official version은 `0.1.0-initial.1`이며 immutable filesystem
release와 기존 schema용 empty-local transactional seed를 사용한다. release 준비와 local dispatcher
activation은 별도 복구 가능 단계이고, seed/compensation은 역할 확인과 8개 table exclusive lock,
정확한 semantic projection 검증 아래 disposable local DB에서만 허용한다. 서면 명세는
`2026-07-19T09:20:31+09:00`, 실행계획은 `2026-07-19T09:52:08+09:00` 승인됐다.

Q-SEED-002=A/D-044와 Q-MVP-001=A/D-058에 따라 historical `.1`과 v1 schema byte를 보존하면서
같은 PM 승인 19/3/10을 corrected effective-option union guard·strict v2 schema·new manifest에
묶은 immutable `0.1.0-initial.2`를 게시했다. 독립 기술 검토와 create-once/byte 검증을 통과했고
`supabase/seed.sql`은 `.2`와 byte-identical하며 `[db.seed].enabled=false`다.

초기 4회는 concurrency B에서 중단됐지만 relation observer의 accepted lock mode 교정 뒤 2026-07-22
지원 actual disposable PostgreSQL 17 cycle은 baseline·exact identity·forced rollback
(`tables=8 partial=0`)·concurrency A/B·seed cycle·second-seed/compensation guard·replay·final
projection·cleanup까지 PASS했다. local DB projection은 ACTIVE/OFFICIAL KB 19, OFFICIAL office 3,
approved mapping 10이며 final citizen 19/exclusions 0/operational 0 및 final runtime
process/container 0을 확인했다. immutable `.2`는 변경하지 않았고 `official_data=0.1.0-initial.2`로
승격한다. `/ready=200`과 20번째 ACTIVE는 이 seed 증거와 별개인 실제 application probe/rehearsal이
소유한다. 그 separate final local rehearsal은 `/ready=200`, one NEW failure→different approver→
`KB-WASTE-03` SUCCESS, final ACTIVE 20/four fields×5를 PASS했으며 `.2` artifact는 그대로다.
final API/Web/contracts/E2E/scanner, clean disposable DB와 root `verify.ps1 -Offline`은 PASS했다.
deterministic sample T-01~T-20도 20/20이며 별도 보고서가 수치를 소유한다. local/private AI scope는
PR #9 병합으로 Done이다. 사람이 병합한 Frontend PR #8의 current UI는 owner 후속에서 PERSONAL 미저장→별도
INSUFFICIENT_GROUNDING 저장→사유 확정→승인된 OFFICIAL 후보→작성자와 다른 승인자·checklist
3/3→20번째 ACTIVE→동일 질문 SUCCESS·서버 결합 공식 출처를 actual desktop browser 1/1로
재검증했다. feedback dialog keyboard focus gate와 Web 390/430/desktop fixture 18/18도 통과했다.
`[db.seed].enabled=false`는 유지하고 reset 뒤 immutable `.2`의 정식 seed 단계를 별도로 실행한다.
`allowedDevOrigins: ["127.0.0.1"]`는 team PR #10의 owner-reviewed config 경계를 유지한 별도
owner PR 과제다. owner Draft PR review/merge와 manual demo는 인간 Pending이다.

## 7. 시스템 설계

![시스템 아키텍처](assets/architecture.png)

### 기술 스택

| 영역 | 확정 선택 | 비고 |
| --- | --- | --- |
| Frontend | Next.js + TypeScript + Tailwind CSS, Node 24.x+pnpm | 초기 로컬 실행; Vercel은 공개 배포 승인 후 |
| Backend | FastAPI + Python 3.12+uv | 초기 로컬 실행·백업; Render는 공개 배포 승인 후 |
| DB | Supabase PostgreSQL + Supabase CLI 버전 SQL migration | Docker local stack 우선; 원격 push·파괴 변경은 별도 승인 |
| 검색 | 키워드+메타데이터 기본, 임베딩 보조 | KB 20건에서 예측 가능성 우선 |
| LLM | selectable classifier adapter + Upstage grounded generator | classifier는 local/private에서 disabled/Upstage/DeepSeek exact `deepseek-v4-flash`를 명시 선택하고, 최종 시민 답변 생성은 Upstage exact `solar-pro3`를 유지한다. 합성 evaluator의 max 1024/concurrency 1/retry 1/cap 30과 별도로, 승인된 local/private 시민 경로는 supported+masked+ACTIVE/OFFICIAL+grounded, 8초·1 attempt·server-issued fact ID·전체 template fallback |
| 차트 | Recharts | 기본 KPI만 |
| 테스트 | Pytest, Playwright, k6/Locust, 수동 표본 평가 | 품질·UI·성능 분리 |

### 저장소·협업·변경 통합

- current history는 private `tskwak111/Sejong_AI` monorepo에 연결됐다. initial push SHA는
  `5e09deccc7205503df07d938b6d4a88f4d5a327e`, PR #1 historical merge SHA는
  `ce8a6085fb57670ca74e009ed45e3d02d784c24b`다. 해당 SHA의 post-merge policy and frozen Frontend CI
  hosted runs passed, and `koregy` collaborator write/variable evidence is verified. current remote
  authority는 `git fetch origin` 뒤 `origin/main`으로 동적 확인하며 어떤 local `main`도 같다고 전제하지 않는다.
  private PR #1~#5, Cloud docs-only PR #3, Frontend onboarding PR #4와 제품 PR #8의
  PR-only/manual-merge rehearsal은 완료됐다. teammate MFA/recovery 확인만 human-only Pending이다.
  Q-GIT-004=A/D-053의 author/committer history·SHA 보존은 유지한다. COLLAB-001은 이 human
  recovery gate 때문에 In Progress다.
- GitHub Free·0원으로 시작하므로 private branch protection/CODEOWNERS 강제를 전제하지 않는다.
  PR-only 팀 규칙, 변경 범위 분류, CI와 작은 revert 가능한 PR을 사용한다.
- Frontend 팀원은 `/`, `/chat`, `/admin`, typed client, 모든 화면 상태, 반응형·접근성과 frontend
  unit/E2E를 소유한다. 자가 병합은 `apps/web/src/**`, `tools/web-e2e/e2e/**`, 신규 web 구현 노트
  하나와 INDEX append만 포함한 green PR로 제한한다.
- 공개 계약·backend·DB·migration·official data·privacy/security policy·dependency/lockfile 변경은
  사용자 검토 대상이다. 계약 간극은 frontend 임의 타입이 아니라 Issue와 owner contract PR로
  해결한다.
- Codex Cloud는 `codex/<task-id>-<slug>` branch와 Draft PR까지만 만들고 사용자가 병합한다.
  App installation의 `Only select repositories / Sejong_AI`와 secret-free `sejong-ai-cloud-docs`
  환경 저장은 사용자 확인됐다. Cloud docs-only task/Draft-PR/manual-merge rehearsal은 private
  PR #3으로 완료됐다.
  비밀·외부 LLM 실호출·Docker/Supabase actual 검증은 Cloud에서 금지한다.
- private GitHub source remote는 D-046이 차단하는 remote/public application·DB deployment와
  별개이며 이를 해제하지 않는다.

### 핵심 데이터 저장

```text
interaction_events
- 질문 문장 없음
- intent, answer_status, fallback_reason
- source_count, response_time_ms, selected_region

failed_questions
- masked_question
- fallback_reason, candidate_eligible, text_expires_at, text_purged_at
- 30일 후 masked_question만 NULL; 행·비텍스트 메타데이터·후보 연결 유지

kb_candidates
- 사람 작성 답변·공식 출처·확인일
- created_by, reviewed_by, review_status

kb_documents
- ACTIVE만 시민 검색

audit_logs
- 상태·행위·필드명만 저장
- 질문·답변 전체 스냅샷 미저장
```

## 8. 개인정보·폴백 정책

### 폴백 규칙

| 사유 | KB 후보 | 텍스트 저장 |
| --- | --- | --- |
| INSUFFICIENT_GROUNDING | 가능 | 마스킹 후 30일 |
| PERSONAL_LOOKUP | 불가 | 7/25 local은 질문 text·event·실패 질문 행 미생성 |
| LEGAL_JUDGMENT | 불가 | 7/25 local은 질문 text·event·실패 질문 행 미생성 |
| OUT_OF_SCOPE (공개 응답 공통) | 불가 | 질문 텍스트 저장 금지; NON_CIVIC은 event도 0, 행정 범위 확장은 아래 별도 queue |
| PRIVACY_UNRESOLVED | 불가 | 7/25 local은 질문 텍스트·실패 질문 행·DB event 모두 미생성 |
| FOLLOWUP | 해당 없음 | 실패 질문 목록 미저장 |
| CIVIC_SCOPE_GAP (local/private active) | 기존 KB 후보 불가 | 별도 범위확대 queue의 PII-safe 마스킹 text 30일; 자동 ACTIVE 금지 |
| NON_CIVIC (active) | 불가 | 질문 text·event·실패·검토 row 미저장 |

Q-PM-DEMO-001=B의 local/private 실제 시연에서는 먼저 `PERSONAL_LOOKUP` 전후
`interaction_events`·`failed_questions` count 무변화를 확인하고, 별도의
`INSUFFICIENT_GROUNDING` 질문만 실패 저장·후보·별도 승인·20번째 ACTIVE 개선 루프로 보낸다.
backend runner stdout/stderr/log/report에는 질문·UUID·DSN·secret을 출력하지 않는다. actual
browser는 승인된 비식별 고정 fixture를 현재 탭의 메모리 UI에만 표시하며, 실패 시 local
gitignored trace/screenshot이 남을 수 있으므로 이것을 DB 무저장 증거로 해석하지 않는다.

### 외부 AI

- 외부 LLM 호출 전 백엔드에서 개인정보를 마스킹한다.
- local/private 시민 경로는 마스킹된 현재 질문과 실제 답변에 필요한 최소 ACTIVE/OFFICIAL
  KB, server-issued fact ID와 strict schema만 전달한다.
- 최종 시민 답변 생성 공급자는 Upstage direct API의 exact `solar-pro3`를 유지한다. 질문
  분류 공급자는 Q-LLM-PROVIDER-001=A/D-122/ADR-0028에 따라 local/private에서
  disabled/Upstage/DeepSeek exact `deepseek-v4-flash`를 명시 선택한다. 각 키는 서로 다른
  ignored backend local 환경변수에만 두며 새 충전·자동 충전·잔액 조회를 하지 않는다.
- A-074 offline Tasks 1~6b는 selector/settings, strict DeepSeek transport, provider별
  보수 비용·usage, local composition과 one-shot runner/wrapper를 TDD로 완료했다. Integrated
  pre-gate review의 Important 5와 compressed-decoding Important 1을 두 fix wave로 닫았고
  최종 fresh review는 Critical 0 / Important 0 / Minor 0 `READY`다. Recursive duplicate-key
  rejection, identity/raw `<64 KiB` streaming, complete exchange 3초·aggregate 32초 deadline,
  exact-byte/pre-lease TOCTOU와 post-child source/tree fail-closed가 포함된다. public main과
  final answer provider는 불변이다. D-123의 source
  `9c7f818123533a4adc61d3953ed4d4630c793891` A-074 offline exact-one은 exit 1,
  timed_out false, invocation/rerun 1/0과 `TEST-ROOT` first failure로 immutable `FAIL`이다.
  Standalone 434-test repository-boundary mismatch는 test-only +4 교정 뒤 `434 OK / skipped 2`
  와 corrective review C0/I0/M0로 해소했지만 gate를 소급 변경하지 않는다. DeepSeek actual은
  blocked/unexecuted 0/0이며 report/lease·outbound·token·cost는 0이다.
- D-124/D-125의 별도 A-075 identity는 source `982198f...` offline gate와 readiness를
  PASS한 뒤 actual을 정확히 한 번 실행했다. Fixed 20/0·11/9와 policy/privacy outbound0은
  충족했지만 outbound9 모두 HTTP 응답 전 `transport_no_response`여서 provider response,
  2xx, parse, accepted, oracle match와 observed token은 0이고 acceptance는 `FAIL`이다.
  Retention/retry/rerun은 0이며 보수적 worst-case 비용 USD0.02306304는 cap0.20 미만이다.
  A-074 증거는 불변이고 DeepSeek runtime 성공·public/remote/free-input 승인으로 보지 않는다.
- D-126/D-127의 A-076은 value-free DNS·TCP443·TLS/HTTP probe PASS 뒤 source `c9fc1be...`
  offline/readiness를 PASS하고 actual을 한 번 실행했다. 그러나 outbound9 모두 다시 HTTP 응답 전
  `transport_no_response`, response/2xx/parse/accepted/match/token0으로 FAIL했다. 28.6초가
  9×3초 complete-exchange timeout과 거의 일치하므로 timeout 만료가 가장 강한 가설이지만
  exception detail 비보관 경계상 확정하지 않는다. Timeout 변경과 추가 actual은 새 승인 전
  금지하고 A-074/A-075/A-076 증거를 모두 보존한다.
- D-128의 A-077은 이 timeout 가설만 최소 변경으로 검증한다. connect/write/pool3초와
  read/complete10초를 분리하고, clean source offline/readiness 뒤 one-call HTTP 2xx probe가
  PASS한 경우에만 별도 9-call actual을 실행한다. Retry0·무보관·USD0.20·exact parser와
  이전 evidence 불변을 유지하며 public/API/DB/data/Web/final-answer provider는 바꾸지 않는다.
- D-129의 A-078은 A-077 offline PASS 1/0 뒤 provider 실행 전 발견된 evidence-chain 결함만
  보강한다. Exact probe lease+bounded report+same-source acceptance를 clean-source revalidation
  뒤 actual lease 직전에 재검사하고 callback 뒤 final source/input 재검증, probe 응답 뒤
  재검증도 강제한다. D-128의 probe 1-call과 조건부 actual run 1회(정확히 9 provider calls)
  한도를 공유한다.
- D-130/D-131의 A-078 probe는 transport-no-response1로 FAIL해 actual을 차단했다. Binary-open
  lease correction 뒤 별도 A-079 clean source에서 offline/readiness/probe 1-call을 재시도하고
  2xx일 때만 9-call actual run 1회를 실행한다. 모든 이전 evidence는 불변이다.
- 합성 evaluator의 historical 경계와 별도로, Q-LLM-006~012/D-072 시민 경로는 서버가
  supported intent·안전한 마스킹·ACTIVE/OFFICIAL retrieval·grounding을 모두 확인한 SUCCESS
  후보에만 호출을 허용한다. 클라이언트 flag/intent/source/KB ID/mode는 신뢰하지 않는다.
- D-073에서 written specification, D-074에서 8-task TDD 실행계획과 Subagent-Driven 구현을
  승인했다. local/private product/API/Web 구현, task-scoped 검토와 provider-disabled 최종 offline
  repository gate를 완료했고, D-075 local actual도 10건 GENERATED 4/TEMPLATE 6, 출처 10/10,
  공식 mismatch 0과 PII-free fixture typed write-boundary 위반 0으로 PASS했다. 이는
  public/remote/실제 기관 운영 승인이 아니다.
- 시민 chat은 8초, logical attempt 1, hidden retry 0, concurrency 1, process outbound attempt
  30 이하를 강제한다. 한도 도달·429·잔액 부족은 자동 충전이나 재시도 없이 template로 전환한다.
- 모델은 summary와 server-issued fact ID만 제안하고 서버가 공식 fact text·source·office를
  결합한다. schema·ID·fact drift 또는 LLM 장애가 하나라도 있으면 모델 결과 전체를 버리고
  구조화 KB template를 반환한다. 근거가 없으면 provider call 0의 안전 폴백이다.
- provider는 기본 disabled이고 합성 mode와 시민 chat mode를 분리한다. public/remote/실제 기관
  운영은 별도 개인정보·보안·비용·배포 승인 전까지 provider 호출을 금지한다.
- DeepSeek는 `sejong_ai_api.local.create_local_app`와 `127.0.0.1` local runner에만 구성한다.
  exact five-string/uppercase `NONE`을 shared server parser가 재검증하며 `json_object`를
  schema 신뢰 경계로 보지 않는다. DeepSeek actual은 fixed synthetic 20, 3초·retry0·
  concurrency1·max output128·temperature0/thinking disabled·USD0.20 cap의 one-shot이다.

### 마스킹·대화·오류 경계

- 이름·상세주소는 재현율 우선으로 보수적으로 가린다. 답변 성공률 80% 미달의 원인이 과잉 마스킹으로 입증돼도 정밀도 우선으로 자동 전환하지 않고 인간 재승인을 받는다.
- 초기 마스킹 코어는 표준 라이브러리 기반 결정론적 typed rule engine과 원문 값 없는 고정 토큰을 사용한다. 정규화·탐지 후에도 안전한 마스킹 문자열을 만들 수 없으면 텍스트를 반환하지 않고 실패 질문 row·provider 호출을 금지하며 질문 없는 interaction event만 허용한다.
- 안전한 마스킹 문자열을 만들 수 없는 시민 요청은 HTTP 200 `PRIVACY_UNRESOLVED`로 개인정보를 빼거나 표현을 바꿔 다시 질문하도록 안내한다. source/context/office, provider 호출, 질문 text, 실패 질문 행·DB event·후보는 만들지 않는다. Q-MVP-001로 local/private route와 API 3.1.0-draft consumer는 활성화했지만, public route와 persistent metadata migration은 reserved `00700` 단계의 별도 승인 전까지 비활성이다.
- 시민 질문에 들어온 phone-shaped value는 사용자가 “공식 대표번호”라고 적어도 모두 마스킹한다. 공식 연락처는 입력에서 보존하지 않고 승인된 KB·기관 메타데이터를 서버가 결합한 기관 카드에서만 제공한다.
- 마스킹 성공은 저장·provider 호출의 필요조건일 뿐 충분조건이 아니다. local/private에서는
  supported intent·ACTIVE/OFFICIAL·grounding까지 통과해야 하며 public/remote/실제 기관 운영의
  시민 질문은 별도 승인 전 Upstage 또는 다른 외부 LLM에 전송하지 않는다.
- Q-CLASS-001=A의 local/private hybrid classifier는 PII/policy deterministic gate 뒤
  ambiguous current question만 closed enum 분류에 사용한다. D-095의 PII-free frozen 60 actual은
  완료됐고 current local interactive 상한은 D-099/D-104의 classifier 80, generator 100,
  combined 160, VAT 포함 USD 0.20이다. Task 10의 새 PII-free 20-case selector actual은
  정확히 한 번 실행했으나 strict accepted usage/provider match 0으로 FAIL해 재실행 금지 상태다.
  Q-LLM-013=A/D-107의 명시적 JSON 지시 교정 actual은 9/9 HTTP 2xx와 usage accepted로 4xx를
  해소했지만 strict closed decision accepted/match 0이라 overall FAIL이다. 재시도는 0이고
  current runtime은 provider 응답 거부 시 안전한 결정론 fallback을 유지한다.
- 화면상 대화 기록과 15분 서명형 `context_token`은 현재 브라우저 탭 메모리에만 둔다. 서버 세션·raw 대화문·token을 DB/로그에 저장하지 않고 새로고침·탭 종료 시 화면 기록을 없앤다.
- token에는 서버 정의 enum/ID와 발급·만료 시각만 허용하며 질문·답변·PII·URL·공식 사실을 넣지 않는다. 만료·위변조 token은 문맥 없는 새 요청으로 처리하고 인증·권한·ACTIVE KB·근거 판단에 사용하지 않는다.
- 정책 폴백은 HTTP 200이다. provider/DB 장애라도 ACTIVE KB·검증 snapshot으로 안전 응답이 가능하면 200이고, 안전 대체가 없을 때만 HTTP 503 `SERVICE_UNAVAILABLE`을 반환한다.

## 9. 팀 역할

| 역할 | 최종 책임 | 3주차 핵심 |
| --- | --- | --- |
| PM·제안서·QA·KB 승인자 | 범위·문서·정책·승인·발표 | 승인 체크리스트·테스트 판정 |
| Frontend 팀원 | `/`, `/chat`, `/admin` 전체 frontend 수직 흐름·typed API client·모든 화면 상태·반응형·접근성·unit/E2E | 탭·모달·카드 통합, 계약 간극 Issue, 허용 frontend-only PR 자가 병합 |
| Backend | API·DB·마스킹·상태·배포 | 승인 권한·이벤트·성능 |
| AI/Data·민원 운영자 | KB·검색·폴백·평가 | 공식 KB 10건+후보 작성 |

사용자는 Backend·DB·공개 계약·공식 데이터·보안·배포 결정과 Codex Cloud PR의 최종 merge를
책임진다. Frontend 팀원은 구현자이며 공식 데이터 승인자나 PM reviewer가 아니다.

## 10. 주차별 실행계획

### 2주차: 7/13~7/17

| 날짜 | PM | FE | BE | AI/Data | 완료 게이트 |
| --- | --- | --- | --- | --- | --- |
| 7/13 | 최종 범위·제안서 구조 | 3페이지 와이어프레임 | DB/API 확정 | 4개 분야·폴백 확정 | 범위 동결 |
| 7/14 | 문제·시장·수익모델 | 홈·채팅 기본 UI | chat mock·이벤트 구조 | 공식 KB 5건 | 정상 답변 데모 |
| 7/15 | 개인정보·승인 정책 | 답변·출처·폴백 카드 | 마스킹·실패 로그 | KB 10건·표본 초안 | 폴백 저장 데모 |
| 7/16 | 로드맵·예산·RFP 표 | 지역·기관 카드 | 기관 API·사유 코드 | 기관 데이터·매핑 | 기관 안내 데모 |
| 7/17 | 제안서 v2 제출본 | 시민 흐름 통합 | Chat·로그 통합 | KB 15건·질문 20개 | 제안서·중간 시연 |

### 3주차: 7/20~7/24

| 날짜 | PM | FE | BE | AI/Data | 완료 게이트 |
| --- | --- | --- | --- | --- | --- |
| 7/20 | 관리자 검수 시나리오 | 실패 질문 탭 | 목록·상세 API | KB 20건 완료 | 실패 목록 동작 |
| 7/21 | 승인 체크리스트 | 상세·후보 모달 | 사유 정정·후보 API | 후보 샘플 | 후보 작성 동작 |
| 7/22 | 역할·권한 검수 | 역할 전환·승인 모달 | 권한 차단·감사 이력 | 후보 출처 검토 | 승인 동작 |
| 7/23 | 테스트 기준 | 품질 현황 탭 | 품질·성능 API | 표본 테스트 1차 | KPI 표시 |
| 7/24 | 중간 리허설 | 모바일 통합 | 회귀·로컬 백업 | 실패 분석 | P0/P1 통합 완료 |

### Q-MVP-001 가속 마일스톤: 7/22~7/25

기존 주차표의 최종 범위는 유지하되 현재 저장소의 실제 선후관계에 맞춰 local/private 핵심 루프를
아래 순서로 재배치한다. 상세 task/명령/담당 경계는 승인된
`docs/superpowers/plans/2026-07-22-four-day-local-private-core-loop-mvp.md`가 소유한다.

| 날짜 | Owner/BE·Data·Security | Frontend 팀원 | PM·QA | 일일 완료 gate |
|---|---|---|---|---|
| 7/22 | 통합 회귀 복구, DATA-SEED-002 `.2` | PR #4 `012→014`, `/chat` fixture states | 명세·표시 문구 확인 | staging/release green, `.2` reviewable |
| 7/23 | actual 19 ACTIVE, PII/chat 계약·pure core | `/chat` fixture 완료·typed client 준비 | 19 official/계약 확인 | DATA actual와 chat core green |
| 7/24 | chat API, event/admin API, 20번째 후보 backend | 실제 `/chat`, 최소 `/admin` | author/reviewer rehearsal | PASS: candidate approval atomic local E2E |
| 7/25 | 전체 회귀·보안·데모 | 390/430/desktop 접근성 수정 | 표본 20·회귀 1 판정 | AI closeout PASS: final ACTIVE 20·sample 20/20·root green; human manual review Pending |

7월 25일 gate에는 외부 LLM 품질 평가, 100명 부하, 자동 백업, public deployment, 고급 UI를
포함하지 않는다. 이 항목은 4주차 P1에 남으며, 개인정보·ACTIVE·승인·출처·접근성 최소선은
마일스톤에서도 필수다.

### 4주차: 7/27~7/31

| 날짜 | PM | FE | BE | AI/Data | 완료 게이트 |
| --- | --- | --- | --- | --- | --- |
| 7/27 | 발표자료 초안 | UI 버그 수정 | 오류 처리 | 표본 테스트 2차 | 기능 동결 |
| 7/28 | 제안서·계획서 정합 | 접근성·모바일 | 로그·보관·부하 | 품질 수치 확정 | 문서·지표 일치 |
| 7/29 | 발표자료 완성 | 화면 polish | 배포·로컬 백업 | 테스트 리포트 | 최종 데모 |
| 7/30 | 리허설 2회 | 데모 지원 | 장애 대응 | 예상 질문 | 발표 게이트 |
| 7/31 | 최종 발표 | 데모 | 데모 | QA | 제출 완료 |

## 11. 테스트·성공 기준

| 지표 | 목표 | 판정 |
| --- | --- | --- |
| 답변 성공률 | 80% 이상 | 정상 10개 중 8개 이상 |
| 출처 표기율 | 100% | 직접 답변에 출처 누락 0건 |
| 적절한 폴백률 | 87.5% 이상 | 폴백 8개 중 7개 이상 |
| 후속질문 성공률 | 100% | 모호 질문 2개 모두 FOLLOWUP |
| 개인정보 마스킹률 | 100% | DB·로그 원문 0건 |
| 승인 없는 KB 노출 | 0건 | DRAFT/PENDING 검색 결과 0건 |
| 회귀 흐름 | 1회 완주 | 승인 전 폴백→승인 후 답변 |
| 응답시간 | 평균 3초 목표 | 평균·p95·오류율 공개 |
| 100명 스모크 | 오류율 1% 미만 목표 | 캐시 경로 1분, 용량 보증 아님 |

마스킹 완화 검토는 같은 20문항 평가셋에서 답변 성공률 80% 미달과 과잉 마스킹의 인과를 함께 기록한 경우에만 시작한다. 개인정보 마스킹률 100% 기준은 완화하지 않는다.

PERF-001은 2026-07-26 실행계획에서 두 단계로 분리한다. Phase A는 provider-disabled
loopback-only `/health`와 official office read에 100 virtual users·60초를 적용해 harness와
aggregate-only 결과를 검증하며 DB write는 0이다. Phase B는 cached/fixed chat 경로를 대상으로
하지만 interaction/idempotency metadata를 만들 수 있어 A-052에서 disposable clean DB 또는
current non-KPI local DB bounded write를 인간이 선택하기 전까지 실행하지 않는다. 두 단계 모두
오류율 1% 미만과 평균 3초 이하를 pass 기준으로 사용하고 p95는 측정·공개하되 별도 threshold를
임의로 만들지 않는다. 이 결과는 실서비스 용량 보증이 아니다.

## 12. 데모 시나리오

1. `이사했는데 전입신고 어떻게 해요?` → 공식 KB 답변·출처
2. `신고하고 싶어요.` → 선택형 후속질문
3. `내 자동차세 체납액 알려줘.` → PERSONAL_LOOKUP 폴백
4. 지역 `아름동` 선택 → 공식 기관 카드
5. `침대 2인용 프레임 수수료가 얼마예요?` → 승인 전 근거 부족
6. 관리자 운영자 역할로 후보 작성
7. 승인자 역할로 공식 출처 검수·승인
8. 동일 질문 재질의 → 10,000원·출처 카드
9. 품질 현황에서 운영 이벤트·표본 테스트·시연용 샘플 배지 구분

## 13. 리스크 통제

| 리스크 | 통제 |
| --- | --- |
| 기능 범위 증가 | 3페이지·4개 분야·단일 승인 루프 동결 |
| FE 부담 | 탭·카드·모달·공통 컴포넌트 재사용 |
| KB 품질 부족 | 20건만 전원 분담, 출처대장 전수 검수 |
| 개인정보 외부 전송 | 외부 LLM 호출 전 마스킹 |
| 승인 없는 배포 | ACTIVE 필터와 작성자 본인 승인 차단 |
| mock 수치 오해 | 이벤트 집계·MVP 표본·시연용 샘플 배지 |
| 데모 장애 | 고정 KB·템플릿 답변·로컬 백업·녹화 |
| 제안서와 MVP 불일치 | RFP 대응표와 인수 기준을 개발 백로그에 연결 |
| GitHub Free의 약한 merge 강제 | direct `main` push 금지 팀 규칙, scope CI, 작은 PR, green evidence와 revert runbook |
| Frontend 자가 병합 범위 초과 | contract/backend/DB/data/security/dependency deny 경계와 owner-review 승격 |
| GitHub App·collaborator 권한 과다 | private repository, selected-repository-only Codex 권한, 최소 collaborator와 revoke 절차 |
| Cloud가 local 검증을 대체 | Docker/Supabase/Upstage actual은 `local-verification-required`로 유지 |

## 14. 최종 완료 기준

- [ ] `/`, `/chat`, `/admin`이 모바일·데스크톱에서 동작
- [ ] 공식 KB 20건과 출처대장 완성
- [ ] 공식 기관 데이터 3개 이상
- [ ] 4개 폴백과 FOLLOWUP 구분
- [ ] 외부 LLM 전 마스킹
- [ ] 성공 이벤트와 실패 로그 정책 구현
- [ ] 운영자·승인자 역할 분리
- [ ] 회귀 테스트 REG-01 완주
- [ ] 표본 질문 20개 결과 기록
- [ ] 평균·p95·오류율과 100명 스모크 결과 기록
- [ ] 제안서·계획서·발표자료·MVP 범위 일치
