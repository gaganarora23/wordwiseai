import type { WordWiseService } from "./types";
import { mockService } from "./mock/mock-service";
import { httpProfileService } from "./api";

// Profiles live in PostgreSQL behind the API. Sessions, quizzes and the dashboard are not built on the
// backend yet (post-mvp), so those calls stay on the mock. Set VITE_USE_MOCK=true to run fully offline.
export const service: WordWiseService =
  import.meta.env["VITE_USE_MOCK"] === "true" ? mockService : { ...mockService, ...httpProfileService };
export * from "./types";
