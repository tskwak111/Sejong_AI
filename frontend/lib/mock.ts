/**
 * mock 응답 fixture - CLAUDE.md §10 데모 5문항을 정확히 포함한다.
 * NEXT_PUBLIC_USE_MOCK=true + 로컬 실행 = 로컬 시연 버전 (제안서 7.4).
 *
 * [임시값 근거] 2026-07-22, 무인 세션 결정사항:
 * - KB ID/문서명, 기관 연락처, 배출 요일 등은 시연용 mock 값이다.
 *   실KB 구축 시 백엔드 응답으로 대체된다.
 * - 질문 매칭은 키워드 기반 단순 라우팅 (mock 전용 로직).
 */

import type {
  ChatResponse,
  CivilCategory,
  FailureQueueItem,
  FailureStatus,
  FallbackCode,
  FollowupResponse,
  KbCandidate,
  KbCandidateStatus,
  KbDraftSchema,
  KbRejectReason,
  SuccessResponse,
} from "@/types/api";

/** 세종시 동 목록 (RegionSelect 공용) - 시연용 일부 */
export const SEJONG_DONGS = [
  "아름동",
  "도담동",
  "고운동",
  "종촌동",
  "한솔동",
  "새롬동",
  "다정동",
  "보람동",
  "소담동",
  "대평동",
] as const;

/* ---------- 데모 #1: "전입신고는 언제까지 해야 하나요?" ---------- */
export const DEMO1_MOVE_IN: SuccessResponse = {
  result_type: "SUCCESS",
  category: "MOVE_IN",
  answer_summary:
    "이사한 날부터 14일 이내에 새로운 거주지의 읍·면·동 주민센터 또는 정부24에서 전입신고를 해야 합니다. 기간이 지나면 과태료(5만 원 이하)가 부과될 수 있습니다.",
  procedure_steps: [
    "이사 완료 후 14일 이내에 신고를 준비합니다.",
    "정부24 온라인 신고 또는 새 거주지 주민센터 방문 중 하나를 선택합니다.",
    "세대주 확인이 필요한 경우 세대주가 정부24에서 확인하거나 함께 방문합니다.",
    "신고 완료 후 처리 결과를 확인합니다.",
  ],
  // v3 §6-1-3: 신청 방법 2갈래 (온라인/방문) - 시안 1b 문구 기준
  application_methods: [
    { title: "온라인 신청", description: "정부24에서 24시간 신청할 수 있어요" },
    {
      title: "주민센터 방문",
      description: "가까운 읍·면·동 행정복지센터, 평일 09:00~18:00",
    },
  ],
  required_documents: ["신분증 (주민등록증, 운전면허증 등)", "온라인 신고 시 본인 인증 수단 (공동·금융인증서 등)"],
  processing_time: "근무시간 내 즉시 처리 (온라인은 담당자 확인 후 처리)",
  fee: "무료",
  caution:
    "개인별 세대 관계(세대주 확인 필요 여부 등)는 공식 페이지에서 확인하세요.",
  fallback_contact: {
    name: "세종특별자치시 각 읍·면·동 주민센터",
    phone: "044-300-3000 (세종시청 대표)",
    hours: "평일 09:00~18:00",
  },
  sources: [
    {
      kb_id: "KB-MOVE-01",
      title: "전입신고 기본 안내",
      url: "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016",
      last_verified_at: "2026-07-15",
    },
  ],
  deep_link: {
    label: "정부24에서 바로 신청",
    url: "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016",
  },
  // 제안서 3.2: 전입신고 안내 시 대형폐기물 배출도 안내 (v2 §4-2-9)
  related_question: "아름동에서 대형폐기물은 언제 내놓나요?",
};

/* ---------- 데모 #2: "아름동에서 대형폐기물은 언제 내놓나요?" ---------- */

/**
 * 대형폐기물 담당 기관 - 데모 #2의 "세종시설관리공단 실데이터 기반 안내"
 * (제안서 7.5 · 6.3 "세종시설관리공단은 실연락처·운영시간 확보") 근거 값.
 *
 * TODO(데이터 팀·오현송): 아래는 시연용 임시값이다. 데이터 팀이 확보한
 * 세종시설관리공단 실연락처·실운영시간으로 이 상수만 교체하면
 * 대형폐기물 관련 응답 전체에 반영된다.
 */
