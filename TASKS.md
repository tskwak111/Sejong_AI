# TASKS.md — 현재 백로그

> 이 문서는 우선순위와 의존성을 보여주는 작업 인덱스다. 실제 작업을 시작하면 실행계획과 구현 노트를 연결한다.

## Phase 0 — 발견·결정·정리

| ID | 우선순위 | 담당 영역 | 작업 | 상태 | 의존성 | 완료 기준 |
|---|---|---|---|---|---|---|
| DISC-001 | P0 | Architecture·Security·Data·Docs | [저장소 감사와 최종 기준 드리프트 보고서](docs/discovery/INITIAL_DISCOVERY_REPORT.md) | Done | 없음 | 코드/문서/데이터/계약 충돌표와 [IMP-20260714-001](docs/implementation-notes/IMP-20260714-001-초기-저장소-발견-감사.md) 작성 |
| DISC-002 | P0 | Architecture·Product·Security | 아키텍처 영향 인터뷰 | Done | DISC-001 | batch 1~3 기록, 인간 결정형 A/Blocker 0 |
| DOC-001 | P0 | Architecture·Docs | 결정 로그·ADR·모호성·계약·DB draft 동기화 | Done | DISC-002 | D-009~024, ADR-0002~0010, OpenAPI 2.0.1-draft와 source-of-truth 정합성 검사 통과 |
| PLAN-001 | P0 | Architecture·전체 | [local-first 기반과 승인형 민원 안내 실행계획](docs/plans/PLAN-20260714-001-foundation-and-governed-chat.md) | Done | DISC-002, DOC-001 | 2026-07-15 사용자 `진행` 승인; 공개/실제 시민 경계는 별도 승인 유지 |
| COLLAB-001 | P0 | Platform·Security·Docs·Frontend | [private GitHub·Codex Cloud 협업 전환](docs/superpowers/specs/2026-07-20-github-codex-cloud-collaboration-design.md) | In Progress — Tasks 1~4 complete; Task 5 partial; Task 6 complete; Task 7 ready for human merge | D-047~D-058/ADR-0019/0020, approved [execution plan](docs/superpowers/plans/2026-07-20-github-codex-cloud-collaboration-transition.md), [owner checklist](docs/handoffs/HANDOFF-20260721-OWNER-GITHUB-CLOUD-CHECKLIST.md) | PR #5 merged at `9044ddb`. PR #4 was corrected to note `014`, head `37dfc8b`, exact note+INDEX two-file diff, CLEAN/MERGEABLE and hosted summaries green; Frontend collaborator/user merge pending. MFA/recovery yes/no도 Pending이며 public deployment/remote DB는 계속 차단한다 |
| MVP-001 | P0 | 전체 | [7/25 local/private 핵심 개선 루프](docs/superpowers/specs/2026-07-22-four-day-local-private-core-loop-mvp-design.md) | Review — local/private AI scope complete; human review/manual gates pending | Q-MVP-001=A/D-058/ADR-0020, Q-PM-DEMO-001=B/D-068, [approved plan](docs/superpowers/plans/2026-07-22-four-day-local-private-core-loop-mvp.md), [sample report](docs/test-reports/MVP-001-SAMPLE-20-RESULT.md) | actual PERSONAL interaction-event/failed-row delta 0/0, 별도 INSUFFICIENT_GROUNDING delta 1/1, same-writer block, PM approval, final ACTIVE 20·target 1·requery source `KB-WASTE-03`·ready200와 actual desktop browser 1/1 PASS. sample 20/20와 기존 API/Web/contracts/DB/root closeout 유지. manual demo/a11y와 owner PR은 인간 Pending; public admin auth/remote/provider-ready 아님 |

## Phase 1 — 프로젝트 스캐폴딩

