# 팀 결정사항 요약

## 제품

- 서비스명: 세종 민원이음
- 구조: 시민용 민원 AI 플랫폼 + 관리자용 AI 민원 운영센터
- 기준 문장: **모르면 지어내지 않고, 알면 끝까지 안내한다.**
- 차별점: 실패 질문을 공식 KB 후보로 전환하고 담당자가 승인하는 개선 루프
- 현재 실제 개발 협업: 사용자 owner 1명 + Frontend 팀원 1명. PM·Frontend·Backend·AI/Data는
  책임 역할 구분이며 Backend·DB·계약·데이터·보안의 최종 책임은 사용자가 가진다.

## 구현 범위

- 실제 페이지: `/`, `/chat`, `/admin`
- 지원 분야: 전입·주민등록, 증명서 발급, 대형폐기물, 지방세 일반 안내
- P0: 질문·분류·공식 KB 답변·출처·후속질문·4개 행정-domain 폴백+privacy 안전 재질문·지역 선택·기관 카드·관리자 승인 루프
- P1: 쉬운 말, 큰 글씨, 기본 명도 대비 4.5:1 이상, 실패 질문 필터, KPI, 품질 카드, 감사 이력, 성능 스모크 테스트
- P2: 실제 GPS·지도 내장·상태조회·정부24/내부망 연계·다국어·음성·고급 분석·전체 KB CRUD

## 데이터

- 공식 KB 20건: 4개 분야 × 5건
- 공식 기관 3개: 아름동, 도담동, 조치원읍 중심
- 공식 KB·기관 데이터 작성: AI/Data·Backend
- 공식 KB·기관 데이터 승인: PM 전수 검수
- 공식 데이터 완료 목표: 2026-07-20
- 승인 전 canonical authoring: `data/staging/data-001/<draft-version>/`의 KB·기관·매핑 JSON 3종
- PM 승인 증거: artifact SHA-256·count·레코드별 결정·comment를 가진 별도 approval manifest
- 승인 record 승격: DATA-SEED-001에서만 immutable `data/official/releases/<data-version>/` 생성
- PM 최종 승인 증거: reviewer `PM-LOCAL-001`, confirmation
  `2026-07-19T02:06:19+09:00`, 35개 current recommendation 전부 채택
- 초기 release projection: ACTIVE KB 19건·기관 3건·매핑 10건;
  `KB-WASTE-03`과 거절 매핑 2건은 제외하고, WASTE-03은 회귀 뒤 최종 20번째 ACTIVE
- DATA-SEED architecture: initial version `0.1.0-initial.1`의 immutable filesystem release와
  기존 schema용 empty-local transactional seed. written specification은
  `2026-07-19T09:20:31+09:00`, 실행계획은 `2026-07-19T09:52:08+09:00` 승인됐다.
- DATA-SEED actual status: historical `.1`을 보존한 채 같은 승인 19/3/10 projection의 immutable
  `0.1.0-initial.2` successor와 strict v2 schema가 게시·독립 검토·byte 검증됐고,
  `supabase/seed.sql`은 `.2` seed와 byte-identical이며 `[db.seed].enabled=false`다. 초기 4회
  concurrency B failure 뒤 observer accepted-lock-mode 교정을 집중 검증했고, 2026-07-22 지원 actual
  cycle은 baseline·identity·forced rollback·concurrency A/B·seed·compensation/replay·final projection과
  cleanup까지 PASS했다. PostgreSQL local projection은 ACTIVE/OFFICIAL KB 19·OFFICIAL office 3·approved
  mapping 10이고 final citizen 19/exclusions 0/operational 0, process/container 0이다.
  `official_data=0.1.0-initial.2`로 승격한다. 이 seed 증거 자체는 `/ready=200`, 20번째 ACTIVE 또는
  public/remote 운영을 뜻하지 않으며 `.1`·`.2`·v1 불변은 유지한다. 별도 final local application
  rehearsal은 `/ready=200`, governed `KB-WASTE-03` 19→20 flow와 final four fields×5를 PASS했지만,
  public/remote/external-provider/deployment 증거는 여전히 없다.
