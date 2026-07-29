# 팀 결정사항 요약

## 제품

- 서비스명: 세종 민원이음
- 구조: 시민용 민원 AI 플랫폼 + 관리자용 AI 민원 운영센터
- 기준 문장: **모르면 지어내지 않고, 알면 끝까지 안내한다.**
- 차별점: 실패 질문을 공식 KB 후보로 전환하고 담당자가 승인하는 개선 루프
- 현실형 목표: 공식 근거를 자연스럽게 안내하고 담당 기관과 운영 개선으로 연결하는
  안내·운영센터. 실제 신청·상태조회·결제 완료를 제공한다고 표현하지 않는다.
- 현재 실제 개발 협업: 사용자 owner 1명 + Frontend 팀원 1명. PM·Frontend·Backend·AI/Data는
  책임 역할 구분이며 Backend·DB·계약·데이터·보안의 최종 책임은 사용자가 가진다.

## 구현 범위

- 실제 페이지: `/`, `/chat`, `/admin`
- 지원 분야: 전입·주민등록, 증명서 발급, 대형폐기물, 지방세 일반 안내
- P0: 질문·분류·공식 KB 답변·출처·후속질문·4개 행정-domain 폴백+privacy 안전 재질문·지역 선택·기관 카드·관리자 승인 루프
- P1: 쉬운 말, 큰 글씨, 기본 명도 대비 4.5:1 이상, 실패 질문 필터, KPI, 품질 카드, 감사 이력, 성능 스모크 테스트
- P2: 실제 GPS·지도 내장·상태조회·정부24/내부망 연계·다국어·음성·고급 분석·전체 KB CRUD
- Q-PROD-REAL-001=A/D-088: 자연스러운 대화·공식 안내·기관 연결·범위 확대 검토·사람 승인
  운영을 먼저 현실 사용 수준으로 고도화한다. 실제 신청·상태조회·결제·기관 transaction은
  별도 범위 변경 전 P2다.

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
- CIVIC_SCOPE_GAP active local/private: 네 분야 밖 행정 민원은 기존 KB 후보와 분리된 범위확대 검토
  queue에 PII-safe masked text만 30일 보관한다. public 응답은 `intent=OUT_OF_SCOPE`,
  `fallback.reason=CIVIC_SCOPE_GAP`, candidate false다. 기존 event/failed/candidate와 분리하고
  자동 KB/ACTIVE 전환은 금지한다. exact contract·`00680` migration·typed admin/API/Web 흐름은
  D-093에서 local 검증을 통과했다.
- NON_CIVIC active: 날씨·맛집 등 민원과 무관한 질문은 기존 OUT_OF_SCOPE 시민 응답을
  사용하고 text/event/failed/review row를 저장하지 않는다.
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
- 마스킹 성공은 저장·provider 호출의 필요조건일 뿐 충분조건이 아니다. local/private에서는
  D-072의 supported intent·ACTIVE/OFFICIAL·근거 gate까지 통과해야 하며 public/remote/실제
  기관 운영의 시민 질문 외부 전송 금지는 유지한다.
- Q-LLM-005=A: 외부 합성 평가 공급자는 Upstage exact `solar-pro3`다. local/private의 서버
  검증 canonical `T-01`~`T-10`만 최대 30 outbound attempt로 평가하며 실제 시민·PII·민감정보·
  자유 입력·공개 운영은 금지한다. D-066/D-067로 written specification과 실행계획이 승인돼
  offline 구현·리뷰를 완료했고 D-071의 local actual은 strict-schema 27/30으로 FAIL했다.
  인간 검토 9개 평균 4.8444·최저 4와 비용 cap은 통과했지만 option B는 승인되지 않았다.
  이 역사적 FAIL과 당시 option B 미승인 증거는 유지한다.