| ID | 우선순위 | 담당 영역 | 작업 | 상태 | 의존성 | 완료 기준 |
|---|---|---|---|---|---|---|
| DEV-001 | P0 | Platform·FE·BE | 독립 Git·Node 24/pnpm·Python 3.12/uv 모노레포와 health | Done | PLAN-001 Approved | corrected fresh default·warm-offline 24/24와 actual API/Web smoke, final P0/P1/P2 0; DB·승인 seed 전 `/ready=503` 유지 |
| DEV-002 | P0 | Platform·Security | 환경변수·비밀관리·local 수동 검증 gate | Done | DEV-001 | 예제 환경, 비밀 스캔, raw body logging off, synthetic/offline env 복원과 clean gate 통과 |
| DB-001 | P0 | Backend·Data·Security | [Supabase SQL v1 migration·보상 rollback·권한](docs/discovery/DB_001_DISCOVERY_REPORT.md) | Done | DEV-001 Done, approved DB spec/plan, D-026~D-032, ADR-0012/0013/0014, verified local baseline; D-046/ADR-0018 public hardening decision | disposable local/private `0.4.0-local` only. exact loopback, 9 pgTAP files/356·rollback absence/reapply 36/36 and `.2` 19/3/10 actual seed PASS. final local `/ready=200` is separately PASS; public `00700` remains blocked |
| CONTRACT-001 | P0 | FE·BE·QA | OpenAPI 3.1·공유 타입 생성 경로와 chat/admin/200/503/context/idempotency 계약 | Done | DEV-001, D-045/D-058 | API 3.1.0-draft, shared 0.4.0, discriminated ChatResponse·PRIVACY_UNRESOLVED·optional UUID Idempotency-Key·strict admin/error/HTTPS fixture와 generated TypeScript/Pydantic drift 0; 89/89 PASS |

### Phase 1 실행 상세 — PLAN-20260715-002

| ID | 우선순위 | 담당 영역 | 작업 | 상태 | 의존성 | 완료 기준 |
|---|---|---|---|---|---|---|
| DEV-001A | P0 | Platform | exact runtime과 root workspace contract | Done | PLAN-001 | Node/pnpm/Python/uv exact pin, config RED→GREEN, remote 0 |
| DEV-001B | P0 | Backend·Platform | FastAPI health와 pre-DB readiness | Done | DEV-001A | `/health=200`, `/ready=503` exact, uv lock, ruff/mypy/pytest |
| DEV-001C | P0 | Frontend·Platform | 최소 접근 가능 Next.js shell | Done | DEV-001A | frozen pnpm install, lint/typecheck/unit/build, 390/430px QA, [IMP-20260715-005](docs/implementation-notes/IMP-20260715-005-접근-가능한-next-js-애플리케이션-shell.md) |
| DEV-002A | P0 | Security·Platform | 서비스별 env·metadata-only log·secret/browser scan | Done | DEV-001B, DEV-001C | raw body/sentinel/browser secret 0, [IMP-20260715-006](docs/implementation-notes/IMP-20260715-006-서비스별-환경변수와-안전-로그-경계.md) |
| CONTRACT-001A | P0 | FE·BE·QA | 승인 계약 불변조건과 공통 fixtures | Done | DEV-001B, DEV-001C | SUCCESS source≥1·office/context/503 양 계약 fixture 정합, [IMP-20260715-007](docs/implementation-notes/IMP-20260715-007-승인-계약-불변조건과-공통-fixture.md) |
| CONTRACT-001B | P0 | FE·BE·QA | 생성 TS·Pydantic model drift gate | Done | CONTRACT-001A | 재생성 diff 0, 동일 fixture 통과, [IMP-20260715-008](docs/implementation-notes/IMP-20260715-008-생성-typescript와-pydantic-계약-drift-gate.md) |
| DEV-001D | P0 | Platform·QA·Docs | clean local verify와 Phase 1 마감 | Done | DEV-002A, CONTRACT-001B | corrected snapshot default·warm-offline 24/24, actual API/Web smoke와 final read-only review 완료 |
| DEV-002B | P0 | Platform·Security·QA | fail-fast local verification과 환경 복원 경계 | Done | DEV-002A, CONTRACT-001B | 24단계 gate, child exit 보존, 성공/실패 출력 비노출, synthetic/offline env 복원과 fresh review 통과 |

