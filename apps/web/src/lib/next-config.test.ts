import { describe, expect, it } from "vitest";

import nextConfig from "../../next.config";

describe("Next.js local development origin policy", () => {
  it("allows only the documented 127.0.0.1 loopback host", () => {
    expect(nextConfig.allowedDevOrigins).toEqual(["127.0.0.1"]);
  });
});
