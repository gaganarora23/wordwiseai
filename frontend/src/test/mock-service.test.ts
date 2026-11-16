import { beforeEach, describe, expect, it } from "vitest";
import { mockService } from "@/services/mock/mock-service";
import { GRADES } from "@/services/types";

beforeEach(() => localStorage.clear());

describe("WordWise mock learning flow", () => {
  it("provides five sample words for every grade", async () => {
    for (const grade of GRADES) {
      const words = await mockService.getGradeContent(grade);
      expect(words).toHaveLength(5);
      expect(words.every((word) => word.grade === grade)).toBe(true);
    }
  });

  it("resumes progress and completes a five-word quiz with review words", async () => {
    const profile = await mockService.createProfile({ nickname: "Sunny", grade: "1", dailyGoal: 5 });
    const words = await mockService.getGradeContent(profile.grade);
    const session = await mockService.startOrResumeSession(profile.id);
    await mockService.updateSessionProgress(session.id, "quiz", 2);
    expect(await mockService.startOrResumeSession(profile.id)).toMatchObject({ id: session.id, phase: "quiz", position: 2 });
    for (const [index, id] of session.wordIds.entries()) {
      const word = words.find((item) => item.id === id);
      if (!word) throw new Error("Test word missing");
      await mockService.submitAnswer(session.id, index, word.question.correctOptionId, index === 0);
    }
    const result = await mockService.completeSession(session.id);
    expect(result).toMatchObject({ correctCount: 5, incorrectCount: 0, score: 100, reviewWordIds: [session.wordIds[0]] });
    expect(await mockService.getResult(session.id)).toEqual(result);
    expect(await mockService.startReviewSession(profile.id, result.reviewWordIds)).toMatchObject({ wordIds: result.reviewWordIds, position: 0, phase: "learn" });
  });

  it("rejects missing question positions without saving an answer", async () => {
    const profile = await mockService.createProfile({ nickname: "Sunny", grade: "K", dailyGoal: 5 });
    const session = await mockService.startOrResumeSession(profile.id);
    await expect(mockService.submitAnswer(session.id, 5, "missing", false)).rejects.toThrow("Question not found");
    expect((await mockService.getSession(session.id))?.answers).toEqual([]);
  });
});