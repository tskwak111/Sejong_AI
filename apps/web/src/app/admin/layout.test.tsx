// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AdminLayout from "./layout";

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>(
    "next/navigation",
  );
  return {
    ...actual,
    usePathname: () => "/admin",
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  };
});

describe("admin layout gate", () => {
  afterEach(() => {
    delete process.env.ADMIN_UI_ENABLED;
    delete process.env.ADMIN_UI_MODE;
  });

  it("keeps the administrator route closed unless the server explicitly enables it", () => {
    process.env.ADMIN_UI_MODE = "actual";
    expect(() => AdminLayout({ children: null })).toThrow(
      /NEXT_HTTP_ERROR_FALLBACK;404/,
    );
  });

  it("renders the fixture shell by default when enabled", () => {
    process.env.ADMIN_UI_ENABLED = "true";
    render(<AdminLayout>{null}</AdminLayout>);

    expect(screen.getAllByText("이음")[0]).toBeInTheDocument();
    expect(screen.getByText("시연용 샘플 데이터")).toBeInTheDocument();
    expect(screen.queryByText("실제 local DB API 연결")).not.toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "관리자 메뉴" }),
    ).toBeInTheDocument();
  });

  it("selects the actual API transport only when the server explicitly requests actual mode", () => {
    process.env.ADMIN_UI_ENABLED = "true";
    process.env.ADMIN_UI_MODE = "actual";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ items: [], total: 0 }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    render(<AdminLayout>{null}</AdminLayout>);

    expect(screen.getByText("실제 local DB API 연결")).toBeInTheDocument();
    expect(screen.queryByText("시연용 샘플 데이터")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
