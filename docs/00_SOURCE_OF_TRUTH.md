# Source of Truth와 문서 충돌 해결 규칙

## 1. 목적

기존 업로드 패키지에는 초기 아이디어, 넓은 기능 범위, 오래된 스타터 코드가 함께 있다. 이 문서는 Codex와 인간 개발자가 어떤 문서를 정답으로 사용해야 하는지 고정한다.

## 2. 권위 순서

| 순위 | 위치 | 역할 |
|---:|---|---|
| 1 | `AGENTS.md` | 작업 방식·안전·기록 의무 |
| 2 | `docs/source-of-truth/TEAM_DECISIONS.md` | 최종 제품·범위·기술·정책 결정 |
| 3 | `docs/source-of-truth/PROJECT_PLAN.md` | 일정·P0/P1/P2·인수 기준 |
| 4 | `docs/source-of-truth/RFP_MATRIX.md` | 요구사항 추적과 구현 수준 |
| 5 | `docs/source-of-truth/PRIVACY_POLICY.md`, `APPROVAL_POLICY.md`, `KB_GUIDE.md` | 영역별 필수 정책 |
| 6 | `docs/adr/` | 아키텍처 결정과 트레이드오프 |
| 7 | `contracts/`, `database/` | 현재 코드가 따라야 할 실행 계약 초안/확정본 |
| 8 | `docs/implementation-notes/` | 실제 구현 이력과 증거 |
| 9 | `legacy/` | 역사·참고만 가능, 활성 범위가 아님 |

상위 문서와 하위 문서가 충돌하면 상위 문서를 따른다. 다만 상위 문서가 모호하거나 현실 구현과 불일치하면 임의로 해석하지 않고 모호성 레지스터와 인터뷰를 사용한다.

## 3. 현재 절대 범위

- 4개 민원 분야
- 공식 KB 20건
- 페이지 3개
- 표본 질문 20개 + 회귀 1개
- 관리자 승인형 개선 루프
- 실제 GPS/상태조회/다국어/고급 분석은 P2

2026-07-25의 Q-MVP-001 local/private 마일스톤은 위 최종 범위를 줄이지 않는다. 19개 초기 ACTIVE를
실제 local DB에 반영한 뒤 관리자 개선 루프로 20번째 ACTIVE를 만들고 표본 20·회귀 1·보안·데모를
완주하는 중간 gate다. 외부 LLM 품질 평가, 고급 UI, 100명 부하, 자동 백업과 공개 배포는 이
마일스톤 뒤로 연기하지만 최종 P1 백로그에서 삭제하지 않는다. 상세 권위는 D-058/ADR-0020과
승인된 MVP-001 명세·계획이다.

2026-07-23 Q-LLM-005=A/D-065/ADR-0022는 아직 구현되지 않은 DeepSeek 선택을 대체한다. 외부
공급자는 Upstage exact `solar-pro3`이며, 먼저 local/private server-allowlisted 합성
`T-01`~`T-10` 평가로 한국어 품질·strict JSON·비용을 검증한다. 결정론적 시민 경로는 계속
기본이다. 당시 실제 시민/free-input/public/remote provider 사용 금지는 D-092에서
PII-free allowlisted actual classifier 검증만 좁게 supersede됐고, real citizen/free-input
outbound는 ADR-0026의 개인정보·약관·법무 운영 gate 전까지 금지한다.
2026-07-25 actual은 outbound 30회에서 strict-schema 27/30으로 전체 FAIL했다. 인간 검토 9개
평균 4.8444·최저 4와 VAT 포함 USD 0.004654815는 통과했지만 JSON 100% 기준을 충족하지
못했으므로 D-071에서 선택지 B 미승인과 provider-disabled/template 시민 경로 유지를 확정했다.

