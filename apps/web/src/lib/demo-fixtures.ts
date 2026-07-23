/**
 * 데모 5문항 fixture + 시민↔이음센터 공유 인메모리 스토어 (CLAUDE.md §10).
 *
 * - 모든 데이터는 contracts/openapi-v1.yaml 생성 타입(ChatResponse,
 *   FailedQuestion, KBCandidateSummary)에 정확히 맞춘다.
 * - CHAT_UI_MODE/ADMIN_UI_MODE=fixture일 때만 사용되는 로컬 시연 버전이다
 *   (제안서 7.4). fixture와 actual 데이터는 절대 섞지 않는다.
 * - 같은 탭 세션 동안 시민 화면 폴백 → 실패 질문 큐 "도착"이 보이도록
 *   모듈 스코프 배열을 mock DB로 쓴다 (브라우저 스토리지 저장 금지 §9).
 *   새로고침 시 초기 fixture로 리셋되며, 데모 #4 건은 fixture에 '신규'로
 *   상시 존재하므로 데모 #5는 항상 완주 가능하다.
 * - 계약 불변식 준수: OUT_OF_SCOPE·PRIVACY_UNRESOLVED는 실패 질문 행을
 *   만들지 않고, candidate_eligible=true는 INSUFFICIENT_GROUNDING뿐이며,
 *   APPROVED 후보는 data_origin=OFFICIAL일 때만 가능하다.
 */
import type { components } from "../../../../packages/shared-contracts/src/generated/api";
import type { ChatRequest, ChatResponse, ChatTransport, Office } from "./chat-api";
import type { AdminActor, AdminTransport } from "./admin-api";
import { isRegion, type Region } from "./labels";

type FailedQuestion = components["schemas"]["FailedQuestion"];
type KBCandidateCreate = components["schemas"]["KBCandidateCreate"];
type KBCandidateSummary = components["schemas"]["KBCandidateSummary"];
type StoredFailureReason = components["schemas"]["StoredFailureReason"];
type SupportedIntent = components["schemas"]["SupportedIntent"];

// 로딩 상태가 보이도록 응답 지연을 흉내낸다 (테스트에서는 지연 없음)
const IS_TEST = process.env.NODE_ENV === "test";
const DEMO_DELAY_MS = IS_TEST ? 0 : 600;
const ADMIN_DELAY_MS = IS_TEST ? 0 : 300;

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function uuid(): string {
  return crypto.randomUUID();
}

function plusDays(iso: string, days: number): string {
  return new Date(Date.parse(iso) + days * 86_400_000).toISOString();
}

/* ---------- 공식 기관 (Office) - 시연용 값 ---------- */

const VERIFIED_AT = "2026-07-15";

function communityOffice(region: Region): Office {
  return {
    id: `office-${region}`,
    region,
    office_name: `${region} 행정복지센터`,
    address: `세종특별자치시 ${region} 행정복지센터`,
    phone: "044-300-3000",
    opening_hours: "평일 09:00~18:00",
    map_url: null,
    source_title: "세종특별자치시 읍면동 안내",
    source_url: "https://www.sejong.go.kr",
    last_verified_at: VERIFIED_AT,
  };
}

const WASTE_OFFICE: Office = {
  id: "office-waste",
  region: "세종특별자치시",
  office_name: "세종시설관리공단",
  address: "세종특별자치시",
  phone: "044-300-3000",
  opening_hours: "평일 09:00~18:00",
  map_url: null,
  source_title: "세종시 대형폐기물 배출 안내",
  source_url: "https://www.sejong.go.kr",
  last_verified_at: VERIFIED_AT,
};

const TAX_OFFICE: Office = {
  id: "office-tax",
  region: "세종특별자치시",
  office_name: "세종특별자치시 세정과",
  address: "세종특별자치시 한누리대로 2130",
  phone: "044-300-3000",
  opening_hours: "평일 09:00~18:00",
  map_url: null,
  source_title: "세종특별자치시 조직 안내",
  source_url: "https://www.sejong.go.kr",
  last_verified_at: VERIFIED_AT,
};

