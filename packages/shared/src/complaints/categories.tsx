// Category icons and the status list, shared by both apps (docs/02 §8).
import {
  ArrowUpDown,
  Car,
  CircleHelp,
  Droplets,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import type { ReactNode } from "react";

import type { ComplaintCategory, ComplaintStatus } from "./api";

export const COMPLAINT_CATEGORIES: {
  value: ComplaintCategory;
  icon: ReactNode;
}[] = [
  { value: "water", icon: <Droplets size={28} /> },
  { value: "lift", icon: <ArrowUpDown size={28} /> },
  { value: "electricity", icon: <Zap size={28} /> },
  { value: "cleaning", icon: <Sparkles size={28} /> },
  { value: "security", icon: <Shield size={28} /> },
  { value: "parking", icon: <Car size={28} /> },
  { value: "other", icon: <CircleHelp size={28} /> },
];

export const COMPLAINT_STATUSES: ComplaintStatus[] = [
  "open",
  "in_progress",
  "resolved",
  "closed",
];

export function categoryIcon(category: ComplaintCategory): ReactNode {
  return COMPLAINT_CATEGORIES.find((c) => c.value === category)?.icon;
}