이후 사용자는 2026-07-25 Q-LLM-006~012/D-072/ADR-0023으로 **local/private 입찰 시연
MVP에 한해** 근거 제한형 Upstage 시민 답변 생성을 새로 승인했다. 보수적 마스킹, deterministic
supported intent, ACTIVE/OFFICIAL 검색과 근거 gate를 모두 통과한 요청만 마스킹 질문과 최소
KB를 보낸다. 모델은 summary와 server-issued fact ID만 제안하고, 공식 fact text·출처·기관·정책
결과는 서버가 결합한다. 8초·1 attempt·hidden retry 0이며 검증이나 호출 실패 시 모델 결과 전체를
버리고 기존 공식 template로 답한다. LLM-002 actual FAIL 증거는 그대로이며 public/remote/실제
기관 운영은 별도 개인정보·보안·비용·배포 승인 전까지 계속 금지한다. 현재 상태는 설계·D-073
written specification·D-074 8-task 실행계획 승인에 따른 offline 구현·task-scoped review·
provider-disabled final root gate 완료와 D-075 local actual PASS다. final 10건은
GENERATED 4/TEMPLATE 6, 출처 10/10, 공식 사실 mismatch 0, PII-free fixture의 typed
write-boundary forbidden-value 위반 0,
outbound 10이었다. legacy runner의 VAT 포함 USD 0.001319835는 usage completeness를 강제하기
전 reported lower-bound이며, configured maximum USD 0.0135168은 USD 0.05 cap 아래다. 종료 뒤
provider-disabled TEMPLATE로 복원했다.
corrective second 10-call run의 governance incident는 D-076에서 사용자가 사후 확인하고 PR #13
병합을 승인해 A-049를 해결했다. D-077/Q-DB-CLEANUP-001=A에 따라 오표시 metadata 22행은
현재 유지하고 해당 local DB snapshot의 event 통계를 평가 KPI로 사용하지 않는다. 정식 수치가
필요해지는 시점의 local reset·정식 `.2` 재시드·필요한 19→20 승인 흐름 재현은 B의 별도 인간
승인을 받는다. 이는 future provider rerun, DB reset/delete/update, public/remote 또는 실제 기관
운영 승인이 아니다.

2026-07-27 Q-CLASS-001=A/D-086/ADR-0025는 future local/private 질문 분류를 hybrid로
확장하는 방향을 승인했다. PII·policy·명백한 결과는 deterministic server gate가 유지하고,
안전하게 마스킹됐지만 애매한 현재 질문만 Upstage closed-enum classifier에 전달한다. 모델은
답변·출처·저장 여부를 결정하지 못한다. Q-CLASS-002=A/D-087은 classifier를 요청당 1회·3초·
retry 0·입력 1,024자·출력 128 token·process sub-cap 20으로 제한하고, 기존 grounded
generation의 8초·1회·sub-cap 30과 합친 process cap을 40, local synthetic run 비용 stop
line을 VAT 포함 USD 0.05로 고정한다. exact schema written specification·실행계획·별도 local
D-092가 PII-free allowlisted actual classifier 실행을 승인했고 D-093은 offline classifier
runtime과 local 00680/00700/admin/Web 구현 검증을 기록했다. public/remote 시민 검증은
ADR-0026에 따라 provider-disabled와 admin-disabled가 기본이며 real citizen/free-input
provider 전송은 계속 금지한다.

2026-07-27 Q-PROD-REAL-001=A/D-088은 제품 목표를 **현실형 민원 안내·운영센터**로 확정한다.
자연스러운 구조화 대화, 승인된 공식 근거, 기관 연결, 범위 확대 검토와 사람 승인 개선 루프를
고도화한다. 실제 신청·상태조회·결제·정부24/기관 내부 시스템 연계는 현재 P2로 유지하며 이
제품이 처리 완료를 보장한다고 표현하지 않는다. 향후 실제 처리 플랫폼으로 바꾸려면 기관 API,
본인인증, 법무·개인정보, transaction·감사·보상과 production 배포를 별도 discovery/승인한다.

