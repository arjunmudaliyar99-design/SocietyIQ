# SocietyIQ

**Society management, automated.** Committee software and a resident app (PWA) for Maharashtra cooperative housing societies.

- Start here: [`CLAUDE.md`](CLAUDE.md) (rules for AI builders) and [`docs/09_SETUP_GUIDE.md`](docs/09_SETUP_GUIDE.md) (setup for people).
- What exists: [`docs/PROGRESS.md`](docs/PROGRESS.md). What to build next: [`docs/07_BUILD_PLAN.md`](docs/07_BUILD_PLAN.md).

| Folder | Contents |
|---|---|
| `docs/` | Product, design, architecture, database, rules, legal, plan |
| `docs/legal/` | Legal reference for the founders |
| `docs/marketing/` | Marketing plan and brand book |
| `docs/inputs/` | Raw notes from advisors |
| `reference/` | Logos, old decks, old prototype (reference only) |
| `backend/` | FastAPI (from M0) |
| `apps/` | Committee web and resident PWA (from M0) |
| `packages/shared/` | Shared UI, translations, API client (from M0) |

Private repository. Team: the Founder (Technology), the Co-founder (Engineering). Design and marketing: the Design & Marketing Lead.

## How to run

Needs Python 3.12 via [uv](https://docs.astral.sh/uv/), Node.js 22+ and pnpm. Same commands as `CLAUDE.md` §6.

```bash
# backend (http://localhost:8000/api/v1/health)
cd backend
cp .env.example .env        # fill in values; never commit .env
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run ruff check . && uv run pytest

# front ends (from the repo root)
pnpm install
pnpm --filter committee-web dev     # http://localhost:5173
pnpm --filter resident-pwa dev      # http://localhost:5174
pnpm -r lint && pnpm -r typecheck && pnpm -r test && pnpm -r build
```

Each app reads its own `.env.local` (see `apps/*/.env.example`). CI runs the same checks on every pull request (`.github/workflows/ci.yml`).