## Phase 2 — 시민 질문 수직 흐름

| ID | 우선순위 | 담당 영역 | 작업 | 상태 | 의존성 | 완료 기준 |
|---|---|---|---|---|---|---|
| DATA-001 | P0 | AI/Data·Backend 작성, PM 승인 | 공식 KB 20건·기관 3건·지역×민원 매핑 12건 staging 작성·전수 검수 | Done | [DATA plan](docs/superpowers/plans/2026-07-18-data-001-staging-and-review-package.md), D-033/D-035, ADR-0015 | PM-LOCAL-001의 35건 승인 evidence와 exact 19/3/10 projection materialize·63-test/canonical/hash review PASS; official release/seed/DB 변화 0, [IMP-20260719-004](docs/implementation-notes/IMP-20260719-004-data-001-pm-승인-증거-확정.md) |
| DATA-SEED-001 | P0 | Backend·Data·Security | 승인 record의 initial immutable official release·버전 seed·lineage | Blocked | DATA-001 approved manifest, D-036/D-038/D-039 | `.1` filesystem 19/3/10 release·dispatcher·offline gate PASS, actual DB는 legacy single-row guard에서 write 전 차단된 historical execution. `.1` 불변 보존하고 D-044의 DATA-SEED-002가 교정 소유. [lineage](docs/data-lineage/DATA-SEED-001-0.1.0-initial.1.md), [report](docs/test-reports/DATA-SEED-001-LOCAL-VERIFICATION.md) |
| DATA-SEED-002 | P0 | Backend·Data·Security | [immutable `.2` successor와 actual DB 재검증](docs/superpowers/specs/2026-07-20-data-seed-002-successor-release-correction-design.md) | Done — local/private actual seed PASS | D-044/D-058/ADR-0017/0020, approved DATA-001 19/3/10, [approved execution plan](docs/superpowers/plans/2026-07-20-data-seed-002-successor-release-correction.md), [lineage](docs/data-lineage/DATA-SEED-002-0.1.0-initial.2.md), [report](docs/test-reports/DATA-SEED-002-LOCAL-VERIFICATION.md) | `.1`/v1 불변, `.2` exact identity, forced rollback 8/0, concurrency A/B, 19/3/10 seed, replay·second seed/compensation guard, final 19/0/0 and cleanup process/container 0 PASS; official_data 0.1.0-initial.2 |
| READY-001 | P0 | Backend·Data·Platform | 실제 DB·필수 승인 seed readiness probe 전환 | Done — local/private actual | DATA-SEED-002 actual PASS, DEV-001B | DB 연결과 필수 ACTIVE KB/기관 seed가 모두 준비된 final local DB에서 dedicated Windows `/ready=200` PASS; 결손/장애와 import-safe 기본 앱은 503, public/remote는 범위 밖 |
| AI-001A | P0 | Backend·Security | [순수 fail-closed PII 마스킹 코어](docs/superpowers/specs/2026-07-20-ai-001-pii-masking-design.md)와 frozen v1 합성 평가셋 | Done | D-041/D-042/D-043, approved written spec, A-032 Resolved, [approved execution plan](docs/superpowers/plans/2026-07-20-ai-001a-pii-masking-core.md), [IMP-006](docs/implementation-notes/IMP-20260720-006-ai-001a-pii-마스킹-코어-구현.md) | privacy 1,161·architecture+privacy 1,165+5 subtests·full API 1,318+8 DB skips+5 subtests PASS. 13범주·5 reason, frozen 74 불변, actual 77 원문 유출 0·safe 219 오탐 0, raw/log/I/O/dependency 0, API/DB/data/provider/route 불변 |
| PII-CONSUMER-001 | P0 | Backend·Frontend 팀원·Security·Contract | `PRIVACY_UNRESOLVED` HTTP 200 consumer 계약 | Done for local/private | D-045/D-058/ADR-0004/0020 | source/context/office/provider/text/failed row/event/candidate 0, 고정 시민 copy, OpenAPI/JSON Schema/Pydantic/TS 동시 변경; persistent metadata는 reserved `00700` 뒤 별도 |
| AI-001 | P0 | AI/Data·Backend·Security | 보수적 PII 마스킹과 분류·검색·근거 gate·template 응답 | Review — local/private deterministic scope complete | DATA-SEED-002, AI-001A, PII-CONSUMER-001, Q-MVP-002 | raw sentinel, ACTIVE/OFFICIAL retrieval, actual 19→20와 [sample 20/20](docs/test-reports/MVP-001-SAMPLE-20-RESULT.md) PASS. 실제 시민 external provider와 public/remote는 deferred |
| LLM-002 | P1 | AI/Data·Backend·Security·PM | [Upstage Solar Pro 3 합성 평가와 장애 fallback](docs/superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md) / [승인 실행계획](docs/superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md) | In Progress — offline Tasks 1~6 complete/review clean | AI-001, Q-LLM-005=A/D-065~D-067/ADR-0022 | fail-closed settings, strict source-free JSON/prompt/cost, bounded HTTPX, canonical grounded evaluator, content-free trace/report, readiness-first runner와 offline security/architecture gate 완료. full API 1,782+8 DB skips+5 subtests, 독립 review clean; key/network/public chat/remote DB 0. Task 7 actual local human gate와 실제 시민 option B는 별도 |
| API-CHAT-001 | P0 | Backend·QA | `/api/v1/chat`·signed context와 공통 오류 계약 | Done — local/private | CONTRACT-001, AI-001 | final DB `/ready=200`, atomic retry/requery, full 1,640 PASS·8 DB-only skip·5 subtests, Ruff/Mypy 64와 root offline PASS; public route는 별도 승인 |
| WEB-HOME-001 | P0 | Frontend 팀원·QA | `/` 서비스 소개·4개 지원 분야·한계·`/chat` 진입 | Done | DEV-001 complete; Q-WEB-001=A/D-037; [execution plan](docs/superpowers/plans/2026-07-19-web-home-and-static-chat-shell.md) | 정적 `/chat`·home CTA, 입력/저장/외부 요청 0, 390/430/desktop·키보드·focus·contrast·실제 Chrome UI 200%·prod dependency gate PASS, [IMP-20260719-005](docs/implementation-notes/IMP-20260719-005-web-home과-정적-채팅-준비-화면.md) |
| WEB-CHAT-001 | P0 | Frontend 팀원·QA | `/chat` current-tab 대화·카드·출처·폴백·기관 | Review — automated scope complete | API-CHAT-001, WEB-HOME-001 | same-origin typed client와 memory-only 경계, Web 48/48 및 390/430/desktop E2E 15/15 PASS; human manual demo/a11y Pending |