D-089/D-090의 CHAT-NATURAL 설계 1~2부는 privacy-first hybrid pipeline과 context v2를
승인했다. `CIVIC_SCOPE_GAP`은 public `intent=OUT_OF_SCOPE`+새 fallback reason, candidate
false이며 별도 queue에 마스킹 text만 30일 보관한다. NON_CIVIC·개인조회·법적판단·privacy
unresolved는 text/event/failed/review row 0이다. context v2는 topic/pending-slot/dialog-act
같은 closed server ID만 사용하고 raw transcript·프로필은 금지한다. exact contract/DB와
runtime은 D-091의 통합 written specification을 구현 권위로 사용한다.

D-091은 classifier/generator 오류·성능·60개 분류/5개 후속/7개 장애 acceptance와 세 수직
흐름을 확정했다. D-092는 PII-free allowlisted actual Upstage, local DB reset·immutable `.2`
정식 seed, `00680` scope queue와 ADR-0018의 `00700` public hardening, 구성된 remote 시민 경로
검증을 승인한다. secret·DSN·raw payload를 출력하지 않고 remote target을 추측하지 않는다.
인증 없는 public 관리자 경로는 승인 범위가 아니며 계속 fail-closed로 비활성이다. actual provider,
formal `.2` seed/19→20과 remote 작업은 unit/area gate 뒤 통합 명세의 비용·rollback·증거
경계를 따라 수행한다. local 00700은 exact 22 property-only 변경과 11-file pgTAP/11-stage
rollback·replay를 통과했지만 remote 배포 완료를 뜻하지 않는다.

2026-07-27 D-095 actual evidence에서 frozen 60 classifier는 deterministic 40/provider 20,
policy/privacy outbound 0, corrective 60/60으로 PASS했고 두 bounded run 누적 비용은 VAT 포함
USD 0.003873210이다. provider request/response와 key는 저장하지 않았다. 같은 시점 remote
discovery는 public application target, remote DB project, deployment credential/origin/saved
version을 찾지 못했다. 따라서 remote migration·seed·deploy·smoke는
`Not executed: target not configured`이며 local DB ACTIVE 20과 00700 evidence를 remote
production-ready로 해석하지 않는다.

2026-07-27 `CLASSIFIER-RUNTIME-WIRING-001`은 위 classifier adapter와 `ChatService` port가
실제 local `create_local_app()`에 조립되지 않았던 완료 판정 결함을 교정했다. exact
classifier-only/combined profile에서 ambiguous safe question만 classifier를 사용하며,
combined profile은 classifier 20/generator 30/combined 40의 같은 process ledger를 공유한다.
 NON_CIVIC·PERSONAL_LOOKUP·LEGAL_JUDGMENT·privacy/policy fast path는 provider 호출과 질문
 row가 계속 0이다. API 계약·DB·공식 데이터·public/remote 경계는 변하지 않는다.

2026-07-27 Q-RAG-001=A, Q-DATA-RAG-001=A와 D-096~D-102는 위 hybrid classifier를
**ACTIVE topic catalog와 coverage grounding을 사용하는 제한형 Hybrid RAG**로 개선하는 목표를
확정한다. current ACTIVE/OFFICIAL projection과 non-factual versioned coverage metadata의
교집합만 최대 20개 catalog로 만들고, exact approved·unique lexical·validated semantic
`topic_id+coverage_id`·validated context facet 중 하나가 있을 때만 top-1 KB를 사용한다.
모델은 답변·사실·출처·기관·저장 여부를 생성하거나 결정하지 못하며 서버가 current membership,
intent, coverage와 source를 다시 검증한다. vector/embedding, 새 dependency, DB migration,
official `.2` 수정과 다중 KB 합성은 이 구현 범위가 아니다.