- Q-LLM-006~012/D-072: 사용자는 이후 local/private 입찰 시연 MVP에 한해 실제 시민 chat의
  근거 제한형 Upstage 연결을 새로 승인했다. 안전한 마스킹+supported intent+ACTIVE/OFFICIAL+
  grounding을 모두 통과한 경우만 masked question과 최소 KB를 보내고, 모델은 summary와
  server-issued fact ID만 제안한다. 공식 fact text·source·office·policy는 서버가 결합하며
  8초 1 attempt 뒤 오류·schema·fact drift가 하나라도 있으면 전체 template fallback이다.
  SUCCESS는 `GENERATED|TEMPLATE` 작성 방식 배지를 제공한다. D-073에서 written specification,
  D-074에서 후속 TDD 실행계획과 Subagent-Driven 구현을 승인했다. D-075 local actual은 10건
  GENERATED 4/TEMPLATE 6, 출처 10/10, 공식 mismatch 0, PII-free fixture typed
  write-boundary 위반 0, outbound 10으로 PASS했다.
  corrective second 10-call run은 D-076에서 사용자가 사후 확인하고 PR #13 병합을 승인했다.
  D-077/Q-DB-CLEANUP-001=A에 따라 오표시 metadata 22행은 현재 유지하고 이 local DB의
  event 통계를 평가 KPI로 사용하지 않는다. 정식 수치가 필요할 때의 reset·정식 `.2`
  재시드·필요한 19→20 승인 흐름 재현과 future rerun은 각각 별도 인간 승인이 필요하다.
  public/remote/실제 기관 운영은 계속 금지한다.
- Q-CLASS-001=A/D-086 implemented local/private: PII·policy·명백한 supported/NON_CIVIC은 deterministic으로
  유지하고 안전한 ambiguous 질문만 Upstage closed-enum classifier에 전달한다. 모델은
  답변·출처·저장·candidate 여부를 결정하지 않는다. historical actual acceptance는
  Q-CLASS-002=A/D-087의 20/30/40·USD 0.05이고 D-095에서 PII-free frozen 60 actual을 통과했다.
  current local interactive profile은 D-099/D-104의 80/100/160·USD 0.20이다. D-105의 새
  PII-free 20-case selector actual은 정확히 한 번 실행해 20 selected·skip 0·11
  provider-free·9 outbound였으나 strict accepted usage/provider match 0으로 FAIL했고
  재실행하지 않았다.
- Q-LLM-013=A/D-107: 명시적 `JSON만` 지시만 복원한 source `4cb42ff`의 exact-one actual은
  같은 9 outbound 모두 HTTP 2xx와 accepted usage를 반환해 D-106의 4xx를 해소했다. strict
  closed decision accepted/match는 0이라 overall FAIL이며 재시도하지 않았다. response body를
  보관하지 않아 다음 검증 단계는 A-071로 분리하고 현재 fail-closed fallback을 유지한다.
- D-108: A-071은 production parser의 enum-only optional observer와 aggregate-only report로
  진단한다. same fixed 20·9 outbound·retry 0·USD0.20 exact-one actual 방향은 승인됐지만
  written specification 확인 전 code/provider call은 0이다.
- D-109: written specification과 exact RED/GREEN inline 실행계획을 승인했다. code/test/source
  commit 뒤 actual 1회만 실행하고 결과와 관계없이 재시도하지 않는다.
- D-110: A-071의 contract parser, production optional observer와 aggregate-only runner를
  TDD로 구현했다. 13개 terminal enum 외 값은 진단 경계를 통과하지 않고 observer 오류는
  시민 decision/fallback을 바꾸지 않는다. 142 focused PASS와 Ruff/Mypy PASS 뒤 D-107 report를
  archive했으며, clean source commit과 exact-one actual은 다음 gate다.
- D-111: clean source `0646db0`의 approved exact-one actual은 20 selected·0 skip·11
  provider-free·9 outbound, 9/9 HTTP 2xx·strict usage·stage total을 기록했고 모든 response가
  `KEY_SET_REJECTED`에서 종료했다. accepted/match 0이라 FAIL이며 retry 0, 비용은 VAT 포함
  USD0.002626503이다. body/status detail/key/DSN/question 보관 0과 local modes false/false를
  유지한다. A-071은 resolved, exact-key corrective와 새 actual은 A-072 human gate다.
