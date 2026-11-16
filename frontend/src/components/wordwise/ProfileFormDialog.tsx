import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { GRADES, gradeLabel, type ChildProfile, type DailyGoal, type Grade, type ProfileInput } from "@/services";
import { cn } from "@/lib/utils";

interface Props {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initial?: ChildProfile | null;
  onSubmit: (input: ProfileInput) => Promise<void>;
}

export function ProfileFormDialog({ open, onOpenChange, initial, onSubmit }: Props) {
  const [nickname, setNickname] = useState("");
  const [grade, setGrade] = useState<Grade | "">("");
  const [goal, setGoal] = useState<DailyGoal>(5);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setNickname(initial?.nickname ?? "");
      setGrade(initial?.grade ?? "");
      setGoal(initial?.dailyGoal ?? 5);
    }
  }, [open, initial]);

  const valid = nickname.trim().length > 0 && grade !== "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="block-card">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl">{initial ? "Edit profile" : "New learner"}</DialogTitle>
          <DialogDescription>Just a nickname, grade and daily goal. No personal details needed.</DialogDescription>
        </DialogHeader>
        <form
          className="space-y-5"
          onSubmit={async (e) => {
            e.preventDefault();
            if (!valid) return;
            setBusy(true);
            try { await onSubmit({ nickname, grade: grade as Grade, dailyGoal: goal }); } finally { setBusy(false); }
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="nickname">Nickname</Label>
            <Input id="nickname" maxLength={20} value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="e.g. Sunny" className="h-11 border-2" />
          </div>
          <div className="space-y-2">
            <Label>Grade</Label>
            <Select value={grade} onValueChange={(v) => setGrade(v as Grade)}>
              <SelectTrigger className="h-11 border-2"><SelectValue placeholder="Choose a grade" /></SelectTrigger>
              <SelectContent>{GRADES.map((g) => <SelectItem key={g} value={g}>{gradeLabel(g)}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Daily goal</legend>
            <div className="grid grid-cols-2 gap-3">
              {([5, 10] as DailyGoal[]).map((g) => (
                <button key={g} type="button" aria-pressed={goal === g} onClick={() => setGoal(g)}
                  className={cn("press rounded-lg border-2 border-foreground py-3 font-display text-lg font-bold shadow-block-sm",
                    goal === g ? "bg-secondary" : "bg-card")}>
                  {g} words
                </button>
              ))}
            </div>
          </fieldset>
          <DialogFooter>
            <Button type="submit" variant="block" size="lg" disabled={!valid || busy}>{busy ? "Saving…" : "Save"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
