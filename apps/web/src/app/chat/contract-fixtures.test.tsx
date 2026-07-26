// @vitest-environment jsdom

/**
 * 계약 fixture 렌더링 검증 - contracts/fixtures/chat-response의 valid 계열
 * fixture를 그대로 카드 컴포넌트에 주입해 화면이 계약 payload와 맞는지
 * 확인한다 (fixture가 곧 렌더링 테스트의 데이터 소스).
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import validSuccess from "../../../../../contracts/fixtures/chat-response/valid-success.json";
import validFollowup from "../../../../../contracts/fixtures/chat-response/valid-followup.json";
import validFallbackOffice from "../../../../../contracts/fixtures/chat-response/valid-fallback-office.json";
import validFallbackNoOffice from "../../../../../contracts/fixtures/chat-response/valid-fallback-no-office.json";
import validPrivacyUnresolved from "../../../../../contracts/fixtures/chat-response/valid-privacy-unresolved.json";

import type { components } from "../../../../../packages/shared-contracts/src/generated/api";
import AnswerCard from "../../components/citizen/AnswerCard";
import FollowupCard from "../../components/citizen/FollowupCard";
import FallbackCard from "../../components/citizen/FallbackCard";

type SuccessResponse = components["schemas"]["SuccessResponse"];
type Fallback = components["schemas"]["Fallback"];

describe("contract fixture rendering", () => {
  it("renders valid-success.json with its source strip and office metadata", () => {
    const response = validSuccess as unknown as SuccessResponse;
    render(<AnswerCard response={response} />);

    // summary가 없는 fixture는 기본 제목으로 렌더링하되 카드가 깨지지 않는다
    expect(screen.getByText("확인된 민원 안내")).toBeInTheDocument();
    expect(screen.getByText("공식 안내")).toBeInTheDocument();
    expect(
      screen.getByText(
        "AI가 표현을 정리할 수 있지만 행정 사실과 출처는 승인된 공식 자료에서 확인하며, 오류가 있으면 공식 안내 형식을 사용합니다.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("시연용 샘플 출처 — 공식 데이터 아님"),
    ).toBeInTheDocument();
    expect(screen.getByText("2026-07-15 확인 기준")).toBeInTheDocument();
    const sourceLink = screen.getByRole("link", { name: /원문 보기/ });
    expect(sourceLink).toHaveAttribute(
      "href",
      "https://example.invalid/sources/001",
    );
    expect(sourceLink).toHaveAttribute("target", "_blank");
    expect(sourceLink).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText("시연용 샘플 행정복지센터")).toBeInTheDocument();
    expect(screen.getByText("시연용 샘플 주소")).toBeInTheDocument();
  });

  it.each([
    ["blank source id", { source_id: "   " }],
    ["blank source title", { title: "   " }],
    ["blank verified date", { last_verified_at: "   " }],
    ["missing source URL", { url: undefined }],
    ["non-HTTPS source URL", { url: "http://example.invalid/sources/001" }],
    ["unparseable HTTPS source URL", { url: "https://" }],
  ])("fails closed for a SUCCESS response with %s", (_, sourceOverride) => {
    const validResponse = validSuccess as unknown as SuccessResponse;
    const response = {
      ...validResponse,
      sources: [{ ...validResponse.sources[0], ...sourceOverride }],
    } as unknown as SuccessResponse;

    render(<AnswerCard response={response} />);

    expect(screen.getByRole("alert")).toHaveTextContent("일시적인 오류");
    expect(screen.queryByText("공식 안내")).not.toBeInTheDocument();
    expect(
      screen.queryByText(
        "AI가 표현을 정리할 수 있지만 행정 사실과 출처는 승인된 공식 자료에서 확인하며, 오류가 있으면 공식 안내 형식을 사용합니다.",
      ),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /원문 보기/ })).not.toBeInTheDocument();
  });

  it("renders valid-followup.json options as selectable chips", () => {
    render(
      <FollowupCard
        intent="UNKNOWN"
        options={(validFollowup as { followup_options: string[] }).followup_options}
        onSelect={() => {}}
      />,
    );

    expect(
      screen.getByRole("button", { name: "시연용 샘플 선택지" }),
    ).toBeInTheDocument();
    // 단정적 답변 금지 - 출처 스트립 없음
    expect(screen.queryByText("공식 출처 확인")).not.toBeInTheDocument();
  });

  it("renders valid-fallback-office.json with the office contact block", () => {
    const fallback = (validFallbackOffice as { fallback: unknown })
      .fallback as Fallback;
    render(<FallbackCard fallback={fallback} />);

    expect(screen.getByText("시연용 샘플 기관 안내")).toBeInTheDocument();
    expect(
      screen.getByText("시연용 샘플이며 공식 기관 데이터가 아닙니다."),
    ).toBeInTheDocument();
    expect(screen.getByText("시연용 샘플 행정복지센터")).toBeInTheDocument();
    // PERSONAL_LOOKUP - 공식 조회 채널 CTA + 전화 CTA
    expect(screen.getByRole("link", { name: /위택스에서 조회/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /전화 000-000-0000/ })).toBeInTheDocument();
  });

  it("renders valid-fallback-no-office.json with the default call-center contact", () => {
    const fallback = (validFallbackNoOffice as { fallback: unknown })
      .fallback as Fallback;
    render(<FallbackCard fallback={fallback} />);

    expect(screen.getByText("시연용 샘플 폴백")).toBeInTheDocument();
    // OUT_OF_SCOPE - 지원 4개 분야 재안내 + 기본 민원콜센터 연결
    expect(screen.getByText("전입·주민등록")).toBeInTheDocument();
    expect(screen.getByText("세종특별자치시 민원콜센터")).toBeInTheDocument();
  });

  it("renders valid-privacy-unresolved.json with the fixed contract copy only", () => {
    const fallback = (validPrivacyUnresolved as { fallback: unknown })
      .fallback as Fallback;
    render(<FallbackCard fallback={fallback} />);

    expect(
      screen.getByText("개인정보를 안전하게 처리하지 못했어요"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("이름, 주소, 전화번호, 접수번호 등을 적지 마세요."),
    ).toBeInTheDocument();
    // office가 항상 null - 전화 CTA 없음
    expect(screen.queryByRole("link", { name: /전화/ })).not.toBeInTheDocument();
  });
});
