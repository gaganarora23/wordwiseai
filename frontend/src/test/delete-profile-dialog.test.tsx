import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DeleteProfileDialog } from "@/components/wordwise/DeleteProfileDialog";
import type { ChildProfile } from "@/services";

const profile: ChildProfile = {
  id: "p1", nickname: "Sam", grade: "3", dailyGoal: 5,
  createdAt: "2026-01-01T00:00:00Z", updatedAt: "2026-01-01T00:00:00Z",
};

function setup() {
  const onConfirm = vi.fn().mockResolvedValue(undefined);
  render(<DeleteProfileDialog profile={profile} onOpenChange={() => {}} onConfirm={onConfirm} />);
  return { onConfirm, input: screen.getByLabelText(/to continue/i), next: screen.getByRole("button", { name: "Continue" }) };
}

describe("DeleteProfileDialog safeguards", () => {
  it("says deletion is permanent, with no undo, and that the data is in the shared database", () => {
    setup();
    const text = screen.getByRole("dialog").textContent ?? "";
    expect(text).toMatch(/permanently/i);
    expect(text).toMatch(/no undo/i);
    expect(text).toMatch(/shared database/i);
    expect(text).not.toMatch(/from this browser/i);
  });

  it.each(["", "delete", " DELETE", "DELETE "])("keeps Continue disabled for %j", (typed) => {
    const { input, next } = setup();
    fireEvent.change(input, { target: { value: typed } });
    expect(next).toBeDisabled();
  });

  it("needs exactly DELETE, then a separate final confirmation before confirming", async () => {
    const { onConfirm, input, next } = setup();
    fireEvent.change(input, { target: { value: "DELETE" } });
    expect(next).toBeEnabled();
    fireEvent.click(next);
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText(/this cannot be undone/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /yes, delete forever/i }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1));
  });
});
