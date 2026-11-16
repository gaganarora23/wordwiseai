# WordWise frontend

TanStack Start app (React 19, Vite, Tailwind v4). Needs Node 24 and bun 1.4.

```sh
bun install --frozen-lockfile   # once, and after dependency changes
bun run test                    # Vitest
bun run build                   # production build
bun run dev                     # local dev server
```

`make test` at the repository root runs the backend and frontend suites; run
`bun install` first on a fresh clone.
