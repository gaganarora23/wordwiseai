// Contract between the UI and the service layer. The real service must implement WordWiseService.
export type Grade = "K" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12";
export const GRADES: Grade[] = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];
export const gradeLabel = (g: Grade) => (g === "K" ? "Kindergarten" : `Grade ${g}`);

export type DailyGoal = 5 | 10;

export interface ChildProfile {
  id: string;
  nickname: string;
  grade: Grade;
  dailyGoal: DailyGoal;
  createdAt: string;
  updatedAt: string;
}
export type ProfileInput = Pick<ChildProfile, "nickname" | "grade" | "dailyGoal">;

export interface AnswerOption { id: string; text: string }
export interface Word {
  id: string;
  word: string;
  grade: Grade;
  definition: string;
  example: string;
  syllables: string;
  contentVersion: string;
  question: { id: string; options: AnswerOption[]; correctOptionId: string; explanation: string };
}

export type MasteryStatus = "NEW" | "LEARNING" | "MASTERED";
export interface WordMastery {
  childId: string;
  wordId: string;
  status: MasteryStatus;
  consecutiveCorrect: number;
  lastPracticed: string | null;
  needsReview: boolean;
}

export type SessionPhase = "learn" | "quiz" | "done";
export interface Answer {
  index: number; // position in the session (words may repeat)
  wordId: string;
  selectedOptionId: string;
  correct: boolean;
  hintUsed: boolean;
  answeredAt: string;
}
export interface Session {
  id: string;
  childId: string;
  startedAt: string;
  wordIds: string[]; // fixed order, never reshuffled on restore
  phase: SessionPhase;
  position: number;
  answers: Answer[];
  completed: boolean;
}

export interface QuizResult {
  sessionId: string;
  score: number;
  correctCount: number;
  incorrectCount: number;
  missedWordIds: string[];
  hintedWordIds: string[];
  reviewWordIds: string[];
}

export interface WordWiseService {
  listProfiles(): Promise<ChildProfile[]>;
  getProfile(id: string): Promise<ChildProfile | null>;
  createProfile(input: ProfileInput): Promise<ChildProfile>;
  updateProfile(id: string, input: ProfileInput): Promise<ChildProfile>;
  deleteProfile(id: string): Promise<void>;

  getGradeContent(grade: Grade): Promise<Word[]>;

  /** Returns the in-progress session for the child, or creates one. Word selection belongs to the service. */
  startOrResumeSession(childId: string): Promise<Session>;
  /** Starts a session with only the given words (retry review words). */
  startReviewSession(childId: string, wordIds: string[]): Promise<Session>;
  updateSessionProgress(sessionId: string, phase: SessionPhase, position: number): Promise<Session>;
  submitAnswer(sessionId: string, index: number, selectedOptionId: string, hintUsed: boolean): Promise<Answer>;
  completeSession(sessionId: string): Promise<QuizResult>;
  getSession(sessionId: string): Promise<Session | null>;
  getResult(sessionId: string): Promise<QuizResult | null>;

  getMastery(childId: string): Promise<WordMastery[]>;
}