export const BULKY_WASTE_CONTACT = {
  name: "세종시설관리공단",
  phone: "044-300-3000 (세종시청 대표, 자동 안내)", // TODO: 공단 실번호로 교체
  hours: "평일 09:00~18:00", // TODO: 공단 실운영시간으로 교체
} as const;

/** 지역(동)이 확정된 경우의 SUCCESS. region 값에 따라 문구를 만든다. */
export function makeBulkyWasteAnswer(region: string): SuccessResponse {
  return {
    result_type: "SUCCESS",
    category: "BULKY_WASTE",
    region,
    answer_summary: `${region}은 인터넷 또는 주민센터에서 배출 신고 후 받은 스티커(납부필증)를 부착하여, 신고 시 지정한 배출일 전날 저녁 지정 장소에 내놓으면 됩니다.`,
    procedure_steps: [
      "세종시 대형폐기물 인터넷 신고 또는 주민센터 방문 신고를 합니다.",
      "품목·규격에 따른 수수료를 납부하고 납부필증(스티커)을 출력·수령합니다.",
      "납부필증을 폐기물에 잘 보이게 부착합니다.",
      `지정한 배출일 전날 저녁, ${region} 지정 배출 장소(자택 앞 등)에 내놓습니다.`,
    ],
    required_documents: ["별도 서류 없음 (신고 시 배출 품목·규격 정보 필요)"],
    processing_time: "신고 후 지정 배출일에 수거 (통상 신고일로부터 2~3일 내)",
    fee: "품목·규격별 수수료 상이 (예: 의자 2,000원~, 장롱 폭 1m당 4,000원~)",
    caution:
      "품목별 수수료와 수거 일정은 계절·지역 사정에 따라 달라질 수 있으니 신고 화면에서 최종 확인하세요.",
    fallback_contact: { ...BULKY_WASTE_CONTACT },
    sources: [
      {
        kb_id: "KB-WASTE-01",
        title: "세종시 대형폐기물 배출 안내",
        url: "https://www.sejong.go.kr",
        last_verified_at: "2026-07-15",
      },
    ],
    deep_link: {
      label: "대형폐기물 인터넷 신고 바로가기",
      url: "https://www.sejong.go.kr",
    },
  };
}

/** 대형폐기물 질문에 동이 없을 때 - 지역을 좁히는 FOLLOWUP (SFR-004) */
export const BULKY_WASTE_REGION_FOLLOWUP: FollowupResponse = {
  result_type: "FOLLOWUP",
  trigger: "AMBIGUOUS",
  message:
    "대형폐기물 배출 안내는 사시는 동에 따라 달라요. 어느 동에 거주하시나요?",
  options: [
    {
      id: "region",
      label: "동 선택하기",
      description: "사시는 동 기준으로 배출일을 안내해 드려요",
      kind: "REGION",
    },
  ],
  region_question: "대형폐기물은 언제 내놓나요?",
};

/* ---------- 데모 #3: "이사했는데 뭐 해야 하나요?" ---------- */
export const DEMO3_FOLLOWUP: FollowupResponse = {
  result_type: "FOLLOWUP",
  trigger: "AMBIGUOUS",
  message:
    "이사 후에 필요한 민원이 여러 가지 있어요. 어떤 것부터 안내해 드릴까요?",
  options: [
    {
      id: "move-in",
      label: "전입신고 하기",
      description: "이사한 날부터 14일 이내",
      kind: "QUERY",
      next_question: "전입신고는 언제까지 해야 하나요?",
    },
    {
      id: "waste",
      label: "대형폐기물 버리기",
      description: "배출 예약과 수수료",
      kind: "QUERY",
      next_question: "대형폐기물은 언제 내놓나요?",
    },
    {
      id: "cert",
      label: "주소가 바뀐 증명서 발급",
      description: "등본, 초본",
      kind: "QUERY",
      next_question: "주민등록등본은 어떻게 발급받나요?",
    },
  ],
  related_suggestion:
    "전입신고를 마치셨다면 대형폐기물 배출도 함께 확인해 보세요.",
};

