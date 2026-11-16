import type {
  Answer, ChildProfile, Grade, ProfileInput, QuizResult, Session, SessionPhase, Word, WordMastery, WordWiseService,
} from "../types";
import { getMockGradeWords } from "./mock-content";

// Mock persistence in localStorage (browser only). Real service will use IndexedDB per spec.
interface DB {
  children: ChildProfile[];
  sessions: Session[];
  quizResults: QuizResult[];
  wordMastery: WordMastery[];
}
const KEY = "wordwise-mock-db-v1";
const delay = (ms = 150) => new Promise((r) => setTimeout(r, ms));
const now = () => new Date().toISOString();
const uid = () => crypto.randomUUID();

function load(): DB {
  const raw = localStorage.getItem(KEY);
  return raw ? JSON.parse(raw) : { children: [], sessions: [], quizResults: [], wordMastery: [] };
}
function save(db: DB) {
  try {
    localStorage.setItem(KEY, JSON.stringify(db));
  } catch {
    throw new Error("We couldn't save your progress on this device.");
  }
}
function allWords(): Word[] {
  return (["K","1","2","3","4","5","6","7","8","9","10","11","12"] as Grade[]).flatMap(getMockGradeWords);
}
function findWord(id: string) {
  const w = allWords().find((x) => x.id === id);
  if (!w) throw new Error("Word not found");
  return w;
}

// Simple mock selection: review words first, then new/learning, then mastered; repeat to fill goal.
function selectWords(db: DB, child: ChildProfile): string[] {
  const words = getMockGradeWords(child.grade);
  const m = (id: string) => db.wordMastery.find((x) => x.childId === child.id && x.wordId === id);
  const rank = (id: string) => {
    const s = m(id);
    if (s?.needsReview) return 0;
    if (!s || s.status !== "MASTERED") return 1;
    return 2;
  };
  const ordered = [...words].sort((a, b) => rank(a.id) - rank(b.id)).map((w) => w.id);
  const out: string[] = [];
  while (out.length < child.dailyGoal && ordered.length) {
    const wordId = ordered[out.length % ordered.length];
    if (!wordId) break;
    out.push(wordId);
  }
  return out;
}

export const mockService: WordWiseService = {
  async listProfiles() { await delay(); return load().children; },
  async getProfile(id) { await delay(); return load().children.find((c) => c.id === id) ?? null; },
  async createProfile(input: ProfileInput) {
    await delay();
    const db = load();
    const p: ChildProfile = { id: uid(), ...input, nickname: input.nickname.trim(), createdAt: now(), updatedAt: now() };
    db.children.push(p); save(db); return p;
  },
  async updateProfile(id, input) {
    await delay();
    const db = load();
    const p = db.children.find((c) => c.id === id);
    if (!p) throw new Error("Profile not found");
    const gradeChanged = p.grade !== input.grade;
    Object.assign(p, input, { nickname: input.nickname.trim(), updatedAt: now() });
    if (gradeChanged) db.sessions = db.sessions.filter((s) => !(s.childId === id && !s.completed));
    save(db); return p;
  },
  async deleteProfile(id) {
    await delay();
    const db = load();
    const sessionIds = db.sessions.filter((s) => s.childId === id).map((s) => s.id);
    db.children = db.children.filter((c) => c.id !== id);
    db.sessions = db.sessions.filter((s) => s.childId !== id);
    db.quizResults = db.quizResults.filter((r) => !sessionIds.includes(r.sessionId));
    db.wordMastery = db.wordMastery.filter((m) => m.childId !== id);
    save(db);
  },

  async getGradeContent(grade) { await delay(300); return getMockGradeWords(grade); },

  async startOrResumeSession(childId) {
    await delay();
    const db = load();
    const open = db.sessions.find((s) => s.childId === childId && !s.completed);
    if (open) return open;
    const child = db.children.find((c) => c.id === childId);
    if (!child) throw new Error("Profile not found");
    const s: Session = { id: uid(), childId, startedAt: now(), wordIds: selectWords(db, child), phase: "learn", position: 0, answers: [], completed: false };
    db.sessions.push(s); save(db); return s;
  },
  async startReviewSession(childId, wordIds) {
    await delay();
    const db = load();
    db.sessions = db.sessions.filter((s) => !(s.childId === childId && !s.completed));
    const s: Session = { id: uid(), childId, startedAt: now(), wordIds, phase: "learn", position: 0, answers: [], completed: false };
    db.sessions.push(s); save(db); return s;
  },
  async updateSessionProgress(sessionId, phase: SessionPhase, position) {
    const db = load();
    const s = db.sessions.find((x) => x.id === sessionId);
    if (!s) throw new Error("Session not found");
    s.phase = phase; s.position = position; save(db); return s;
  },
  async submitAnswer(sessionId, index, selectedOptionId, hintUsed) {
    await delay();
    const db = load();
    const s = db.sessions.find((x) => x.id === sessionId);
    if (!s) throw new Error("Session not found");
    const existing = s.answers.find((a) => a.index === index);
    if (existing) return existing; // answers are final
    const wordId = s.wordIds[index];
    if (!wordId) throw new Error("Question not found");
    const word = findWord(wordId);
    const a: Answer = { index, wordId: word.id, selectedOptionId, correct: selectedOptionId === word.question.correctOptionId, hintUsed, answeredAt: now() };
    s.answers.push(a); save(db); return a;
  },
  async completeSession(sessionId) {
    await delay();
    const db = load();
    const s = db.sessions.find((x) => x.id === sessionId);
    if (!s) throw new Error("Session not found");
    const prior = db.quizResults.find((r) => r.sessionId === sessionId);
    if (prior) return prior;
    const correctCount = s.answers.filter((a) => a.correct).length;
    const unique = [...new Set(s.wordIds)];
    const missed = unique.filter((id) => s.answers.some((a) => a.wordId === id && !a.correct));
    const hinted = unique.filter((id) => !missed.includes(id) && s.answers.some((a) => a.wordId === id && a.hintUsed));
    // Mastery: once per word per session.
    for (const id of unique) {
      let m = db.wordMastery.find((x) => x.childId === s.childId && x.wordId === id);
      if (!m) { m = { childId: s.childId, wordId: id, status: "NEW", consecutiveCorrect: 0, lastPracticed: null, needsReview: false }; db.wordMastery.push(m); }
      const wasMissed = missed.includes(id);
      m.consecutiveCorrect = wasMissed ? 0 : m.consecutiveCorrect + 1;
      m.status = m.consecutiveCorrect >= 3 ? "MASTERED" : "LEARNING";
      m.needsReview = wasMissed || hinted.includes(id);
      m.lastPracticed = now();
    }
    const r: QuizResult = {
      sessionId, score: Math.round((correctCount / Math.max(1, s.answers.length)) * 100), correctCount,
      incorrectCount: s.answers.length - correctCount, missedWordIds: missed, hintedWordIds: hinted, reviewWordIds: [...missed, ...hinted],
    };
    s.completed = true; s.phase = "done";
    db.quizResults.push(r); save(db); return r;
  },
  async getSession(id) { await delay(); return load().sessions.find((s) => s.id === id) ?? null; },
  async getResult(id) { await delay(); return load().quizResults.find((r) => r.sessionId === id) ?? null; },
  async getMastery(childId) { await delay(); return load().wordMastery.filter((m) => m.childId === childId); },
};
