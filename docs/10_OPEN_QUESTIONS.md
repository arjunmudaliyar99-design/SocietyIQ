# 10 — Open questions

Anything undecided. Code that depends on an open question uses a configurable placeholder marked `TODO(confirm): Q-xxx`. When answered, write the answer here, move the decision to `DECISIONS.md`, and update the affected doc.

Format: **ID — question** · who can answer · status.

## Product and money rules

- **Q-001 — Which SMS provider for phone OTP and reminders, and when?** · founders · open (email-only until decided)
- **Q-002 — Exactly when does a due become "in default" for interest (bill date, due date, grace days)?** Act s.154B-1(11),(12) plus bye-laws · consultant / lawyer · open
- **Q-003 — Do vacant flats (not let out) attract non-occupancy charges?** · consultant · open (default: no)
- **Q-004 — Bounced cheque charges: allowed, how much, on what basis?** · consultant · open (default: none)
- **Q-005 — Should SocietyIQ ever generate reminder or demand notices with legal wording?** · lawyer · open (v1: no)
- **Q-006 — Bill rounding: nearest rupee or exact paise? Is a "rounding off" line acceptable to auditors?** · consultant / CA · open (default nearest rupee)
- **Q-007 — Quarterly billing: any rules different from monthly?** · consultant · open
- **Q-008 — When a partial payment arrives, does it settle interest first or charges first?** · consultant / CA · open
- **Q-009 — Add "Cleaning" and "Landscaping" to expense categories?** · founders · open
- **Q-010 — Quote comparison: is the advance % applied to the price before GST or the total payable?** · founders · open (default total payable)
- **Q-011 — Water by "number and size" of inlets: how to weight different tap sizes?** · consultant · open (default: count only, `water_points` allows fractions)
- **Q-015 — Old buildings without an architect-certified construction cost: how should sinking and repair funds be computed?** · consultant · open (default: committee enters the GB-approved amount with a reason; warning shown)
- **Q-016 — MCGM ≤500 sq ft exemption: all components or general tax only? Status of the 501–700 sq ft concession?** · CA / MCGM bill · open (always use bill amounts)
- **Q-018 — Property tax: billed monthly in maintenance, or once a year?** · consultant · open (setting per society)

- **Q-028 — Which milestone builds the `documents` domain (docs/04 §3 lists it; docs/07 does not)?** · founders · open (stub only)

## Legal and compliance

- **Q-012 — Exact provision allowing notices by SMS/electronic means (the Legal & Society Advisor's point): which section, rule or circular, and for which notices?** · the Legal & Society Advisor / lawyer · open
- **Q-013 — How long must financial and member records be retained (affects data deletion requests)?** · lawyer / CA · open
- **Q-014 — Should the software support GST on members' bills for societies above the thresholds?** · CA · open (v1: no)
- **Q-017 — Have the revised Model Bye-laws 2026 been notified? If so, which provisions change billing?** · check Sahakar website monthly · open
- **Q-019 — Business structure: registered partnership vs proprietorship + founders' agreement (see `docs/legal/LEGAL_REFERENCE.md` §6)** · CA / lawyer · open
- **Q-020 — Employment contracts of the Founder and the Co-founder (Engineering): any side-business or IP clauses?** · each founder · open
- **Q-021 — AI provider data terms (Groq, Gemini): may real society data be sent?** · founders · open (demo data only)

- **Q-029 — The GitHub repository is public, but docs/09 §3 and DECISIONS say private. Make it private before pushing docs and code?** · the Founder · open (nothing pushed until answered)

## Business and people

- **Q-022 — One-liner "Society management, automated.": trademark and web check done?** · the Design & Marketing Lead · open
- **Q-023 — Confirm the identities and contact details of the three referrals listed in `reference/private/PEOPLE.md`** · Founder (ask the advisor) · open
- **Q-024 — Who owns society domain knowledge (bye-laws, compliance calendar, billing rules) in the team?** · founders · open
- **Q-025 — Name of the society consultant and his inputs** · the Founder · open
- **Q-026 — The Marketing Mentor's 4 pending points; "Infina" and "ESP"** · the Founder · open
- **Q-027 — Which book(s) to buy at Vikas Premises (the advisor's reference)?** · the Legal & Society Advisor · open