- D-112/Q-LLM-014=A: A-072 provider wire는 Upstage strict `json_schema`를 사용하고
  `route`, `intent`, `topic_id`, `coverage_id`, `pending_slot` 다섯 필드를 모두 required
  string으로 제한한다. nullable 의미는 wire의 고정 `NONE` sentinel로 표현한 뒤 서버가 기존
  내부 `None`으로 정규화한다. public API/DB/data/dependency와 server-bound source는 불변이다.
  상세 설계 승인 전 code/provider call은 0이고 새 actual은 구현·offline 검증 뒤 별도 gate다.
- D-113: A-072 설계 1부를 승인했다. exact 5-key string schema와 nullable 4필드의 `NONE`
  normalization, full-name prompt, 기존 closed server validation, retry 0·fail-closed가 권위다.
  provider schema는 동적 catalog enum을 복제하지 않는다. 설계 2부와 written specification
  승인 전 code/provider call은 0이다.
- D-114: A-072 설계 2부를 승인하고 strict wire integrated written specification을 Review로
  게시했다. provider-only parser는 exact `NONE`만 canonical `None`으로 바꾸며 기존 validator와
  fixed terminal stage를 공유한다. target application/prompt/tests는 `0.12.3/0.4.2/2.1.6`이고
  API/DB/data/dependency는 불변이다. actual은 offline/root gate와 clean source 뒤 별도 승인 전 0이다.
- D-115: A-072 written specification을 Approved로 전환하고 exact RED/GREEN Tasks 1~5 plan을
  Review로 게시했다. Task 6 actual은 이 plan 승인과 분리하며 Tasks 1~5 PASS·clean source 뒤
  exact 별도 승인이 필요하다. code/provider call/dependency/API/DB/data/push/merge는 아직 0이다.
- D-116: 사용자의 `계획 승인, 1번으로 구현 시작`으로 A-072 Tasks 1~5와 Subagent-Driven
  실행을 승인했다. exact `NONE` provider parser, bounded canonical prompt, fresh strict schema와
  offline area/version integration을 구현해 area 333·controlled-double runner 24·Ruff/Mypy
  115 PASS를 얻었다. application/prompt/tests만 `0.12.3/0.4.2/2.1.6`으로 전진하고 API/contracts/
  DB/data/dependency/provider actual call/cost는 0이다. Task 5 뒤 corrective actual은 D-117
  별도 exact 인간 승인 전 금지한다.
- D-117: 사용자의 exact 승인 뒤 clean source `efc0b34`에서 A-072 corrective actual을 정확히
  한 번 실행했다. 20 selected·0 skip·11 provider-free·9 outbound, privacy/policy outbound 0,
  HTTP 2xx·strict usage·terminal stage total 9였고 D-111의 `KEY_SET_REJECTED`는 0으로
  해소됐다. 그러나 9건 모두 `ENUM_SHAPE_REJECTED`, accepted/match 0이라 전체 acceptance는
  FAIL이며 재실행하지 않았다. retry 0, 비용은 VAT 포함 USD 0.002496648로 cap USD 0.20
  미만이다. 질문·provider body·status detail·key·DSN 보관 0, lock 0, local modes false/false다.
- D-118: A-073의 explicit route matrix와 refined value-free diagnostics 설계를 승인했다.
  provider schema와 public contract는 유지하고 prompt에 route별 exact five-field 조합,
  provider intent/pending vocabulary, literal uppercase `NONE`과 same-row topic/coverage를
  명시한다. 새 진단은 route·intent·pending-slot·identifier·route-shape first-failure count만
  aggregate하며 질문·provider body·wrong value·fixture별 stage를 보관하지 않는다.
  written specification과 plan 승인 전 code/provider call은 0이고, actual은 별도 exact 승인
  전 금지한다.
- D-119: 사용자의 `명세 승인`으로 A-073 written specification을 Approved로 확정하고 TDD
  implementation plan을 Review로 게시했다. Tasks 1~5는 offline TDD·영역 검증·clean-source
  gate까지만 포함한다. provider-only catalog는 intent별 compact row로 직렬화하되 exact
  topic/coverage/label과 approved example 최대 2개를 보존한다. configured question 1,024와
  complete-message 4,096 guard는 유지하며 actual-eligible 20-topic/256-character prompt만
  guard 통과를 요구한다. 제품 코드·provider call·DB/data/API/dependency는 이 checkpoint에서
  0이고 Task 6 actual은 별도 exact 인간 승인 전 금지한다.
