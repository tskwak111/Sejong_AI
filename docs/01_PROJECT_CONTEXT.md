# 프로젝트 컨텍스트

## 제품

`세종 민원이음`은 시민용 민원 AI 플랫폼과 관리자용 AI 민원 운영센터로 구성된다.

### 시민 가치

- 행정 용어 없이 일상어 질문
- 공식 근거가 있는 절차·서류·기간·수수료·기관 안내
- 출처·확인일 확인
- 모호하면 후속질문
- 답하면 안 되는 질문은 이유와 다음 행동 안내

### 운영자 가치

- 지원 범위 안의 근거 부족 질문 발견
- 개인정보가 제거된 실패 질문 검토
- 공식 출처 기반 KB 후보 작성
- 별도 승인자의 검수
- 승인된 지식만 시민 답변에 반영

## 대표 수직 흐름

```text
침대 2인용 프레임 수수료 질문
→ 초기 ACTIVE KB에 세부 근거 없음
→ INSUFFICIENT_GROUNDING
→ 실패 질문 마스킹 저장
→ 운영자 후보 작성
→ 작성자와 다른 승인자 승인
→ ACTIVE KB 생성
→ 동일 질문 재질의
→ 공식 수수료와 서버 결합 출처 카드
```

## 지원 분야

1. 전입·주민등록
2. 증명서 발급
3. 대형폐기물
4. 지방세 일반 안내

## 핵심 품질 목표

- 정상 10개 중 8개 이상 성공
- 직접 답변 출처 표기율 100%
- 폴백 8개 중 7개 이상 적절
- 모호 질문 FOLLOWUP 100%
- 개인정보 원문 저장 0건
- 승인 전 KB 노출 0건
- 회귀 흐름 1회 완주

## LLM과 배포

- Upstage `solar-pro3` 합성 평가 뒤 local/private 근거 제한형 시민 chat 설계를 승인했다.
  supported+masked+ACTIVE/OFFICIAL+grounded만 8초·1 attempt·cap 30으로 호출하고,
  server-issued fact ID·server-bound source와 전체 template fallback을 강제한다. public/remote는 별도 승인
- 화면 transcript는 현재 탭 메모리, 문맥은 15분 서명형 client-carried token; 서버 세션·raw transcript 저장 없음
- 키워드·메타데이터 검색 기본, MVP 임베딩 off
- Vercel(web) + Render(api) + Supabase(DB) 권장
- 공개 배포 계정·리전·쿼터·비밀값은 별도 승인 전 미정
