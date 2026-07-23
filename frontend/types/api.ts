/**
 * API 응답 타입 정의 - CLAUDE.md §11
 *
 * [임시 필드명 근거] 2026-07-22, 무인 세션 결정사항:
 * 백엔드(곽태성)와 미확정인 필드명을 아래와 같이 임시 확정한다.
 * 전부 mock 단계이므로 확정 시 이 파일과 lib/mock.ts만 수정하면 된다.
 *  - 응답 구분 필드: `result_type` ('SUCCESS' | 'FOLLOWUP' | 'FALLBACK' | 'ERROR')
 *  - 폴백 사유 필드: `fallback_code`
 *  - 후속질문 트리거 필드: `trigger` ('AMBIGUOUS')
 *  - 출처 배열: `sources: { kb_id, title, url?, last_verified_at }[]`
 *  - 주의사항: `caution?: string` (값이 있으면 반드시 표시)
 *  - 지역(동) 조건: 요청 시 별도 파라미터 `region` (질문 텍스트 파싱은 백엔드 몫)
 *  - 대화 맥락: `context_token` (요청 바디 필드로 가정)
 *  - 담당 기관: `{ name, phone, hours }` (DAR-002: 연락처·운영시간 포함)
 */

/** 응답 결과 타입 - union 고정 (CLAUDE.md §11) */
export type ResultType = "SUCCESS" | "FOLLOWUP" | "FALLBACK" | "ERROR";

/** 폴백 사유 4종 */
export type FallbackCode =
  | "INSUFFICIENT_GROUNDING"
  | "PERSONAL_LOOKUP"
  | "LEGAL_JUDGMENT"
  | "OUT_OF_SCOPE";

/** 폴백 사유 한글 라벨 (관리자 화면 분류/필터 공용) */
export const FALLBACK_CODE_LABEL: Record<FallbackCode, string> = {
  INSUFFICIENT_GROUNDING: "근거 부족",
  PERSONAL_LOOKUP: "개인별 조회",
  LEGAL_JUDGMENT: "법적 판단",
  OUT_OF_SCOPE: "범위 밖",
};

/** 후속질문 트리거 - 폴백 코드와 섞지 않는다 (제안서 6.2) */
export type FollowupTrigger = "AMBIGUOUS";

/** 지원 분야 4개 */
export type CivilCategory =
  | "MOVE_IN" // 전입·주민등록
  | "BULKY_WASTE" // 대형폐기물
  | "CERTIFICATE" // 증명서 발급
  | "LOCAL_TAX"; // 지방세

export const CATEGORY_LABEL: Record<CivilCategory, string> = {
  MOVE_IN: "전입·주민등록",
  BULKY_WASTE: "대형폐기물",
  CERTIFICATE: "증명서 발급",
  LOCAL_TAX: "지방세",
};

/** 출처 (KB 근거) - 출처 없으면 답변 카드를 렌더링하지 않는다 (SER-003) */
export interface Source {
  kb_id: string;
  title: string;
  url?: string;
  /** 최종 확인일 (예: "2026-07-15") */
  last_verified_at: string;
}

/** 담당 기관 - 이름만이 아니라 연락처·운영시간까지 (DAR-002) */
export interface AgencyContact {
  name: string;
  phone: string;
  hours: string;
}

/** 딥링크 버튼 (정부24, 위택스 등) */
export interface DeepLink {
  label: string;
  url: string;
}

/**
 * 신청 방법 2갈래 항목 (DESIGN.md v3 §6-1-3 - 온라인/방문).
 * [임시 필드명 근거] 2026-07-23, 무인 세션 결정사항: v3 답변 카드의
 * "온라인/방문 2갈래" 표시용. 값이 없으면 procedure_steps(절차형)를
 * 같은 번호+이음선 문법으로 나열한다. 백엔드 확정 시 필드명만 대조.
 */
export interface ApplicationMethod {
  /** 예: "온라인 신청" / "주민센터 방문" */
  title: string;
  /** 채널·가용 시간 보조 설명 - 예: "정부24에서 24시간 신청할 수 있어요" */
  description: string;
}

/** (A) SUCCESS - 답변 카드 */
export interface SuccessResponse {
  result_type: "SUCCESS";
  category: CivilCategory;
  answer_summary: string;
  procedure_steps: string[];
  /** 신청 방법 2갈래(온라인/방문) - 있으면 procedure_steps 대신 이 구조로 표시 */
  application_methods?: ApplicationMethod[];
  required_documents: string[];
  processing_time: string;
  fee: string;
  /** 값이 있으면 반드시 표시 (KB 스키마 필드) */
  caution?: string;
  fallback_contact: AgencyContact;
  sources: Source[];
  deep_link?: DeepLink;
  /** 답변에 적용된 지역(동) 조건 - 있으면 카드에서 "동 변경" 인라인 노출 */
  region?: string;
  /**
   * 관련 민원 한 줄 제안 (DESIGN.md v2 §4-2-9, 제안서 3.2).
   * 값이 있으면 "함께 확인해 보세요:" + 질문 칩 1개. 칩 탭 → 해당 질문 전송.
   */
  related_question?: string;
}

