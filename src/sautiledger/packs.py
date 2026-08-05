"""Language pack loading. A pack is pure data (packs/*.yaml) — adding a
language means adding a pack file and test cases, never code (rule 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"


@dataclass
class Pack:
    name: str
    currency: str
    numbers: dict[str, int]
    units: dict[str, str]
    currency_words: frozenset[str] = frozenset()
    connectives: frozenset[str] = frozenset()
    fillers: frozenset[str] = frozenset()
    k_words: frozenset[str] = frozenset()
    each_words: frozenset[str] = frozenset()
    hard_money_words: frozenset[str] = frozenset()
    sale_triggers: list[str] = field(default_factory=list)
    expense_triggers: list[str] = field(default_factory=list)
    log_triggers: list[str] = field(default_factory=list)
    queries: list[dict] = field(default_factory=list)
    summary_triggers: list[str] = field(default_factory=list)
    corrections: list[dict] = field(default_factory=list)
    correction_stop_words: frozenset[str] = frozenset()
    periods: dict[str, str] = field(default_factory=dict)
    days: frozenset[str] = frozenset()
    # native-validated grammar switches (default off for unvalidated packs)
    reduplication_distributive: bool = False
    # v2: accept "5k 5" as the digit twin of spoken "five thousand five"
    digit_twin_thousands: bool = False
    # "3 FOR 500" — connective marking the following figure as a total
    price_connectives: frozenset[str] = frozenset()
    # question markers: interrogative + sale trigger = query, not transaction
    interrogatives: list[str] = field(default_factory=list)

    @property
    def units_ordered(self) -> list[tuple[str, str]]:
        """Unit surface forms, multi-word first so 'paint rubber' wins over 'rubber'."""
        return sorted(self.units.items(), key=lambda kv: -len(kv[0].split()))


def load_pack(name: str, packs_dir: Path | None = None) -> Pack:
    path = (packs_dir or PACKS_DIR) / f"{name}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Pack(
        name=raw["name"],
        currency=raw["currency"],
        numbers={str(k): int(v) for k, v in (raw.get("numbers") or {}).items()},
        units={str(k): str(v) for k, v in (raw.get("units") or {}).items()},
        currency_words=frozenset(raw.get("currency_words") or []),
        connectives=frozenset(raw.get("connectives") or []),
        fillers=frozenset(raw.get("fillers") or []),
        k_words=frozenset(raw.get("k_words") or []),
        each_words=frozenset(raw.get("each_words") or []),
        hard_money_words=frozenset(raw.get("hard_money_words") or []),
        sale_triggers=list(raw.get("sale_triggers") or []),
        expense_triggers=list(raw.get("expense_triggers") or []),
        log_triggers=list(raw.get("log_triggers") or []),
        queries=list(raw.get("queries") or []),
        summary_triggers=list(raw.get("summary_triggers") or []),
        corrections=list(raw.get("corrections") or []),
        correction_stop_words=frozenset(raw.get("correction_stop_words") or []),
        periods={str(k): str(v) for k, v in (raw.get("periods") or {}).items()},
        days=frozenset(raw.get("days") or []),
        reduplication_distributive=bool(raw.get("reduplication_distributive", False)),
        digit_twin_thousands=bool(raw.get("digit_twin_thousands", False)),
        price_connectives=frozenset(raw.get("price_connectives") or []),
        interrogatives=list(raw.get("interrogatives") or []),
    )
