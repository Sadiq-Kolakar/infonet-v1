import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, getErrorMessage } from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("typed API client", () => {
  it("serializes supported search and pagination parameters", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            items: [],
            total: 0,
            limit: 12,
            offset: 0,
            facets: {},
          }),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    await api.people({
      q: "Ada Lovelace",
      category: "Professor",
      limit: 12,
      offset: 24,
    });
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "http://127.0.0.1:8000/api/v1/people?q=Ada+Lovelace&category=Professor&limit=12&offset=24",
    );
  });

  it("normalizes the API error envelope without exposing internal details", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({
              error: {
                code: "DATABASE_UNAVAILABLE",
                message: "Neo4j is unavailable.",
                details: {},
              },
            }),
            { status: 503 },
          ),
        ),
    );
    await expect(api.summary()).rejects.toMatchObject({
      status: 503,
      code: "DATABASE_UNAVAILABLE",
    });
    expect(
      getErrorMessage(
        new ApiError("Neo4j is unavailable.", 503, "DATABASE_UNAVAILABLE"),
      ),
    ).toMatch(/database is currently unavailable/i);
  });

  it("reports network failures with a safe message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("fetch failed")),
    );
    await expect(api.health()).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });

  it("rejects graph payloads outside the approved graph response shape", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ nodes: [], edges: [], meta: {} }), {
            status: 200,
          }),
        ),
    );
    await expect(api.graph()).rejects.toMatchObject({
      code: "INVALID_RESPONSE",
      status: 502,
    });
  });
});
