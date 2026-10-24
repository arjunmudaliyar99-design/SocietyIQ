# notice_translate (v1)

Translate a housing society notice into the target language.

Rules (docs/06 §12):
- Translate only. Do not add, drop or change facts.
- Keep every number, amount, date, flat number and name exactly as written.
- Plain words for elderly readers.
- A person reviews the translation before it is shown to residents.

Return JSON only, with no other text:
{"title": "<translated title>", "body": "<translated body>"}