generic certificate는 등본/초본/차이 3개로 시작하고 move/waste/tax의 generic 질문은 해당
intent의 bounded topic 선택지를 제시한다. 지역은 chat 입력창 위에 항상 표시하되 같은 탭
React memory에서만 새 대화 후 유지하고 browser/server storage에는 넣지 않는다. local
interactive provider target은 classifier 80/generator 100/combined 160, 3초/8초, retry 0,
concurrency 1, request hard wall 12초, VAT 포함 USD0.20 pre-reservation stop이다. historical
20/30/40·USD0.05 actual은 과거 evidence로 보존한다. D-103의 명세·계획 승인 뒤 Tasks 1~9
local/offline 구현과 독립 검토가 끝났고 D-104가 이를 통합한다. immutable official `.2`의
runtime ACTIVE/OFFICIAL 교집합은 19이며 metadata의 20번째 topic을 허위 ACTIVE로 만들지 않는다.
offline UAT는 48/48, official 57/57, classifier 60/60, focused 91 PASS·skip 0이다. Task 10
PII-free Upstage actual은 정확히 한 번 실행해 20 selected·skip 0·11 provider-free·9 outbound를
기록했지만 strict accepted usage와 provider match가 0이라 FAIL했고 재실행하지 않았다.
2026-07-28 D-106의 별도 승인으로 prior FAIL을 archive하고 value-free failure-stage counters를
추가한 source `1f337ad`에서 corrective actual을 정확히 한 번 더 실행했다. 9/9 outbound는 모두
HTTP response를 받았지만 전부 4xx class였고 2xx·5xx·transport/timeout·usage parse·closed
decision·route/topic match는 0이었다. 따라서 provider client-rejection 단계까지는 진단됐지만
auth/access/request-shape/quota 중 정확한 원인은 보관하지 않은 body/status detail 없이
단정하지 않는다. corrective 결과도 FAIL이며 추가 실제 호출은 새 승인 전 금지한다.
Q-LLM-013=A/D-107은 closed selector prompt의 누락된 명시적 `JSON만` 지시만 TDD로 복원했다.
source `4cb42ff`의 단 한 번 corrective actual은 동일 20 selected·11 provider-free·9 outbound에서
9/9 HTTP 2xx와 accepted usage, 4xx/5xx/transport 0을 기록해 D-106의 request-validation 4xx를
해소했다. 그러나 strict closed decision accepted와 route/topic match는 0/9이므로 전체 결과는
여전히 FAIL이고 재실행하지 않았다. 본문 비보관 경계 안에서 정확한 response-validation 단계는
A-071로 남으며 local runtime은 fail-closed fallback을 유지한다.
D-108은 A-071의 후속으로 production parser가 fixed terminal enum 하나만 optional observer에
전달하고 runner가 aggregate count만 기록하는 value-free 진단 설계를 승인했다. body·status
detail·exception·key·DSN과 per-fixture stage는 기록하지 않는다. public parser·시민 fallback·
prompt·provider profile·API/DB/data/dependency는 불변이며 written spec 확인 전 구현과 provider
call은 0이다.
D-109는 위 written specification과 RED/GREEN inline plan을 승인했다. contract-stage parser,
production enum-only observer, aggregate runner, clean source commit, fixed exact-one actual
순으로 실행하며 actual 전까지 prompt/profile/API/DB/data/dependency는 고정한다.
D-110은 A-071의 code/test/runner 구현을 완료했다. production parser는 HTTP response마다
13개 fixed terminal enum 중 하나만 optional observer에 전달하고, observer 오류는 시민
decision/fallback을 바꾸지 않는다. runner는 전체 aggregate count만 기록하며 per-fixture stage,
질문·provider body·status detail·exception·key·DSN은 기록하지 않는다. 142개 집중 테스트와
Ruff/Mypy가 통과했고, clean source commit 뒤 exact-one actual만 남았다.
D-111은 clean source `0646db0`에서 승인된 exact-one actual을 실행했다. 20 selected·0 skip·
11 provider-free·9 outbound, HTTP 2xx/strict usage/stage total은 모두 9였고 9건 전부
`KEY_SET_REJECTED`에서 종료했다. accepted decision/match 0이라 전체 acceptance는 FAIL이며
재실행하지 않았다. 비용은 VAT 포함 USD 0.002626503이고 local ignored modes false/false,
lock 0, 질문·provider body·status detail·key·DSN 보관 0이다. A-071은 원인 단계 진단으로
해결됐고 exact five-key 교정과 새 actual gate는 A-072다.
D-112/Q-LLM-014=A는 A-072의 provider-only wire를 strict Upstage `json_schema`로 확정한다.
응답은 `route`, `intent`, `topic_id`, `coverage_id`, `pending_slot` 다섯 required string만
허용하고 nullable 의미는 고정 `NONE` sentinel로 표현한 뒤 서버가 기존 내부 `None`으로
정규화한다. public classifier/chat 계약, DB/data/dependency와 서버 소유 출처 결합은 바뀌지
않는다. 상세 설계 승인 전 제품 코드와 provider call은 0이고 corrective actual은 구현·offline
검증 후 별도 인간 gate다.
D-113은 사용자의 `설계 1부 승인`으로 위 provider wire와 서버 권위 경계를 확정했다. nullable
대상은 `intent`, `topic_id`, `coverage_id`, `pending_slot`이며 exact `NONE`만 내부 `None`으로
바꾼다. 동적 catalog 값은 schema에 복제하지 않고 기존 server validation이 판정한다. 설계 2부와
written specification 승인 전 code/provider call은 0이다.
D-114는 사용자의 `설계 2부 승인`으로 provider-only normalization, fixed-stage 오류 처리,
TDD·version·actual gate를 승인하고 A-072 integrated written specification을 Review로 게시했다.
정확한 문제는 provider HTTP·JSON은 성공하지만 exact canonical key set이 9/9 불일치해 기존
strict server가 모두 폐기한다는 것이다. 이번 교정은 schema/prompt/wire adapter만 바꾸고
public API/DB/data/dependency는 보존한다. 실제 호출은 offline/root gate와 clean source 뒤
별도 승인 전 0이다.
D-115는 사용자의 `명세 승인`으로 A-072 written specification을 Approved로 전환하고
provider wire parser→canonical prompt→strict schema transport→area/version integration→
root/clean-source gate의 exact TDD Tasks 1~5 plan을 Review로 게시했다. Task 6 actual은 plan
승인에 포함되지 않으며 Tasks 1~5 PASS 뒤 별도 exact 승인이 필요하다. code/provider call,
API/DB/data/dependency, push/merge는 아직 0이다.
D-116은 사용자의 `계획 승인, 1번으로 구현 시작`으로 Tasks 1~5와 Subagent-Driven 실행을
승인했다. provider-only exact `NONE` parser, bounded canonical prompt와 fresh strict schema를
TDD로 구현했고 area 333·controlled-double runner 24·Ruff/Mypy 115 PASS를 확인했다. application
`0.12.3`, prompt `0.4.2`, tests `2.1.6`으로 전진했지만 API/contracts/DB/data/dependency와
provider actual call/cost는 0이다. Task 5 clean-source review는 완료됐지만 root wrapper는 단
1회 실행 중 environment-only `PREFLIGHT-UV reason=exception code=2`에서 FAIL했고 재실행하지
않았으므로 PASS가 아니다. 나머지 constituent·security·scope 검사는 documented skip을 제외하고
PASS했다. provider call/cost는 계속 0이며 실제 1회 호출은 D-117의 별도 exact 문구
`A-072 corrective actual 1회 실행 승인` 전까지 금지한다.
D-117은 위 exact 승인 뒤 clean source `efc0b34`에서 A-072 corrective actual을 정확히 한 번
실행했다. 20 selected·0 skip·11 provider-free·9 outbound, privacy/policy outbound 0,
HTTP 2xx·strict usage·terminal stage total 9를 기록했고 D-111의 `KEY_SET_REJECTED`는 0으로
해소됐다. 그러나 9건 모두 `ENUM_SHAPE_REJECTED`, accepted/match 0이라 최종 acceptance는
FAIL이다. retry 0, 비용은 VAT 포함 USD 0.002496648로 cap USD 0.20 미만이며 재실행하지
않았다. 질문·provider body·status detail·key·DSN 보관 0, lock 0, local modes false/false다.
따라서 시민 runtime은 계속 결정론적 fail-closed 경로가 권위이고, 다음 교정 actual은 새
인간 결정·별도 승인 전 금지한다.
D-118은 A-073의 다음 최소 교정으로 explicit route matrix, exact uppercase `NONE`,
same-row topic/coverage와 route·intent·pending-slot·identifier·route-shape의 value-free
first-failure aggregate를 승인했다. D-119의 `명세 승인`으로 written specification은
Approved이며 Tasks 1~5 TDD plan은 Review다. configured safe-question max 1,024와
complete-message 4,096 guard는 유지하고 actual-eligible 20-topic/256-character prompt만
guard 통과를 요구한다. 초과 complete message는 질문/catalog 절단 없이 provider 전에
fail closed한다. 이 checkpoint에서 application/prompt/tests/API/contracts/DB/data/dependency와
provider call/cost는 불변이며 Task 6 actual은 별도 exact 인간 승인 전 금지한다.
D-120은 사용자의 exact `계획 승인, 1번 Subagent-Driven으로 구현 시작`으로 A-073 Tasks 1~5
offline plan을 승인했다. Tasks 1~4에서 shared typed builder·five refined value-free stage,
explicit route matrix·literal `NONE`·intent-grouped catalog와 production-wire oracle을
TDD로 구현했다. D-121의 final review fix와 scoped re-review는 누락됐던 네 provider intent의
contiguous vocabulary, adjacent first-failure precedence와 selected-question/provider-body/
invalid-value 비보관 증거를 보강했고 area 397·controlled-double 39·Ruff/Mypy 115가 PASS했다.
final governed prompt는 4,067자, guard margin은 29자다. baseline-stale
controlled mock의 JSON null 1건은 RED 뒤 exact wire `"NONE"`으로만 교정했다. application
`0.12.4`, prompt `0.4.3`, tests `2.1.7`, docs `2.30.7`만 전진하며 API/contracts/Web/DB/data/
dependency와 provider/network actual call/cost는 0이다. A-073은
offline scoped review까지 닫혔다. Task 5 root wrapper는 exact 1회 호출했지만 shell harness timeout 124로
final stdout/exit를 회수하지 못해 aggregate를 `NOT VERIFIED/FAIL`로 기록하고 재실행하지 않았다.
독립 docs/secret/diff/status는 PASS, provider/network actual call/cost는 계속 0/USD 0이다.
현재 종료 지시에 따라 Task 6 A-073 corrective actual은 실행하지 않았고 기존 Upstage actual도
재실행하지 않았다.

