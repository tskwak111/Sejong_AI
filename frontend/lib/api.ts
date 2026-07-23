/**
 * 모든 API 호출은 이 파일에 모은다 - 컴포넌트에서 직접 fetch 금지 (CLAUDE.md §11).
 *
 * [임시 스펙 근거] 2026-07-22, 무인 세션 결정사항 (백엔드 확정 전 가정):
 * - 채팅 엔드포인트: POST {NEXT_PUBLIC_API_BASE_URL}/api/chat
 * - 요청 바디: { question, region?, context_token? } (지역은 별도 파라미터로 전달)
 * - 피드백 엔드포인트: POST {NEXT_PUBLIC_API_BASE_URL}/api/feedback
 * - NEXT_PUBLIC_USE_MOCK=true면 lib/mock.ts fixture로 응답 (지연 600ms 시뮬레이션)
 */

import type {
  ChatResponse,
  FailureQueueItem,
  FailureStatus,
  FeedbackRequest,
  KbCandidate,
  KbRejectReason,
} from "@/types/api";
import {
  mockAnswer,
  mockContextExpired,
  mockCreateKbDraft,
  mockKpi,
  mockListFailures,
  mockListKbCandidates,
  mockResetContext,
  mockReviewKbCandidate,
  mockUpdateFailureStatus,
} from "@/lib/mock";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/** 시민 질문 전송 */
export async function askQuestion(
  question: string,
  opts?: {
    region?: string;
    contextToken?: string;
    /** context_token 만료 강제 발동 (?demo_expire=1 - mock 시연·검증 전용) */
    forceExpire?: boolean;
  },
): Promise<ChatResponse> {
  if (USE_MOCK) {
    // context_token 만료 시뮬레이션 (CLAUDE.md §9) - 기본 15분 내 미발동
    if (mockContextExpired(opts?.forceExpire ?? false)) {
      return {
        result_type: "ERROR",
        error_code: "CONTEXT_EXPIRED",
        message: "안전을 위해 대화가 종료되었습니다. 새 대화를 시작해 주세요.",
      };
    }
    // 로딩 스켈레톤이 보이도록 응답 지연을 흉내낸다
    await new Promise((r) => setTimeout(r, 600));
    return mockAnswer(question, opts?.region);
  }

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        region: opts?.region,
        context_token: opts?.contextToken,
      }),
      // DESIGN.md v3 §6-4: 10초 초과 시 타임아웃 → 오류 카드(재시도)로 전환.
      // 무한 스피너 금지.
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) {
      return {
        result_type: "ERROR",
        message: "일시적으로 응답을 받지 못했어요. 잠시 후 다시 시도해 주세요.",
      };
    }
    return (await res.json()) as ChatResponse;
  } catch {
    // §9: 에러 리포팅에 사용자 입력 원문을 싣지 않는다
    return {
      result_type: "ERROR",
      message: "네트워크 연결에 문제가 있어요. 다시 시도해 주세요.",
    };
  }
}

/** "새 대화 시작" - context_token 재발급 (CLAUDE.md §9 만료 UI에서 호출) */
export async function resetConversation(): Promise<void> {
  if (USE_MOCK) {
    mockResetContext();
    return;
  }
  // 실API: 새 context_token 발급 엔드포인트 확정 후 연결 (백엔드 협의 필요)
}

/** 만족/불만족 피드백 전송 - 질문 원문 미포함 (§9) */
export async function sendFeedback(feedback: FeedbackRequest): Promise<void> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return;
  }
  try {
    await fetch(`${API_BASE}/api/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(feedback),
    });
  } catch {
    // 피드백 실패는 사용자 흐름을 막지 않는다
  }
}

/* ---------- 관리자(이음센터) API ----------
 *
 * [임시 스펙 근거] 2026-07-22, 무인 세션 결정사항 (백엔드 곽태성과 확정 전):
 * - GET   /api/admin/failures                → { items: FailureQueueItem[] }
 * - PATCH /api/admin/failures/{id}           바디 { status: FailureStatus }
 * - GET   /api/admin/kb-candidates           → { items: KbCandidate[] }
 * - POST  /api/admin/kb-candidates           바디 { source_failure_id: string }
 *         (INSUFFICIENT_GROUNDING 건만 허용 - 서버에서도 검증한다고 가정)
 * - PATCH /api/admin/kb-candidates/{id}      바디 { status: '승인' | '반려' }
 * - GET   /api/admin/kpi                     → { total_questions, auto_answer_rate,
 *         fallback_rate, avg_response_seconds, source_citation_rate }
 * - 인증: 미구현 (P0 범위 밖). 확정 시 Authorization 헤더를 이 파일에서 일괄 추가.
 */

const ADMIN_MOCK_DELAY = 300;

export interface AdminKpi {
  total_questions: number;
  auto_answer_rate: number;
  fallback_rate: number;
  avg_response_seconds: number;
  source_citation_rate: number;
}

/** 실패 질문 큐 목록 */
export async function fetchFailureQueue(): Promise<FailureQueueItem[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, ADMIN_MOCK_DELAY));
    return mockListFailures();
  }
  const res = await fetch(`${API_BASE}/api/admin/failures`);
  if (!res.ok) throw new Error("failures fetch failed");
  return ((await res.json()) as { items: FailureQueueItem[] }).items;
}

/** 실패 질문 처리 상태 변경 (신규 → 검토중 → 처리완료) */
export async function updateFailureStatus(
  id: string,
  status: FailureStatus,
): Promise<void> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, ADMIN_MOCK_DELAY));
    mockUpdateFailureStatus(id, status);
    return;
  }
  await fetch(`${API_BASE}/api/admin/failures/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

/** KB 후보 초안 생성 - INSUFFICIENT_GROUNDING 건 전용 */
export async function createKbDraft(
  sourceFailureId: string,
): Promise<KbCandidate | null> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, ADMIN_MOCK_DELAY));
    return mockCreateKbDraft(sourceFailureId);
  }
  const res = await fetch(`${API_BASE}/api/admin/kb-candidates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_failure_id: sourceFailureId }),
  });
  if (!res.ok) return null;
  return (await res.json()) as KbCandidate;
}

/** KB 후보 목록 */
export async function fetchKbCandidates(): Promise<KbCandidate[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, ADMIN_MOCK_DELAY));
    return mockListKbCandidates();
  }
  const res = await fetch(`${API_BASE}/api/admin/kb-candidates`);
  if (!res.ok) throw new Error("kb-candidates fetch failed");
  return ((await res.json()) as { items: KbCandidate[] }).items;
}

/** KB 후보 판정 (승인 주체: 운영 관리자). 반려 시 사유 코드 필수 (v2 §8) */
export async function reviewKbCandidate(
  id: string,
  status: "승인" | "반려",
  reasonCode?: KbRejectReason,
): Promise<void> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, ADMIN_MOCK_DELAY));
    mockReviewKbCandidate(id, status, reasonCode);
    return;
  }
  await fetch(`${API_BASE}/api/admin/kb-candidates/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, reason_code: reasonCode }),
  });
}

/** Overview KPI 5종 */
export async function fetchKpi(): Promise<AdminKpi> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, ADMIN_MOCK_DELAY));
    return mockKpi();
  }
  const res = await fetch(`${API_BASE}/api/admin/kpi`);
  if (!res.ok) throw new Error("kpi fetch failed");
  return (await res.json()) as AdminKpi;
}
