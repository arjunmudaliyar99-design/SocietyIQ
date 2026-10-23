import {
  Calculator,
  FileText,
  House,
  IndianRupee,
  Megaphone,
  MessageSquareWarning,
  Settings,
  ShieldCheck,
  Users,
  Wallet,
} from "lucide-react";
import type { ReactNode } from "react";

export interface NavItem {
  path: string;
  key: string;
  icon: ReactNode;
}

// Simple view shows 5 items (docs/03 §1.2). Which 5 is not in the docs yet:
// TODO(confirm): Q-030. Chosen from the v1 modules the treasurer uses most.
export const SIMPLE_NAV: NavItem[] = [
  { path: "/", key: "home", icon: <House size={22} /> },
  { path: "/bills", key: "bills", icon: <FileText size={22} /> },
  { path: "/payments", key: "payments", icon: <Wallet size={22} /> },
  { path: "/dues", key: "dues", icon: <IndianRupee size={22} /> },
  { path: "/complaints", key: "complaints", icon: <MessageSquareWarning size={22} /> },
];

export const DETAILED_NAV: NavItem[] = [
  { path: "/flats", key: "flats", icon: <Users size={22} /> },
  { path: "/charges", key: "charges", icon: <Calculator size={22} /> },
  { path: "/notices", key: "notices", icon: <Megaphone size={22} /> },
  { path: "/compliance", key: "compliance", icon: <ShieldCheck size={22} /> },
  { path: "/settings", key: "settings", icon: <Settings size={22} /> },
];
