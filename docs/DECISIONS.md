# DECISIONS

Decisions made during planning and building. Newest first. Format: date — decision — why — who.

- 2026-10-24 — Excel import keeps warnings importable and errors skipped; confirm re-checks against the database; issues are i18n keys with parameters, never English text from the backend — docs/02 §4 "never import silently" and five UI languages — M3 build session, to be confirmed.
- 2026-10-24 — Tests log in as `app_backend_test`, a role that inherits `app_backend`'s grants, because Postgres roles are server-wide and tests must not change a developer's local password — M3 build session.
- 2026-10-24 — Demo seed layout (flat numbering per wing/floor) is chosen to contain every flat listed in docs/02 §12 and reach the stated flat counts; bill day 1 and due after 15 days are demo values only — docs give counts but not numbering — M3 build session, to be confirmed.
- 2026-10-24 — The migration creates `app_backend` without LOGIN; each environment enables login with its own password outside the migration — no secret ever sits in the repo — M2 build session, to be confirmed by the Co-founder (Engineering).
- 2026-10-24 — Local-only dev sign-in (`POST /api/v1/dev/token`, mounted only when `APP_ENV=local` and a JWT secret is set; front ends show it only with `VITE_DEV_SIGN_IN=true` in dev builds) — lets anyone preview and test the apps without a Supabase project — M2 build session, to be confirmed.
- 2026-10-24 — Until email sending (M9), invite links are shown to the admin once, to copy and share; tokens are random, stored only as SHA-256, single use, scoped to one society, and bound to the invited email when one is given — invites must work before an email provider is chosen — M2 build session, to be confirmed.
- 2026-10-24 — Society routes return 404 (not 403) to people who are not members, so another society's ids are never confirmed; members without the needed role get 403 — docs/07 M2 acceptance — M2 build session.
- 2026-10-24 — Front-end data layer: `@supabase/supabase-js` 2.118 for sign-in, TanStack Query 5 for API calls (hooks in `packages/shared/src/api`), API types generated with `openapi-typescript` 7 from the backend's OpenAPI (`pnpm --filter @societyiq/shared api:generate`) — stack in CLAUDE.md §3 and docs/04 §3 — M2 build session.
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
