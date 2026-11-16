import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Header } from "@/components/wordwise/Header";
import { ProfileFormDialog } from "@/components/wordwise/ProfileFormDialog";
import { DeleteProfileDialog } from "@/components/wordwise/DeleteProfileDialog";
import { service, gradeLabel, type ChildProfile } from "@/services";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "WordWise — Who's learning today?" },
      { name: "description", content: "Pick a learner profile and start today's vocabulary words." },
      { property: "og:title", content: "WordWise — Who's learning today?" },
      { property: "og:description", content: "Pick a learner profile and start today's vocabulary words." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

const TILE_COLORS = ["bg-primary text-primary-foreground", "bg-secondary text-secondary-foreground", "bg-accent text-accent-foreground", "bg-success text-success-foreground"];

function Index() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const profiles = useQuery({ queryKey: ["profiles"], queryFn: () => service.listProfiles() });
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ChildProfile | null>(null);
  const [deleting, setDeleting] = useState<ChildProfile | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["profiles"] });

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-5xl px-4 py-10">
        <h1 className="font-display text-4xl font-bold md:text-6xl">Who's learning today?</h1>
        <p className="mt-2 text-lg text-muted-foreground">Pick your profile to start today's words.</p>

        {profiles.isPending && <p className="mt-10" role="status">Loading profiles…</p>}
        {profiles.isError && (
          <div className="block-card mt-10 p-6">
            <p className="font-medium">We couldn't load profiles.</p>
            <Button variant="blockPlain" className="mt-4" onClick={() => profiles.refetch()}>Try again</Button>
          </div>
        )}

        {profiles.data && (
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {profiles.data.map((p, i) => (
              <div key={p.id} className="block-card flex flex-col overflow-hidden">
                <button
                  className={`flex flex-1 flex-col items-start gap-1 p-6 text-left ${TILE_COLORS[i % TILE_COLORS.length]} focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring`}
                  onClick={() => navigate({ to: "/words/$childId", params: { childId: p.id } })}
                >
                  <span className="font-display text-3xl font-bold">{p.nickname}</span>
                  <span className="font-medium opacity-90">{gradeLabel(p.grade)} · {p.dailyGoal} words a day</span>
                  <span className="mt-4 font-display font-bold underline underline-offset-4">See your words →</span>
                </button>
                <div className="flex border-t-2 border-foreground">
                  <button className="flex flex-1 items-center justify-center gap-2 py-3 text-sm font-medium hover:bg-muted" onClick={() => { setEditing(p); setFormOpen(true); }}>
                    <Pencil className="h-4 w-4" /> Edit
                  </button>
                  <button className="flex flex-1 items-center justify-center gap-2 border-l-2 border-foreground py-3 text-sm font-medium hover:bg-muted" onClick={() => setDeleting(p)}>
                    <Trash2 className="h-4 w-4" /> Delete
                  </button>
                </div>
              </div>
            ))}
            <button
              onClick={() => { setEditing(null); setFormOpen(true); }}
              className="press flex min-h-48 flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-foreground bg-card p-6 font-display text-xl font-bold hover:bg-muted"
            >
              <Plus className="h-8 w-8" /> Add a learner
            </button>
          </div>
        )}

        <p className="mt-12 max-w-xl text-sm text-muted-foreground">
          Profiles and progress are kept only in this browser. Clearing browser data or switching devices will remove them.
        </p>
      </main>

      <ProfileFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        initial={editing}
        onSubmit={async (input) => {
          try {
            if (editing) await service.updateProfile(editing.id, input);
            else await service.createProfile(input);
            toast.success(editing ? "Profile updated" : "Profile created");
            setFormOpen(false);
            refresh();
          } catch (e) { toast.error((e as Error).message || "Couldn't save the profile."); }
        }}
      />
      <DeleteProfileDialog
        profile={deleting}
        onOpenChange={(o) => !o && setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          try { await service.deleteProfile(deleting.id); toast.success("Profile deleted"); setDeleting(null); refresh(); }
          catch (e) { toast.error((e as Error).message || "Couldn't delete the profile."); }
        }}
      />
    </div>
  );
}