## Phase 3 — 관리자 개선 루프

| ID | 우선순위 | 담당 영역 | 작업 | 상태 | 의존성 | 완료 기준 |
|---|---|---|---|---|---|---|
| LOG-001 | P0 | Backend·Security·Data | 비식별 이벤트·실패 질문 저장과 30일 텍스트 파기 | Done — local/private | API-CHAT-001, Q-MVP-002 | clean disposable API DB integration 8/8에서 insert/purge/FK·30-day purge와 policy row-zero PASS; 원문 저장 0, public retention 재승인 필요 |
| ADMIN-001 | P0 | Frontend 팀원·Backend·Security | local/private 실패 질문 확인·사유 정정 | Done — local/private | LOG-001, Q-DB-004 | actual reason confirm/row-zero/30-day purge, admin race correction과 review 0/0/0 PASS; public admin auth는 미구현·금지 |
| ADMIN-002 | P0 | Frontend 팀원·Backend·PM·Security | KB 후보 작성·제출·별도 승인·반려·재작성 | Done — local/private core flow | ADMIN-001, Q-DB-004 | candidate create without client public_id, submit, same-writer block, distinct approval과 exact `KB-WASTE-03` ACTIVE/SUCCESS PASS; public admin은 계속 금지 |
| REG-001 | P0 | 전체·QA | 침대 프레임 개선 전후 회귀 | Done — local/private actual | ADMIN-002 | 승인 전 fallback→승인 후 server-bound official source answer, old idempotency K1 fallback 유지, final ACTIVE 20/four fields×5/target once PASS |