- 표본 질문 20개 + 개선 전후 회귀 테스트 1개
- 실패 질문 mock 20~30건, 운영 이벤트 mock 50~100건, KB 후보 mock 5~10건
- 시민 기관 정보는 공식 데이터만 사용
- 관리자 mock 데이터에는 `시연용 샘플` 배지 표시

## 폴백

- INSUFFICIENT_GROUNDING: 후보 가능
- PERSONAL_LOOKUP: 후보 불가
- LEGAL_JUDGMENT: 후보 불가
- OUT_OF_SCOPE: 후보 불가, 질문 텍스트 저장 금지
- PRIVACY_UNRESOLVED: 안전한 마스킹 text 생성 불능 전용 HTTP 200 재질문; 후보·질문 text·실패 행·provider 호출 없음
- 2026-07-25 local/private MVP의 PERSONAL_LOOKUP·LEGAL_JUDGMENT: 공개 `intent=UNKNOWN`+정확한 reason, 후보 불가, 질문 text·event·실패 행 저장 없음
- 모호 질문: FOLLOWUP, 실패 질문이 아님

## 개인정보

- 외부 LLM 호출 전 백엔드에서 마스킹
- 사용자 원문 DB 미저장
- 성공 질문 텍스트 미저장, 이벤트 메타데이터만 저장
- 실패 질문의 `masked_question` 텍스트만 생성 후 30일 보관하고 만료 시 NULL 파기
- 실패 질문 행·비텍스트 메타데이터·KB 후보 연결은 텍스트 파기 후에도 유지
- 애플리케이션 DB에서 IP·기기 ID 미수집
- 30일은 MVP 내부 운영 기준
- 이름·상세주소는 재현율 우선 보수적 마스킹; 답변 성공률 저하가 입증돼도 정밀도 우선 전환은 인간 재승인 후
- 초기 runtime 마스커는 표준 라이브러리 기반 결정론적 typed rule engine으로 구현한다. 원문 값 없는 고정 토큰만 반환하고 안전한 결과를 만들 수 없으면 텍스트 저장·실패 질문 row·provider 호출을 금지하며 metadata-only event만 허용한다.
- 시민 입력이 번호를 “공식 대표번호”라고 표시해도 그 label은 신뢰하지 않고 모든 phone-shaped value를 마스킹한다. 공식 기관 연락처는 승인된 KB·기관 메타데이터를 서버가 결합한 카드에서만 제공한다.
- 안전한 마스킹 text를 만들 수 없으면 HTTP 200 `PRIVACY_UNRESOLVED`로 개인정보를 빼거나 표현을 바꿔 다시 질문하도록 안내한다. 질문 text·source/context/office·provider·실패 질문 행·후보는 0이다. Q-MVP-001은 public response enum 동결을 승인했고, 7/25 local milestone에서는 DB event를 만들지 않는다. persistent metadata DB migration은 reserved public `00700` 이후 별도 승인·실행한다.
- 마스킹 성공은 저장·합성 fixture provider 호출의 필요조건일 뿐 충분조건이 아니며 실제 시민 질문의 외부 LLM 전송 금지는 유지한다.
- Q-LLM-005=A: 외부 합성 평가 공급자는 Upstage exact `solar-pro3`다. local/private의 서버
  검증 canonical `T-01`~`T-10`만 최대 30 outbound attempt로 평가하며 실제 시민·PII·민감정보·
  자유 입력·공개 운영은 금지한다. D-066/D-067로 written specification과 실행계획이 승인돼
  offline 구현·리뷰를 완료했고 D-071의 local actual은 strict-schema 27/30으로 FAIL했다.
  인간 검토 9개 평균 4.8444·최저 4와 비용 cap은 통과했지만 option B는 승인되지 않았다.
  provider-disabled/template 시민 경로와 실제 시민 외부 전송 금지를 유지한다.
- 화면 transcript와 대화 token은 현재 탭 메모리에만 유지; 서버 세션·raw transcript·token 영속 저장 금지