2026-07-29 Q-LLM-PROVIDER-001=A/D-122/ADR-0028은 질문 분류 공급자 역할만 좁게 보완한다.
`CLASSIFIER_PROVIDER`로 `disabled|upstage|deepseek`를 명시 선택하며 DeepSeek exact
`deepseek-v4-flash`는 `sejong_ai_api.local.create_local_app`의 loopback local/private
classifier에만 사용한다. public `sejong_ai_api.main`, remote DB와 실제 시민 운영에는
연결하지 않는다. 기존 Upstage classifier와 ADR-0023의 grounded final answer generator는
삭제·교체하지 않는다. exact five-string/uppercase `NONE`, deterministic PII/policy/obvious
route, shared parser·ACTIVE/OFFICIAL grounding·server-owned source와 무보관 경계는 불변이다.
DeepSeek `json_object`는 신뢰 경계가 아니며 3초·retry0·concurrency1·output128,
temperature0/thinking disabled와 보수적 USD0.20 cap을 적용한다. 새 A-074 offline wrapper
1회와 clean-source review 뒤 고정 synthetic 20 actual lease 1회만 승인됐고, PASS/FAIL과
무관하게 자동 재실행하지 않는다. A-073 root/Upstage actual은 이 작업에서 재사용·재실행하지
않는다.

