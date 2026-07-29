import type { components } from "../../../../packages/shared-contracts/src/generated/api";

type CandidateReviewRequest = components["schemas"]["CandidateReviewRequest"];
type CivicScopeGapListResponse = components["schemas"]["CivicScopeGapListResponse"];
type CivicScopeGapReviewRequest = components["schemas"]["CivicScopeGapReviewRequest"];
type CivicScopeGapReviewResponse = components["schemas"]["CivicScopeGapReviewResponse"];
type CivicScopeGapStatus = components["schemas"]["CivicScopeGapStatus"];
type FailedQuestionDetailResponse = components["schemas"]["FailedQuestionDetailResponse"];
type FailedQuestionListResponse = components["schemas"]["FailedQuestionListResponse"];
type FeedbackSummaryResponse = components["schemas"]["FeedbackSummaryResponse"];
type KBCandidateCreate = components["schemas"]["KBCandidateCreate"];
type KBCandidateCreateResponse = components["schemas"]["KBCandidateCreateResponse"];
type KBCandidateListResponse = components["schemas"]["KBCandidateListResponse"];
type KBCandidateReviewResponse = components["schemas"]["KBCandidateReviewResponse"];
type KBCandidateSubmitResponse = components["schemas"]["KBCandidateSubmitResponse"];
type ReasonConfirmationRequest = components["schemas"]["ReasonConfirmationRequest"];
type ReasonConfirmationResponse = components["schemas"]["ReasonConfirmationResponse"];

type Fetcher = typeof fetch;
export type AdminErrorCode =
  | "ADMIN_ROUTE_DISABLED"
  | "ADMIN_FORBIDDEN"
  | "ADMIN_NOT_FOUND"
  | "ADMIN_INVALID_STATE"
  | "ADMIN_VALIDATION_FAILED";

const ADMIN_ERROR_CODES = new Set<AdminErrorCode>([
  "ADMIN_ROUTE_DISABLED",
  "ADMIN_FORBIDDEN",
  "ADMIN_NOT_FOUND",
  "ADMIN_INVALID_STATE",
  "ADMIN_VALIDATION_FAILED",
]);

export type AdminActor = Readonly<{
  role: "OPERATOR" | "APPROVER";
  actorId: string;
}>;

export interface AdminTransport {
  listFailedQuestions(actor: AdminActor): Promise<FailedQuestionListResponse>;
  getFailedQuestion(actor: AdminActor, id: string): Promise<FailedQuestionDetailResponse>;
  confirmReason(
    actor: AdminActor,
    id: string,
    request: ReasonConfirmationRequest,
  ): Promise<ReasonConfirmationResponse>;
  listCivicScopeGaps(
    actor: AdminActor,
    status?: CivicScopeGapStatus,
  ): Promise<CivicScopeGapListResponse>;
  reviewCivicScopeGap(
    actor: AdminActor,
    id: string,
    request: CivicScopeGapReviewRequest,
  ): Promise<CivicScopeGapReviewResponse>;
  listCandidates(actor: AdminActor): Promise<KBCandidateListResponse>;
  getFeedbackSummary(actor: AdminActor): Promise<FeedbackSummaryResponse>;
  createCandidate(actor: AdminActor, request: KBCandidateCreate): Promise<KBCandidateCreateResponse>;
  submitCandidate(actor: AdminActor, id: string): Promise<KBCandidateSubmitResponse>;
  reviewCandidate(
    actor: AdminActor,
    id: string,
    request: CandidateReviewRequest,
  ): Promise<KBCandidateReviewResponse>;
}

export class AdminTransportError extends Error {
  readonly retryable: boolean;
  readonly status: number | null;
  readonly code: AdminErrorCode | null;

  constructor(
    status: number | null,
    retryable = true,
    code: AdminErrorCode | null = null,
  ) {
    super("운영 데이터를 불러오지 못했어요.");
    this.name = "AdminTransportError";
    this.retryable = retryable;
    this.status = status;
    this.code = code;
  }
}

function headersFor(actor: AdminActor): Record<string, string> {
  return {
    "X-Demo-Actor-Id": actor.actorId,
    "X-Demo-Role": actor.role,
  };
}

