/**
 * source: contracts/openapi-v1.yaml
 * OpenAPI: 4.0.0-draft; generator: openapi-typescript 7.13.0
 * Generated deterministically; do not edit by hand.
 */
export interface paths {
    "/api/v1/admin/civic-scope-gaps": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["listCivicScopeGaps"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/civic-scope-gaps/{id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["reviewCivicScopeGap"];
        trace?: never;
    };
    "/api/v1/admin/failed-questions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["listFailedQuestions"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/failed-questions/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["getFailedQuestion"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/failed-questions/{id}/reason": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["confirmFallbackReason"];
        trace?: never;
    };
    "/api/v1/admin/kb-candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["listKBCandidates"];
        put?: never;
        post: operations["createKBCandidate"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/kb-candidates/{id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["reviewKBCandidate"];
        trace?: never;
    };
    "/api/v1/admin/kb-candidates/{id}/submit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["submitKBCandidate"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/quality-summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["getQualitySummary"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/chat": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["createChatAnswer"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/offices": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["listOffices"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["health"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["readiness"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        AdminError: components["schemas"]["AdminRouteDisabledError"] | components["schemas"]["AdminForbiddenError"] | components["schemas"]["AdminNotFoundError"] | components["schemas"]["AdminInvalidStateError"] | components["schemas"]["AdminValidationFailedError"];
        AdminErrorEnvelope: {
            error: components["schemas"]["AdminError"];
        };
        AdminForbiddenError: {
            /** @constant */
            code: "ADMIN_FORBIDDEN";
            /** @constant */
            message: "이 작업을 수행할 권한이 없습니다.";
            /** Format: uuid */
            request_id: string;
            /** @constant */
            retryable: false;
        };
        AdminInvalidStateError: {
            /** @constant */
            code: "ADMIN_INVALID_STATE";
            /** @constant */
            message: "현재 상태에서는 이 작업을 수행할 수 없습니다.";
            /** Format: uuid */
            request_id: string;
            /** @constant */
            retryable: false;
        };
        AdminNotFoundError: {
            /** @constant */
            code: "ADMIN_NOT_FOUND";
            /** @constant */
            message: "대상을 찾을 수 없습니다.";
            /** Format: uuid */
            request_id: string;
            /** @constant */
            retryable: false;
        };
        AdminRouteDisabledError: {
            /** @constant */
            code: "ADMIN_ROUTE_DISABLED";
            /** @constant */
            message: "관리자 기능을 사용할 수 없습니다.";
            /** Format: uuid */
            request_id: string;
            /** @constant */
            retryable: false;
        };
        AdminValidationFailedError: {
            /** @constant */
            code: "ADMIN_VALIDATION_FAILED";
            /** @constant */
            message: "입력값을 확인해 주세요.";
            /** Format: uuid */
            request_id: string;
            /** @constant */
            retryable: false;
        };
        CandidateReviewRequest: {
            /** @enum {string} */
            decision: "APPROVED" | "REJECTED";
            review_comment: string;
        };
        /**
         * @description SYSTEM_ERROR is represented by the HTTP 503 envelope, not a 200 ChatResponse.
         * @enum {string}
         */
        ChatAnswerStatus: "SUCCESS" | "FOLLOWUP" | "FALLBACK";
        ChatRequest: {
            /** @description Optional signed conversational context. Clients treat it as opaque and keep it only in current-tab memory. Missing, null, expired, invalid, or unsupported tokens are treated as no context, not authentication failures. The token is never a source of official facts or authority. */
            context_token?: string | null;
            question: string;
            /** @enum {string|null} */
            selected_region?: "아름동" | "도담동" | "조치원읍" | null;
            /** @default false */
            simple_language?: boolean;
        };
        ChatResponse: components["schemas"]["SuccessResponse"] | components["schemas"]["FollowupResponse"] | components["schemas"]["FallbackResponse"];
        ChatResponseBase: {
            answer_status: components["schemas"]["ChatAnswerStatus"];
            confidence?: number | null;
            /** @description Fresh signed 15-minute context for current-tab memory. SUCCESS and FOLLOWUP may return a token; FALLBACK always returns null. Never log, persist, display, or use it as authentication. */
            context_token: string | null;
            department?: string | null;
            fallback?: components["schemas"]["Fallback"] | null;
            fee?: string | null;
            followup_options?: string[];
            intent: components["schemas"]["Intent"];
            procedure_steps?: string[];
            processing_time?: string | null;
            /** Format: uuid */
            request_id: string;
            required_documents?: string[];
            sources: components["schemas"]["Source"][];
            summary?: string | null;
        };
        CivicScopeGapFallback: components["schemas"]["FallbackPayloadBase"] & {
            /** @constant */
            candidate_eligible: false;
            /** @constant */
            reason: "CIVIC_SCOPE_GAP";
        };
        CivicScopeGapListResponse: {
            items: components["schemas"]["CivicScopeGapSummary"][];
            total: number;
        };
        CivicScopeGapResponse: components["schemas"]["FallbackResponseBase"] & {
            fallback: components["schemas"]["CivicScopeGapFallback"];
            /** @constant */
            intent: "OUT_OF_SCOPE";
        };
        CivicScopeGapReviewRequest: {
            /** @enum {string} */
            decision: "PLANNED" | "DISMISSED";
            review_comment: string;
        };
        CivicScopeGapReviewResponse: {
            /** Format: uuid */
            id: string;
            /** @enum {string} */
            status: "PLANNED" | "DISMISSED";
        };
        /** @enum {string} */
        CivicScopeGapStatus: "NEW" | "PLANNED" | "DISMISSED";
        CivicScopeGapSummary: {
            /** Format: date-time */
            created_at: string;
            /** Format: uuid */
            id: string;
            /** @description PII-safe text only; null after exact 30-day retention purge. */
            masked_question: string | null;
            review_comment: string | null;
            /** Format: date-time */
            reviewed_at: string | null;
            reviewed_by: string | null;
            status: components["schemas"]["CivicScopeGapStatus"];
            /**
             * Format: date-time
             * @description Exactly 30 days after creation.
             */
            text_expires_at: string;
            /** Format: date-time */
            text_purged_at: string | null;
            /** Format: date-time */
            updated_at: string;
        } & (unknown & unknown);
        FailedQuestion: {
            candidate_eligible: boolean;
            /** Format: date-time */
            created_at: string;
            fallback_reason: components["schemas"]["StoredFailureReason"];
            /** Format: uuid */
            id: string;
            intent: components["schemas"]["SupportedIntent"];
            /** @description Null only after the 30-day text retention job has purged the field. */
            masked_question: string | null;
            /** @enum {string} */
            status: "NEW" | "REASON_CONFIRMED";
            /**
             * Format: date-time
             * @description Expiry of masked_question only; exactly 30 days after creation.
             */
            text_expires_at: string;
            /**
             * Format: date-time
             * @description Actual purge time; null while masked_question is retained.
             */
            text_purged_at: string | null;
        } & (unknown & unknown);
        FailedQuestionDetailResponse: {
            item: components["schemas"]["FailedQuestion"];
        };
        FailedQuestionListResponse: {
            items: components["schemas"]["FailedQuestion"][];
            total: number;
        };
        /** @enum {string} */
        FailedQuestionStatus: "NEW" | "REASON_CONFIRMED";
        Fallback: components["schemas"]["InsufficientGroundingFallback"] | components["schemas"]["PersonalLookupFallback"] | components["schemas"]["LegalJudgmentFallback"] | components["schemas"]["CivicScopeGapFallback"] | components["schemas"]["OutOfScopeFallback"] | components["schemas"]["PrivacyUnresolvedFallback"];
        FallbackPayloadBase: {
            candidate_eligible: boolean;
            message: string;
            next_actions?: string[];
            office?: components["schemas"]["Office"] | null;
            reason: components["schemas"]["FallbackReason"];
            title: string;
        };
        /** @enum {string} */
        FallbackReason: "INSUFFICIENT_GROUNDING" | "PERSONAL_LOOKUP" | "LEGAL_JUDGMENT" | "CIVIC_SCOPE_GAP" | "OUT_OF_SCOPE" | "PRIVACY_UNRESOLVED";
        FallbackResponse: components["schemas"]["InsufficientGroundingResponse"] | components["schemas"]["PersonalLookupResponse"] | components["schemas"]["LegalJudgmentResponse"] | components["schemas"]["CivicScopeGapResponse"] | components["schemas"]["OutOfScopeResponse"] | components["schemas"]["PrivacyUnresolvedResponse"];
        FallbackResponseBase: components["schemas"]["ChatResponseBase"] & {
            /** @constant */
            answer_status: "FALLBACK";
            confidence?: null;
            context_token: null;
            department?: null;
            fallback: components["schemas"]["Fallback"];
            fee?: null;
            followup_options?: [
            ];
            intent: components["schemas"]["Intent"];
            procedure_steps?: [
            ];
            processing_time?: null;
            required_documents?: [
            ];
            sources: [
            ];
            summary?: null;
        };
        FollowupResponse: components["schemas"]["ChatResponseBase"] & {
            /** @constant */
            answer_status: "FOLLOWUP";
            department?: null;
            fallback?: null;
            fee?: null;
            followup_options: [
                string,
                ...string[]
            ];
            /** @enum {unknown} */
            intent: "MOVE_IN_RESIDENT_REGISTRATION" | "CERTIFICATE_ISSUANCE" | "BULKY_WASTE" | "LOCAL_TAX_GENERAL" | "UNKNOWN";
            office: null;
            procedure_steps?: [
            ];
            processing_time?: null;
            required_documents?: [
            ];
            sources: [
            ];
            summary?: null;
        };
        HealthResponse: {
            /** @constant */
            status: "ok";
        };
        InsufficientGroundingFallback: components["schemas"]["FallbackPayloadBase"] & {
            /** @constant */
            candidate_eligible: true;
            /** @constant */
            reason: "INSUFFICIENT_GROUNDING";
        };
        InsufficientGroundingResponse: components["schemas"]["FallbackResponseBase"] & {
            fallback: components["schemas"]["InsufficientGroundingFallback"];
            /** @enum {unknown} */
            intent: "MOVE_IN_RESIDENT_REGISTRATION" | "CERTIFICATE_ISSUANCE" | "BULKY_WASTE" | "LOCAL_TAX_GENERAL";
        };
        /** @enum {string} */
        Intent: "MOVE_IN_RESIDENT_REGISTRATION" | "CERTIFICATE_ISSUANCE" | "BULKY_WASTE" | "LOCAL_TAX_GENERAL" | "OUT_OF_SCOPE" | "UNKNOWN";
        KBCandidateCreate: {
            answer_summary: string;
            category: components["schemas"]["SupportedIntent"];
            caution?: string | null;
            department: string;
            /** Format: uuid */
            failed_question_id: string;
            fee?: string | null;
            /** Format: date */
            last_verified_at: string;
            procedure_steps?: string[];
            processing_time?: string | null;
            /** @description Human-generalized question that must pass PII validation; not a long-term copy of masked_question. */
            representative_question: string;
            required_documents?: string[];
            source_title: string;
            /** Format: uri */
            source_url: string;
            title: string;
        };
        KBCandidateCreateResponse: {
            /** Format: uuid */
            id: string;
            /** @constant */
            status: "DRAFTED";
        };
        KBCandidateListResponse: {
            items: components["schemas"]["KBCandidateSummary"][];
            total: number;
        };
        KBCandidateReviewResponse: {
            /** Format: uuid */
            id: string;
            /** @enum {string} */
            status: "APPROVED" | "REJECTED";
        };
        /** @enum {string} */
        KBCandidateStatus: "DRAFTED" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED";
        KBCandidateSubmitResponse: {
            /** Format: uuid */
            id: string;
            /** @constant */
            status: "PENDING_APPROVAL";
        };
        KBCandidateSummary: {
            /** Format: uuid */
            activated_kb_id: string | null;
            answer_summary: string;
            /** Format: date-time */
            approved_at: string | null;
            /** @enum {string} */
            category: "MOVE_IN_RESIDENT_REGISTRATION" | "CERTIFICATE_ISSUANCE" | "BULKY_WASTE" | "LOCAL_TAX_GENERAL";
            caution: string | null;
            /** Format: date-time */
            created_at: string;
            created_by: string;
            /** @enum {string} */
            data_origin: "OFFICIAL" | "MOCK";
            department: string;
            /** Format: uuid */
            failed_question_id: string;
            fee: string | null;
            /** Format: uuid */
            id: string;
            /** Format: date */
            last_verified_at: string;
            procedure_steps: string[];
            processing_time: string | null;
            representative_question: string;
            required_documents: string[];
            review_comment: string | null;
            reviewed_by: string | null;
            source_title: string;
            /** Format: uri */
            source_url: string;
            status: components["schemas"]["KBCandidateStatus"];
            title: string;
            /** Format: date-time */
            updated_at: string;
        } & (unknown & unknown & unknown);
        LegalJudgmentFallback: components["schemas"]["FallbackPayloadBase"] & {
            /** @constant */
            candidate_eligible: false;
            /** @constant */
            reason: "LEGAL_JUDGMENT";
        };
        LegalJudgmentResponse: components["schemas"]["FallbackResponseBase"] & {
            fallback: components["schemas"]["LegalJudgmentFallback"];
            /** @constant */
            intent: "UNKNOWN";
        };
        Office: {
            address: string;
            id: string;
            /** Format: date */
            last_verified_at: string;
            /** Format: uri */
            map_url?: string | null;
            office_name: string;
            opening_hours?: string | null;
            phone: string;
            region: string;
            source_title: string;
            /** Format: uri */
            source_url?: string;
        };
        OfficeListResponse: {
            items: components["schemas"]["Office"][];
        };
        OutOfScopeFallback: components["schemas"]["FallbackPayloadBase"] & {
            /** @constant */
            candidate_eligible: false;
            /** @constant */
            reason: "OUT_OF_SCOPE";
        };
        OutOfScopeResponse: components["schemas"]["FallbackResponseBase"] & {
            fallback: components["schemas"]["OutOfScopeFallback"];
            /** @constant */
            intent: "OUT_OF_SCOPE";
        };
        PersonalLookupFallback: components["schemas"]["FallbackPayloadBase"] & {
            /** @constant */
            candidate_eligible: false;
            /** @constant */
            reason: "PERSONAL_LOOKUP";
        };
        PersonalLookupResponse: components["schemas"]["FallbackResponseBase"] & {
            fallback: components["schemas"]["PersonalLookupFallback"];
            /** @constant */
            intent: "UNKNOWN";
        };
        PrivacyUnresolvedFallback: components["schemas"]["FallbackPayloadBase"] & {
            /** @constant */
            candidate_eligible: false;
            /** @constant */
            message: "개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요.";
            next_actions: [
                "이름, 주소, 전화번호, 접수번호 등을 적지 마세요."
            ];
            office: null;
            /** @constant */
            reason: "PRIVACY_UNRESOLVED";
            /** @constant */
            title: "개인정보를 안전하게 처리하지 못했어요";
        };
        PrivacyUnresolvedResponse: components["schemas"]["FallbackResponseBase"] & {
            confidence: null;
            fallback: components["schemas"]["PrivacyUnresolvedFallback"];
            /** @constant */
            intent: "UNKNOWN";
        };
        ReadyResponse: {
            /** @constant */
            status: "ready";
        };
        ReasonConfirmationRequest: {
            reason: components["schemas"]["StoredFailureReason"];
        };
        ReasonConfirmationResponse: {
            /** Format: uuid */
            id: string;
            /** @constant */
            status: "REASON_CONFIRMED";
        };
        ServiceUnavailableEnvelope: {
            error: {
                /** @constant */
                code: "SERVICE_UNAVAILABLE";
                message: string;
                /** Format: uuid */
                request_id: string;
                /** @constant */
                retryable: true;
            };
        };
        Source: {
            /** Format: date */
            last_verified_at: string;
            source_id: string;
            title: string;
            /** Format: uri */
            url: string;
            used_fields?: string[];
        };
        /**
         * @description OUT_OF_SCOPE and CIVIC_SCOPE_GAP never create a failed_questions row.
         * @enum {string}
         */
        StoredFailureReason: "INSUFFICIENT_GROUNDING" | "PERSONAL_LOOKUP" | "LEGAL_JUDGMENT";
        SuccessResponse: components["schemas"]["ChatResponseBase"] & {
            /** @enum {unknown} */
            answer_mode: "GENERATED" | "TEMPLATE";
            /** @constant */
            answer_status: "SUCCESS";
            fallback?: null;
            followup_options?: [
            ];
            /** @enum {unknown} */
            intent: "MOVE_IN_RESIDENT_REGISTRATION" | "CERTIFICATE_ISSUANCE" | "BULKY_WASTE" | "LOCAL_TAX_GENERAL";
            office: components["schemas"]["Office"] | null;
            sources: [
                components["schemas"]["Source"],
                ...components["schemas"]["Source"][]
            ];
        };
        /** @enum {string} */
        SupportedIntent: "MOVE_IN_RESIDENT_REGISTRATION" | "CERTIFICATE_ISSUANCE" | "BULKY_WASTE" | "LOCAL_TAX_GENERAL";
        ValidationErrorDetail: {
            /** @constant */
            code: "VALIDATION_ERROR";
            /** @constant */
            message: "입력값을 확인해 주세요.";
            /** Format: uuid */
            request_id: string;
            /** @constant */
            retryable: false;
        };
        ValidationErrorEnvelope: {
            error: components["schemas"]["ValidationErrorDetail"];
        };
    };
    responses: {
        /** @description Stable local/private admin error without request input echo. */
        AdminError: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["AdminErrorEnvelope"];
            };
        };
        /** @description No safe response can be produced from approved ACTIVE KB and currently available dependencies. */
        ServiceUnavailable: {
            headers: {
                /** @description Suggested retry delay in seconds. */
                "Retry-After"?: number;
                [name: string]: unknown;
            };
            content: {
                /**
                 * @example {
                 *       "error": {
                 *         "code": "SERVICE_UNAVAILABLE",
                 *         "message": "잠시 후 다시 시도해 주세요.",
                 *         "request_id": "7d444840-9dc0-11d1-b245-5ffdce74fad2",
                 *         "retryable": true
                 *       }
                 *     }
                 */
                "application/json": components["schemas"]["ServiceUnavailableEnvelope"];
            };
        };
        /** @description Value-free request validation error without request input echo. */
        ValidationError: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ValidationErrorEnvelope"];
            };
        };
    };
    parameters: {
        /** @description Local/private demo actor only; not an authentication credential. */
        DemoActorId: string;
        /** @description Local/private role switch only; reject when admin routes are not privately gated. */
        DemoRole: "OPERATOR" | "APPROVER";
        /**
         * @description Optional UUID identifying one logical chat submission across retries. It is
         *     distinct from the per-HTTP-request correlation request_id. Reusing a completed
         *     key with the same request replays the stored safe response; reusing it with a
         *     different request is rejected without echoing input.
         */
        IdempotencyKey: string;
        IdPath: string;
    };
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    listCivicScopeGaps: {
        parameters: {
            query?: {
                status?: components["schemas"]["CivicScopeGapStatus"];
            };
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Separate masked civic scope-gap review queue */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CivicScopeGapListResponse"];
                };
            };
            403: components["responses"]["AdminError"];
            422: components["responses"]["AdminError"];
        };
    };
    reviewCivicScopeGap: {
        parameters: {
            query?: never;
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path: {
                id: components["parameters"]["IdPath"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CivicScopeGapReviewRequest"];
            };
        };
        responses: {
            /** @description Scope gap marked for planning or dismissal without creating KB */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CivicScopeGapReviewResponse"];
                };
            };
            403: components["responses"]["AdminError"];
            404: components["responses"]["AdminError"];
            409: components["responses"]["AdminError"];
            422: components["responses"]["AdminError"];
        };
    };
    listFailedQuestions: {
        parameters: {
            query?: {
                reason?: components["schemas"]["StoredFailureReason"];
                status?: components["schemas"]["FailedQuestionStatus"];
            };
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Masked failures only */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FailedQuestionListResponse"];
                };
            };
            403: components["responses"]["AdminError"];
        };
    };
    getFailedQuestion: {
        parameters: {
            query?: never;
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path: {
                id: components["parameters"]["IdPath"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Failed question detail */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FailedQuestionDetailResponse"];
                };
            };
            403: components["responses"]["AdminError"];
            404: components["responses"]["AdminError"];
        };
    };
    confirmFallbackReason: {
        parameters: {
            query?: never;
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path: {
                id: components["parameters"]["IdPath"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReasonConfirmationRequest"];
            };
        };
        responses: {
            /** @description Reason confirmed */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReasonConfirmationResponse"];
                };
            };
            403: components["responses"]["AdminError"];
            404: components["responses"]["AdminError"];
            409: components["responses"]["AdminError"];
            422: components["responses"]["AdminError"];
        };
    };
    listKBCandidates: {
        parameters: {
            query?: never;
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Candidate list */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KBCandidateListResponse"];
                };
            };
            403: components["responses"]["AdminError"];
        };
    };
    createKBCandidate: {
        parameters: {
            query?: never;
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KBCandidateCreate"];
            };
        };
        responses: {
            /** @description Draft candidate created */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KBCandidateCreateResponse"];
                };
            };
            403: components["responses"]["AdminError"];
            409: components["responses"]["AdminError"];
            422: components["responses"]["AdminError"];
        };
    };
    reviewKBCandidate: {
        parameters: {
            query?: never;
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path: {
                id: components["parameters"]["IdPath"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CandidateReviewRequest"];
            };
        };
        responses: {
            /** @description Review applied; approval activates KB atomically */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KBCandidateReviewResponse"];
                };
            };
            403: components["responses"]["AdminError"];
            404: components["responses"]["AdminError"];
            409: components["responses"]["AdminError"];
            422: components["responses"]["AdminError"];
        };
    };
    submitKBCandidate: {
        parameters: {
            query?: never;
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path: {
                id: components["parameters"]["IdPath"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Candidate pending approval */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KBCandidateSubmitResponse"];
                };
            };
            403: components["responses"]["AdminError"];
            404: components["responses"]["AdminError"];
            409: components["responses"]["AdminError"];
        };
    };
    getQualitySummary: {
        parameters: {
            query?: never;
            header: {
                /** @description Local/private demo actor only; not an authentication credential. */
                "X-Demo-Actor-Id": components["parameters"]["DemoActorId"];
                /** @description Local/private role switch only; reject when admin routes are not privately gated. */
                "X-Demo-Role": components["parameters"]["DemoRole"];
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Values labeled by source: event, evaluation, or mock */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            403: components["responses"]["AdminError"];
        };
    };
    createChatAnswer: {
        parameters: {
            query?: never;
            header?: {
                /**
                 * @description Optional UUID identifying one logical chat submission across retries. It is
                 *     distinct from the per-HTTP-request correlation request_id. Reusing a completed
                 *     key with the same request replays the stored safe response; reusing it with a
                 *     different request is rejected without echoing input.
                 */
                "Idempotency-Key"?: components["parameters"]["IdempotencyKey"];
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChatRequest"];
            };
        };
        responses: {
            /** @description Success, follow-up, or safe fallback */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChatResponse"];
                };
            };
            422: components["responses"]["ValidationError"];
            503: components["responses"]["ServiceUnavailable"];
        };
    };
    listOffices: {
        parameters: {
            query: {
                intent: components["schemas"]["SupportedIntent"];
                region: "아름동" | "도담동" | "조치원읍";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Official office matches */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OfficeListResponse"];
                };
            };
            422: components["responses"]["ValidationError"];
            503: components["responses"]["ServiceUnavailable"];
        };
    };
    health: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Process health */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    readiness: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Required dependencies and seed data ready */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadyResponse"];
                };
            };
            503: components["responses"]["ServiceUnavailable"];
        };
    };
}
