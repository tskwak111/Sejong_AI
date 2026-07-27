// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import RegionSelect from "./RegionSelect";

describe("RegionSelect", () => {
  it("shows the collapsed optional copy with a labelled native keyboard control", () => {
    render(<RegionSelect current={null} onSelect={vi.fn()} />);

    const select = screen.getByRole("combobox", {
      name: "거주 지역 선택 · 선택사항",
    });
    expect(select).toHaveValue("");
    expect(screen.getAllByText("거주 지역 선택 · 선택사항")[0]).toBeVisible();
    expect(select.className).toContain("min-h-11");
  });

  it("uses the selected region change copy and handles native select keyboard values", () => {
    const onSelect = vi.fn();
    const { rerender } = render(
      <RegionSelect current={null} onSelect={onSelect} />,
    );

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "도담동" },
    });
    expect(onSelect).toHaveBeenCalledWith("도담동");

    rerender(<RegionSelect current="도담동" onSelect={onSelect} />);
    expect(
      screen.getByRole("combobox", { name: "도담동 · 변경" }),
    ).toHaveValue("도담동");
    expect(screen.getAllByText("도담동 · 변경")[0]).toBeVisible();
  });
});