2026-07-29 A-074 offline Tasks 1~6b로 selector/settings, DeepSeek strict transport,
provider별 보수 비용·usage, local composition과 one-shot runner/wrapper를 구현했다. Initial
integrated pre-gate review의 Critical 0 / Important 5 `NOT READY`와 후속 compressed-decoding
Important 1을 두 RED/GREEN wave로 닫았고, 최종 fresh review는 Critical 0 / Important 0 /
Minor 0 `READY`였다. Recursive duplicate-key 거부, identity/raw `<64 KiB` bounded
streaming, complete exchange 3초·aggregate 32초 deadline, exact-byte/pre-lease TOCTOU
재검증, nonzero `taskkill`·post-child source drift fail-closed가 현재 경계다.
public main·API/contracts/Web/DB/data/dependency는 변경하지 않았다.

D-123에서 hardened source `9c7f818123533a4adc61d3953ed4d4630c793891`의 A-074 offline
wrapper를 exact-one 소비했고 immutable outcome은 `FAIL`이다. Exit 1, timed_out false,
invocation/rerun 1/0, stdout/stderr 475/0 bytes, first failing governed stage `TEST-ROOT`를
aggregate evidence로 보존하며 wrapper는 재실행하지 않는다. Standalone 434-test 진단은
expected environment map과 기존 안전 tracked classifier 설정 사이 repository-truth mismatch
1건을 찾았고 test-only +4 교정 뒤 exact PASS와 full `434 OK / skipped 2`, corrective review
C0/I0/M0를 확인했다. 이 교정은 gate FAIL을 소급 변경하지 않는다. 따라서 DeepSeek actual은
blocked/unexecuted invocation/rerun 0/0이고 report/lease·outbound·token·cost는 모두 0이다.
A-073 root `NOT VERIFIED/FAIL`, invocation/rerun 1/0도 그대로다.

