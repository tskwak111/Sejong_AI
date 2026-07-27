/**
 * 계약 enum의 한글 표시 라벨과 UI 상수 - 시민·이음센터 공용.
 * 값 자체는 contracts/openapi-v1.yaml(생성 타입)이 기준이며, 이 파일은
 * 표시용 라벨만 소유한다. 계약에 없는 값을 만들지 않는다.
 */
import type { components } from "../../../../packages/shared-contracts/src/generated/api";

export type Intent = components["schemas"]["Intent"];
export type SupportedIntent = components["schemas"]["SupportedIntent"];
export type FallbackReason = components["schemas"]["FallbackReason"];
export type StoredFailureReason = components["schemas"]["StoredFailureReason"];

/** 지원 분야 4개 - 첫 화면 카드 순서 (CLAUDE.md §5) */
export const SUPPORTED_INTENTS: readonly SupportedIntent[] = [
  "MOVE_IN_RESIDENT_REGISTRATION",
  "BULKY_WASTE",
  "CERTIFICATE_ISSUANCE",
  "LOCAL_TAX_GENERAL",
];

export const INTENT_LABEL: Record<SupportedIntent, string> = {
  MOVE_IN_RESIDENT_REGISTRATION: "전입·주민등록",
  BULKY_WASTE: "대형폐기물",
  CERTIFICATE_ISSUANCE: "증명서 발급",
  LOCAL_TAX_GENERAL: "지방세",
};

/** 폴백 사유 6종 한글 라벨 */
export const FALLBACK_REASON_LABEL: Record<FallbackReason, string> = {
  INSUFFICIENT_GROUNDING: "근거 부족",
  PERSONAL_LOOKUP: "개인별 조회",
  LEGAL_JUDGMENT: "법적 판단",
  CIVIC_SCOPE_GAP: "지원 범위 확대",
  OUT_OF_SCOPE: "범위 밖",
  PRIVACY_UNRESOLVED: "개인정보 미해소",
};

/** 실패 질문 큐에 저장되는 사유 3종 (OUT_OF_SCOPE는 행이 생성되지 않는다) */
export const STORED_REASON_LABEL: Record<StoredFailureReason, string> = {
  INSUFFICIENT_GROUNDING: "근거 부족",
  PERSONAL_LOOKUP: "개인별 조회",
  LEGAL_JUDGMENT: "법적 판단",
};

/** 지역(동) - 계약 selected_region enum 3개동 한정 (SFR-004) */
export const REGION_OPTIONS = ["아름동", "도담동", "조치원읍"] as const;
export type Region = (typeof REGION_OPTIONS)[number];

export function isRegion(value: string): value is Region {
  return (REGION_OPTIONS as readonly string[]).includes(value);
}

/**
 * 공식 조회·신청 채널 딥링크 - 계약 응답에 deep_link 필드가 없어(보고 항목)
 * UI 상수로 유지한다. 값은 공식 채널 대표 주소만 사용한다.
 */
export const DEEP_LINK_BY_INTENT: Record<
  SupportedIntent,
  { label: string; url: string }
> = {
  MOVE_IN_RESIDENT_REGISTRATION: {
    label: "정부24에서 바로 신청",
    url: "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016",
  },
  CERTIFICATE_ISSUANCE: {
    label: "정부24에서 바로 발급",
    url: "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000015",
  },
  BULKY_WASTE: {
    label: "대형폐기물 인터넷 신고 바로가기",
    url: "https://www.sejong.go.kr",
  },
  LOCAL_TAX_GENERAL: {
    label: "위택스에서 조회",
    url: "https://www.wetax.go.kr",
  },
};

/** PERSONAL_LOOKUP 폴백의 공식 조회 채널 CTA (예: 위택스) - UI 상수 */
export const PERSONAL_LOOKUP_DEEP_LINK = {
  label: "위택스에서 조회",
  url: "https://www.wetax.go.kr",
} as const;

/** 폴백에 기관 정보가 없을 때의 대표 민원 창구 - UI 상수 */
export const CALL_CENTER = {
  name: "세종특별자치시 민원콜센터",
  phone: "044-120",
  hours: "평일 09:00~18:00",
} as const;
