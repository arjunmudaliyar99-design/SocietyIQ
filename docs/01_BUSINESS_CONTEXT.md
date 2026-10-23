# 01 — Business context

Why SocietyIQ exists, who it is for, and what is decided about the business. Builders read this for context; it does not define features (that is `02_PRODUCT_SPEC.md`).

Status of facts: **Decided** = agreed by the founders. **Hypothesis** = not yet validated with customers. **Verify** = researched once, may be out of date.

---

## 1. One-line summary

SocietyIQ automates the routine office work of a housing society: bills, dues, receipts, reminders, compliance dates, notices and spending checks, in English, Marathi, Hindi, Gujarati and Tamil, simple enough for committee members aged 50 to 70.

## 2. One-liner and messages

**Recommended one-liner (Decided pending trademark check):** "Society management, automated."

**Supporting line:** "Bills, dues, receipts and reminders run themselves, in your language."

**Investor line:** "SocietyIQ automates the back office of India's housing societies, starting with Maharashtra's cooperative societies."

Retired lines, do not use in the product:

- "Your society's office, on autopilot." Too close to competitor Socei's headline "Your Society, on Autopilot".
- "Society logistics." Sounds like transport.
- "Know where your society's money is going." Earlier positioning; may still appear in old decks in `reference/`.

Messaging rules:

- Sell outcomes (less work, fewer missed dates, clear money), not "AI".
- Never promise "guaranteed savings"; say "potential savings".
- Never say "fraud" or "overcharging"; see `06_RULES_AND_CALCULATIONS.md` §12.

## 3. The problem

- Societies spend lakhs every month, but bills, AMCs, dues and records sit in WhatsApp, paper files, Excel and the treasurer's memory.
- Committees are volunteers, often aged 50 to 70. They spend hours making bills, writing receipts, chasing defaulters, drafting notices and tracking audit dates.
- Many residents still pay by cash or cheque. Many older members do not use smartphones well.

## 4. Target market (Decided)

- **Geography:** tier 1 cities in Maharashtra: Mumbai, Thane, Navi Mumbai, Pune. One cluster at a time, starting with Thane and nearby Mumbai suburbs.
- **First segment (lowest-hanging fruit):** older standalone cooperative housing societies, 20 to 150 flats, on paper, Excel or an accountant using Tally, with a current pain: an AMC renewal, an audit objection, defaulters or a new committee.
- **Test segment:** Gujarati-majority societies (for example Ghatkopar, Mulund, Borivali, Kandivali), suggested by the Marketing Mentor. Lead with rupees saved.
- **Later:** other Maharashtra cities, then other states (each has its own Cooperative Societies Act), then abroad.

## 5. Users

| User | Uses | Main jobs |
|---|---|---|
| Secretary | Committee web | Notices, minutes, compliance dates, registers |
| Treasurer | Committee web | Billing, receipts, payments, bank matching, reports |
| Chairman and committee members | Committee web | View summary, approve, upload documents |
| Consultant or society accountant | Committee web (later: multi-society view) | Works for several societies |
| Auditor | Committee web, read-only | Exports for the audit year |
| Owner member | Resident PWA | Dues, receipts, notices, complaints |
| Tenant | Resident PWA | Notices, complaints; payments only if the owner allows |
| Family delegate (e.g. child abroad) | Resident PWA | Pays and sees receipts for a parent's flat |

## 6. Competitors (Verify — researched 21–23 Oct 2026)

Full list with links: the "How We Beat Competitors" Claude Doc (link in `reference/LINKS.md`). Summary:

- **Big all-in-one apps:** MyGate, NoBrokerHood, ADDA, ApnaComplex. All have billing, accounting, gate and complaints. MyGate (MIRA) and ADDA already use AI.
- **Bank-backed:** Society Connekt by Saraswat Co-operative Bank: society accounting app with payment gateway, bank statement API and virtual accounts for societies that bank with Saraswat.
- **Maharashtra accounting tools:** CHSONE (Thane), CHS Online (Mumbai), societyTALK (Pune, MCS Act), SocietySphere (Marathi and English), MySocietyClub, Bhoomi Infosolutions, Tally modules.
- **AI-first entrants:** Socei, MyCloudSociety (Nexa AI voice, 4 languages), myKutir (Ahmedabad), SocietyFix AI (announced Oct 2026).
- **Legal-compliance tools:** SocietySeWA (free MCS Act forms, compliance calendar, eManager, backed by advocates), Societybee.
- **Small and low-price apps:** SocietyRun, SocietynMore, Neighbium, SocietyEasy, SocietyKit, AppSociety, Paperbit and others.

