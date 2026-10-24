import { createContext, useContext } from "react";

import type { MySociety } from "../api/hooks";

export interface CurrentSocietyValue {
  society: MySociety;
  /** True when the person belongs to more than one society. */
  canSwitch: boolean;
  switchSociety: () => void;
}

export const CurrentSocietyContext = createContext<CurrentSocietyValue | null>(null);

/** Null outside the gate (e.g. component tests of the shell). */
export function useCurrentSociety(): CurrentSocietyValue | null {
  return useContext(CurrentSocietyContext);
}