/* ---------- 데모 #3에서 파생: 증명서 발급 SUCCESS (선택지 완주용) ---------- */
export const CERT_ANSWER: SuccessResponse = {
  result_type: "SUCCESS",
  category: "CERTIFICATE",
  answer_summary:
    "주민등록등본은 정부24에서 온라인 발급(무료)하거나, 가까운 읍·면·동 주민센터와 무인민원발급기에서 발급받을 수 있습니다.",
  procedure_steps: [
    "정부24 접속 후 본인 인증을 합니다.",
    "'주민등록표 등본(초본)' 발급을 신청합니다.",
    "필요한 표시 항목(세대원, 주소 변동 이력 등)을 선택합니다.",
    "PDF 저장 또는 프린터로 출력합니다.",
  ],
  // v3 §6-1-3: 신청 방법 2갈래 (온라인/방문)
  application_methods: [
    {
      title: "온라인 발급",
      description: "정부24에서 24시간 무료 발급할 수 있어요",
    },
    {
      title: "주민센터·무인발급기 방문",
      description: "주민센터 평일 09:00~18:00, 무인발급기는 연중 운영",
    },
  ],
  required_documents: ["본인 인증 수단 (공동·금융인증서, 간편인증 등)", "방문 발급 시 신분증"],
  processing_time: "즉시 발급",
  fee: "온라인 무료 / 주민센터 400원 / 무인발급기 200원",
  caution: "타인 등본 발급은 위임장 등 요건이 있으니 공식 페이지에서 확인하세요.",
  fallback_contact: {
    name: "세종특별자치시 각 읍·면·동 주민센터",
    phone: "044-300-3000 (세종시청 대표)",
    hours: "평일 09:00~18:00",
  },
  sources: [
    {
      kb_id: "KB-CERT-01",
      title: "주민등록표 등본 발급 안내",
      url: "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000015",
      last_verified_at: "2026-07-15",
    },
  ],
  deep_link: {
    label: "정부24에서 바로 발급",
    url: "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000015",
  },
};

/* ---------- 데모 #4: "제 자동차세 얼마 나왔나요?" ---------- */
export const DEMO4_PERSONAL_LOOKUP: ChatResponse = {
  result_type: "FALLBACK",
  fallback_code: "PERSONAL_LOOKUP",
  message:
    "개인별 자동차세 부과 내역은 본인 확인이 필요한 정보라서 여기서는 알려드릴 수 없어요. 안전하게 공식 조회 채널로 연결해 드립니다. 위택스에서 본인 인증 후 바로 확인하실 수 있어요.",
  contact: {
    name: "세종특별자치시 세정과",
    phone: "044-300-3000 (세종시청 대표)",
    hours: "평일 09:00~18:00",
  },
  deep_link: {
    label: "위택스에서 조회",
    url: "https://www.wetax.go.kr",
  },
};

/* ---------- 범위 밖 질문 공통 폴백 ---------- */
export const OUT_OF_SCOPE_FALLBACK: ChatResponse = {
  result_type: "FALLBACK",
  fallback_code: "OUT_OF_SCOPE",
  message:
    "지금은 전입·주민등록, 대형폐기물, 증명서 발급, 지방세 4개 분야를 안내해 드리고 있어요. 다른 민원은 세종시 대표 민원 창구로 안전하게 연결해 드립니다.",
  contact: {
    name: "세종특별자치시 민원콜센터",
    phone: "044-120",
    hours: "평일 09:00~18:00",
  },
};

/* ---------- mock 라우터 ---------- */