const CALL_CENTER_OFFICE: Office = {
  id: "office-call-center",
  region: "세종특별자치시",
  office_name: "세종특별자치시 민원콜센터",
  address: "세종특별자치시 한누리대로 2130",
  phone: "044-120",
  opening_hours: "평일 09:00~18:00",
  map_url: null,
  source_title: "세종특별자치시 민원 안내",
  source_url: "https://www.sejong.go.kr",
  last_verified_at: VERIFIED_AT,
};

/* ---------- 데모 응답 (계약형 ChatResponse) ---------- */

const CONTEXT_TOKEN = "demo-signed-context-token";

/** 데모 #1: "전입신고는 언제까지 해야 하나요?" - SUCCESS */
function moveInAnswer(region: Region | null): ChatResponse {
  return {
    request_id: uuid(),
    answer_status: "SUCCESS",
    intent: "MOVE_IN_RESIDENT_REGISTRATION",
    confidence: 0.96,
    summary:
      "이사한 날부터 14일 이내에 새로운 거주지의 읍·면·동 주민센터 또는 정부24에서 전입신고를 해야 합니다. 기간이 지나면 과태료(5만 원 이하)가 부과될 수 있습니다.",
    procedure_steps: [
      "이사 완료 후 14일 이내에 신고를 준비합니다.",
      "정부24 온라인 신고 또는 새 거주지 주민센터 방문 중 하나를 선택합니다.",
      "세대주 확인이 필요한 경우 세대주가 정부24에서 확인하거나 함께 방문합니다.",
      "신고 완료 후 처리 결과를 확인합니다.",
    ],
    required_documents: [
      "신분증 (주민등록증, 운전면허증 등)",
      "온라인 신고 시 본인 인증 수단 (공동·금융인증서 등)",
    ],
    processing_time: "근무시간 내 즉시 처리 (온라인은 담당자 확인 후 처리)",
    fee: "무료",
    department: "세종특별자치시 각 읍·면·동 주민센터",
    sources: [
      {
        source_id: "KB-MOVE-01",
        title: "전입신고 기본 안내",
        url: "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016",
        last_verified_at: VERIFIED_AT,
      },
    ],
    followup_options: [],
    fallback: null,
    office: region ? communityOffice(region) : null,
    context_token: CONTEXT_TOKEN,
  };
}

/** 데모 #2: 대형폐기물 + 지역 확정 - SUCCESS */
function bulkyWasteAnswer(region: Region): ChatResponse {
  return {
    request_id: uuid(),
    answer_status: "SUCCESS",
    intent: "BULKY_WASTE",
    confidence: 0.93,
    summary: `${region}은 인터넷 또는 주민센터에서 배출 신고 후 받은 스티커(납부필증)를 부착하여, 신고 시 지정한 배출일 전날 저녁 지정 장소에 내놓으면 됩니다.`,
    procedure_steps: [
      "세종시 대형폐기물 인터넷 신고 또는 주민센터 방문 신고를 합니다.",
      "품목·규격에 따른 수수료를 납부하고 납부필증(스티커)을 출력·수령합니다.",
      "납부필증을 폐기물에 잘 보이게 부착합니다.",
      `지정한 배출일 전날 저녁, ${region} 지정 배출 장소(자택 앞 등)에 내놓습니다.`,
    ],
    required_documents: ["별도 서류 없음 (신고 시 배출 품목·규격 정보 필요)"],
    processing_time: "신고 후 지정 배출일에 수거 (통상 신고일로부터 2~3일 내)",
    fee: "품목·규격별 수수료 상이 (예: 의자 2,000원~ / 장롱 폭 1m당 4,000원~)",
    department: "세종시설관리공단",
    sources: [
      {
        source_id: "KB-WASTE-01",
        title: "세종시 대형폐기물 배출 안내",
        url: "https://www.sejong.go.kr",
        last_verified_at: VERIFIED_AT,
      },
    ],
    followup_options: [],
    fallback: null,
    office: WASTE_OFFICE,
    context_token: CONTEXT_TOKEN,
  };
}

/** 데모 #2 파생: 지역이 없으면 동을 좁히는 FOLLOWUP (SFR-004).
 *  계약상 followup_options는 문자열 배열이라 지역명 3개를 그대로 담는다 -
 *  UI가 지역명 선택지를 selected_region으로 승격해 원 질문을 재전송한다. */
