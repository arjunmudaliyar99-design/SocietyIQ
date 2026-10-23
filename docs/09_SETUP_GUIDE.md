# 09 — Setup guide (for the Founder and the Co-founder (Engineering))

Step by step, in order. Commands are for Windows PowerShell unless noted; macOS/Linux are the same apart from install steps.

---

## 1. Make the project folder

1. Create a folder, e.g. `D:\Projects\societyiq`.
2. Copy this whole pack into it, keeping the structure: `CLAUDE.md`, `README.md`, `.gitignore`, `docs/`, `reference/`.
3. Put the brand and reference files from `society_iq_download_file.zip` into `reference/` like this:

| Put here | Files |
|---|---|
| `reference/brand/` | `logo-dark.svg`, `logo-dark.png`, `logo-light.svg`, `logo-light.png`, `mark.svg`, `mark.png` |
| `reference/decks/` | `SocietyIQ.pptx`, `SocietyIQ_Overview.pptx`, `SocietyIQ_Modules_Pilot.pptx`, `SocietyIQ_Modules_Pilot.pdf`, `SocietyIQ_Master_Plan_v3.pptx`, `SocietyIQ_Summary.pdf`, `SocietyIQ_Summary.docx` |
| `reference/business/` | `SocietyIQ_Master_Blueprint_v2.docx`, `SocietyIQ_Costing.xlsx`, `SocietyIQ_Founders_Checklist.xlsx`, `SocietyIQ_Business_Model_Canvas.png` |
| `reference/prototype/` | `societyiq-prototype.html` (old demo, for look and flow only) |
| `reference/exports/` | `SocietyIQ_Chat_Export.md`, `SocietyIQ_Handover_Prompt.md` |
| `reference/videos/` (not committed) | the `.mp4` screen tours |

**Do not copy these into the project** (they belong to the old claude.ai artifact runtime and will confuse Claude Code): `user.d.ts`, `self.d.ts`, `db.d.ts`, `artifact.d.ts`, `sample.d.ts`, `assets.d.ts`, `mcp.d.ts`, `files.d.ts`, `comments.d.ts`, `downloads.d.ts`, `claude.d.ts`, `permissions.d.ts`, `room.d.ts`, all `*.js.json` files, `deck.json` and the slide `*.html` files (`cover.html`, `problem.html` and so on). Also skip the older `SocietyIQ_Master_Blueprint.docx` (superseded by v2) and `dashboard_output.png` (unrelated).

**Never put real society data** (bills, member lists, phone numbers) in the repository.

## 2. Install the tools

1. **Git:** https://git-scm.com/downloads
2. **Python 3.12** and **uv** (Python package manager): https://docs.astral.sh/uv/getting-started/installation/
3. **Node.js LTS** and **pnpm**: https://nodejs.org and https://pnpm.io/installation
4. **VS Code** (optional, helpful): https://code.visualstudio.com
5. **Claude Code:** follow the official install guide: https://docs.claude.com/en/docs/claude-code/overview (check its Node.js and OS requirements there).
6. **Docker Desktop** (optional, to run PostgreSQL locally for tests): https://www.docker.com/products/docker-desktop

Check: `git --version`, `uv --version`, `node --version`, `pnpm --version`.

## 3. GitHub

1. The Founder creates a GitHub account (if needed) and turns on two-factor authentication.
2. Create a **private** repository named `societyiq` (no README, since we have one).
3. In the project folder:
   ```powershell
   git init
   git add .
   git commit -m "Docs and reference pack"
   git branch -M main
   git remote add origin https://github.com/<owner-username>/societyiq.git
   git push -u origin main
   ```
4. **Add the Co-founder (Engineering):** repository → Settings → Collaborators → Add people → his GitHub username → he accepts the email invite.
5. The Design & Marketing Lead: add later only if he needs to commit design files; designs can also be shared through Figma links in `docs/DECISIONS.md`.
6. Protect `main` if your plan allows it (Settings → Branches or Rules): require a pull request before merging. If not available on your plan, agree as a rule: nobody pushes directly to `main`.
7. Later, when the business is registered, move the repo to a GitHub **organisation** owned by the business (Settings → Transfer).

## 4. Daily workflow (both developers)

```powershell
git checkout main
git pull
git checkout -b feat/m3-flats-import     # one branch per task
# ... work with Claude Code ...
git add .
git commit -m "M3: flats and Excel import preview"
git push -u origin feat/m3-flats-import
# open a Pull Request on GitHub; the other person reviews; merge
```

Rules: one task per branch; update `docs/PROGRESS.md` in the same PR; never commit `.env` files or real data.

## 5. Using Claude Code well

**Starting a session:** open a terminal in the project folder and start Claude Code. It reads `CLAUDE.md` automatically. Then give it a task like this:

```text
Read CLAUDE.md, docs/PROGRESS.md and docs/07_BUILD_PLAN.md.
Take milestone M0. Before writing code, list the files you will create and
anything in the docs that is unclear. Then build it, run the tests and
the build, and update docs/PROGRESS.md. Do not invent anything not in docs/.
```

**Several sessions at once (you said you will use multiple Claude Code windows):** each session must work in its own folder copy so they do not overwrite each other. Use git worktrees:

```powershell
git worktree add ..\societyiq-m1 -b feat/m1-design-system
git worktree add ..\societyiq-m2 -b feat/m2-auth-isolation
```

Open one Claude Code session in each folder. Each session marks its task "IN PROGRESS" in `PROGRESS.md` first. Only run sessions in parallel where the build plan says "can run in parallel"; database migrations must be done one at a time.

**Keeping Claude accurate:**
- Ask it to quote the doc section it is following when it makes a rule-based decision.
- If it says "done", ask: "Which commands did you run and what was the output?"
- If it proposes something not in the docs, ask it to add a question to `docs/10_OPEN_QUESTIONS.md` instead.
- Start a fresh session for each milestone; long sessions drift.

**When your Claude subscription pauses:** nothing is lost. The repository, `PROGRESS.md` and `DECISIONS.md` carry the state. The Co-founder (Engineering) can continue from his machine, or you can resume later with the same starting prompt.

## 6. Accounts to create (free tiers first)

| Service | For | When |
|---|---|---|
| Supabase | Database, sign-in, file storage (create projects in the Mumbai region) | M2 |
| Vercel | Hosting the two front ends for demos | After M1 |
| Render | Hosting FastAPI for demos | After M2 |
| Email provider with a free tier (choose and record in `DECISIONS.md`) | Bill and notice emails | M9 |
| PostHog | Usage analytics | M11 |
| Groq or Google Gemini | AI (demo data only until data terms are checked) | M9 / M12 |

Store every key in the service's environment settings and in local `.env` files, never in code.

## 7. Hosting

**Demo / internal sharing:** Vercel (front ends) + Render free (FastAPI) + Supabase free. Costs nothing; the backend sleeps when idle, so the first click after a while is slow.

**Pilots and paying societies:** Cloudflare Pages or Vercel Pro (front ends), Render paid always-on instance (FastAPI), Supabase Pro (backups). Roughly ₹3,000–4,500 a month in total (verify current prices). Details: `04_ARCHITECTURE.md` §9.

Use a separate Supabase project for demo and for real societies.