/** 키워드 매칭으로 데모 5문항 fixture를 돌려준다 (mock 전용) */
export function mockAnswer(question: string, region?: string): ChatResponse {
  const q = question.replace(/\s/g, "");

  // 데모 #1
  if (q.includes("전입신고")) {
    return DEMO1_MOVE_IN;
  }

  // 데모 #2 - 질문에 동이 포함된 경우 / 선택 UI로 지정한 경우 모두 동작
  // 선택 UI(region 파라미터)가 질문 텍스트 파싱보다 우선한다 ("동 변경" 시 명시적 선택이 이겨야 함)
  if (q.includes("대형폐기물") || q.includes("폐기물")) {
    const dongInQuestion = SEJONG_DONGS.find((d) => q.includes(d));
    const dong = region ?? dongInQuestion;
    if (dong) return makeBulkyWasteAnswer(dong);
    return BULKY_WASTE_REGION_FOLLOWUP;
  }

  // 데모 #3
  if (q.includes("이사") && !q.includes("전입")) {
    return DEMO3_FOLLOWUP;
  }

  // 데모 #3 파생 - 증명서
  if (q.includes("등본") || q.includes("증명서")) {
    return CERT_ANSWER;
  }

  // 데모 #4
  if (q.includes("자동차세") || q.includes("재산세") || q.includes("지방세")) {
    enqueueFailure(question, "PERSONAL_LOOKUP", "LOCAL_TAX");
    return DEMO4_PERSONAL_LOOKUP;
  }

  enqueueFailure(question, "OUT_OF_SCOPE", null);
  return OUT_OF_SCOPE_FALLBACK;
}

/* ---------- 관리자(이음센터) mock - 데모 #5 대비 ---------- */

/**
 * 실패 질문 큐 - 데모 #4의 폴백 건이 '신규' 상태로 미리 들어 있어야 한다 (§10).
 *
 * [저장 정책 정합] 제안서 6.2: masked_question 텍스트 보관은
 * INSUFFICIENT_GROUNDING(근거 부족) 실패에 한정한다. 나머지 사유(개인별 조회,
 * 법적 판단, 범위 밖)는 텍스트 없이 비텍스트 메타데이터(분야·사유·시각)만 관리
 * → masked_question: null (화면에서는 "미보관 - 메타데이터만 관리" 라벨).
 * ISG 건의 null은 "30일 경과 파기"를 의미한다 (화면 라벨: "보관 기간 경과").
 */
export const MOCK_FAILURE_QUEUE: FailureQueueItem[] = [
  {
    id: "fq-001",
    // 데모 #4 건 - PERSONAL_LOOKUP은 텍스트 미보관 (6.2)
    masked_question: null,
    fallback_code: "PERSONAL_LOOKUP",
    category: "LOCAL_TAX",
    status: "신규",
    created_at: "2026-07-22T10:30:00+09:00",
  },
  {
    id: "fq-002",
    // OUT_OF_SCOPE - 텍스트 미보관 (6.2)
    masked_question: null,
    fallback_code: "OUT_OF_SCOPE",
    category: null,
    status: "검토중",
    created_at: "2026-07-21T14:05:00+09:00",
  },
  {
    id: "fq-003",
    // ISG - 개선 대상이므로 마스킹 텍스트 보관 (6.2), 데모 #5의 초안 생성 대상
    masked_question: "전입신고를 대리인이 하면 위임장 공증이 필요한가요?",
    fallback_code: "INSUFFICIENT_GROUNDING",
    category: "MOVE_IN",
    status: "신규",
    created_at: "2026-07-21T09:12:00+09:00",
    // §9-3 발단 요약 바 "최근 30일 N회 반복" 표시용 (데모 #5 초안 생성 대상)
    repeat_count: 5,
  },
  {
    id: "fq-004",
    // ISG였으나 30일 경과로 텍스트 NULL 파기된 행 - 깨지지 않게 렌더링 (CLAUDE.md §6).
    // 6.2에 따라 파기 가능한 텍스트는 ISG 건뿐이므로 이 행의 사유도 ISG다.
    masked_question: null,
    fallback_code: "INSUFFICIENT_GROUNDING",
    category: "LOCAL_TAX",
    status: "처리완료",
    created_at: "2026-06-18T11:00:00+09:00",
  },
];

/**
 * [임시 결정 근거] 2026-07-22, 무인 세션 결정사항:
 * 초기 KB 후보 fixture는 비워둔다. 이전 fixture(kbc-001)가 fq-003의 초안으로
 * 미리 존재하면 데모 #5의 핵심 클릭("KB 후보 초안 생성")이 '초안 생성됨'으로
 * 비활성화되어 흐름이 끊긴다. 빈 상태 UI가 "실패 질문 관리에서 생성하라"고
 * 다음 행동을 안내하므로 첫 진입 화면도 비어 있지 않게 보인다.
 */