function bulkyWasteRegionFollowup(): ChatResponse {
  return {
    request_id: uuid(),
    answer_status: "FOLLOWUP",
    intent: "BULKY_WASTE",
    confidence: null,
    summary: null,
    procedure_steps: [],
    required_documents: [],
    processing_time: null,
    fee: null,
    department: null,
    sources: [],
    followup_options: ["아름동", "도담동", "조치원읍"],
    fallback: null,
    office: null,
    context_token: CONTEXT_TOKEN,
  };
}

/** 데모 #3: "이사했는데 뭐 해야 하나요?" - FOLLOWUP */
function moveFollowup(): ChatResponse {
  return {
    request_id: uuid(),
    answer_status: "FOLLOWUP",
    intent: "UNKNOWN",
    confidence: null,
    summary: null,
    procedure_steps: [],
    required_documents: [],
    processing_time: null,
    fee: null,
    department: null,
    sources: [],
    followup_options: [
      "전입신고는 언제까지 해야 하나요?",
      "대형폐기물은 언제 내놓나요?",
      "주민등록등본은 어떻게 발급받나요?",
    ],
    fallback: null,
    office: null,
    context_token: CONTEXT_TOKEN,
  };
}

/** 데모 #3 파생: 증명서 발급 SUCCESS (선택지 완주용) */
function certificateAnswer(region: Region | null): ChatResponse {
  return {
    request_id: uuid(),
    answer_status: "SUCCESS",
    intent: "CERTIFICATE_ISSUANCE",
    confidence: 0.95,
    summary:
      "주민등록등본은 정부24에서 온라인 발급(무료)하거나, 가까운 읍·면·동 주민센터와 무인민원발급기에서 발급받을 수 있습니다.",
    procedure_steps: [
      "정부24 접속 후 본인 인증을 합니다.",
      "'주민등록표 등본(초본)' 발급을 신청합니다.",
      "필요한 표시 항목(세대원, 주소 변동 이력 등)을 선택합니다.",
      "PDF 저장 또는 프린터로 출력합니다.",
    ],
    required_documents: [
      "본인 인증 수단 (공동·금융인증서, 간편인증 등)",
      "방문 발급 시 신분증",
    ],
    processing_time: "즉시 발급",
    fee: "온라인 무료 / 주민센터 400원 / 무인발급기 200원",
    department: "세종특별자치시 각 읍·면·동 주민센터",
    sources: [
      {
        source_id: "KB-CERT-01",
        title: "주민등록표 등본 발급 안내",
        url: "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000015",
        last_verified_at: VERIFIED_AT,
      },
    ],
    followup_options: [],
    fallback: null,
    office: region ? communityOffice(region) : null,
    context_token: CONTEXT_TOKEN,
  };
}

/** FALLBACK 공통 골격 - FALLBACK은 context_token이 항상 null이다 (계약) */
function fallbackResponse(
  intent: components["schemas"]["Intent"],
  fallback: NonNullable<components["schemas"]["ChatResponseBase"]["fallback"]>,
): ChatResponse {
  return {
    request_id: uuid(),
    answer_status: "FALLBACK",
    intent,
    confidence: null,
    summary: null,
    procedure_steps: [],
    required_documents: [],
    processing_time: null,
    fee: null,
    department: null,
    sources: [],
    followup_options: [],
    fallback,
    office: null,
    context_token: null,
  } as ChatResponse;
}

/** 데모 #4: "제 자동차세 얼마 나왔나요?" - PERSONAL_LOOKUP 폴백 */
function personalLookupFallback(): ChatResponse {
  return fallbackResponse("UNKNOWN", {
    reason: "PERSONAL_LOOKUP",
    title: "본인 확인이 필요한 정보예요",
    message:
      "개인별 자동차세 부과 내역은 본인 확인이 필요한 정보라서 여기서는 알려드릴 수 없어요. 안전하게 공식 조회 채널로 연결해 드립니다. 위택스에서 본인 인증 후 바로 확인하실 수 있어요.",
    next_actions: ["위택스에서 본인 인증 후 조회하기", "세정과에 전화 문의하기"],
    candidate_eligible: false,
    office: TAX_OFFICE,
  });
}