## 기술

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI + Python
- 개발 기준: Node 24.x+pnpm, Python 3.12+uv
- DB/Search: Supabase PostgreSQL + Supabase CLI 버전 SQL migration + 키워드·메타데이터 검색; MVP embedding off
- LLM: Upstage direct API, exact `solar-pro3`, local/private canonical 합성 fixture 전용,
  max output 1024, concurrency 1, retry 최대 1회, run당 outbound attempt 총 30회;
  provider adapter와 disabled/template fallback 필수. 실제 구현·actual call은 승인된 명세와
  후속 실행계획 뒤에만 수행한다.
- 초기 실행: local-first, 외부 인프라 예산 0원
- 현재 웹 기준선: 사람이 병합한 Frontend PR #8과 owner 통합 commit `c15f61b`부터 local/private
  `/chat`과 `/admin`은 typed actual transport가 기본이고 fixture는 명시적 개발·테스트 mode에서만
  사용한다. public 관리자·remote DB·공개 배포 승인은 여전히 없으며 서버 gate 없이 활성화하지 않는다.
  PR #8의 `/admin/*` 하위 경로는 local/private 관리자 view이며 공개 제품 페이지 범위 확장으로
  해석하지 않는다. `/`, `/chat`, `/admin`의 공개 3페이지 범위는 그대로다. 하위 경로를 영구
  구조로 유지할지는 `WEB-ROUTE-SCOPE-001`의 인간 범위 검토 전까지 Pending이다.
- local Web 개발 origin: `allowedDevOrigins: ["127.0.0.1"]`는 owner-reviewed config
  PR에서만 반영한다. Frontend 팀원 PR #10은 Web CI를 통과했지만 config 소유 경계 때문에 owner가
  인계하며, 이는 public CORS·배포 allowlist 승인이 아니다.
- local seed 실행: `supabase/config.toml`의 `[db.seed].enabled=false`를 유지한다. `db reset`은
  migration만 재현하며, 승인된 immutable `.2`는 별도 정식 `seed-cycle → verify-final →
  provision_local_database_login` 단계로만 적용한다. 자동 seed 또는 임의 SQL 적용은 금지한다.
- 향후 배포 추천: Vercel(Frontend) + Render(Backend) + Supabase(DB); 공개 배포는 계정·리전·로그·CORS·예산 별도 승인 후
- 관리자: 초기 local/private 전용, public 환경에서는 서버측 gate 없이는 `/admin`과 관리자 API 비활성
- chat 재시도: optional UUID `Idempotency-Key`를 logical 질문 단위로 유지하고 correlation request ID와 분리한다. local DB에는 HMAC request digest, 독립 opaque claim token·5분 lease와 안전 응답만 논리 TTL 24시간 동안 보관하며 원문·마스킹 질문·correlation ID는 저장하지 않는다. startup과 60초 주기 purge를 사용하고 public retention은 재승인한다.
- local 관리자 read: immutable `00650`, chat idempotency: immutable `00660`을 사용한다. 둘 다 reserved public `00700` 앞의 local/private capability이며 public admin·remote DB·배포 승인이 아니다.
- 저장소: private `tskwak111/Sejong_AI`에 `5e09deccc7205503df07d938b6d4a88f4d5a327e`를 ordinary
  first push로 연결했고, PR #1 historical merge SHA는
  `ce8a6085fb57670ca74e009ed45e3d02d784c24b`다. 현재 remote authority는 `git fetch origin` 뒤
  `origin/main`으로 확인하며 별도 worktree의 local `main`과 같다고 전제하지 않는다. repository는 private이고
  PR #1 SHA의 post-merge hosted policy `29782433649`와 Frontend CI `29782433682`가 통과했다.
  `koregy`의 accepted write access·repository variable·read-only default Actions permissions도 검증됐다.
  Task 5는 partial이며 teammate MFA/recovery와 첫 Task 7 PR-only/no-direct-main-push rehearsal이
  남는다. Q-GIT-004=A/D-053에 따라 author/committer history·SHA는 보존한다.