- D-120: 사용자의 exact `계획 승인, 1번 Subagent-Driven으로 구현 시작`으로 A-073 Tasks 1~5
  offline plan과 Subagent-Driven 실행을 승인했다. Tasks 1~4는 shared typed decision builder,
  five refined value-free stages, explicit route matrix·literal `NONE`·intent-grouped catalog,
  production-wire oracle와 version/authority 통합을 완료했다. baseline-stale
  controlled mock의 JSON null 1건은 RED 뒤 exact string `"NONE"`으로만 교정했다. application
  `0.12.4-classifier-wire-diagnostics`, prompt_set `0.4.3-explicit-route-matrix`, test_suite
  `2.1.7-classifier-wire-correction`만 전진하고 API/contracts/Web/DB/
  data/dependency는 불변이다. Task 5 root wrapper는 exact 1회 호출했지만 harness timeout
  `124`로 final stdout/exit를 회수하지 못해 aggregate를 `NOT VERIFIED/FAIL`로 기록하고
  재실행하지 않았다. 독립 docs/secret/diff/status는 PASS이며 provider/network actual
  call/cost는 계속 0/USD 0이다. Task 6은 root-gate 해소와 exact-one actual 승인 전 blocked다.
- D-121: A-073 final review fix wave와 scoped re-review를 완료했다. production prompt에 네
  provider intent의 contiguous vocabulary를 복원하고 adjacent first-failure precedence와
  selected-question/provider-body/invalid-value 비보관을 mutation/focused test로 강화했다.
  final prompt는 4,067자·guard margin 29, area 397·controlled-double 39·Ruff/Mypy 115이며
  scoped re-review는 actionable finding 0이다. documentation만 `2.30.6→2.30.7`로 전진하고
  다른 version axis와 API/contracts/Web/DB/data/dependency는 불변이다. Task 5 root aggregate
  `NOT VERIFIED/FAIL`, invocation/rerun `1/0`을 그대로 보존한다. A-073 corrective actual은
  실행 0이며 기존 Upstage actual도 재실행하지 않고 offline review 상태로 종료한다.
- D-122/Q-LLM-PROVIDER-001=A: DeepSeek exact `deepseek-v4-flash`를 local/private
  질문 분류의 명시적 선택 공급자로 추가한다. exact five-string/`NONE`, server parser,
  deterministic PII/policy/obvious route, ACTIVE/OFFICIAL grounding과 server-owned source를
  유지하고 기존 Upstage classifier·grounded final generator를 보존한다. DeepSeek는 local
  `create_local_app`/loopback에만 구성하며 public main·remote DB·실제 시민 운영에는 연결하지
  않는다. 새 A-074 offline gate 1회와 clean-source review 뒤 고정 synthetic 20 actual을
  1회만 실행하고 실패도 aggregate evidence로 닫아 rerun0을 유지한다. 새 production
  dependency, final answer 공급자 변경과 자동 merge는 금지한다. Offline Tasks 1~6b는
  selector/settings, strict transport, provider별 비용·usage, local composition과 controlled
  one-shot runner/wrapper를 구현하고 pre-gate review의 Important 5+1을 두 fix wave로 닫았다.
  최종 fresh review는 Critical 0 / Important 0 / Minor 0 `READY`이며, recursive duplicate
  key·bounded identity/raw response·total deadline·exact-byte/pre-lease identity·post-child
  source/tree 경계를 포함한다. 이 checkpoint의 A-074 gate와 DeepSeek actual은 invocation/
  rerun 각각 0/0이고 artifact·token·비용·PASS/FAIL은 아직 없다.
