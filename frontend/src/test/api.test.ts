import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchGradeWords } from "@/services/api";

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

    const [word] = await fetchGradeWords("1");

    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/v1\/grades\/1\/words$/);
    expect(word).toMatchObject({ id: "w1", word: "cat", contentVersion: "v1" });
    expect(word.question.correctOptionId).toBe("2");
    expect(word.question.options).toEqual([{ id: "1", text: "a" }, { id: "2", text: "b" }]);
  });

  it("throws when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(fetchGradeWords("1")).rejects.toThrow("500");
  });
});
