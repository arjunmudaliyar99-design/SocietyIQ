import { ApiError } from "../api/client";
import { SignInError } from "./auth-context";

/** i18n key (common namespace) for any error from sign-in or the API. */
export function messageKeyOf(error: unknown): string {
  if (error instanceof SignInError || error instanceof ApiError) return error.messageKey;
  return "errors.generic";
}