- D-123: hardened source `9c7f818123533a4adc61d3953ed4d4630c793891`의 A-074 offline
  wrapper exact-one outcome은 immutable `FAIL`이다. Exit 1, timed_out false, invocation/rerun
  1/0, stdout/stderr 475/0 bytes, first failing governed stage `TEST-ROOT`를 aggregate로
  보존하고 재실행하지 않는다. Standalone 434-test 진단은 expected environment map이 이미
  안전하게 tracked된 classifier 네 값을 누락한 repository-truth mismatch 1건을 찾았고
  test-only +4 교정 뒤 exact PASS와 full `434 OK / skipped 2`, review C0/I0/M0를 확인했다.
  이 corrective evidence는 immutable gate를 PASS로 바꾸지 않는다. DeepSeek actual은
  blocked/unexecuted invocation/rerun 0/0이고 report/lease, outbound, token, cost는 모두 0이다.
  A-073 root `NOT VERIFIED/FAIL` 1/0은 불변이다.
- D-124: 사용자의 exact `변수명 수정 완료, A-075 DeepSeek actual 1회 실행 승인`으로
  A-075 corrective evidence를 새 identity에서 실행한다. Remote main의 PR #21 merge
  `67fe37c...`를 baseline으로 별도 branch를 만들었고, diverged local main은 변경하지 않았다.
  A-074 wrapper/result/report/lease와 FAIL 1/0·actual 0/0은 불변이다. A-075는 전용 offline
  result/log/lease와 actual report/lease를 사용하며 새 clean-source offline PASS와 network-free
  readiness 뒤에만 고정 synthetic 9 outbound actual을 정확히 한 번 실행한다. 제품 코드,
  exact five-string/`NONE`, ACTIVE/OFFICIAL source, 3초·retry0·concurrency1·USD0.20 및 비보관
  경계는 유지하고 public/remote/free-input·새 dependency·자동 rerun/merge는 금지한다.
- D-125: Source `982198faed073a6c4e04205f5b3dde3f95ebae20`의 A-075 offline gate는
  exact-one `PASS`, exit0·timed_out false·invocation/rerun1/0·stdout/stderr2006/0이며
  network-free readiness도 PASS했다. 이어 actual lease를 한 번 소비했으나 fixed
  20/0·11/9·policy/privacy outbound0과 별개로 outbound9 모두 HTTP 응답 전
  `transport_no_response`여서 provider response/2xx/parse/accepted/match/token 0,
  acceptance `FAIL`이다. Retention/retry/rerun은 모두 0이고 report/lease를 보존한다.
  Conservative worst-case USD0.02306304<0.20은 실제 청구액 주장이 아니며 transport 하위
  원인은 단정하지 않는다. A-074 evidence는 불변이고 추가 actual은 새 인간 결정 전 금지한다.
- D-126: 사용자의 DeepSeek network-recovery 재실행 지시로 A-075를 덮어쓰지 않는 A-076
  actual 1회를 승인한다. 비밀 없는 DNS·TCP443·TLS/HTTP 사전 진단은 모두 성공했고 무인증
  HTTP 4xx를 받아 응답 경로 복구를 확인했다. A-076은 별도 offline/result/report/lease
  identity에서 기존 20/0·11/9·3초·retry0·concurrency1·output128·USD0.20·무보관 경계를
  그대로 사용한다. clean source offline PASS와 readiness 뒤 정확히 한 번만 actual을 실행하며
  결과와 무관하게 A-074/A-075 증거를 변경하거나 자동 재실행·merge하지 않는다.
- D-127: Source `c9fc1be452db81ea6270211da666e7c854298fe0`의 A-076 offline/readiness는
  PASS했지만 exact-one actual은 다시 `transport_no_response` 9/9로 `FAIL`했다. DNS·TCP443·
  TLS/HTTP value-free probe는 PASS했고 actual 28.6초가 9×3초 전체 timeout budget과 거의
  일치하므로 3초 timeout 만료가 가장 강한 가설이지만 exception detail 비보관 정책상 확정하지
  않는다. Provider response/2xx/parse/accepted/match/token0, retention/retry/rerun0이며 A-074/
  A-075/A-076 report와 lease를 보존한다. Timeout 변경과 추가 actual은 새 인간 결정이 필요하다.
- D-128/Q-LLM-015=A: DeepSeek classifier의 connect/write/pool은 3초, read와 complete
  exchange는 10초로 분리한다. 새 A-077 offline/readiness 뒤 aggregate-only 합성 1-call이
  HTTP 2xx일 때만 고정 9-call actual을 실행한다. Retry0·무보관·USD0.20와 A-074~076 불변,
  public/remote/free-input·final-answer provider·dependency 불변을 유지한다.