function jsonHeadersFor(actor: AdminActor): Record<string, string> {
  return { ...headersFor(actor), "Content-Type": "application/json" };
}

async function fetchJson<T>(fetcher: Fetcher, path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetcher(path, init);
  } catch {
    throw new AdminTransportError(null);
  }
  if (!response.ok) {
    let code: AdminErrorCode | null = null;
    try {
      const body: unknown = await response.json();
      if (typeof body === "object" && body !== null) {
        const error = (body as Record<string, unknown>).error;
        if (typeof error === "object" && error !== null) {
          const value = (error as Record<string, unknown>).code;
          if (
            typeof value === "string" &&
            ADMIN_ERROR_CODES.has(value as AdminErrorCode)
          ) {
            code = value as AdminErrorCode;
          }
        }
      }
    } catch {
      code = null;
    }
    throw new AdminTransportError(
      response.status,
      response.status >= 500,
      code,
    );
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new AdminTransportError(response.status);
  }
}

export function createAdminTransport(fetcher: Fetcher = fetch): AdminTransport {
  return {
    listFailedQuestions(actor) {
      return fetchJson<FailedQuestionListResponse>(
        fetcher,
        "/api/v1/admin/failed-questions",
        { method: "GET", headers: headersFor(actor) },
      );
    },
    getFailedQuestion(actor, id) {
      return fetchJson<FailedQuestionDetailResponse>(
        fetcher,
        `/api/v1/admin/failed-questions/${encodeURIComponent(id)}`,
        { method: "GET", headers: headersFor(actor) },
      );
    },
    confirmReason(actor, id, request) {
      return fetchJson<ReasonConfirmationResponse>(
        fetcher,
        `/api/v1/admin/failed-questions/${encodeURIComponent(id)}/reason`,
        {
          method: "PATCH",
          headers: jsonHeadersFor(actor),
          body: JSON.stringify(request),
        },
      );
    },
    listCivicScopeGaps(actor, status) {
      const query = status === undefined ? "" : `?status=${encodeURIComponent(status)}`;
      return fetchJson<CivicScopeGapListResponse>(
        fetcher,
        `/api/v1/admin/civic-scope-gaps${query}`,
        { method: "GET", headers: headersFor(actor) },
      );
    },
    reviewCivicScopeGap(actor, id, request) {
      return fetchJson<CivicScopeGapReviewResponse>(
        fetcher,
        `/api/v1/admin/civic-scope-gaps/${encodeURIComponent(id)}/review`,
        {
          method: "PATCH",
          headers: jsonHeadersFor(actor),
          body: JSON.stringify(request),
        },
      );
    },
    listCandidates(actor) {
      return fetchJson<KBCandidateListResponse>(
        fetcher,
        "/api/v1/admin/kb-candidates",
        { method: "GET", headers: headersFor(actor) },
      );
    },
    getFeedbackSummary(actor) {
      return fetchJson<FeedbackSummaryResponse>(
        fetcher,
        "/api/v1/admin/feedback-summary",
        { method: "GET", headers: headersFor(actor) },
      );
    },
    createCandidate(actor, request) {
      return fetchJson<KBCandidateCreateResponse>(
        fetcher,
        "/api/v1/admin/kb-candidates",
        {
          method: "POST",
          headers: jsonHeadersFor(actor),
          body: JSON.stringify(request),
        },
      );
    },
    submitCandidate(actor, id) {
      return fetchJson<KBCandidateSubmitResponse>(
        fetcher,
        `/api/v1/admin/kb-candidates/${encodeURIComponent(id)}/submit`,
        { method: "POST", headers: headersFor(actor) },
      );
    },
    reviewCandidate(actor, id, request) {
      return fetchJson<KBCandidateReviewResponse>(
        fetcher,
        `/api/v1/admin/kb-candidates/${encodeURIComponent(id)}/review`,
        {
          method: "PATCH",
          headers: jsonHeadersFor(actor),
          body: JSON.stringify(request),
        },
      );
    },
  };
}
