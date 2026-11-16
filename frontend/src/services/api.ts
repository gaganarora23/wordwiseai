import type { Grade, Word } from "./types";

const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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