- 협업 비용·강제 경계: Q-GIT-002=A로 GitHub Free·초기 0원을 유지한다. private repository의
  branch protection/CODEOWNERS 강제를 전제하지 않고 PR·CI·scope classification과 팀 규칙을
  사용하며, merge 버튼이 보이는 것은 정책상 허가를 뜻하지 않는다.
- Frontend 소유권: Q-OWN-001=A로 인간 Frontend 팀원이 `/`, `/chat`, `/admin`, typed API client,
  loading/empty/error/offline, 반응형·접근성, unit/E2E를 소유한다. `apps/web/**`,
  `tools/web-e2e/**`와 자신의 frontend 구현 노트만 직접 쓰며 계약·backend·DB·migration·official
  data·privacy/security policy는 read-only 또는 owner 요청 대상이다.
- 병합: Q-GIT-003=B로 허용 범위만 포함하고 CI를 통과한 frontend-only PR은 팀원이 자가
  병합할 수 있다. exact self-merge allowlist는 `apps/web/src/**`, `tools/web-e2e/e2e/**`, 신규 web
  구현 노트 1개와 그 INDEX append뿐이다. 기존 note/INDEX 행·env/package/lockfile/config·공개
  계약·backend·DB·data·security·`.github`가 포함되면 사용자 검토로 승격한다.
- Codex Cloud: Q-CLOUD-001=A로 branch와 Draft PR까지만 수행하고 사람이 병합한다. 사용자는
  2026-07-21 GitHub UI에서 `Only select repositories / Sejong_AI`를 확인했고 secret 없는
  `sejong-ai-cloud-docs` environment를 저장했다. Task 6은 App scope와 environment creation까지
  완료됐고 docs-only task·Draft PR·사람 병합 evidence 전에는 partial이다. LLM API
  key·DB DSN·context secret을 Cloud에 넣지 않으며 Docker/Supabase actual과 Upstage 합성 실호출은 local-only다.
- 원격 의미: private GitHub는 source collaboration/off-device tracked-history이고 public Web/API,
  remote DB, admin 공개, D-046의 `00700` 또는 public deployment 승인이 아니다.
- 오류 계약: 정책 응답은 HTTP 200, 승인 근거로 안전 응답을 만들 수 없는 시스템 불능만 HTTP 503 `SERVICE_UNAVAILABLE`
- 대화 기억: 화면 기록은 현재 탭 메모리, 짧은 구조화 문맥은 15분 서명형 client-carried `context_token`; 서버 세션·raw 대화문·token 저장 금지, token은 인증이나 공식 사실 근거가 아님
- DB role bootstrap: PostgreSQL 17 non-superuser migration runner를 유지한다. role은 처음부터 안전 속성으로 생성하고, replay에서는 runner가 허용받은 `NOLOGIN`·`NOCREATEDB`·`NOCREATEROLE`만 재적용한 뒤 `NOSUPERUSER`·`NOREPLICATION`·`NOBYPASSRLS`, membership, role setting을 catalog로 검증한다. 안전하지 않으면 중단하며 privileged 자동 downgrade/bootstrap은 도입하지 않는다.
- 실패 사유 확인: backend-only `confirm_failed_question_reason(uuid,text,text,text)` capability로 OPERATOR만 `NEW → REASON_CONFIRMED`를 수행한다. 최초 `interaction_events.fallback_reason`은 자동 분류 기록으로 불변이고, 운영자 확인·정정값은 `failed_questions.fallback_reason`에만 반영하며 `candidate_eligible`을 다시 계산한다.
- 후보 gate: 후보 작성은 `REASON_CONFIRMED + INSUFFICIENT_GROUNDING + candidate_eligible=true` failure에서만 가능하다. 사유 확인은 질문/답변 snapshot 없이 metadata audit를 남긴다.
- 승인 comment: 공개 OpenAPI가 승인·반려 모두 `review_comment`를 요구하므로 내부 승인 capability도 `approve_kb_candidate(uuid,text,text,text)`를 사용해 승인 comment를 후보와 metadata audit에 저장한다. 공개 wire 계약은 바뀌지 않는다.
- 적용된 migration은 불변이다. 이미 commit된 migration을 수정하지 않고 reviewed forward를 추가한다.
  현재 9개 rollback 순서는 `00670 → 00660 → 00650 → 00600 → 00500 → 00400 → 00300 → 00200 → 00100`이다.
