## WordWise service boundary
- Keep vocabulary selection and persistence behind `WordWiseService`; profile calls go to the backend API (`src/services/api.ts`) and the remaining calls (sessions, quiz, dashboard) still use the mock implementation until their endpoints exist (`VITE_USE_MOCK=true` forces the mock for everything), so UI and service logic remain independently replaceable.
- Narrow optional grades, words, and selections before service calls or rendering; missing saved values must show a recoverable error instead of crashing the learning flow.

## Documents

- Styling tokens and components: `_docs/design-system.md` (source: `src/styles.css`, `src/components`)
- Before writing tests, read `_docs/testing-guidelines.md`
- API the services call: `_docs/api.md`
- Spec and architecture: `_docs/plan.md`, `_docs/architecture.md`; the original Lovable repo is never modified
- Process: `_docs/process.md`, `docs/process.md`, `docs/agents.md`

## Commands

- `bun install` - install dependencies; `bun run dev` - run the UI; `bun run test` - the suite