- D-129: A-077 source `675eef4...` offline PASS 1/0은 보존하지만 provider 호출은 0회다.
  Independent review의 exact probe-lease 결합과 actual pre-lease same-source 재검사 누락을
  교정한 별도 A-078 identity만 실행 후보로 사용한다. Callback 뒤 final source/input 재검증과
  probe 응답 뒤 재검증도 PASS 전 강제한다. D-128의 probe 1-call·조건부 actual run 1회
  (정확히 9 provider calls)·비용·local/private 범위는 늘리지 않고 A-074~077을 재실행하지 않는다.
- D-130/D-131: A-078 source `844e53b...` offline은 PASS 1/0이지만 exact-one probe는
  response/2xx0·transport-no-response1로 FAIL했고 actual은 0회다. Windows CRLF lease writer를
  binary-open으로 교정한 별도 A-079에서 사용자가 승인한 probe 1-call을 다시 실행하고, 2xx일
  때만 9 provider-call actual run 1회를 실행한다. A-078은 불변 보존한다.
- 화면 transcript와 대화 token은 현재 탭 메모리에만 유지; 서버 세션·raw transcript·token 영속 저장 금지
- D-089/D-090 context v2 implemented local/private: optional topic ID, `CERTIFICATE_KIND|REGION|WASTE_ITEM`
  pending slot, closed dialog act만 추가한다. v1은 남은 최대 TTL read-only, issuer v2 only며
  topic은 매 요청 ACTIVE/OFFICIAL 재검증한다. Web `새 대화`는 current-tab transcript와 token을
  함께 초기화한다.

## 기술

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI + Python
- 개발 기준: Node 24.x+pnpm, Python 3.12+uv
- DB/Search: Supabase PostgreSQL + Supabase CLI 버전 SQL migration + 키워드·메타데이터 검색; MVP embedding off
- LLM: 최종 시민 답변 생성은 Upstage direct API exact `solar-pro3`를 유지한다. 질문
  classifier는 explicit selector로 disabled/Upstage/DeepSeek `deepseek-v4-flash` 중 하나를
  local/private에서 선택할 수 있다. 합성 evaluator는 기존 max output 1024,
  concurrency 1, retry 최대 1, run outbound attempt 30 경계를 유지한다. 후속 LLM-003 시민
  경로는 local/private에서 supported+masked+ACTIVE/OFFICIAL+grounded일 때만 8초·1 attempt·
  hidden retry 0·concurrency 1·process cap 30으로 호출하고, server-issued fact ID와
  disabled/template fallback을 강제한다. hybrid classifier는 3초·1 attempt·retry 0이고
  current local interactive profile은 classifier 80/generator 100/combined 160으로 제한한다.
  D-092는 PII-free allowlisted classifier actual과
  ADR-0026의 admin-disabled remote 시민 검증을 승인했지만 real citizen/free-input provider
  outbound와 실제 기관 운영은 개인정보·약관·법무 운영 gate 전까지 금지한다.
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
  현재 11개 rollback 순서는 `00700 → 00680 → 00670 → 00660 → 00650 → 00600 → 00500 → 00400 → 00300 → 00200 → 00100`이다.
- deferred ACTIVE-question trigger 실행: `app_private.validate_active_kb_question()` 하나만 새 `00600`에서 제한된 SECURITY DEFINER로 전환한다. `sejong_schema_owner`, `search_path=pg_catalog, pg_temp`(공식 PostgreSQL 17 SECURITY DEFINER 지침에 따라 임시 스키마를 마지막에 명시), PUBLIC·anon·authenticated·backend 직접 EXECUTE revoke를 재확인하며 backend private schema/table grant와 repository/admin-DSN 우회는 금지한다. 사용자의 직전 추천안 뒤 계속 진행 지시는 Q-DB-003=A 승인으로 해석했고 문자 A를 직접 입력했다고 기록하지 않는다.
- DB local schema 현재 기준선: forward/rollback 각 11개, pgTAP 11 files/385 tests와 backend
  integration·rollback/absence/reset/replay를 갖춘 disposable `0.5.0-local` 기준선이다. Q-SEC-006=A/D-031과 Q-TOOL-001=A/D-032의
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
- DB public release 경계: Q-SEC-003=A/D-046/D-092에 따라 exact privileged function 22
  signatures의 property-only `00700`과 matching rollback·body/owner/ACL fingerprint·전체
  regression을 local에서 구현·검증했다. 이는 remote/public 배포 완료가 아니다. ADR-0026의
  configured citizen target smoke 전 production-ready를 주장하지 않으며 인증 없는 public
  admin/API와 public backend DB credential 사용은 계속 차단한다.