/** 범위 밖 질문 공통 폴백 - 실패 질문 행은 만들지 않는다 (계약) */
function outOfScopeFallback(): ChatResponse {
  return fallbackResponse("OUT_OF_SCOPE", {
    reason: "OUT_OF_SCOPE",
    title: "다른 창구에서 도와드릴 민원이에요",
    message:
      "지금은 전입·주민등록, 대형폐기물, 증명서 발급, 지방세 4개 분야를 안내해 드리고 있어요. 다른 민원은 세종시 대표 민원 창구로 안전하게 연결해 드립니다.",
    next_actions: [],
    candidate_eligible: false,
    office: CALL_CENTER_OFFICE,
  });
}

/** 근거 부족 폴백 - KB 후보 전환 대상 (candidate_eligible: true) */
function insufficientGroundingFallback(intent: SupportedIntent): ChatResponse {
  return fallbackResponse(intent, {
    reason: "INSUFFICIENT_GROUNDING",
    title: "확인 후 안내해 드릴게요",
    message:
      "지원 범위의 민원이지만 아직 승인된 근거 문서가 부족해요. 지어내서 답하지 않고, 담당 부서 확인 후 안내가 보강됩니다.",
    next_actions: ["담당 부서에 전화로 먼저 확인하기", "정부24에서 관련 안내 찾아보기"],
    candidate_eligible: true,
    office: communityOffice("아름동"),
  });
}

/** 개인정보 미해소 폴백 - 계약 고정 문구 그대로 */
function privacyUnresolvedFallback(): ChatResponse {
  return fallbackResponse("UNKNOWN", {
    reason: "PRIVACY_UNRESOLVED",
    title: "개인정보를 안전하게 처리하지 못했어요",
    message: "개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요.",
    next_actions: ["이름, 주소, 전화번호, 접수번호 등을 적지 마세요."],
    candidate_eligible: false,
    office: null,
  });
}

/* ---------- 실패 질문 큐 + KB 후보 인메모리 스토어 ---------- */

/** 데모 #5 초안 생성 대상 - 전입신고 대리인 위임장 (근거 부족, 텍스트 보관) */
export const CURATED_ISG_FAILURE_ID = "10000000-0000-4000-8000-000000000001";
const DEMO_PERSONAL_FAILURE_ID = "10000000-0000-4000-8000-000000000002";
const PURGED_FAILURE_ID = "10000000-0000-4000-8000-000000000003";

function initialFailures(): FailedQuestion[] {
  const isgCreated = "2026-07-21T09:12:00Z";
  const personalCreated = "2026-07-22T10:30:00Z";
  const purgedCreated = "2026-06-18T11:00:00Z";
  return [
    {
      id: DEMO_PERSONAL_FAILURE_ID,
      // 데모 #4 건 - fixture에 '신규'로 상시 존재해야 데모 #5가 항상 완주된다 (§10)
      masked_question: "제 자동차세 얼마 나왔나요?",
      intent: "LOCAL_TAX_GENERAL",
      fallback_reason: "PERSONAL_LOOKUP",
      candidate_eligible: false,
      status: "NEW",
      created_at: personalCreated,
      text_expires_at: plusDays(personalCreated, 30),
      text_purged_at: null,
    },
    {
      id: CURATED_ISG_FAILURE_ID,
      masked_question: "전입신고를 대리인이 하면 위임장 공증이 필요한가요?",
      intent: "MOVE_IN_RESIDENT_REGISTRATION",
      fallback_reason: "INSUFFICIENT_GROUNDING",
      candidate_eligible: true,
      status: "NEW",
      created_at: isgCreated,
      text_expires_at: plusDays(isgCreated, 30),
      text_purged_at: null,
    },
    {
      // 30일 경과로 텍스트가 파기된 행 - NULL이어도 깨지지 않게 렌더링 (CLAUDE.md §6)
      id: PURGED_FAILURE_ID,
      masked_question: null,
      intent: "LOCAL_TAX_GENERAL",
      fallback_reason: "INSUFFICIENT_GROUNDING",
      candidate_eligible: true,
      status: "REASON_CONFIRMED",
      created_at: purgedCreated,
      text_expires_at: plusDays(purgedCreated, 30),
      text_purged_at: plusDays(purgedCreated, 30),
    },
  ];
}

let failureQueue: FailedQuestion[] = initialFailures();
let kbCandidates: KBCandidateSummary[] = [];

