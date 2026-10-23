# DECISIONS

Decisions made during planning and building. Newest first. Format: date — decision — why — who.

- 2026-10-23 — Front-end toolchain pinned for M0: Vite 8, React 18.3, Tailwind 4 (`@tailwindcss/vite`), Vitest 5, ESLint 10 with typescript-eslint; TypeScript held at 5.9 because typescript-eslint does not support TypeScript 7 — React 18 is the decided stack (CLAUDE.md §3); the rest are current releases — M0 build session, to be confirmed by the Co-founder (Engineering).
- 2026-10-23 — `packages/shared` exports TypeScript source (no pre-build step needed by apps); `tsc` still type-checks and builds it — simpler dev loop — M0 build session, to be confirmed.

- 2026-10-23 — Billing follows the statutory apportionment of MCS Rules 106C-12 and 106C-11 (2026), with legal limits stored in a versioned `legal_parameters` table — law requires it; limits change — The Founder (from the Legal & Society Advisor's feedback).
- 2026-10-23 — Languages: English (main and fallback), Marathi, Hindi, Gujarati, Tamil — target users — The Founder.
- 2026-10-23 — One-liner "Society management, automated." (pending trademark check, Q-022) — automation positioning; "on autopilot" is used by competitor Socei — The Founder.
- 2026-10-23 — Stack: FastAPI (Python 3.12) backend, React + TypeScript + Vite front ends, PostgreSQL 16 on Supabase (Mumbai), Supabase Auth and Storage — founder preference plus reliability for financial data — The Founder.
- 2026-10-23 — Two front ends (committee web, resident PWA) in one pnpm monorepo with a shared package — parallel work, shared design — The Founder.
- 2026-10-23 — Money stored as integer paise; financial records never deleted, only reversed — accuracy and audit — The Founder.
- 2026-10-23 — Society isolation in both API and PostgreSQL row-level security — critical requirement — The Founder.
- 2026-10-23 — PDFs with WeasyPrint and Noto fonts — correct Indic script shaping — The Founder.
- 2026-10-23 — Hosting: demo on Vercel + Render free + Supabase free; pilots on Cloudflare Pages or Vercel Pro + Render paid + Supabase Pro — low cost, low maintenance — The Founder.
- 2026-10-23 — AI via Groq or Gemini behind a provider interface; demo data only until data terms are checked — cost and DPDP — The Founder.
- 2026-10-23 — WhatsApp features show "Coming soon"; no WhatsApp build in v1 — The Founder.
- 2026-10-23 — GitHub: private repo owned by the Founder; collaborator the Co-founder (Engineering); the Design & Marketing Lead optional for design files — The Founder.
- 2026-10-23 — Partnerships with Supplybase (home services) and a fire-safety equipment company are future business partnerships, not software features, after 10–15 societies and business registration — The Founder.
