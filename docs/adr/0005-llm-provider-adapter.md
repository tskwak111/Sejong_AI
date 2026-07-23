# ADR-0005: DeepSeek LLM 공급자 어댑터와 합성 시연 경계

- Status: Superseded by ADR-0022 for provider/model selection
- Date: 2026-07-13 (updated 2026-07-14 by Q-LLM-001, Q-LLM-002, Q-LLM-003, Q-LLM-004)

> 2026-07-23 Q-LLM-005=A로 실제 구현 전 공급자를 Upstage `solar-pro3` 합성 평가로
> 변경했다. 아래 내용은 DeepSeek 선택의 역사 기록이며, provider abstraction·합성 전용·cap·
> deterministic fallback·서버 출처 결합 원칙은 ADR-0022가 승계한다.

## Decision

도메인 로직은 특정 LLM SDK에 직접 의존하지 않는다. adapter interface와 disabled/template fallback provider를 제공한다. 실제 호스팅 공급자는 사용자가 보유한 기존 DeepSeek API 잔액을 사용하며 새 충전·자동 충전은 하지 않는다. 키는 서버 환경변수에만 두고 값·잔액을 저장소, 문서, 브라우저, 로그에 기록하지 않는다.

DeepSeek 호출은 local/private 환경에서 서버가 allowlist로 검증한 합성 fixture에만 허용한다. 클라이언트의 `is_test` 표시는 신뢰하지 않는다. 실제 시민 자유 입력, 실제 개인정보·민감정보, 공개 환경 요청은 마스킹 여부와 무관하게 DeepSeek로 보내지 않고 disabled/template 경로만 사용한다. 공개 운영이나 실제 시민 입력은 개인정보 처리 고지·국외 처리·보관·법적 근거를 별도 승인한 뒤 새 ADR로 재검토한다.

DeepSeek API의 context caching은 기본 활성화되어 입력 prefix가 디스크에 기록되고 미사용 cache가 보통 수 시간~수일 유지될 수 있다. API 문서에서 cache 비활성화, no-training, Zero Data Retention, 한국 리전, 전체 prompt의 고정 보관기간은 확인되지 않았다. 따라서 합성 fixture도 백엔드 마스킹을 거치고 ACTIVE KB 최소 청크만 보내며 `user_id`에는 개인정보 없이 비식별 난수만 사용한다.

새 구현은 정확히 `deepseek-v4-flash`를 사용하고 `deepseek-chat`·`deepseek-reasoner` 같은 legacy alias와 다른 model ID를 설정 검증에서 거부한다. thinking은 비활성화하고 `max_tokens=1024`, JSON object mode를 강제한다. 동시 외부 호출은 1개, 논리 요청당 최초 1회와 재시도 최대 1회로 제한하며 HTTP client/SDK의 숨은 자동 재시도는 끈다.

한 번의 명시적 local 평가/데모 process run에서 실제 외부 전송을 시도한 횟수는 재시도·timeout·연결 실패·429·empty·truncated·schema-invalid를 모두 포함해 총 30회를 넘지 않는다. 네트워크 전 원자적으로 횟수를 예약하고, 30회를 소진하면 31번째 요청과 재시도를 보내지 않는다. 시작 시 model 조회, 잔액 조회, 결제·자동 충전, counter reset endpoint는 구현하지 않는다. process 재시작은 새 run이라는 사실을 runbook과 결과에 기록한다.

JSON Output은 서버 schema 검증을 통과해야 한다. cap 도달이나 provider 장애 자체는 503 사유가 아니다. ACTIVE KB가 충분하면 서버 template SUCCESS, 근거가 부족하면 정책 FALLBACK을 HTTP 200으로 반환하며, KB/template/필수 의존성까지 불능일 때만 ADR-0009의 503을 사용한다. disabled/template provider는 실제 공급자 선택 후에도 장애 대체 경로로 유지한다.

## Consequences

초기 코드와 테스트 fixture gate가 늘지만 비용, 장애, 모델 교체, 보관정책 변화에 대응할 수 있다. 최종 계획 승인 전에는 SDK/HTTP 연동 설치, 비밀 입력, 네트워크 호출을 하지 않는다. 승인 후에도 `DEEPSEEK_ENABLED=false`가 기본이며, 명시적 synthetic evaluation mode와 서버 fixture allowlist가 함께 만족할 때만 호출한다. 로그에는 model, attempt/retry 수, latency, outcome, token usage 같은 비텍스트 지표만 허용하고 질문·provider body·reasoning·잔액·키는 금지한다. DeepSeek 약관·모델·가격·캐시 정책은 변경 가능하므로 구현 시작과 데모 전 공식 문서를 다시 확인한다.

## Official references checked 2026-07-14

- Models/pricing and alias retirement: https://api-docs.deepseek.com/quick_start/pricing/
- JSON Output limits: https://api-docs.deepseek.com/guides/json_mode/
- Default disk cache: https://api-docs.deepseek.com/guides/kv_cache/
- `user_id` privacy rule: https://api-docs.deepseek.com/quick_start/rate_limit/
- Open Platform developer obligations: https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html
