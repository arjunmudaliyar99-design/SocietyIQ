"""AI for reading and writing words only (docs/04 §11, docs/06 §12).

The provider interface has the two methods of docs/04 §11. Only `FakeProvider` exists so far:
no provider's data terms are checked yet, so no society text goes to a real model
(TODO(confirm): Q-083). Every output is validated against a schema; invalid output is a
"needs review" error, never a guess.
"""

import json
import re
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.errors import AppError

PROMPTS = Path(__file__).parent / "prompts"


class AIProvider(Protocol):
    async def extract(self, document: bytes, schema: dict[str, Any]) -> dict[str, Any]: ...

    async def draft(self, prompt_name: str, inputs: dict[str, Any], language: str) -> str: ...


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


class FakeProvider:
    """Deterministic stand-in for demos and tests. It only tidies the words it is given and
    never adds facts, so its output obeys the same guardrails as a real model's."""

    async def extract(self, document: bytes, schema: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def draft(self, prompt_name: str, inputs: dict[str, Any], language: str) -> str:
        load_prompt(prompt_name)  # a missing prompt file fails here, as it would for real
        if prompt_name == "notice_draft":
            lines = [ln.strip() for ln in str(inputs["notes"]).splitlines() if ln.strip()]
            title = re.sub(r"\s+", " ", lines[0])[:80] if lines else "[to be confirmed]"
            body = "\n\n".join(lines[1:] or lines)
            return json.dumps({"title": title[:1].upper() + title[1:], "body": body})
        if prompt_name == "notice_translate":
            tag = f"[{language.upper()}]"
            return json.dumps(
                {"title": f"{tag} {inputs['title']}", "body": f"{tag} {inputs['body']}"}
            )
        raise AppError(422, "AI_UNKNOWN_PROMPT", "errors.aiNeedsReview")


def ai_available() -> bool:
    """docs/02 §9: the helper shows only when AI is configured. The fake counts outside
    production so demos can show the flow."""
    settings = get_settings()
    if settings.ai_provider == "fake":
        return settings.app_env != "production"
    return False  # Groq and Gemini are not built yet (Q-083)


def get_provider() -> AIProvider:
    if not ai_available():
        raise AppError(503, "AI_NOT_CONFIGURED", "errors.aiNotConfigured")
    return FakeProvider()


class NoticeText(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)


def parse_notice_text(raw: str) -> NoticeText:
    try:
        return NoticeText.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise AppError(422, "AI_NEEDS_REVIEW", "errors.aiNeedsReview") from exc
