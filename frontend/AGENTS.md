## WordWise service boundary
- Keep vocabulary selection and persistence behind `WordWiseService`; profile calls go to the backend API (`src/services/api.ts`) and the remaining calls (sessions, quiz, dashboard) still use the mock implementation until their endpoints exist (`VITE_USE_MOCK=true` forces the mock for everything), so UI and service logic remain independently replaceable.
- Narrow optional grades, words, and selections before service calls or rendering; missing saved values must show a recoverable error instead of crashing the learning flow.
