import type { WordWiseService } from "./types";
import { mockService } from "./mock/mock-service";

// Swap this for the real implementation when the service layer is ready.
export const service: WordWiseService = mockService;
export * from "./types";