export const MOCK_KB_CANDIDATES: KbCandidate[] = [];

/** Overview KPI mock */
export const MOCK_KPI = {
  total_questions: 128,
  auto_answer_rate: 0.72,
  fallback_rate: 0.19,
  avg_response_seconds: 2.4,
  source_citation_rate: 1.0,
};

/* ---------- 관리자 mock 스토어 (인메모리, 데모 #5 선순환 시뮬레이션) ----------
 *
 * [임시 결정 근거] 2026-07-22, 무인 세션 결정사항:
 * - 같은 탭 세션 동안 시민 화면 폴백 → 실패 질문 큐 "도착"이 보이도록
 *   모듈 스코프 배열을 mock DB로 사용한다 (브라우저 스토리지 저장 금지 §9 -
 *   메모리 유지만 허용. 새로고침 시 초기 fixture로 리셋되며, 데모 #4 건은
 *   fixture에 '신규'로 상시 존재하므로 데모 #5는 항상 완주 가능).
 * - 상태 전이 정책(임시): KB 후보 초안 생성 시 원 실패 질문은 '검토중'으로,
 *   후보 승인/반려 판정 시 '처리완료'로 자동 전환한다.
 * - 초안 생성은 INSUFFICIENT_GROUNDING 건에만 허용 (CLAUDE.md §6). mock에서도
 *   가드하고, 동일 실패 건의 중복 초안 생성은 막는다.
 */

let failureQueue: FailureQueueItem[] = MOCK_FAILURE_QUEUE.map((f) => ({ ...f }));
let kbCandidates: KbCandidate[] = MOCK_KB_CANDIDATES.map((c) => ({ ...c }));
let seq = 100;

/** 시민 화면 폴백 발생 시 실패 질문 큐에 신규 건을 넣는다 (mock 전용).
 *  질문 마스킹은 백엔드 책임 - mock에서는 원문을 그대로 쓴다.
 *  제안서 6.2 저장 정책: 텍스트 보관은 INSUFFICIENT_GROUNDING에 한정.
 *  나머지 사유는 메타데이터만 적재한다 (masked_question: null). */
function enqueueFailure(
  question: string,
  code: FallbackCode,
  category: CivilCategory | null,
) {
  const keepText = code === "INSUFFICIENT_GROUNDING";
  failureQueue = [
    {
      id: `fq-${++seq}`,
      masked_question: keepText ? question : null,
      fallback_code: code,
      category,
      status: "신규",
      created_at: new Date().toISOString(),
    },
    ...failureQueue,
  ];
}

export function mockListFailures(): FailureQueueItem[] {
  return failureQueue.map((f) => ({ ...f }));
}

export function mockUpdateFailureStatus(
  id: string,
  status: FailureStatus,
): void {
  failureQueue = failureQueue.map((f) => (f.id === id ? { ...f, status } : f));
}

/**
 * INSUFFICIENT_GROUNDING 실패 건 → KB 후보 초안 생성 (AI 초안 시뮬레이션).
 * v2 §8: 초안은 KB 실물 스키마(KbDraftSchema) 형태로 생성하되 완벽하게 꾸미지
 * 않는다 - source_url은 항상 null(미검증)로 남겨 사람 판정의 필요성을 보인다.
 * 데모 #5의 fq-003(전입신고 대리인) 건에는 그럴듯한 특화 초안을 준비한다.
 */
