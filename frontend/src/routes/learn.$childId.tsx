import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Lightbulb, XCircle, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Header } from "@/components/wordwise/Header";
import { service, gradeLabel, type Answer, type QuizResult, type Session, type Word } from "@/services";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/learn/$childId")({
  head: () => ({
    meta: [
      { title: "Today's words — WordWise" },
      { name: "description", content: "Learn today's vocabulary words, then take a quick quiz." },
      { property: "og:title", content: "Today's words — WordWise" },
      { property: "og:description", content: "Learn today's vocabulary words, then take a quick quiz." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: LearnPage,
});

function LearnPage() {
  const { childId } = Route.useParams();
  const profile = useQuery({ queryKey: ["profile", childId], queryFn: () => service.getProfile(childId) });
  const grade = profile.data?.grade;
  const content = useQuery({ queryKey: ["content", grade], queryFn: () => {
    if (!grade) throw new Error("Profile grade is missing.");
    return service.getGradeContent(grade);
  }, enabled: !!grade, staleTime: Infinity });
  const [session, setSession] = useState<Session | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const startSession = async (fn: () => Promise<Session>) => {
    setSessionError(null); setResult(null);
    try {
      const s = await fn();
      setSession(s);
      if (s.completed) setResult(await service.getResult(s.id));
    } catch (e) { setSessionError((e as Error).message); }
  };

  useEffect(() => { if (profile.data) startSession(() => service.startOrResumeSession(childId)); }, [profile.data, childId]);

  const wordsById = useMemo(() => new Map((content.data ?? []).map((w) => [w.id, w])), [content.data]);

  const shell = (body: React.ReactNode) => (
    <div className="min-h-screen">
      <Header right={profile.data && <span className="rounded-md border-2 border-foreground bg-secondary px-3 py-1 font-display font-bold">{profile.data.nickname} · {gradeLabel(profile.data.grade)}</span>} />
      <main className="mx-auto max-w-3xl px-4 py-8">{body}</main>
    </div>
  );

  if (profile.isPending) return shell(<p role="status">Loading…</p>);
  if (!profile.data) return shell(<ErrorBox msg="We couldn't find that profile." />);
  if (content.isError) return shell(<ErrorBox msg="We couldn't load the words for this grade." onRetry={() => content.refetch()} />);
  if (sessionError) return shell(<ErrorBox msg={sessionError} onRetry={() => startSession(() => service.startOrResumeSession(childId))} />);
  if (content.isPending || !session) return shell(<p role="status">Getting today's words ready…</p>);

  const words = session.wordIds.map((id) => wordsById.get(id)).filter((word): word is Word => word !== undefined);
  if (words.length !== session.wordIds.length) return shell(<ErrorBox msg="Some words for this session are missing." onRetry={() => content.refetch()} />);

  const persist = async (phase: Session["phase"], position: number) => {
    try { setSession(await service.updateSessionProgress(session.id, phase, position)); }
    catch { toast.error("We couldn't save your place. Your progress may not be saved."); }
  };

  if (result) return shell(
    <Results result={result} wordsById={wordsById}
      onRetry={() => startSession(() => service.startReviewSession(childId, result.reviewWordIds))}
      onNew={() => startSession(() => service.startOrResumeSession(childId))} />,
  );

  const currentWord = words[session.position];
  if (!currentWord) return shell(<ErrorBox msg="We couldn't find the current word for this session." />);

  if (session.phase === "learn") return shell(
    <LearnCard key={session.position} word={currentWord} index={session.position} total={words.length}
      onBack={session.position > 0 ? () => persist("learn", session.position - 1) : undefined}
      onNext={() => session.position + 1 < words.length ? persist("learn", session.position + 1) : persist("quiz", 0)} />,
  );

  return shell(
    <QuizCard key={session.position} word={currentWord} index={session.position} total={words.length}
      existing={session.answers.find((a) => a.index === session.position)}
      onSubmit={async (optionId, hint) => {
        try {
          const a = await service.submitAnswer(session.id, session.position, optionId, hint);
          setSession((s) => s && { ...s, answers: [...s.answers.filter((x) => x.index !== a.index), a] });
          return a;
        } catch { toast.error("We couldn't save that answer. Please try again."); return null; }
      }}
      onNext={async () => {
        if (session.position + 1 < words.length) return persist("quiz", session.position + 1);
        try { setResult(await service.completeSession(session.id)); }
        catch { toast.error("We couldn't save your results. Please try again."); }
      }} />,
  );
}

function ErrorBox({ msg, onRetry }: { msg: string; onRetry?: () => void }) {
  return (
    <div className="block-card p-6" role="alert">
      <p className="font-display text-xl font-bold">Oops!</p>
      <p className="mt-1">{msg}</p>
      <div className="mt-4 flex gap-3">
        {onRetry && <Button variant="block" onClick={onRetry}>Try again</Button>}
        <Button variant="blockPlain" asChild><Link to="/">Back to profiles</Link></Button>
      </div>
    </div>
  );
}

function Progress({ index, total, label }: { index: number; total: number; label: string }) {
  const pct = ((index + 1) / total) * 100;
  return (
    <div className="mb-6">
      <div className="mb-2 flex justify-between font-display font-bold">
        <span>{label}</span><span>{index + 1} of {total}</span>
      </div>
      <div className="h-4 overflow-hidden rounded-full border-2 border-foreground bg-card" role="progressbar" aria-valuemin={1} aria-valuemax={total} aria-valuenow={index + 1}>
        <div className="h-full bg-primary transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function LearnCard({ word, index, total, onNext, onBack }: { word: Word; index: number; total: number; onNext: () => void; onBack?: (() => void) | undefined }) {
  return (
    <>
      <Progress index={index} total={total} label="Learn" />
      <article className="block-card p-6 md:p-10">
        <p className="font-mono text-lg text-muted-foreground" aria-label="Syllables">{word.syllables}</p>
        <h1 className="mt-1 font-display text-5xl font-bold md:text-7xl">{word.word}</h1>
        <div className="mt-8 space-y-6">
          <section>
            <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">What it means</h2>
            <p className="mt-1 text-2xl">{word.definition}</p>
          </section>
          <section className="rounded-lg border-2 border-foreground bg-secondary p-4">
            <h2 className="text-sm font-bold uppercase tracking-wider">Example</h2>
            <p className="mt-1 text-xl italic">"{word.example}"</p>
          </section>
        </div>
      </article>
      <div className="mt-6 flex justify-between gap-3">
        {onBack ? <Button variant="blockPlain" size="xl" onClick={onBack}>Back</Button> : <span />}
        <Button variant="block" size="xl" onClick={onNext} autoFocus>{index + 1 < total ? "Next word" : "Start quiz"}</Button>
      </div>
    </>
  );
}

function QuizCard({ word, index, total, existing, onSubmit, onNext }: {
  word: Word; index: number; total: number; existing?: Answer | undefined;
  onSubmit: (optionId: string, hint: boolean) => Promise<Answer | null>; onNext: () => void;
}) {
  const [selected, setSelected] = useState<string | null>(existing?.selectedOptionId ?? null);
  const [hint, setHint] = useState(existing?.hintUsed ?? false);
  const [answer, setAnswer] = useState<Answer | null>(existing ?? null);
  const [busy, setBusy] = useState(false);
  const locked = !!answer;

  return (
    <>
      <Progress index={index} total={total} label="Quiz" />
      <article className="block-card p-6 md:p-10">
        <p className="text-lg text-muted-foreground">What does this word mean?</p>
        <h1 className="mt-1 font-display text-5xl font-bold md:text-6xl">{word.word}</h1>

        <div className="mt-4">
          {hint ? (
            <p className="rounded-lg border-2 border-foreground bg-secondary p-3 italic"><Lightbulb className="mr-2 inline h-5 w-5" aria-hidden />Hint: "{word.example}"</p>
          ) : !locked && (
            <Button variant="blockSecondary" onClick={() => setHint(true)}><Lightbulb className="h-4 w-4" /> Show a hint</Button>
          )}
        </div>

        <div role="radiogroup" aria-label="Answer choices" className="mt-6 grid gap-3">
          {word.question.options.map((o, i) => {
            const isSel = selected === o.id;
            const isCorrect = o.id === word.question.correctOptionId;
            return (
              <button key={o.id} role="radio" aria-checked={isSel} disabled={locked} onClick={() => setSelected(o.id)}
                className={cn(
                  "press flex min-h-16 items-center gap-4 rounded-lg border-2 border-foreground p-4 text-left text-lg shadow-block-sm focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring",
                  !locked && (isSel ? "bg-primary text-primary-foreground" : "bg-card hover:bg-muted"),
                  locked && isCorrect && "bg-success text-success-foreground",
                  locked && isSel && !isCorrect && "bg-destructive text-destructive-foreground",
                  locked && !isSel && !isCorrect && "bg-card opacity-60",
                )}>
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border-2 border-current font-display font-bold">{String.fromCharCode(65 + i)}</span>
                <span className="flex-1">{o.text}</span>
                {locked && isCorrect && <span className="flex items-center gap-1 font-bold"><CheckCircle2 className="h-5 w-5" />Correct answer</span>}
                {locked && isSel && !isCorrect && <span className="flex items-center gap-1 font-bold"><XCircle className="h-5 w-5" />Your answer</span>}
              </button>
            );
          })}
        </div>

        {answer && (
          <div role="status" className={cn("mt-6 rounded-lg border-2 border-foreground p-4", answer.correct ? "bg-success text-success-foreground" : "bg-accent text-accent-foreground")}>
            <p className="font-display text-2xl font-bold">{answer.correct ? "Nice work! 🎉" : "Not quite — good try!"}</p>
            <p className="mt-1 text-lg">{word.question.explanation}</p>
            {answer.correct && answer.hintUsed && <p className="mt-2 text-sm font-medium">You used a hint, so we'll practice this word again soon.</p>}
          </div>
        )}
      </article>

      <div className="mt-6 flex justify-end">
        {answer ? (
          <Button variant="block" size="xl" onClick={onNext} autoFocus>{index + 1 < total ? "Next question" : "See results"}</Button>
        ) : (
          <Button variant="block" size="xl" disabled={!selected || busy}
            onClick={async () => {
              if (!selected || busy) return;
              setBusy(true);
              try { const a = await onSubmit(selected, hint); if (a) setAnswer(a); }
              finally { setBusy(false); }
            }}>
            {busy ? "Checking…" : "Submit answer"}
          </Button>
        )}
      </div>
    </>
  );
}

function Results({ result, wordsById, onRetry, onNew }: { result: QuizResult; wordsById: Map<string, Word>; onRetry: () => void; onNew: () => void }) {
  const total = result.correctCount + result.incorrectCount;
  const list = (ids: string[], title: string, note: string) => ids.length > 0 && (
    <section className="mt-8">
      <h2 className="font-display text-2xl font-bold">{title}</h2>
      <p className="text-muted-foreground">{note}</p>
      <div className="mt-3 grid gap-3">
        {ids.map((id) => { const w = wordsById.get(id); return w && (
          <div key={id} className="block-card p-4">
            <p className="font-display text-xl font-bold">{w.word} <span className="ml-2 font-mono text-sm font-normal text-muted-foreground">{w.syllables}</span></p>
            <p>{w.definition}</p>
            <p className="mt-1 italic text-muted-foreground">"{w.example}"</p>
          </div>
        ); })}
      </div>
    </section>
  );

  return (
    <>
      <div className="block-card bg-primary p-8 text-center text-primary-foreground">
        <p className="font-display text-lg font-bold">Session complete!</p>
        <p className="font-display text-7xl font-bold">{result.correctCount}/{total}</p>
        <p className="mt-2 text-lg">{result.correctCount === total ? "Perfect score — amazing!" : "Great effort — keep going!"}</p>
      </div>
      <div className="mt-6 grid grid-cols-2 gap-4">
        <div className="block-card flex items-center gap-3 p-4"><CheckCircle2 className="h-8 w-8 text-success" aria-hidden /><div><p className="font-display text-3xl font-bold">{result.correctCount}</p><p>Correct</p></div></div>
        <div className="block-card flex items-center gap-3 p-4"><XCircle className="h-8 w-8 text-destructive" aria-hidden /><div><p className="font-display text-3xl font-bold">{result.incorrectCount}</p><p>Incorrect</p></div></div>
      </div>
      {list(result.missedWordIds, "Words missed", "These need another look.")}
      {list(result.hintedWordIds, "Correct with a hint", "You got these! We'll review them again.")}
      <div className="mt-8 flex flex-wrap gap-3">
        {result.reviewWordIds.length > 0 && <Button variant="blockSecondary" size="xl" onClick={onRetry}><RotateCcw className="h-5 w-5" />Retry review words</Button>}
        <Button variant="block" size="xl" onClick={onNew}>New session</Button>
        <Button variant="blockPlain" size="xl" asChild><Link to="/">Switch profile</Link></Button>
      </div>
    </>
  );
}
