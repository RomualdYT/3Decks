import { beforeEach, describe, expect, it, vi } from "vitest";

beforeEach(() => {
  vi.resetModules();
  vi.unstubAllGlobals();
  sessionStorage.clear();
  history.replaceState(null, "", "/?token=local-session");
});

describe("local session error handling", () => {
  it("keeps the session after an origin refusal", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "origine refusee", code: "origin_refused", request_id: "r1" }), { status: 403 }));
    vi.stubGlobal("fetch", fetch);
    const { agentApi } = await import("./client");
    await expect(agentApi.rotatePairing()).rejects.toMatchObject({ code: "origin_refused", requestId: "r1" });
    expect(sessionStorage.getItem("deck3ds.token")).toBe("local-session");
    expect(location.search).toBe("");
  });

  it("preserves a native-menu destination while removing the session token", async () => {
    history.replaceState(null, "", "/?token=local-session#status");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}")));
    await import("./client");
    expect(location.search).toBe("");
    expect(location.hash).toBe("#status");
  });

  it("clears only an expired session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "invalid", code: "invalid_session", request_id: "r2" }), { status: 403 })));
    const { agentApi } = await import("./client");
    await expect(agentApi.state()).rejects.toMatchObject({ status: 403, code: "invalid_session" });
    expect(sessionStorage.getItem("deck3ds.token")).toBeNull();
  });

  it("restores a session after reload and retains conflict diagnostics", async () => {
    sessionStorage.setItem("deck3ds.token", "remembered");
    history.replaceState(null, "", "/");
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "changed", code: "config_conflict", request_id: "r3" }), { status: 409 }));
    vi.stubGlobal("fetch", fetch);
    const { agentApi } = await import("./client");
    await expect(agentApi.config()).rejects.toMatchObject({ code: "config_conflict", requestId: "r3" });
    expect(fetch.mock.calls[0][1].headers["X-Deck3DS-Token"]).toBe("remembered");
  });
});