export function mockCreateKbDraft(failureId: string): KbCandidate | null {
  const failure = failureQueue.find((f) => f.id === failureId);
  if (!failure || failure.fallback_code !== "INSUFFICIENT_GROUNDING")
    return null;
  const exists = kbCandidates.find((c) => c.source_failure_id === failureId);
  if (exists) return exists;

  const question = failure.masked_question ?? "(보관 기간 경과)";

  // 데모 #5 특화 초안 (fq-003: 전입신고 대리인 위임 요건)
  const isDemoDraft = failureId === "fq-003";
  const draftSchema: KbDraftSchema = isDemoDraft
    ? {
        category: "MOVE_IN",
        question_examples: [
          question,
          "전입신고 위임장은 어떻게 쓰나요?",
          "가족 대신 전입신고할 수 있나요?",
        ],
        answer_summary:
          "대리인이 전입신고를 하는 경우 위임장과 위임인·대리인의 신분증이 필요합니다. 위임장 공증은 일반적으로 요구되지 않으나, 세대주 확인이 필요한 경우가 있습니다.",
        procedure_steps: [
          "위임장을 작성합니다 (전입자 서명 필요).",
          "위임인·대리인 신분증을 준비합니다.",
          "새 거주지 읍·면·동 주민센터에 방문해 신고합니다.",
        ],
        processing_time: "근무시간 내 즉시 처리",
        fee: "무료",
        fallback_contact: {
          name: "세종특별자치시 각 읍·면·동 주민센터",
          phone: "044-300-3000 (세종시청 대표)",
          hours: "평일 09:00~18:00",
        },
        source_url: null,
      }
    : {
        category: failure.category,
        question_examples: [question],
        answer_summary: `실패 질문 "${question}"에 대해 승인된 문서 근거가 부족했습니다. 담당 부서 확인 후 답변 요약을 보완해 주세요.`,
        procedure_steps: ["담당 부서 확인 후 절차를 입력해 주세요."],
        processing_time: "확인 필요",
        fee: "확인 필요",
        fallback_contact: {
          name: "세종특별자치시 민원콜센터",
          phone: "044-120",
          hours: "평일 09:00~18:00",
        },
        source_url: null,
      };

  const draft: KbCandidate = {
    id: `kbc-${++seq}`,
    title: `${question} (KB 후보 초안)`,
    draft: draftSchema,
    source_failure_id: failureId,
    status: "승인 대기",
    created_at: new Date().toISOString(),
  };
  kbCandidates = [draft, ...kbCandidates];
  mockUpdateFailureStatus(failureId, "검토중");
  return draft;
}

export function mockListKbCandidates(): KbCandidate[] {
  return kbCandidates.map((c) => ({ ...c }));
}

export function mockReviewKbCandidate(
  id: string,
  status: Extract<KbCandidateStatus, "승인" | "반려">,
  // 반려 사유 코드 (v2 §8) - mock에서는 저장만 생략, 시그니처는 실API와 동일하게
  _reasonCode?: KbRejectReason,
): void {
  const candidate = kbCandidates.find((c) => c.id === id);
  kbCandidates = kbCandidates.map((c) => (c.id === id ? { ...c, status } : c));
  // 판정 완료 → 원 실패 질문 처리완료 (임시 정책, 상단 주석 참조)
  if (candidate) mockUpdateFailureStatus(candidate.source_failure_id, "처리완료");
}

export function mockKpi() {
  return { ...MOCK_KPI };
}

/* ---------- context_token 만료 시뮬레이션 (CLAUDE.md §9) ----------
 *
 * 15분 서명형 토큰의 만료를 mock으로 흉내낸다. 첫 질문 시각을 기준으로
 * 15분 초과 시 만료. 데모를 방해하지 않도록 기본적으로는 15분 내 발동하지
 * 않으며, 시연·검증용으로 ?demo_expire=1 쿼리 파라미터로 강제 발동한다.
 * 실API 전환 시: 백엔드가 401/만료 응답을 주면 같은 UI 흐름으로 연결한다.
 */
const CONTEXT_TTL_MS = 15 * 60 * 1000;
let contextStartedAt: number | null = null;

export function mockContextExpired(force: boolean): boolean {
  if (force) return true;
  const now = Date.now();
  if (contextStartedAt === null) {
    contextStartedAt = now; // 첫 질문 = 토큰 발급 시점
    return false;
  }
  return now - contextStartedAt > CONTEXT_TTL_MS;
}

/** "새 대화 시작" - 토큰 재발급 시뮬레이션 */
export function mockResetContext(): void {
  contextStartedAt = null;
}
