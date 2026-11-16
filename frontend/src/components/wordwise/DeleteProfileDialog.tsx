import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ChildProfile } from "@/services";

export function DeleteProfileDialog({ profile, onOpenChange, onConfirm }: {
  profile: ChildProfile | null; onOpenChange: (o: boolean) => void; onConfirm: () => Promise<void>;
}) {
  const [step, setStep] = useState<1 | 2>(1);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (profile) { setStep(1); setTyped(""); } }, [profile]);

  return (
    <Dialog open={!!profile} onOpenChange={onOpenChange}>
      <DialogContent className="block-card">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl">Delete {profile?.nickname}?</DialogTitle>
          <DialogDescription>This removes the profile and all of its learning history from this browser.</DialogDescription>
        </DialogHeader>
        {step === 1 ? (
          <>
            <div className="space-y-2">
              <Label htmlFor="confirm-delete">Type <span className="font-mono font-bold">DELETE</span> to continue</Label>
              <Input id="confirm-delete" autoComplete="off" value={typed} onChange={(e) => setTyped(e.target.value)} className="h-11 border-2" />
            </div>
            <DialogFooter>
              <Button variant="blockPlain" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button variant="blockDanger" disabled={typed !== "DELETE"} onClick={() => setStep(2)}>Continue</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <p className="rounded-lg border-2 border-destructive p-3 font-medium">Final check: this cannot be undone.</p>
            <DialogFooter>
              <Button variant="blockPlain" onClick={() => onOpenChange(false)}>Keep profile</Button>
              <Button variant="blockDanger" disabled={busy} onClick={async () => { setBusy(true); try { await onConfirm(); } finally { setBusy(false); } }}>
                Yes, delete forever
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
