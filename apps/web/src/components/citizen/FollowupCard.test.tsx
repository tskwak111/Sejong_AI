// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import FollowupCard from "./FollowupCard";

describe("FollowupCard", () => {
  it("asks the exact certificate-kind question for certificate options", () => {
    render(
      <FollowupCard
        intent="CERTIFICATE_ISSUANCE"
        options={["주민등록등본 발급", "주민등록초본 발급"]}
        onSelect={vi.fn()}
      />,
    );

    expect(
      screen.getByText("어떤 증명서를 발급하려고 하시나요?"),
    ).toBeInTheDocument();
  });

  it("prioritizes the residence-region prompt when every option is a region", () => {
    render(
      <FollowupCard
        intent="CERTIFICATE_ISSUANCE"
        options={["아름동", "도담동", "조치원읍"]}
        onSelect={vi.fn()}
      />,
    );

    expect(
      screen.getByText(
        "안내는 사시는 동에 따라 달라요. 어느 동에 거주하시나요?",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("어떤 증명서를 발급하려고 하시나요?"),
    ).not.toBeInTheDocument();
  });
});
