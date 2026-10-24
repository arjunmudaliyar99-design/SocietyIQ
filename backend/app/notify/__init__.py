"""Outgoing messages (docs/04 §12). v1 sends email only; SMS and WhatsApp show "Coming soon".

No email provider is chosen yet (TODO(confirm): Q-082), so the only sender is `FakeEmailSender`,
which keeps messages in memory for tests and demos. A real provider plugs in behind
`EmailSender` and is picked by EMAIL_PROVIDER.
"""

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from app.config import get_settings


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str


@dataclass(frozen=True)
class SendResult:
    ok: bool
    provider_message_id: str | None = None
    error: str | None = None


class EmailSender(Protocol):
    async def send(self, email: Email) -> SendResult: ...


@dataclass
class FakeEmailSender:
    """Accepts every message and remembers it; nothing leaves the server."""

    sent: list[Email] = field(default_factory=list)

    async def send(self, email: Email) -> SendResult:
        self.sent.append(email)
        return SendResult(ok=True, provider_message_id=f"fake-{uuid4().hex[:12]}")


_fake = FakeEmailSender()


def get_email_sender() -> EmailSender:
    provider = get_settings().email_provider
    if provider in (None, "", "fake"):
        return _fake
    raise RuntimeError(f"Email provider {provider!r} is not built yet (Q-082)")


def fake_outbox() -> FakeEmailSender:
    """Tests read what would have been sent."""
    return _fake


def mask_email(address: str) -> str:
    """The log keeps enough to recognise an address, not the address itself (docs/08 §8)."""
    local, _, domain = address.partition("@")
    if not domain:
        return "***"
    return f"{local[:1]}***@{domain}"