- deferred ACTIVE-question trigger 실행: `app_private.validate_active_kb_question()` 하나만 새 `00600`에서 제한된 SECURITY DEFINER로 전환한다. `sejong_schema_owner`, `search_path=pg_catalog, pg_temp`(공식 PostgreSQL 17 SECURITY DEFINER 지침에 따라 임시 스키마를 마지막에 명시), PUBLIC·anon·authenticated·backend 직접 EXECUTE revoke를 재확인하며 backend private schema/table grant와 repository/admin-DSN 우회는 금지한다. 사용자의 직전 추천안 뒤 계속 진행 지시는 Q-DB-003=A 승인으로 해석했고 문자 A를 직접 입력했다고 기록하지 않는다.
- DB local schema 현재 기준선: forward/rollback 각 9개, pgTAP 9 files/356 assertions와 backend
  integration·rollback/absence/reset/replay를 갖춘 disposable `0.4.0-local` 기준선이다. Q-SEC-006=A/D-031과 Q-TOOL-001=A/D-032의
  patched CLI는 source/patch/runtime hash를 분리 고정하고 runner가 stock/PATH fallback 없이
  patched binary만 사용한다. 2026-07-18 historical gate는 exact one `127.0.0.1:54322`, 당시 pgTAP
  8 files/320, integration·8단계 compensation/absence/reset/replay, final container/process 0·volume delete 0을
  통과했다. `73f300b` bounded child process-tree remediation과 독립 review 0/0/0, final-code DB
  revalidation도 통과했다. 그 **역사적 pre-import 시점**에는 filesystem dispatcher만 `.2`와 같고
  공식/mock DB row 0·`/ready=503`이었다. 현재는 supported actual seed와 별도 application rehearsal이
  local 19→20 ACTIVE·`/ready=200`을 PASS했다. 어느 증거도 production/public/remote readiness가 아니다.
- DB local port 경계: Docker Engine 28+와 actual single `127.0.0.1:54322` binding이 필수다.
  Q-SEC-004=A/D-029의 `default-local-port-binding`과 Q-SEC-005=A/D-030의
  `local-only-port-binding`을 각각 적용·재시작했지만 HostIP 미지정 probe는 모두 IPv4
  `127.0.0.1`과 IPv6 wildcard `::`를 함께 생성했다. explicit `127.0.0.1` control만 단일
  loopback이었다. 현재 `local-only-port-binding`을 유지하되 완료 근거로 사용하지 않는다.
  Q-SEC-006=A/D-031에 따라 official v2.109.1 exact source의 local DB start HostIP만
  `127.0.0.1`로 지정하는 project-local CLI를 tag/commit·patch·Go 1.25.11·binary SHA-256으로
  pin했다. stock CLI는 보존한다. 사용자는 2026-07-18 Q-TOOL-001=A/D-032와 수정 계획
  `수정 계획 승인, 구현 시작`을 승인했고, checkout `.tools/s/a`, `.tools/s/b`와 pre-mutation
  absolute path budget, legacy partial-tree deny-only 경계, reproducible runtime manifest, patched-only
  runner와 actual full gate가 local에서 구현·검증됐다.
- DB public release 경계: Q-SEC-003=A/D-046으로 exact privileged function 22 signatures를
  property-only `00700`에서 `search_path=pg_catalog, pg_temp`로 보정하는 방향은 확정했다.
  구현은 사용자의 지시대로 public 준비 단계까지 보류한다. `00700`·matching compensation·전체
  regression과 별도 배포 승인이 끝날 때까지 remote/public 배포, public admin/API,
  public backend DB credential 사용을 차단하고 local 기준선을 production-ready라고 부르지 않는다.

## 2026-07-25 local/private 핵심 개선 루프 마일스톤