## Phase 4 — P1 품질·배포

| ID | 우선순위 | 담당 영역 | 작업 | 상태 | 의존성 | 완료 기준 |
|---|---|---|---|---|---|---|
| A11Y-001 | P1 | Frontend 팀원·QA | 쉬운 말·큰 글씨·대비·키보드 | Review — automated 390/430/desktop PASS | WEB-CHAT-001 | Playwright 15/15; final human manual contrast/large-text/keyboard/demo checklist Pending |
| QA-001 | P1 | QA·PM·AI/Data | 표본 20개 평가 리포트 | Done — deterministic pure-service | REG-001, Q-MVP-002 | [T-01~T-20 20/20, SUCCESS 10/10, FOLLOWUP 2/2, FALLBACK 8/8](docs/test-reports/MVP-001-SAMPLE-20-RESULT.md); provider/HTTP UI/public QA 아님 |
| PERF-001 | P1 | Backend·QA | 평균/p95·100명 제한 스모크 | Deferred after 2026-07-25 | API-CHAT-001 | Q-MVP-001에서 토요일 뒤로 명시적 연기 |
| ADMIN-QUALITY-001 | P1 | Frontend 팀원·Backend·QA·Security | 품질 카드·최소 감사 이력 | Deferred — advanced UI after MVP closeout | ADMIN-002, QA-001 | EVENT/EVALUATION/MOCK 배지·고급 품질 UI는 후속 P1; public auth 없이 운영 화면으로 사용 금지 |
| DEMO-001 | P1 | PM·Platform·QA | local live→template fallback 데모 리허설 | Review — automated/local evidence complete | REG-001 | provider-off 19→20와 final20 restore PASS; 인간 manual demo·접근성 확인 Pending, 공개 URL·녹화는 별도 승인 |
| BACKUP-001 | P1 | Platform·Backend·Security | local RPO/RTO·dump 보관·restore/purge drill | Deferred after 2026-07-25 | LOG-001 | 자동 백업은 Q-MVP-001에서 연기; 실제 데이터 전 수동 recovery 경계 유지 |
| DEPLOY-001 | P1 | Platform·Security·PM | 조건부 Vercel/Render/Supabase 공개 demo | Blocked | DEV-002, D-046의 deferred `00700` 구현·검증, 별도 공개 배포 승인 | privileged function/public port hardening 뒤 계정·리전·CORS·비밀·로그·비용·admin gate 승인 시에만 URL/health/rollback |
| HANDOFF-001 | P1 | 전체·Docs | local-first 인수인계·운영 런북 | Blocked | ADMIN-QUALITY-001, DEMO-001, BACKUP-001 | 신규 개발자 clean local 재현·backup/restore 성공; 단일 PC 위험과 public 배포 선택 조건 분리 |

## P2 — 명시적 범위 변경 전 백로그 미생성

GPS·지도·상태조회·내부 시스템 연계·다국어·음성·고급 분석·전체 KB CRUD·SSO/RBAC/전자결재는 로드맵에만 남기며 구현 TASK를 만들지 않는다.

## 변경 규칙

- 상태: `Ready`, `In Progress`, `Blocked`, `Review`, `Done`, `Dropped`.
- 작업을 시작할 때 실행계획/구현 노트 링크를 추가한다.
- P2는 사용자의 명시적 범위 변경 전 TASKS에 구현 작업으로 추가하지 않는다.