2026-07-29 D-124/D-125의 A-075 corrective evidence는 A-074를 덮어쓰지 않는 새
identity다. Source `982198faed073a6c4e04205f5b3dde3f95ebae20`의 A-075 offline gate는
exact-one `PASS`, exit0·timed_out false·invocation/rerun1/0이다. Network-free readiness도
PASS한 뒤 DeepSeek actual lease를 정확히 한 번 소비했으나 acceptance는 `FAIL`이다. Fixed
20/0과 deterministic/provider 11/9, policy/privacy outbound0은 맞았지만 outbound9 모두
HTTP 응답 전 `transport_no_response`였고 provider response·2xx·parse·accepted·oracle match와
observed token은 모두 0이다. 보수적 worst-case 비용은 USD0.02306304<0.20이며 실제 청구액으로
간주하지 않는다. 질문·masked question·request/response body·invalid value·secret 보관은
모두 0, retry/rerun0, permanent report/lease 존재 상태로 종료한다. 원인은 transport 단계로만
한정하며 DNS/TLS/proxy/timeout 중 무엇인지 추측하지 않는다. 실제 classifier 활성화 성공이나
public/remote/free-input 승격 근거로 사용하지 않는다.

Task 11 local/private 마감은 browser 27/27, API 2,357 pass·8 local-DB skip, contracts 96/96,
Mypy 114와 secret/bundle/protected diff 0으로 완료했다. 단 한 번의 final aggregate wrapper는
FORMAT-API에서 exit 1이므로 PASS로 승격하지 않으며, formatter 교정 뒤 당시 미실행 constituent는
모두 별도 PASS했다. public/remote, DB reset/seed, official `.2` 수정과 자동 merge는 아직
완료가 아니다. 상세 권위는 ADR-0027과
`2026-07-27-bounded-hybrid-rag-conversation-design.md`다.

## 4. 변경 절차

제품 범위, 공개 계약, DB, 개인정보, 외부 공급자, 배포 아키텍처가 바뀌면:

1. 인간 승인
2. ADR 또는 결정 로그
3. source-of-truth 갱신
4. 계약/스키마/테스트 갱신
5. 버전 매니페스트 갱신
6. 구현 노트 기록

## 5. Legacy 사용 규칙

- 코드를 재사용하기 전 현재 계약·보안·범위와 비교한다.
- 오래된 엔드포인트/데이터/범위를 그대로 복구하지 않는다.
- 재사용한 코드의 출처와 변경 이유를 구현 노트에 기록한다.
- legacy 자체는 자동 포맷·대규모 수정하지 않는다.
