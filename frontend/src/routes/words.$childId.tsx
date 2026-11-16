import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Header } from "@/components/wordwise/Header";
import { service, gradeLabel } from "@/services";
import { fetchGradeWords } from "@/services/api";

export const Route = createFileRoute("/words/$childId")({
  head: () => ({
    meta: [
      { title: "Words to learn — WordWise" },
      { name: "description", content: "Browse the vocabulary words for your grade." },
    ],
  }),
  component: WordsPage,
});

function WordsPage() {
  const { childId } = Route.useParams();
  const profile = useQuery({ queryKey: ["profile", childId], queryFn: () => service.getProfile(childId) });
  const grade = profile.data?.grade;
  const words = useQuery({
    queryKey: ["grade-words", grade],
    queryFn: () => fetchGradeWords(grade!),
    enabled: !!grade,
  });

  const shell = (body: React.ReactNode) => (
    <div className="min-h-screen">
      <Header
        right={
          profile.data && (
            <span className="rounded-md border-2 border-foreground bg-secondary px-3 py-1 font-display font-bold">
              {profile.data.nickname} · {gradeLabel(profile.data.grade)}
            </span>
          )
        }
      />
      <main className="mx-auto max-w-3xl px-4 py-8">{body}</main>
    </div>
  );

  if (profile.isPending) return shell(<p role="status">Loading…</p>);
  if (!profile.data) return shell(<p>We couldn't find that profile.</p>);
  if (words.isError)
    return shell(
      <div className="block-card p-6">
        <p className="font-medium">We couldn't load the words for this grade.</p>
        <Button variant="blockPlain" className="mt-4" onClick={() => words.refetch()}>Try again</Button>
      </div>,
    );
  if (words.isPending) return shell(<p role="status">Getting the words ready…</p>);
  if (words.data.length === 0) return shell(<p>There are no words for this grade yet.</p>);

  return shell(
    <>
      <h1 className="font-display text-3xl font-bold md:text-4xl">Words for {gradeLabel(profile.data.grade)}</h1>
      <ul className="mt-6 grid gap-4">
        {words.data.map((w) => (
          <li key={w.id} className="block-card p-5">
            <p className="font-display text-2xl font-bold">{w.word}</p>
            <p className="text-sm text-muted-foreground">{w.syllables}</p>
            <p className="mt-2">{w.definition}</p>
            <p className="mt-1 italic">“{w.example}”</p>
          </li>
        ))}
      </ul>
    </>,
  );
}
