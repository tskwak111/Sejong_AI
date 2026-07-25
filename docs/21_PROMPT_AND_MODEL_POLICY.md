# 프롬프트·모델 정책

## 원칙

- 합성 평가와 승인된 local/private 시민 chat 목표 모델은 정확히 Upstage `solar-pro3`이며
  서로 다른 명시적 mode로 분리한다. 합성 평가는 max output 1024, concurrency 1, retry 최대
  1회, process run당 outbound attempt 30이고 D-071 actual FAIL로 종료했다. 시민 chat 목표는
  timeout 8초, logical attempt 1, hidden retry 0, concurrency 1, process cap 30이다.
- 프롬프트는 파일/모듈로 버전 관리하고 코드에 장문 문자열로 흩뜨리지 않는다.
- 구조화 출력은 JSON Schema/Pydantic validation을 통과해야 한다.
- 모델이 source title/url/verified date를 만들지 않는다.
- 모델의 confidence는 근거 충족 판정의 유일한 기준이 아니다.
- 낮은 temperature/생성 자유도와 명확한 context boundary를 사용한다.
- D-072/D-073의 local/private 시민 chat은 supported intent·안전 마스킹·ACTIVE/OFFICIAL
  검색·근거 gate를 모두 통과한 현재 질문만 허용한다. public/remote/실제 기관 운영은
  disabled/template 경로다.

## 입력 허용

- 마스킹된 질문
- 지원 intent/policy
- ACTIVE KB의 필요한 필드/청크
- 출력 schema
- 개인정보 없는 비식별 run/attempt ID

## 입력 금지

- raw PII
- 비밀키/내부 지침 전문
- 승인되지 않은 candidate를 공식 근거처럼 전달
- 무관한 전체 DB dump
- 클라이언트 `is_test`만 근거로 허용한 자유 입력
- 실제 시민·실제 PII·민감정보·비밀이 든 identifier

## 출력 검증 실패

1. 시민 chat에서는 생성 결과 전체 폐기, provider retry 0
2. KB가 충분하면 서버 템플릿 SUCCESS
3. 근거가 없으면 provider call 0과 안전 폴백
4. 질문 원문 없이 provider/error metric 기록

## Upstage 합성 평가 adapter 기준

- 정확한 모델은 `solar-pro3`, base URL은 `https://api.upstage.ai/v1`로 pin하고 다른 값은
  설정 검증에서 거부한다.
- 기존 `httpx`로 OpenAI-compatible chat completion을 직접 호출하며 새 SDK/dependency를 추가하지 않는다.
- output은 strict JSON Schema/Pydantic validation을 통과해야 하고 추가/source 필드는 거부한다.
- empty content, truncation, 429, schema invalid를 별도 계측하며 raw payload는 기록하지 않는다.
- ACTIVE/OFFICIAL KB 최소 청크와 output schema만 전달한다.
- 모든 호출에 `max_tokens=1024`를 강제하며 client/route 값으로 덮어쓸 수 없다.
- app 외부 호출 concurrency는 1, 논리 요청당 최초 1회+재시도 최대 1회다. HTTP hidden retry는 0이다.
- 한 명시적 process run에서 timeout·연결 실패·429·empty·truncated·schema-invalid와 재시도를
  포함한 실제 outbound attempt 총 30을 네트워크 전 원자적으로 예약한다. cap 30이면 새
  전송·재시도는 0이다.
- health/readiness/startup preflight는 provider를 호출하지 않는다. model list·결제·잔액 조회·
  자동 충전·counter reset endpoint를 구현하지 않는다.
- cap/429/잔액 부족은 시민 API의 503 사유가 아니며 기존 ACTIVE KB template SUCCESS 또는
  정책 FALLBACK은 독립적으로 유지한다.
- 출처명·URL·확인일, intent/status/candidate eligibility는 provider 결과를 버리고 서버가
  deterministic policy와 KB metadata로 결합한다.
- D-072/D-073은 local/private 시민 chat만 별도로 승인했고 상세 TDD 계획은 Review다.
  public/remote/실제 기관 운영은 여전히 별도 승인이 필요하다.

## Upstage local/private 시민 chat 목표 기준

- 마스킹된 현재 질문, 서버 확정 intent, 답변에 필요한 최소 ACTIVE/OFFICIAL fact와
  server-issued ID만 전달한다.
- 모델은 최대 500자 summary와 procedure/document/time/fee/department ID만 제안한다.
- 서버는 ID를 공식 KB text로 치환하고 source/office/status/policy를 직접 결합한다.
- unknown/duplicate/missing ID, PII, 새 URL·번호·날짜·금액·행정 단정은 전체 TEMPLATE로 닫는다.
- `Idempotency-Key`가 있으면 엄격히 검증된 최종 안전 응답만 기존 논리 TTL 24시간 재생용으로
  저장할 수 있다. 질문·prompt·provider body·context/correlation 저장은 금지한다.

## 버전

prompt set의 모든 변경은 다음을 기록한다.

- prompt version
- model/provider
- evaluation set version
- before/after KPI
- known regression
- rollback template

Upstage 공식 model/API·가격 기준은 구현 시작과 actual 직전에 재확인한다. 개인정보 처리방침
페이지는 2026-07-25 확인했고 `Last Revised: May 21, 2026`로 표시됐다.
