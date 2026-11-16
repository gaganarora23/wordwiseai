import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchGradeWords, httpProfileService } from "@/services/api";

const dto = {
  id: "w1", word: "cat", grade: "1", definition: "a pet", example: "The cat sat.", syllables: "cat",
  content_version: "v1", explanation: "Because.",
  options: [
    { id: "1", text: "a", is_correct: false },
    { id: "2", text: "b", is_correct: true },
  ],
};

afterEach(() => vi.unstubAllGlobals());

describe("fetchGradeWords", () => {
  it("maps the backend response to the Word type", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [dto] });
    vi.stubGlobal("fetch", fetchMock);

    const word = (await fetchGradeWords("1"))[0]!;

    expect(fetchMock.mock.calls[0]![0]).toMatch(/\/api\/v1\/grades\/1\/words$/);
    expect(word).toMatchObject({ id: "w1", word: "cat", contentVersion: "v1" });
    expect(word.question.correctOptionId).toBe("999");
    expect(word.question.options).toEqual([{ id: "1", text: "a" }, { id: "2", text: "b" }]);
  });

  it("throws when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(fetchGradeWords("1")).rejects.toThrow("500");
  });
});

describe("httpProfileService", () => {
  const profileDto = {
    id: "p1", nickname: "Sam", grade: "3", daily_goal: 5,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-02T00:00:00Z",
  };
  const respond = (status: number, body?: unknown) =>
    vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body });

  it("lists profiles and maps snake_case to the UI type", async () => {
    vi.stubGlobal("fetch", respond(200, [profileDto]));
    expect(await httpProfileService.listProfiles()).toEqual([
      { id: "p1", nickname: "Sam", grade: "3", dailyGoal: 5, createdAt: "2026-01-01T00:00:00Z", updatedAt: "2026-01-02T00:00:00Z" },
    ]);
  });

  it("creates a profile with a trimmed nickname and the snake_case body", async () => {
    const fetchMock = respond(201, profileDto);
    vi.stubGlobal("fetch", fetchMock);

    await httpProfileService.createProfile({ nickname: "  Sam ", grade: "3", dailyGoal: 5 });

    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toMatch(/\/api\/v1\/profiles$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ nickname: "Sam", grade: "3", daily_goal: 5 });
  });

  it("updates with PUT and deletes with DELETE on the profile url", async () => {
    const put = respond(200, profileDto);
    vi.stubGlobal("fetch", put);
    await httpProfileService.updateProfile("p1", { nickname: "Sam", grade: "3", dailyGoal: 10 });
    expect(put.mock.calls[0]![0]).toMatch(/\/profiles\/p1$/);
    expect(put.mock.calls[0]![1].method).toBe("PUT");

    const del = respond(204);
    vi.stubGlobal("fetch", del);
    await httpProfileService.deleteProfile("p1");
    expect(del.mock.calls[0]![1].method).toBe("DELETE");
  });

  it("returns null for a profile that does not exist", async () => {
    vi.stubGlobal("fetch", respond(404));
    expect(await httpProfileService.getProfile("missing")).toBeNull();
  });

  it("explains a validation failure and a network failure in plain words", async () => {
    vi.stubGlobal("fetch", respond(422));
    await expect(httpProfileService.createProfile({ nickname: "x", grade: "3", dailyGoal: 5 })).rejects.toThrow(/check the nickname/);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(httpProfileService.listProfiles()).rejects.toThrow(/couldn't reach the server/);
  });
});
