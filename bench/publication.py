"""Remove evaluation-only corpus text at every public artifact boundary."""

LICENSED_TIERS = {"afriswitch-sample"}
REDACTION_NOTE = "AfriSwitch reference and hypothesis transcripts are withheld from this export. The evaluation-only corpus is not redistributed; cached numerical scores are retained."


def public_row(row: dict) -> dict:
    result = dict(row)
    if result.get("tier") in LICENSED_TIERS:
        result.update(truth="", hyp="", redacted=True)
    return result
