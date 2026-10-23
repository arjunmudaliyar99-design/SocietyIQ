# 03 — Design system (elderly-first)

The main users are aged 50 to 70, many not comfortable with apps. Every screen must pass this test: **a 65-year-old secretary can do the main task on first try, without help, in under a minute.**

the Design & Marketing Lead owns the visual design. Until his Figma or design files arrive, build to this document. If his designs differ, his designs win for visuals; this document wins for accessibility rules.

---

## 1. Ten rules

1. **One main task per screen.** One primary button, clearly the biggest.
2. **At most 5 choices** visible at once in Simple mode.
3. **Words with icons.** Never an icon alone.
4. **Plain words.** "Money received", not "Credit". "Pending", not "Unreconciled". No abbreviations except ₹, GST, AMC, UPI.
5. **Large text by default.** Body 18 px. Never below 16 px.
6. **Big targets.** Every tappable thing at least 48 × 48 px, with 8 px space between.
7. **No hidden gestures.** No swipe-only, long-press-only or hover-only actions.
8. **Confirm money actions** in plain words: "Record ₹4,200 cash from Flat B-207?" with **Yes, record** and **No, go back**.
9. **Undo or reverse is always visible** after a money action ("Recorded. Made a mistake? Reverse it").
10. **Errors say what to do.** "Phone number needs 10 digits", not "Invalid input".

## 2. Simple mode and settings

- **Simple mode is on by default** for everyone. It shows the 3 to 5 most-used actions as big buttons.
- A "Detailed view" toggle shows tables, filters and extra columns.
- **Text size** setting: Normal (18 px body) / Large (21 px) / Extra large (24 px). Layouts must not break at Extra large.
- **Language** setting always reachable from the top bar (globe icon + language name in its own script).
- Settings are saved per user.

## 3. Brand

Use the real logo files in `reference/brand/` (`logo-light.svg`, `logo-dark.svg`, `mark.svg`, PNG versions). Do not redraw the logo.

Colours, taken from the logo files:

| Token | Hex | Use |
|---|---|---|
| `ink` | `#17262E` | Main text, dark backgrounds |
| `paper` | `#F7F6F2` | Page background |
| `surface` | `#FFFFFF` | Cards, inputs |
| `teal` | `#2E6B5E` | Primary buttons, links, brand |
| `teal-dark` | `#24554A` | Button pressed or hover |
| `mint` | `#7FC2AE` | Accents on dark backgrounds ("IQ" in the dark logo) |
| `orange` | `#E39A6B` | Brand dot, small highlights only |
| `terracotta` | `#C4622D` | Warnings ("Due soon") |
| `red` | `#B3261E` | Errors, overdue, destructive |
| `green` | `#2E7D32` | Success, paid |
| `muted` | `#55636B` | Secondary text (must still pass contrast) |
| `line` | `#D9E2DF` | Borders |

Contrast: all text at least **WCAG AA** (4.5:1 for body, 3:1 for large text). Never put text on `orange` or `mint` backgrounds except dark `ink` text. Never use colour alone to show status; always add a word ("Overdue") and an icon.

Dark mode: not in v1.

## 4. Typography

- **Font family:** Noto Sans, with Noto Sans Devanagari (Marathi, Hindi), Noto Sans Gujarati and Noto Sans Tamil. One family keeps all five languages consistent. Load from Google Fonts or self-host; fallback `system-ui, sans-serif`.
- **Sizes (Normal setting):** page title 28 px, section title 22 px, body 18 px, small 16 px, button 18 px semibold.
- **Line height:** 1.5 for body; Indic scripts need it.
- Numbers use tabular figures where they line up in tables.
- Older decks used Cambria/Source Serif headings; the web app uses Noto Sans only for readability.

## 5. Components (build these in `packages/shared/ui`)

| Component | Rules |
|---|---|
| `BigButton` | Full width on mobile, min height 56 px, icon + label, one primary per screen |
| `Button` | Min height 48 px; variants primary, secondary, danger |
| `Card` | White, 12 px radius, 1 px `line` border, 20 px padding |
| `StatCard` | Label on top, big number (32 px), one line of explanation, whole card tappable |
| `MoneyText` | Formats paise as `₹1,31,000` (en-IN grouping); negative shown as "₹500 advance" not "-500" for residents |
| `StatusPill` | Word + icon + colour: Paid, Pending, Overdue, Open, Resolved |
| `Field` | Label above input (never placeholder-only), 18 px, help text below, error text in red with icon |
| `ConfirmDialog` | Plain question, two big buttons, the safe choice on the left |
| `EmptyState` | Friendly sentence + one action ("No complaints yet. Report a problem") |
| `StepHeader` | "Step 2 of 3" for multi-step forms |
| `LanguageSwitcher` | Language names in their own scripts: English, मराठी, हिंदी, ગુજરાતી, தமிழ் |
| `HelpButton` | Always in the top bar: shows the society champion's and SocietyIQ's contact |
| `Toast` | Stays at least 6 seconds; includes undo or reverse where relevant |

Tables in committee web: max 6 columns in Simple mode; rows at least 56 px tall; on phones, tables become stacked cards.

## 6. Formats

- Money: `Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })` for display when the amount is whole rupees; show paise only if non-zero. Amounts in words on receipts in English (Indian system: lakh, crore).
- Dates: `25 Sep 2026` in English; localised month names in other languages via `Intl.DateTimeFormat`. Never `09/25/2026`.
- Phone: `+91 98765 43210` display; store E.164 (`+919876543210`).
- Flat numbers exactly as the society writes them (`B-207`, `1-04`, `301`).

## 7. Languages

- Supported: **English (`en`, default and fallback)**, Marathi (`mr`), Hindi (`hi`), Gujarati (`gu`), Tamil (`ta`).
- All UI text through `react-i18next`. Keys in English, namespaced: `billing.approveButton`.
- Translation files: `packages/shared/i18n/<lang>/<namespace>.json`.
- English is written first. Other languages may start as machine drafts but must be marked `"_status": "draft"` in the file and reviewed by a native speaker before a pilot. Never ship AI translations of legal or money terms without review.
- Text in other scripts can be 30 to 50% longer: layouts must wrap, never truncate labels.
- Backend messages that reach users (errors, notification templates, PDF labels) use the same keys with a Python loader.
- PDFs (bills, receipts) are generated in the society's chosen language with English below key labels (bilingual), using Noto fonts. See `04_ARCHITECTURE.md` §8.

## 8. Writing style for UI text

- Short sentences. Active voice. Talk to the person: "You have 3 payments to confirm."
- Say what happens next: "Bills will be sent to 120 flats by email."
- Respectful tone. No slang, no emoji in the committee app. Residents' app: no emoji either.
- Never blame: "We could not read this bill clearly. Please check the highlighted boxes."

## 9. Accessibility checks before any screen is "done"

- Keyboard: every action reachable with Tab and Enter.
- Screen reader: buttons and inputs have labels; images have alt text.
- Zoom: works at 200% browser zoom and at Extra large text.
- Contrast: checked with an automated tool (e.g. axe in tests).
- Tested on a cheap Android phone width (360 px) and a laptop (1366 px).