/** 테스트 전용 - 스토어를 초기 fixture로 되돌린다 */
export function resetDemoStore(): void {
  failureQueue = initialFailures();
  kbCandidates = [];
}

/** 시민 화면 폴백 발생 시 실패 질문 큐에 신규 건 적재 (fixture 전용).
 *  질문 마스킹은 백엔드 책임이라 mock에서는 원문을 그대로 쓴다.
 *  저장 대상은 StoredFailureReason 3종뿐이다 (OUT_OF_SCOPE·PRIVACY 미저장). */
function enqueueFailure(
  question: string,
  reason: StoredFailureReason,
  intent: SupportedIntent,
): void {
  const createdAt = new Date().toISOString();
  failureQueue = [
    {
      id: uuid(),
      masked_question: question,
      intent,
      fallback_reason: reason,
      candidate_eligible: reason === "INSUFFICIENT_GROUNDING",
      status: "NEW",
      created_at: createdAt,
      text_expires_at: plusDays(createdAt, 30),
      text_purged_at: null,
    },
    ...failureQueue,
  ];
}

/* ---------- mock 라우터 (키워드 매칭 - fixture 전용 로직) ---------- */

/** 개인정보 패턴(전화번호·주민번호 유사) - PRIVACY_UNRESOLVED 시연용 */
const PRIVACY_PATTERN = /(\d{6}[-\s]?\d{7})|(01[016789][-\s]?\d{3,4}[-\s]?\d{4})/;

export function routeDemoAnswer(request: ChatRequest): ChatResponse {
  const question = request.question;
  const q = question.replace(/\s/g, "");
  const region: Region | null =
    request.selected_region && isRegion(request.selected_region)
      ? request.selected_region
      : null;

  // 개인정보가 남아 있으면 안전 폴백 (계약 고정 문구)
  if (PRIVACY_PATTERN.test(question)) {
    return privacyUnresolvedFallback();
  }

  // 데모 #5 파생: 근거 부족 시연 (전입신고 대리인·위임장)
  if (q.includes("위임장") || (q.includes("대리") && q.includes("전입"))) {
    enqueueFailure(question, "INSUFFICIENT_GROUNDING", "MOVE_IN_RESIDENT_REGISTRATION");
    return insufficientGroundingFallback("MOVE_IN_RESIDENT_REGISTRATION");
  }

  // 데모 #1
  if (q.includes("전입신고") || q.includes("전입")) {
    return moveInAnswer(region);
  }

  // 데모 #2 - 질문 속 동 표기와 선택 지역 모두 지원.
  // 선택 지역(selected_region)이 질문 텍스트 파싱보다 우선한다 ("동 변경" 우선).
  if (q.includes("대형폐기물") || q.includes("폐기물")) {
    const regionInQuestion = ["아름동", "도담동", "조치원읍"].find((dong) =>
      q.includes(dong),
    ) as Region | undefined;
    const dong = region ?? regionInQuestion ?? null;
    if (dong) return bulkyWasteAnswer(dong);
    return bulkyWasteRegionFollowup();
  }

  // 데모 #3
  if (q.includes("이사")) {
    return moveFollowup();
  }

  // 데모 #3 파생 - 증명서
  if (q.includes("등본") || q.includes("증명서")) {
    return certificateAnswer(region);
  }

  // 데모 #4
  if (q.includes("자동차세") || q.includes("재산세") || q.includes("지방세")) {
    enqueueFailure(question, "PERSONAL_LOOKUP", "LOCAL_TAX_GENERAL");
    return personalLookupFallback();
  }

  return outOfScopeFallback();
}

/** 시민 대화 fixture transport - CHAT_UI_MODE=fixture 전용 */
export function createFixtureChatTransport(): ChatTransport {
  return {
    async send(request) {
      // 로딩 스켈레톤이 보이도록 응답 지연을 흉내낸다
      await delay(DEMO_DELAY_MS);
      return routeDemoAnswer(request);
    },
  };
}

/* ---------- KB 후보 초안 자동 구성 (AI 초안 시뮬레이션) ---------- */