/** FOLLOWUP 선택지 */
export interface FollowupOption {
  id: string;
  label: string;
  /** 선택지 보조 설명 한 줄 (v3 §6-2 - 예: "이사한 날부터 14일 이내") */
  description?: string;
  /**
   * REGION: 지역(동) 선택 UI로 전환 (SFR-004)
   * QUERY: 선택 시 next_question을 새 질문으로 전송
   */
  kind: "REGION" | "QUERY";
  next_question?: string;
}

/** (B) FOLLOWUP - 단정적 답변 금지, 선택형 버튼으로 조건을 좁힌다 */
export interface FollowupResponse {
  result_type: "FOLLOWUP";
  trigger: FollowupTrigger;
  message: string;
  options: FollowupOption[];
  /** 관련 민원 한 줄 제안 */
  related_suggestion?: string;
  /** REGION 선택지가 고른 동을 적용해 다시 물을 원 질문 */
  region_question?: string;
}

/** (C) FALLBACK - 실패가 아니라 안전장치 */
export interface FallbackResponse {
  result_type: "FALLBACK";
  fallback_code: FallbackCode;
  message: string;
  contact: AgencyContact;
  /** PERSONAL_LOOKUP은 공식 조회 채널 딥링크 필수 (예: 위택스) */
  deep_link?: DeepLink;
}

/** (D) 오류 */
export interface ErrorResponse {
  result_type: "ERROR";
  message: string;
  /**
   * CONTEXT_EXPIRED: 15분 서명형 context_token 만료 (CLAUDE.md §9).
   * 대화 화면은 이 코드를 받으면 탭 메모리의 대화 내용을 초기화하고
   * "새 대화 시작" 안내 UI로 전환한다.
   */
  error_code?: "CONTEXT_EXPIRED";
}

export type ChatResponse =
  | SuccessResponse
  | FollowupResponse
  | FallbackResponse
  | ErrorResponse;

/** 채팅 요청 - 임시 스키마 (엔드포인트 경로: POST /api/chat 가정) */
export interface ChatRequest {
  question: string;
  region?: string;
  context_token?: string;
}

/* ---------- 관리자(이음센터) ---------- */

export type FailureStatus = "신규" | "검토중" | "처리완료";

/** 실패 질문 큐 항목 - masked_question은 30일 후 NULL 파기될 수 있다 */
export interface FailureQueueItem {
  id: string;
  /** 마스킹된 질문 텍스트. NULL(파기)이어도 행이 깨지면 안 된다 */
  masked_question: string | null;
  fallback_code: FallbackCode;
  category: CivilCategory | null;
  status: FailureStatus;
  created_at: string;
  /**
   * 최근 30일 동일 질문 반복 접수 횟수 - DESIGN.md v3 §9-3 발단 요약 바·
   * 대기 목록 메타("실패 N회") 표시용.
   * [임시 필드명 근거] 2026-07-23, 무인 세션 결정: 백엔드 확정 전 mock 전용,
   * 값이 없으면 해당 표기를 생략한다.
   */
  repeat_count?: number;
}

export type KbCandidateStatus = "승인 대기" | "승인" | "반려";

/**
 * AI 초안의 KB 실물 스키마 (DESIGN.md v2 §8 - 심사대 우측 패널).
 * source_url은 항상 null - "출처 URL 미검증" 경고가 사람 판정 철학의 물증이다.
 */
export interface KbDraftSchema {
  category: CivilCategory | null;
  question_examples: string[];
  answer_summary: string;
  procedure_steps: string[];
  processing_time: string;
  fee: string;
  fallback_contact: AgencyContact;
  /** 미검증 - 승인 전 담당자가 공식 출처를 확인해야 한다 */
  source_url: null;
}

/** 반려 사유 코드 (v2 §8) - 자유 텍스트 없음 */
export type KbRejectReason =
  | "UNCLEAR_SOURCE" // 출처 불명확
  | "INACCURATE" // 내용 부정확
  | "DUPLICATE" // 중복
  | "OTHER"; // 기타

export interface KbCandidate {
  id: string;
  title: string;
  /** KB 스키마 초안 (v2 §8 심사대) */
  draft: KbDraftSchema;
  source_failure_id: string;
  status: KbCandidateStatus;
  created_at: string;
}

/** 만족/불만족 피드백 - 자유 텍스트 금지, 질문 원문 미포함 (§9) */
export interface FeedbackRequest {
  response_id: string;
  satisfied: boolean;
  category?: CivilCategory;
  reason_code?: string;
}
