import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SharedDemoNotice } from "@/routes/index";

describe("Shared demo notice", () => {
  it("says it is a shared demo without authentication and warns against real children's data", () => {
    render(<SharedDemoNotice />);

    const text = screen.getByTestId("shared-demo-notice").textContent ?? "";
    expect(text).toMatch(/shared demo/i);
    expect(text).toMatch(/no sign-in/i);
    expect(text).toMatch(/do not enter real children's data/i);
    expect(text).not.toMatch(/only in this browser/i);
  });
});