/** 승인 가능한 공식 출처 URL - 이 출처로 만든 초안만 data_origin=OFFICIAL이
 *  되어 ACTIVE 승인까지 완주할 수 있다. 그 외 초안은 MOCK으로 승인이 막힌다
 *  (계약 불변식: APPROVED는 OFFICIAL만). */
const OFFICIAL_SOURCE_URLS = new Set([
  "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016",
]);

/** 실패 질문 → 계약형 KB 후보 초안. 계약상 source_url은 생성 시점부터
 *  https 필수라 '미검증(null)' 표현이 불가능하다 - 검증 책임은 승인 전
 *  체크리스트(사람 판정)로 남긴다. */
export function buildCandidateDraft(failure: FailedQuestion): KBCandidateCreate {
  const question = failure.masked_question ?? "(보관 기간 경과)";

  if (failure.id === CURATED_ISG_FAILURE_ID) {
    // 데모 #5 특화 초안 - 공식 출처(정부24) 기반이라 승인(ACTIVE)까지 가능
    return {
      failed_question_id: failure.id,
      title: "전입신고 대리인 위임 요건",
      representative_question: "대리인이 전입신고할 때 위임장이 필요한가요?",
      category: "MOVE_IN_RESIDENT_REGISTRATION",
      answer_summary:
        "대리인이 전입신고를 하는 경우 위임장과 위임인·대리인의 신분증이 필요합니다. 위임장 공증은 일반적으로 요구되지 않으나, 세대주 확인이 필요한 경우가 있습니다.",
      procedure_steps: [
        "위임장을 작성합니다 (전입자 서명 필요).",
        "위임인·대리인 신분증을 준비합니다.",
        "새 거주지 읍·면·동 주민센터에 방문해 신고합니다.",
      ],
      required_documents: ["위임장", "위임인 신분증", "대리인 신분증"],
      processing_time: "근무시간 내 즉시 처리",
      fee: "무료",
      department: "세종특별자치시 각 읍·면·동 주민센터",
      source_title: "전입신고 기본 안내",
      source_url: "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016",
      last_verified_at: VERIFIED_AT,
      caution: "개인별 세대 관계(세대주 확인 필요 여부 등)는 공식 페이지에서 확인하세요.",
    };
  }

  return {
    failed_question_id: failure.id,
    title: `${question} (KB 후보 초안)`,
    representative_question: question,
    category: failure.intent,
    answer_summary: `실패 질문 "${question}"에 대해 승인된 문서 근거가 부족했습니다. 담당 부서 확인 후 답변 요약을 보완해 주세요.`,
    procedure_steps: ["담당 부서 확인 후 절차를 입력해 주세요."],
    required_documents: [],
    processing_time: null,
    fee: null,
    department: "세종특별자치시 민원콜센터",
    source_title: "출처 확인 필요 (시연용 샘플)",
    source_url: "https://www.sejong.go.kr",
    last_verified_at: VERIFIED_AT,
    caution: null,
  };
}

/* ---------- 이음센터 fixture transport ---------- */

function requireOperator(actor: AdminActor): void {
  if (actor.role !== "OPERATOR") throw new Error("forbidden");
}

