# 위험 레지스터

| ID | 위험 | 가능성 | 영향 | 조기 신호 | 대응 | 인간 승인 |
|---|---|---:|---:|---|---|---|
| R-001 | 오래된 범위 재도입 | 높음 | 높음 | 100문항/status/고급분석 코드 | authority/drift 검사 | 범위 변경 시 필요 |
| R-002 | 원문 질문 로그 유출 | 중간 | 매우 높음 | request body 로그 | 공통 redaction·테스트 | 정책 변경 필요 |
| R-003 | LLM 출처 환각 | 중간 | 매우 높음 | source field가 모델 출력 | 서버 metadata 결합 | 원칙 변경 필요 |
| R-004 | 자기 승인 | 중간 | 높음 | actor==created_by | DB/API guard | 권한 변경 필요 |
| R-005 | 가상 기관 정보 노출 | 높음 | 높음 | 044-000/가상주소 | 공식 데이터만 active | 데이터 예외 필요 |
| R-006 | Upstage 비용·cap 우회·숨은 재시도 | 중간 | 높음 | outbound attempt 30 초과·429/잔액 부족·run USD 0.05 초과 | exact `solar-pro3` pin·원자적 cap·hidden retry off·concurrency 1·disabled/template | model/cap/비용 상한 변경·충전 시 필요 |
| R-007 | 4주 범위 초과 | 높음 | 높음 | P2 작업 증가 | P0/P1 gate | 범위 변경 필요 |
| R-008 | mock KPI 오해 | 중간 | 높음 | 배지 없음 | 집계/표본/mock 구분 | 없음 |
| R-009 | 배포 무료 플랜 sleep | 중간 | 중간 | 첫 응답 지연 | warm-up/로컬 백업 | 계정 플랜 필요 |
| R-010 | KB 최신성 | 중간 | 높음 | 오래된 verified date | registry/review date | 공식 검수 필요 |
| R-011 | Upstage 계정별 logging/Free Tier/국외 처리 조건을 실제 시민 안전으로 오인 | 중간 | 매우 높음 | 실제 시민/PII payload 시도 | canonical 합성 allowlist·보수적 마스킹·public/real-user 호출 차단 | 범위 확대 시 법무·개인정보·비용 재승인 필요 |
| R-012 | 보수적 마스킹이 질문 의미를 과도하게 제거 | 중간 | 중간 | 고정 평가 성공률 80% 미달 | PII 100% 유지·원인분석·대안 비교 | 완화 시 필요 |
| R-013 | COLLAB-001 실행 전 tracked history 단일 PC 손실, 실행 뒤에도 ignored env/DB dump 미백업·수동 gate 누락 | 중간 | 높음 | remote 0·백업 지연·검사 미기록 | private source remote+local backup·명령 증거·handoff; GitHub를 DB backup으로 오인 금지 | remote/backup 변경 시 필요 |
| R-014 | HMAC context token을 암호화·인증으로 오해하거나 브라우저에 영속 저장 | 중간 | 매우 높음 | free-text claim·localStorage·token 로그 | closed claims·15분 TTL·current-tab only·재검증 | TTL/claim/storage 변경 시 필요 |
| R-015 | 오래된 local backup이 30일 텍스트 파기 정책을 우회 | 중간 | 높음 | 30일 초과 dump 존재 | dump 30일 삭제·복구 전 purge·restore drill | 실제/원격 backup 전 필요 |
| R-016 | GitHub Free에서 frontend self-merge 범위 위반·direct main push | 중간 | 높음 | protected 경로가 teammate PR/main에 포함 | scope CI·PR-only 규칙·owner review·작은 revert PR; Pro 전환 재검토 | merge/plan 변경 시 필요 |
| R-017 | collaborator 또는 Codex App 권한 과다·계정 탈취 | 낮음~중간 | 매우 높음 | repository scope 확대·낯선 session/commit | private+selected-repo-only·최소 권한·MFA·즉시 revoke/audit | 접근 권한 변경 시 필요 |
| R-018 | Codex Cloud에 비밀을 넣거나 Cloud 검증을 Docker/Upstage actual로 오인 | 중간 | 매우 높음 | Cloud secret 등록·local-only PASS 주장 | Cloud secret 0·agent internet off 기본·Draft PR-only·local-verification-required | Cloud 경계 변경 시 필요 |
| R-019 | 기존 Git author/committer email metadata를 승인 범위 밖에 공개하거나 무계획 history rewrite로 계보 손상 | 낮음~중간 | 높음 | private collaborator 밖 visibility 확대, SHA 불일치 | Q-GIT-004=A/D-053 private collaborator 공개 동의·history 보존; public/추가 collaborator 확대 또는 rewrite는 재승인 | 가시성/협업자/history 변경 시 필요 |
