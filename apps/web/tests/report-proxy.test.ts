import { afterEach, expect, it, vi } from "vitest";

import { GET } from "../app/api/reports/[symbol]/route";

afterEach(() => {
  delete process.env.RESEARCH_SERVICE_URL;
  vi.unstubAllGlobals();
});

it("proxies a report response from the private research service", async () => {
  process.env.RESEARCH_SERVICE_URL = "http://research.internal";
  const upstreamFetch = vi.fn().mockResolvedValue(Response.json({ symbol: "MU" }, { status: 200 }));
  vi.stubGlobal("fetch", upstreamFetch);

  const response = await GET(new Request("http://localhost/api/reports/MU"), {
    params: Promise.resolve({ symbol: "MU" }),
  });

  expect(upstreamFetch).toHaveBeenCalledWith(
    "http://research.internal/api/reports/MU",
    expect.objectContaining({ cache: "no-store" }),
  );
  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toEqual({ symbol: "MU" });
});

it("does not expose configuration when the research service is unavailable", async () => {
  const response = await GET(new Request("http://localhost/api/reports/MU"), {
    params: Promise.resolve({ symbol: "MU" }),
  });

  expect(response.status).toBe(503);
  await expect(response.json()).resolves.toEqual({ detail: "research service is not configured" });
});
