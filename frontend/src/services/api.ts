import type { ChildProfile, DailyGoal, Grade, ProfileInput, Word, WordWiseService } from "./types";

const API_URL: string = import.meta.env["VITE_API_URL"] ?? "http://localhost:8000";

interface WordDto {
  id: string;
  word: string;
  grade: Grade;
  definition: string;
  example: string;
  syllables: string;
  content_version: string;
  options: { id: string; text: string; is_correct: boolean }[];
  explanation: string;
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_URL}/api/v1${path}`, init);
  } catch {
    throw new Error("We couldn't reach the server. Check your connection and try again.");
  }
}

const jsonInit = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function failure(response: Response, what: string): Error {
  if (response.status === 422) return new Error("Please check the nickname (1 to 20 characters), grade and daily goal.");
  if (response.status === 404) return new Error("That profile no longer exists.");
  return new Error(`We couldn't ${what} (error ${response.status}).`);
}

interface ProfileDto {
  id: string;
  nickname: string;
  grade: Grade;
  daily_goal: number;
  created_at: string;
  updated_at: string;
}

const toProfile = (d: ProfileDto): ChildProfile => ({
  id: d.id,
  nickname: d.nickname,
  grade: d.grade,
  dailyGoal: d.daily_goal as DailyGoal,
  createdAt: d.created_at,
  updatedAt: d.updated_at,
});

const toBody = (input: ProfileInput) => ({
  nickname: input.nickname.trim(),
  grade: input.grade,
  daily_goal: input.dailyGoal,
});

/** Profile calls backed by the API (PostgreSQL); the rest of WordWiseService is still the mock. */
export const httpProfileService: Pick<
  WordWiseService,
  "listProfiles" | "getProfile" | "createProfile" | "updateProfile" | "deleteProfile"
> = {
  async listProfiles() {
    const response = await request("/profiles");
    if (!response.ok) throw failure(response, "load the profiles");
    return ((await response.json()) as ProfileDto[]).map(toProfile);
  },
  async getProfile(id) {
    const response = await request(`/profiles/${encodeURIComponent(id)}`);
    if (response.status === 404 || response.status === 422) return null;
    if (!response.ok) throw failure(response, "load the profile");
    return toProfile((await response.json()) as ProfileDto);
  },
  async createProfile(input) {
    const response = await request("/profiles", jsonInit("POST", toBody(input)));
    if (!response.ok) throw failure(response, "save the profile");
    return toProfile((await response.json()) as ProfileDto);
  },
  async updateProfile(id, input) {
    const response = await request(`/profiles/${encodeURIComponent(id)}`, jsonInit("PUT", toBody(input)));
    if (!response.ok) throw failure(response, "save the profile");
    return toProfile((await response.json()) as ProfileDto);
  },
  async deleteProfile(id) {
    const response = await request(`/profiles/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (!response.ok) throw failure(response, "delete the profile");
  },
};

/** Fetches the curated words of one grade from the backend (GET /api/v1/grades/{grade}/words). */
export async function fetchGradeWords(grade: Grade): Promise<Word[]> {
  const response = await fetch(`${API_URL}/api/v1/grades/${encodeURIComponent(grade)}/words`);
  if (!response.ok) throw new Error(`The words request failed (${response.status}).`);
  const dtos = (await response.json()) as WordDto[];
  return dtos.map((d) => ({
    id: d.id,
    word: d.word,
    grade: d.grade,
    definition: d.definition,
    example: d.example,
    syllables: d.syllables,
    contentVersion: d.content_version,
    question: {
      id: d.id,
      options: d.options.map((o) => ({ id: o.id, text: o.text })),
      correctOptionId: d.options.find((o) => o.is_correct)?.id ?? "",
      explanation: d.explanation,
    },
  }));
}
