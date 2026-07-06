import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, getAccessToken, setOnAuthLost, setTokens } from "./client";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
    setTokens(null, null);
    setOnAuthLost(() => {});
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches the bearer token to requests once set", async () => {
    setTokens("access-123", "refresh-456");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await api.get("/api/v1/whoami");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer access-123");
  });

  it("persists the refresh token to localStorage and clears it on logout", () => {
    setTokens("a", "r");
    expect(localStorage.getItem("ashashala_refresh")).toBe("r");
    setTokens(null, null);
    expect(localStorage.getItem("ashashala_refresh")).toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it("retries once after a 401 by refreshing, then succeeds", async () => {
    setTokens("stale-access", "refresh-456");
    const fetchMock = vi
      .fn()
      // first call: the API rejects the stale access token
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      // second call: the refresh endpoint succeeds
      .mockResolvedValueOnce(jsonResponse({ access_token: "new-access", refresh_token: "new-refresh" }))
      // third call: the retried request succeeds
      .mockResolvedValueOnce(jsonResponse({ hello: "world" }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.get<{ hello: string }>("/api/v1/whoami");

    expect(result).toEqual({ hello: "world" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(getAccessToken()).toBe("new-access");
  });

  it("calls onAuthLost and throws when refresh also fails", async () => {
    setTokens("stale-access", "refresh-456");
    const authLost = vi.fn();
    setOnAuthLost(authLost);

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 401 })); // refresh fails too
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.get("/api/v1/whoami")).rejects.toThrow(ApiError);
    expect(authLost).toHaveBeenCalledTimes(1);
  });

  it("parses a structured error body into ApiError", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ error_code: "VALIDATION_ERROR", message: "bad input" }, 422),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.post("/api/v1/whatever", { x: 1 })).rejects.toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      message: "bad input",
    });
  });
});
