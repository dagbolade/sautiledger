"""Typed results shared across the normaliser, agent, and tools."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ParseResult:
    """Union of every 'expect' shape in normaliser_tests.json.

    Unused fields stay None; tests compare only the keys each case's
    expect block declares.
    """

    intent: str
    type: str | None = None
    item: str | None = None
    quantity: int | None = None
    unit: str | None = None
    amount: int | None = None
    amount_each: int | None = None
    currency: str | None = None
    payment_status: str | None = None
    due: str | None = None
    query: str | None = None
    period: str | None = None
    field: str | None = None
    new_value: object = None
    question_about: str | None = None
    candidates: list[dict] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Transcript:
    """What an AsrClient returns."""

    text: str
    language_hint: str | None = None
    confidence: float | None = None
