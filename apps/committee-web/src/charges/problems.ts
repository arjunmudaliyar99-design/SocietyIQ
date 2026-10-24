import { ApiError } from "@societyiq/shared";

import type { LegalProblem } from "../api/charges";

/** Problems carried by a refused save (LEGAL_BLOCK, REASON_REQUIRED, RESOLUTION_REQUIRED). */
export function problemsOf(error: unknown): LegalProblem[] {
  if (error instanceof ApiError && Array.isArray(error.details)) return error.details as LegalProblem[];
  return [];
}
