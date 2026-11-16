# Design system (as built)

A factual summary of the frontend styling. The source of truth is `frontend/src/styles.css` and the components in `frontend/src/components`; this file does not add rules of its own.

- Stack: Tailwind CSS with theme tokens declared in `@theme inline` in `frontend/src/styles.css`. Use the tokens (`bg-primary`, `text-foreground`, `border-border` and so on) rather than literal colors.
- Colors (oklch): `background`, `foreground`, `card`, `popover`, `primary` (blue), `secondary` (yellow), `muted`, `accent` (orange), `success` (green), `destructive` (red), `border`/`input` (near black), `ring`, plus `sidebar-*` tokens. Each has a `*-foreground` pair where it carries text.
- Fonts: display headings (`h1` to `h4`) use "Space Grotesk" (`--font-display`); body uses "DM Sans" (`--font-sans`). Never `@import` a remote font or CSS URL; the header comment in `styles.css` explains how fonts are loaded.
- Shape: base radius `--radius: 0.75rem` with `sm`, `md`, `lg`, `xl` derived from it; hard-edged block shadows (`--shadow-block`, `--shadow-block-sm`).
- Components: `frontend/src/components/ui/` holds the shadcn-style primitives (button, card, dialog, alert-dialog, form, input, select, tabs, and so on). `frontend/src/components/wordwise/` holds the app's own components (`Header`, `ProfileFormDialog`, `DeleteProfileDialog`). Prefer composing these before adding a new one.
- Tests for UI changes: see `_docs/testing-guidelines.md`.