function createAdminFixture(): AdminTransport {
  return {
    async listFailedQuestions() {
      await delay(ADMIN_DELAY_MS);
      return { items: failureQueue.map((f) => ({ ...f })), total: failureQueue.length };
    },
    async getFailedQuestion(_actor, id) {
      await delay(ADMIN_DELAY_MS);
      const item = failureQueue.find((entry) => entry.id === id);
      if (!item) throw new Error("not found");
      return { item: { ...item } };
    },
    async confirmReason(actor, id, request) {
      requireOperator(actor);
      await delay(ADMIN_DELAY_MS);
      const target = failureQueue.find((entry) => entry.id === id);
      if (!target) throw new Error("not found");
      if (target.status !== "NEW") throw new Error("invalid state");
      failureQueue = failureQueue.map((entry) =>
        entry.id === id
          ? {
              ...entry,
              fallback_reason: request.reason,
              candidate_eligible: request.reason === "INSUFFICIENT_GROUNDING",
              status: "REASON_CONFIRMED",
            }
          : entry,
      );
      return { id, status: "REASON_CONFIRMED" };
    },
    async listCandidates() {
      await delay(ADMIN_DELAY_MS);
      return { items: kbCandidates.map((c) => ({ ...c })), total: kbCandidates.length };
    },
    async createCandidate(actor, request) {
      requireOperator(actor);
      await delay(ADMIN_DELAY_MS);
      if (kbCandidates.some((c) => c.failed_question_id === request.failed_question_id)) {
        throw new Error("duplicate candidate");
      }
      const id = uuid();
      const nowIso = new Date().toISOString();
      kbCandidates = [
        {
          id,
          failed_question_id: request.failed_question_id,
          title: request.title,
          representative_question: request.representative_question,
          data_origin: OFFICIAL_SOURCE_URLS.has(request.source_url) ? "OFFICIAL" : "MOCK",
          category: request.category,
          answer_summary: request.answer_summary,
          procedure_steps: request.procedure_steps ?? [],
          required_documents: request.required_documents ?? [],
          processing_time: request.processing_time ?? null,
          fee: request.fee ?? null,
          department: request.department,
          source_title: request.source_title,
          source_url: request.source_url,
          last_verified_at: request.last_verified_at,
          caution: request.caution ?? null,
          status: "DRAFTED",
          created_by: actor.actorId,
          reviewed_by: null,
          review_comment: null,
          approved_at: null,
          activated_kb_id: null,
          created_at: nowIso,
          updated_at: nowIso,
        },
        ...kbCandidates,
      ];
      return { id, status: "DRAFTED" };
    },
    async submitCandidate(actor, id) {
      requireOperator(actor);
      await delay(ADMIN_DELAY_MS);
      const target = kbCandidates.find((entry) => entry.id === id);
      if (!target) throw new Error("not found");
      if (target.status !== "DRAFTED") throw new Error("invalid state");
      kbCandidates = kbCandidates.map((entry) =>
        entry.id === id
          ? { ...entry, status: "PENDING_APPROVAL", updated_at: new Date().toISOString() }
          : entry,
      );
      return { id, status: "PENDING_APPROVAL" };
    },
    async reviewCandidate(actor, id, request) {
      await delay(ADMIN_DELAY_MS);
      const current = kbCandidates.find((entry) => entry.id === id);
      if (actor.role !== "APPROVER" || !current) throw new Error("forbidden");
      if (current.created_by === actor.actorId) throw new Error("self review forbidden");
      if (current.status !== "PENDING_APPROVAL") throw new Error("invalid state");
      if (!request.review_comment.trim()) throw new Error("comment required");
      if (request.decision === "APPROVED" && current.data_origin !== "OFFICIAL") {
        // 계약 불변식: 시연용(MOCK) 후보는 ACTIVE로 승인할 수 없다
        throw new Error("mock candidates cannot become ACTIVE");
      }
      const nowIso = new Date().toISOString();
      kbCandidates = kbCandidates.map((entry) =>
        entry.id === id
          ? {
              ...entry,
              status: request.decision,
              reviewed_by: actor.actorId,
              review_comment: request.review_comment,
              approved_at: request.decision === "APPROVED" ? nowIso : null,
              activated_kb_id: request.decision === "APPROVED" ? uuid() : null,
              updated_at: nowIso,
            }
          : entry,
      );
      return { id, status: request.decision };
    },
  };
}

let fixtureAdminTransport: AdminTransport | null = null;

/** 이음센터 fixture transport 싱글턴 - 페이지 간 같은 스토어를 공유해
 *  실패 질문 큐 → KB 후보 → 승인 흐름(데모 #5)이 이어진다. */
export function getFixtureAdminTransport(): AdminTransport {
  fixtureAdminTransport ??= createAdminFixture();
  return fixtureAdminTransport;
}

/* ---------- Overview KPI (시연 지표) ----------
 * 계약의 /api/v1/admin/quality-summary는 200 응답 스키마가 정의되어 있지
 * 않아 typed 연동이 불가능하다 (계약 변경 필요 항목으로 보고).
 * Overview KPI 카드는 fixture 모드에서만 이 시연 값을 쓴다. */
export const DEMO_KPI = {
  total_questions: 128,
  auto_answer_rate: 0.72,
  fallback_rate: 0.19,
  avg_response_seconds: 2.4,
  source_citation_rate: 1.0,
} as const;

export type DemoKpi = typeof DEMO_KPI;
