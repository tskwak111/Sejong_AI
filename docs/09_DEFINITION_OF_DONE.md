# Definition of Done

## 모든 작업 공통

- [ ] 요청과 인수 기준이 명시됐다.
- [ ] source-of-truth/ADR와 충돌하지 않는다.
- [ ] 테스트 또는 대체 검증 증거가 있다.
- [ ] diff를 스스로 검토했다.
- [ ] 오류·빈 상태·경계 조건을 처리했다.
- [ ] 개인정보·보안·데이터·접근성 영향을 검토했다.
- [ ] 계약·스키마·문서·버전을 동기화했다.
- [ ] 구현 노트와 INDEX를 갱신했다.
- [ ] 인간이 알아야 할 내용과 내부 세부를 분리해 보고했다.

## 사용자 기능

- [ ] 로딩/성공/FOLLOWUP/FALLBACK과 HTTP 503 SYSTEM_ERROR가 구분된다.
- [ ] 출처는 서버 메타데이터다.
- [ ] mobile 390/430과 키보드 접근을 확인했다.
- [ ] mock 데이터는 배지로 구분된다.
- [ ] `/`에서 4개 지원 분야·서비스 한계·`/chat` 진입이 검증됐다.
- [ ] current-tab 대화는 동작하고 새로고침 후 사라지며 token이 브라우저 저장소·로그에 남지 않는다.

## API/DB

- [ ] 입력/출력 schema validation
- [ ] Supabase migration reset/replay와 명시적 보상 rollback/replay
- [ ] raw question persistence 0
- [ ] approval invariant enforcement
- [ ] health/readiness
- [ ] idempotency/transaction 경계 검토
- [ ] OpenAPI 3.1.0-draft와 JSON Schema가 `session_id` 거부·FALLBACK null context·
  사유별 불변조건·HTTPS 전용 URL·FALLBACK 추가 필드 거부와 optional UUID `Idempotency-Key`를 같은 fixture로 검증
- [ ] Upstage 합성 평가 경로의 exact model/config·30-attempt cap·concurrency 1·hidden retry off 검증

## 데이터

- [ ] 출처·확인일·상태·작성/승인자
- [ ] data version과 lineage
- [ ] official/mock 분리
- [ ] 영향 테스트 갱신

`구현 노트가 없다` 또는 `검증 결과가 없다`면 완료가 아니다.
