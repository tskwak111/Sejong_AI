# RFP 요구사항 대응표

> Q-MVP-001/D-058의 2026-07-25 local/private 마일스톤은 P0 핵심 흐름과 QUR-002 표본 20·회귀
> 1·최소 접근성/보안 gate를 먼저 완료한다. PER-002 100명, 자동 백업, public deployment와
> 고급 UI/외부 LLM 품질 평가는 7월 25일 뒤로 이동하지만 이 표의 최종 P1 요구에서 삭제되지 않는다.

> **P0**: 대표 흐름과 인수 기준에 직접 연결되는 필수 구현  
> **P1**: 핵심 흐름을 보조하며 이번 프로젝트에서 확정 구현·검증  
> **P2**: 외부 시스템·추가 검수·운영환경이 필요한 확장 로드맵

| ID | 요구사항 | 제안 기능 | 구현 수준 | 검증 방법 | 비고 |
| --- | --- | --- | --- | --- | --- |
| SFR-001 | 자연어 질의응답 | 4개 우선 분야의 일상어 질문을 request-local ACTIVE/OFFICIAL topic에 연결하고 구조화 답변과 출처 제공 | P0 실제 구현 + LLM-003 actual + bounded Hybrid RAG offline PASS / historical D-117 Upstage selector actual FAIL | historical generated/template actual 10/10·출처 10/10, synthetic UAT 48/48, official examples 57/57, D-117 actual 20 selected·9 outbound·strict accepted 0 | immutable `.2` runtime 교집합 19, top-1만 사용. D-117 Upstage selector actual은 재실행하지 않았고 public/remote 금지 |
| SFR-002 | 민원 의도 분류 | 전입·주민등록, 증명서, 대형폐기물, 지방세, 범위 밖과 topic/coverage를 closed enum으로 분류 | P0 실제 구현 + selectable classifier; A-078 hardened split-timeout verification in progress | frozen classifier 60/60, Hybrid UAT route/intent/topic 48/48, A-076 actual transport-no-response9; A-077 offline PASS 1/0 and provider0; A-078 clean-source evidence pending | 모호 질문은 exact FOLLOWUP, topic 없음은 INSUFFICIENT_GROUNDING. local/private selector만 허용하고 final answer 생성은 Upstage 유지. A-078은 connect3/read+complete10초의 exact-lease 1-call 2xx probe 뒤에만 9-call actual을 허용한다 |
| SFR-003 | 절차·서류 안내 | 신청 방법, 필요 서류, 처리 기간, 수수료, 담당 기관 카드 | P0 실제 구현 | 민원별 필수 필드 표시 여부 전수 점검 | 해당 정보가 없는 필드는 공란 대신 공식 확인 필요 표시 |
| SFR-004 | 기관·담당 연결 | 아름동·도담동·조치원읍 직접 선택과 민원 유형을 조합해 공식 기관 카드 표시 | 대체·부분 구현(P0) | 지역×민원 매핑 케이스와 공식 기관 데이터 확인 | GPS·거리 기반 가까운 기관 계산은 P2 |
| SFR-005 | 대화형 후속질문 | domain 또는 intent별 ACTIVE topic 선택지와 현재 탭의 15분 서명형 문맥 token으로 연속성 제공 | P0 실제 구현 | certificate/move/waste/property-tax exact option·pending-slot 4/4, context 4/4, Web 68와 E2E 27/27 | 후속질문은 실패 질문으로 저장하지 않음; 서버 세션·raw transcript 저장 없음 |
| SFR-006 | 폴백 처리 | 근거 부족·개인 조회·법적 판단·지원 범위 밖의 4개 행정-domain 사유와 별도 `PRIVACY_UNRESOLVED` 안전 재질문 | P0 실제 구현 | 폴백 질문 8개와 마스킹 불능 표본에서 사유·행동·후보/저장 경계 평가 | 근거 부족만 KB 후보 가능; privacy outcome은 실패 질문 행 없음 |
| SFR-007 | 신청 상태 조회(선택) | 본인 인증 및 내부 행정 시스템 연계 후 구현 | P2 로드맵 | 연계 전제·API 경계·개인정보 처리 계획 설명 | MVP에는 mock 상태조회도 넣지 않음 |
| SFR-008 | 다국어·음성(선택) | 영어·중국어·베트남어, 음성 입력·읽기, 고령자 모드 | P2 로드맵 | 확장 조건과 사람 검수 체계 제시 | MVP 핵심 흐름 완성도 우선 |
| DAR-001 | 행정 지식베이스 | 4개 분야별 세부 주제 단위 공식 KB 20건, 출처대장과 승인 상태 관리 | P0 실제 구현 | staging 20건 전수 검수, 초기 ACTIVE 19건+WASTE-03 보류, REG-001 뒤 최종 ACTIVE 20건 점검 | 시민 답변은 ACTIVE만 검색; hash-bound PM manifest와 immutable release 사용 |
| DAR-002 | 기관 정보 | 아름동·도담동·조치원읍 공식 행정복지센터 데이터와 10~12개 민원 매핑 | P0 실제 구현 | 기관명·주소·전화·출처·기준일 점검 | 시민 화면에는 공식 정보만 표시 |
| DAR-003 | 대화 로그 | 모든 요청은 질문 원문 없이 이벤트 메타데이터 저장, 적격 실패 질문만 마스킹 텍스트 추가 | P0/P1 실제 구현 | DB·액세스 로그·관리자 화면에서 원문 미저장 확인 | 지원 범위 밖·privacy unresolved는 텍스트/실패 행 없이 이벤트만 기록 |
| SIR-001 | 공공데이터 연계 | CSV/DB 입력과 공급자별 어댑터 경계 설계 | P2 로드맵 | 인터페이스·동기화·변경 감지 설계 검토 | MVP는 수동 검증 데이터 |
| SIR-002 | 지도·위치 API | 지역 선택과 공식 지도 링크 제공 | 부분 구현(P0)+P2 | 기관 카드와 링크 동작 확인 | 내장 지도·GPS·거리 정렬은 P2 |
| PER-001 | 평균 응답시간 3초 | 평균·p95·오류율 측정, 캐시·템플릿 폴백 | P1 확정 검증 | 표본 요청의 평균·p95 기록 | 외부 LLM 상태에 따른 병목 공개 |
| PER-002 | 동시 사용자 100명 | 100 VU·60초 제한 스모크: read-only harness preflight 뒤 cached/fixed chat | P1 실행계획 Ready / chat DB-write gate Pending | locked Python/httpx aggregate의 request·error rate·average·p50·p95·max 기록 | Phase A provider-off·DB write 0. Phase B는 A-052 인간 선택 전 HOLD; 실서비스 용량 보증이 아닌 구조 검증 |
| SER-001 | 개인정보 최소수집 | 외부 LLM 호출 전 마스킹, 원문 DB 미저장, 앱 DB IP·기기ID 미수집 | P0 실제 구현 + LLM-003 actual + offline privacy UAT PASS | historical PII-free actual 10건 forbidden-value 0; synthetic phone-shaped MOVE canonical 값 provider/repository/response/report 0; Task 10 report의 question/provider content/key/DSN 0 | Task 10 actual도 PII-free 20만 사용했고 privacy/policy outbound 0; public/remote/실제 기관 운영 금지 |
| SER-002 | 비식별화 | 이름·주민번호·전화·이메일·상세주소·차량번호·접수번호 등 보수적 마스킹과 마스킹 불능 전용 safe-rephrase | P0 실제 구현 | PII 포함 테스트·provider payload·30일 expires_at·`PRIVACY_UNRESOLVED` no-text/no-row 확인 | PII 누락 방지 우선; 완화는 품질 근거와 인간 재승인 필요 |
| SER-003 | 환각 방지 | 출처 없는 직접 답변 금지, 서버가 KB 메타데이터를 출처 카드로 결합 | P0 실제 구현 | 출처 표기율 100%, 근거 부족 폴백 검사 | LLM이 출처명·URL을 생성하지 않음 |
| QUR-001 | 접근성 | 쉬운말 사전, 16→20px 큰 글씨, 본문 대비 4.5:1 이상, 키보드 포커스 | P1 확정 구현 | 390/430px, 200% 확대, 명도 대비, 키보드 모달 점검 | 별도 고대비 토글 대신 기본 대비 준수 |
| QUR-002 | 정확성 점검 | 표본 20개 + 개선 전후 회귀 + bounded synthetic 48-case | P1 확정 검증 | sample 20/20, official 57/57, classifier 60/60, Hybrid UAT 48/48·focused 91/91 skip 0 | synthetic/local 결과를 전체 민원·public 정확도로 일반화 금지 |
| COR-001 | 근거 기반 | ACTIVE KB 검색, 후속질문, 안전 폴백, 사람 승인 | P0 실제 구현 | 정상·모호·폴백·승인·재질의 통합 테스트 | 핵심 차별점 |
| COR-002 | 모바일 우선 | /, /chat, /admin 3페이지 반응형, 탭·카드·모달 통합 | P0 실제 구현 | 390px·430px 가로 스크롤/겹침 0건 | 데스크톱 관리자 화면 병행 |