## 2026-07-25 local/private 핵심 개선 루프 마일스톤

- Q-MVP-001=A/D-058/ADR-0020으로 7월 25일 토요일까지 local/private demo-ready core loop를
  우선 완료한다. 이는 최종 제품 범위 축소가 아니라 7월 31일 앞의 중간 인수 gate다.
- 실행 순서는 owner PR 통합·Frontend PR #4 note-ID 교정, DATA-SEED-002 19 ACTIVE, PII/chat
  계약, deterministic chat API와 `/chat`, 실패 질문·후보·별도 승인·20번째 ACTIVE, 최소
  `/admin`, 표본 20·회귀 1·보안·데모다.
- 7월 25일 뒤 외부 LLM은 Q-LLM-005=A 합성 평가로 시작했고 D-071에서 FAIL로 종료했다.
  이후 Q-LLM-006~012/D-072가 local/private 근거 제한형 시민 chat 설계를 승인했고 D-073에서
  written specification, D-074에서 TDD 실행계획을 승인해 구현을 시작한다. 고급 UI polish, 100명 부하, 자동 백업,
  public deployment와 deferred `00700`은 계속 별도이며 public/remote/실제 기관 운영의 시민
  외부 전송은 계속 금지한다.
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
  USD 0.004654815로 JSON 100% 기준을 충족하지 못해 전체 FAIL이다. 당시 선택지 B는 승인되지
  않아 provider-disabled/template 시민 경로를 유지했다. 후속 D-072가 더 좁은 server-issued
  fact ID 검증과 전체 template fallback을 전제로 local/private 연결 설계를 새로 승인했지만
  written specification은 D-073, 계획과 구현 시작은 D-074에서 승인됐다. D-075의 별도 local
  actual은 PII-free fixture 10건 GENERATED 4/TEMPLATE 6, 출처 10/10, 공식 mismatch 0,
  typed write-boundary forbidden-value 위반 0, outbound 10으로 PASS했다. legacy-reported
  VAT 포함 USD 0.001319835는 usage completeness 전 lower-bound이고 configured maximum
  USD 0.0135168은 USD 0.05 cap 아래다. corrective rerun incident는 D-076/A-049에서 사후
  확인됐다. D-077은 22행 유지와 현재 local event KPI 비권위를 확정했으며, clean KPI가
  필요할 때 reset·재시드·승인 흐름 재현을 별도 승인받는다. future rerun도 새 승인이
  필요하다. 이는 local/private 증거다. 100-user,
  automated backup, advanced UI,
  public/remote deploy와 `00700`은 deferred다. local role selector는 production authentication이 아니다.

## 2026-07-27 자연스러운 민원 대화·운영 통합 결정

- D-091로 설계 1~3부를 하나의
  `docs/superpowers/specs/2026-07-27-natural-civic-dialogue-and-operations-design.md`에
  통합한다. privacy-first hybrid classifier, context v2, `CIVIC_SCOPE_GAP` 별도 queue,
  일반 후보 작성, 오류·성능·acceptance가 구현 권위다.
- D-092로 PII-free actual Upstage, local DB reset·정식 `.2` seed, `00680` 뒤 `00700`
  public hardening과 구성된 remote 시민 경로 검증을 승인한다.
- public/remote에서도 인증 없는 `/admin`과 관리자 API는 비활성이다. 실제 신청·상태조회·결제는
  P2이며 현재 시스템이 행정 처리를 완료한다고 표현하지 않는다.
