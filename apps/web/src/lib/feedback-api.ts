import type { components } from "../../../../packages/shared-contracts/src/generated/api";

export type FeedbackCategory = components["schemas"]["FeedbackCategory"];
export type FeedbackReasonCode = components["schemas"]["FeedbackReasonCode"];
export type FeedbackCreateRequest = components["schemas"]["FeedbackCreateRequest"];
export type FeedbackCreateResponse = components["schemas"]["FeedbackCreateResponse"];

type Fetcher = typeof fetch;

export interface FeedbackTransport {
  record(request: FeedbackCreateRequest): Promise<FeedbackCreateResponse>;
}

export class FeedbackTransportError extends Error {
  readonly status: number | null;
  readonly retryable: boolean;

  constructor(status: number | null, retryable: boolean) {
    super("의견을 저장하지 못했어요.");
    this.name = "FeedbackTransportError";
    this.status = status;
    this.retryable = retryable;
  }
}

function isFeedbackResponse(value: unknown): value is FeedbackCreateResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.request_id === "string" &&
    candidate.status === "RECORDED" &&
    ["NOT_PROVIDED", "STORED", "MASKED"].includes(
      String(candidate.detail_status),
    )
  );
}

export function createFeedbackTransport(
  fetcher: Fetcher = fetch,
): FeedbackTransport {
  return {
    async record(request) {
      let response: Response;
      try {
        response = await fetcher("/api/v1/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        });
      } catch {
        throw new FeedbackTransportError(null, true);
      }
      if (!response.ok) {
        throw new FeedbackTransportError(
          response.status,
          response.status >= 500,
        );
      }
      try {
        const body: unknown = await response.json();
        if (!isFeedbackResponse(body)) {
          throw new FeedbackTransportError(response.status, false);
        }
        return body;
      } catch (error) {
        if (error instanceof FeedbackTransportError) throw error;
        throw new FeedbackTransportError(response.status, false);
      }
    },
  };
}

export function createFixtureFeedbackTransport(): FeedbackTransport {
  return {
    async record(request) {
      return {
        request_id: request.request_id,
        status: "RECORDED",
        detail_status:
          request.detail === null
            ? "NOT_PROVIDED"
            : request.detail.includes("[")
              ? "MASKED"
              : "STORED",
      };
    },
  };
}