- Q-MVP-001=A/D-058/ADR-0020으로 7월 25일 토요일까지 local/private demo-ready core loop를
  우선 완료한다. 이는 최종 제품 범위 축소가 아니라 7월 31일 앞의 중간 인수 gate다.
- 실행 순서는 owner PR 통합·Frontend PR #4 note-ID 교정, DATA-SEED-002 19 ACTIVE, PII/chat
  계약, deterministic chat API와 `/chat`, 실패 질문·후보·별도 승인·20번째 ACTIVE, 최소
  `/admin`, 표본 20·회귀 1·보안·데모다.
- 7월 25일 뒤로 미룬 항목 중 외부 LLM은 Q-LLM-005=A에 따라 Upstage 합성 품질 평가로
  시작한다. 고급 UI polish, 100명 부하, 자동 백업, public deployment와 deferred `00700`은
  계속 별도다. 실제 시민 외부 LLM 전송과 public/remote 사용은
  계속 금지한다.
- 일정 단축으로도 PII 원문 0, ACTIVE/OFFICIAL-only, server-bound source, author≠reviewer,
  official/mock 분리, 390/430 keyboard/contrast 최소선은 완화하지 않는다.
- local/private `/admin`의 role selector는 demo actor 선택일 뿐 인증/RBAC가 아니다. public
  mode에서는 server-side gate 없이 관리자 router와 UI를 노출하지 않는다.
- Q-PM-DEMO-001=B/D-068로 PM 데모의 두 정책 질문을 분리한다. #4 개인조회는
  `UNKNOWN/PERSONAL_LOOKUP/candidate=false` 정책 결과를 반환하고 질문 text·interaction event·failed row를
  만들지 않는다. #5는 별도의 지원 범위 내 `INSUFFICIENT_GROUNDING` 질문으로 event와 eligible
  failed row부터 별도 승인자에 의한 20번째 ACTIVE, 동일 질문 SUCCESS까지 시연한다.
- 2026-07-22 actual continuation은 final local DB에서 one NEW failure→reason confirm→candidate
  submit→same-writer block→different approver→`KB-WASTE-03` SUCCESS와 `/ready=200`을 확인했다.
  FastAPI JSON pre-parse와 strict UUID/date의 canonical wire mismatch는 request field validator의
  exact-string-only 변환으로 보정했고, 전역 strictness와 public admin 금지는 유지했다. final API
  1,640, Web 48/lint/type/build/E2E 15, contracts 89, clean DB pgTAP 9/356·integration 8/8, root offline과
  deterministic sample T-01~T-20 20/20을 PASS했다.
- MVP-001은 PR #9 병합으로 local/private AI scope **Done**이다. PR #6과 Frontend PR #8은 사람이
  병합했고, owner 후속은 current PR #8 UI로 PERSONAL 미저장→별도 IG→사유 확정→OFFICIAL
  후보→별도 승인자·checklist 3/3→20번째 ACTIVE→동일 질문 SUCCESS·정확한 공식 출처를 actual
  browser 1/1로 재검증했다. feedback dialog의 focus 이동·trap·Escape·focus restore도 Web
  unit gate를 통과했다. manual demo는 인간 Pending이다. Upstage 합성 평가는 LLM-002의 승인된 명세와
  실행계획으로 offline Tasks 1~6 review clean 뒤 2026-07-25 local actual을 수행했다. outbound
  30회에서 strict-schema 27/30, 인간 검토 9개 평균 4.8444·최저 4, VAT 포함
  USD 0.004654815로 JSON 100% 기준을 충족하지 못해 전체 FAIL이다. 선택지 B는 승인되지
  않았고 provider-disabled/template 시민 경로를 유지한다. 100-user,
  automated backup, advanced UI,
  public/remote deploy와 `00700`은 deferred다. local role selector는 production authentication이 아니다.

## 제출 정보

- 팀명: [직접 입력]
- 팀원·역할: [직접 입력]
- 대표 연락처: [직접 입력]
- 제출일: [직접 입력]
- 최종 확인란: `팀 대표 확인`
- 문서 버전: v2.4.1