- remote target/credential이 없으면 코드·migration·runbook까지만 검증하고 target을 추측하거나
  새 계정을 자동 생성하지 않는다.
- D-095 actual evidence: frozen 60 classifier는 40 deterministic/20 provider, policy/privacy
  outbound 0, corrective 60/60 PASS이며 두 bounded run 누적 비용은 VAT 포함 USD 0.003873210이다.
  remote discovery에서 application/DB target·credential·origin·saved version이 모두 0이므로
  migration·seed·deploy·smoke는 `Not executed: target not configured`다.

## 2026-07-27 제한형 Hybrid RAG 후속 결정

- Q-RAG-001=A/Q-DATA-RAG-001=A와 D-096/D-100~D-102로 current ACTIVE/OFFICIAL KB 최대
  20개를 사용하는 bounded topic catalog를 선택한다. vector DB, embedding, 새 production
  dependency, DB migration과 official `.2` 변경은 하지 않는다.
- Upstage는 마스킹 질문과 최소 catalog를 받아 closed route/intent/topic/coverage/pending-slot만
  제안한다. server가 current ACTIVE membership·intent·coverage와 source를 재검증하고 typed
  evidence가 없으면 성공시키지 않는다. 최초 구현은 top-1 KB만 사용한다.
- 지원 분야이지만 대응 topic이 없으면 `INSUFFICIENT_GROUNDING`, 모호하면 무실패-row
  FOLLOWUP, 범위 밖 행정은 별도 `CIVIC_SCOPE_GAP` queue, 비행정·policy/provider 장애는
  기존 무저장 경계를 유지한다.
- generic certificate는 등본/초본/차이 3개로 시작하고, generic move/waste/tax는 해당
  intent의 bounded topic 선택지를 반환한다. 지역 selector는 입력창 위 상시 표시, same-tab
  새 대화에서만 React memory로 유지하며 storage/DB에는 저장하지 않는다.
- local interactive provider target은 classifier 80, generator 100, combined 160,
  3초/8초, retry 0, concurrency 1, hard wall 12초, VAT 포함 USD0.20 pre-reservation stop이다.
  historical 20/30/40·USD0.05 actual evidence를 덮어쓰지 않는다.
- 데이터 사실은 추가하지 않는다. retrieval coverage metadata와 48-case synthetic UAT는
  non-factual artifact로 분리하고, 냉장고 폐가전·재산세 세율 같은 새 사실은 후속 official
  data/PM approval cycle 전까지 근거 부족으로 닫는다.
- 상세 권위는 ADR-0027과
  `docs/superpowers/specs/2026-07-27-bounded-hybrid-rag-conversation-design.md`다.
- 사용자의 2026-07-27 `명세 승인`으로 written specification은 Approved다. exact RED/GREEN
  실행계획은 `docs/superpowers/plans/2026-07-27-bounded-hybrid-rag-conversation.md`다.
  이어진 `계획 승인, Subagent-Driven으로 구현 시작`에 따라 D-104의 Tasks 1~9
  local/offline 구현·독립 검토가 완료됐다. immutable official `.2`의 runtime 교집합은 19이고
  synthetic UAT 48/48·official 57/57·classifier 60/60·focused 91 PASS/skip 0이다.
  D-105/Task 10 actual은 20 selected·skip 0·11 provider-free·9 outbound 뒤 strict accepted
  usage/provider match 0으로 FAIL했고 재실행하지 않았다. Task 11 local/private 마감은 browser
  27/27, API 2,357 pass·8 local-DB skip, contracts 96/96, Mypy 114, secret/bundle/protected
  diff 0이다. final wrapper 자체는 FORMAT-API exit 1로 PASS가 아니며 formatter 교정 뒤 미실행
  constituent는 별도 PASS했다. public/remote, DB reset/seed, official `.2` 변경, 자동 merge는
  계속 미실행이다.

## 제출 정보

- 팀명: [직접 입력]
- 팀원·역할: [직접 입력]
- 대표 연락처: [직접 입력]
- 제출일: [직접 입력]
- 최종 확인란: `팀 대표 확인`
- 문서 버전: v2.6.0
