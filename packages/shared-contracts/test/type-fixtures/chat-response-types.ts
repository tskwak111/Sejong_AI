import type { components } from "../../src/generated/api.js";

type ChatResponse = components["schemas"]["ChatResponse"];
type Assert<T extends true> = T;
type AssertFalse<T extends false> = T;
type IsAssignable<From, To> = [From] extends [To] ? true : false;

type ValidSuccess = {
  request_id: string;
  answer_status: "SUCCESS";
  intent: "BULKY_WASTE";
  sources: [{ source_id: string; title: string; url: string; last_verified_at: string }];
  office: null;
  context_token: string;
  answer_mode: "TEMPLATE";
};

type InvalidSuccessWithPrivacy = {
  request_id: string;
  answer_status: "SUCCESS";
  intent: "UNKNOWN";
  sources: [];
  fallback: {
    reason: "PRIVACY_UNRESOLVED";
    title: "개인정보를 안전하게 처리하지 못했어요";
    message: "개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요.";
    next_actions: ["이름, 주소, 전화번호, 접수번호 등을 적지 마세요."];
    candidate_eligible: false;
    office: null;
  };
  context_token: null;
};

type ValidFollowup = {
  request_id: string;
  answer_status: "FOLLOWUP";
  intent: "UNKNOWN";
  sources: [];
  followup_options: [string];
  office: null;
  context_token: string;
};

type InvalidSuccessWithoutOffice = {
  request_id: string;
  answer_status: "SUCCESS";
  intent: "BULKY_WASTE";
  sources: [{ source_id: string; title: string; url: string; last_verified_at: string }];
  context_token: string;
};

type InvalidFollowupWithOffice = {
  request_id: string;
  answer_status: "FOLLOWUP";
  intent: "UNKNOWN";
  sources: [];
  followup_options: [string];
  office: { id: string };
  context_token: string;
};

type InvalidFallbackWithSources = {
  request_id: string;
  answer_status: "FALLBACK";
  intent: "OUT_OF_SCOPE";
  sources: [{ source_id: string; title: string; url: string; last_verified_at: string }];
  fallback: {
    reason: "OUT_OF_SCOPE";
    title: string;
    message: string;
    candidate_eligible: false;
  };
  context_token: null;
};

type InvalidFallbackWithContext = {
  request_id: string;
  answer_status: "FALLBACK";
  intent: "OUT_OF_SCOPE";
  sources: [];
  fallback: {
    reason: "OUT_OF_SCOPE";
    title: string;
    message: string;
    candidate_eligible: false;
  };
  context_token: string;
};

type ValidPrivacy = {
  request_id: string;
  answer_status: "FALLBACK";
  intent: "UNKNOWN";
  confidence: null;
  sources: [];
  fallback: {
    reason: "PRIVACY_UNRESOLVED";
    title: "개인정보를 안전하게 처리하지 못했어요";
    message: "개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요.";
    next_actions: ["이름, 주소, 전화번호, 접수번호 등을 적지 마세요."];
    candidate_eligible: false;
    office: null;
  };
  context_token: null;
};

type _ValidSuccessCompiles = Assert<IsAssignable<ValidSuccess, ChatResponse>>;
type _ValidPrivacyCompiles = Assert<IsAssignable<ValidPrivacy, ChatResponse>>;
type _ValidFollowupCompiles = Assert<IsAssignable<ValidFollowup, ChatResponse>>;
type _SuccessPrivacyRejected = AssertFalse<
  IsAssignable<InvalidSuccessWithPrivacy, ChatResponse>
>;
type _FallbackSourcesRejected = AssertFalse<
  IsAssignable<InvalidFallbackWithSources, ChatResponse>
>;
type _FallbackContextRejected = AssertFalse<
  IsAssignable<InvalidFallbackWithContext, ChatResponse>
>;
type _SuccessWithoutOfficeRejected = AssertFalse<
  IsAssignable<InvalidSuccessWithoutOffice, ChatResponse>
>;
type _FollowupOfficeRejected = AssertFalse<
  IsAssignable<InvalidFollowupWithOffice, ChatResponse>
>;
type SuccessChatResponse = Extract<ChatResponse, { answer_status: "SUCCESS" }>;
type _SuccessAnswerModeAcceptsGenerated = Assert<
  IsAssignable<"GENERATED", SuccessChatResponse["answer_mode"]>
>;
type _SuccessAnswerModeAcceptsTemplate = Assert<
  IsAssignable<"TEMPLATE", SuccessChatResponse["answer_mode"]>
>;
