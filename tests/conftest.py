"""Shared stand-ins: the Deutsche Bundesbank's recorded answer, a fixed
clock, the deployment holding the curve's record, and the lake's wants as
the sidecar delivers them."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.suites import Recorder

from bundesbank.feed import Feed
from bundesbank.portal import SyntheticPortal
from bundesbank.raw import RawStore

#: After the recording: 22:00 UTC on Thursday 19 November 2026, 23:00 in
#: Frankfurt.
AT = datetime(2026, 11, 19, 22, 0, tzinfo=UTC)
INSTANCE = "bundesbank"
CURVES = f"{INSTANCE}:bbk_curves"
BUND = "INS-BUND"
#: The record the tests' deployment holds, by its code at `bbk`.
CODE = "Term structure of interest rates on listed Federal securities"
HELD = {CODE: BUND}


def resolving(plugin: Recorder, *, held: bool = True, ambiguous: bool = False) -> Recorder:
    """`plugin` resolving the curve's record, or reporting it not held, or
    held twice."""

    def resolved(params: ops.ResolveIdentifierParams) -> ops.ResolveIdentifierResult:
        named = params.identifiers[0]
        if ambiguous:
            return ops.ResolveIdentifierResult(found=False, miss_reason=ops.MISS_REASON_AMBIGUOUS)
        found = HELD.get(named.value, "") if named.source == "bbk" and held else ""
        if not found:
            return ops.ResolveIdentifierResult(found=False, miss_reason=ops.MISS_REASON_NOT_FOUND)
        return ops.ResolveIdentifierResult(found=True, instrument_id=found)

    plugin.answer("ResolveIdentifier", resolved)
    return plugin


def feed(
    tmp: Path, plugin: Recorder | None = None, *, portal: Any = None, at: datetime = AT
) -> Feed:
    held = plugin if plugin is not None else resolving(Recorder(INSTANCE))
    return held.bind(Feed(portal or SyntheticPortal(lambda: at), RawStore(tmp), now=lambda: at))


def want(
    want_id: str,
    subjects: list[str],
    *,
    day: str = "",
    standing: bool = False,
    dataset: str = CURVES,
    data_type: str = "meridian.v1.Rate",
    kinds: tuple[Any, ...] = (),
    valid_from_ns: int = 0,
    valid_until_ns: int = 0,
) -> Heard:  # type: ignore[type-arg]
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset=dataset,
            data_type=data_type,
            subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
            kinds=list(kinds),
            business_date=day,
            standing=standing,
            valid_from_ns=valid_from_ns,
            valid_until_ns=valid_until_ns,
        ),
    )
