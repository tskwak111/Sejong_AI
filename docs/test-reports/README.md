# Test reports

표본 평가, 회귀, 접근성, 성능 보고서를 버전과 실행환경과 함께 보관한다.

## 현재 보고서

- [MVP-001 표본 20 deterministic 평가](MVP-001-SAMPLE-20-RESULT.md) — canonical T-01~T-20,
  20/20 outcome과 exact-matrix meta를 포함한 pytest 21 PASS/skip 0; provider·public·HTTP UI QA 아님
- [LLM-002 Upstage `solar-pro3` 합성 평가 — local FAIL / 시민 연결 미승인](LLM-002-UPSTAGE-SYNTHETIC-EVALUATION.md)
  — 30 outbound attempts, strict-schema 27/30, 인간 검토 9개 평균 4.8444, 비용
  USD 0.004654815(VAT 포함); option B/public/free-input은 계속 금지
- [DB-001 local baseline — local verified / public blocked](DB-001-LOCAL-BASELINE.md) — Supabase/PostgreSQL 환경,
  6+6 lineage hash, 과거 pgTAP 282·integration 8/8·rollback/replay와 현재 D-031 구현 local/
  D-046 deferred `00700` public-release block
- [DATA-SEED-002 actual disposable DB — local PASS](DATA-SEED-002-LOCAL-VERIFICATION.md) — immutable
  `.2` 19/3/10 seed와 cleanup PASS; 이후 별도 actual loop가 final ACTIVE 20을 복원, public/remote 아님
- [DATA-SEED-001 actual disposable DB — blocked](DATA-SEED-001-LOCAL-VERIFICATION.md) — `.1`
  filesystem release/dispatcher는 verified, actual PostgreSQL은 seed write 전 grantor-option union 대
  immutable single-row guard 충돌로 Blocked; DATA-SEED-002의 불변 predecessor로 보존