**Where we win (the combination, not one feature):**

1. Elderly-first simplicity: Simple mode, big text, printed bills with QR codes, family delegate.
2. Done-for-you setup: we import their records and run the first billing cycle with them.
3. Real-world payments: cash and cheque recorded in one tap, resident confirms, bank deposit checked.
4. Plain-language decision help in five languages: spending alerts, renewal warnings, quote comparison.
5. No ads, no fees for residents, data never sold. Written in the contract.
6. The consultant and accountant channel.

Rule: copy features where useful, never competitors' code, screens, logos or wording.

**Timely opportunity (Oct 2026):** Maharashtra notified housing-society Rules on 18 June 2026 (Rule 106C-12) that fix how charges must be shared: equal service charges, 12% interest cap, non-occupancy at 10% of service charges, tap-based water, carpet-area insurance. Many societies must change their billing. SocietyIQ bills this way by default. See `docs/marketing/MARKETING_AND_BRAND.md`.

## 7. Pricing (Hypothesis — test in pilot month 3)

- Committee software: ₹1,499 to ₹2,999 per society per month, by size. Alternative: about ₹10 to ₹20 per flat per month.
- Setup and spending review: about ₹999 one-time (free in pilots).
- Consultant plan: volume price per society.
- Residents use the app free. No ads.

Build implication: the product needs a `plan` field per society but **no billing of societies by SocietyIQ in v1**.

## 8. Team

| Person | Role |
|---|---|
| Founder (Technology) | Co-founder: development, AI, architecture. GitHub owner. |
| Co-founder (Engineering) | Co-founder: development, AI integration. GitHub collaborator. |
| Design & Marketing Lead | Partner, part-time: design, UI/UX, marketing. Optional GitHub access for design files. |
| Marketing Mentor | Mentor (CMO elsewhere): marketing strategy, investor introductions. |
| Legal & Society Advisor | Advisor. Recommended starting the app now; legal points pending. Notes go in `docs/inputs/ADVISOR_NOTES.md`. |
| Society consultant | Domain knowledge, pilot introductions. Name to be added. |
| Referrals (via the advisor) | Experts from housing-society associations and federations. Names in `reference/private/PEOPLE.md` (Q-023). |

Founders work part-time (about 10 to 12 focused hours a week each). Keep the product simple and automated.

## 9. Roadmap (Decided as draft; gates are paying societies, not features)

| Phase | When (draft) | What | Gate to next phase |
|---|---|---|---|
| 0. Validate and research | Oct 2026 – Jan 2027 | Field research in 50–60 buildings; build the demo (this repo) | 5 societies sign pilot letters |
| 1. Build the core | Jan – Mar 2027 | Core modules in `07_BUILD_PLAN.md` milestones M0–M10 | Core runs on one society's real data |
| 2. Free pilot | Apr – Jun 2027 | 5–10 societies, 3 months, "free with commitment" | 3 paying societies |
| 3. Paid launch | Jul – Dec 2027 | Payment gateway, bank matching, WhatsApp, consultant view | 25 paying, low churn |
| 4. Scale | 2028+ | Gate and visitor module, price benchmarks, new cities | — |

Building starts now (the Legal & Society Advisor's advice), in parallel with field research. Dates will move.

## 10. Pilot (Decided)

- Research 50–60 buildings; live pilot with 5–10 societies for 3 months, free.
- "Free with commitment": signed one-page pilot letter, a named champion per society, a 30-minute monthly feedback call, a price discussion in month 3.
- Usage tracking (PostHog) to see where people get stuck; see `04_ARCHITECTURE.md` §10.

## 11. Support model (Decided)

1. Self-help: short videos and in-app help in five languages.
2. A trained champion in each society answers residents first.
3. A WhatsApp help number (human), office hours.
4. Founders for escalations only.

Rule: we support the committee; the committee supports its residents. Build implication: in-app help text and a "Need help?" button showing the society champion's and SocietyIQ's contact.

## 12. Future partnerships (business only, not in the software yet)

After the business is registered and 10–15 societies use SocietyIQ:

- **Supplybase** (a friend's company): home and building services such as plumbers, painters and technicians, offered to our societies.
- **A fire-safety equipment company:** fire extinguishers and fire systems for buildings; links naturally to the fire audit reminders.
- **Legal and accounting help:** referrals to society lawyers and CAs.

Rule for the build: do not add marketplace, vendor booking or partner features until a decision is recorded in `DECISIONS.md`. The data model already has `vendors`, which is enough for now.
