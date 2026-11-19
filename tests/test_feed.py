"""The plugin's own conversion of the Deutsche Bundesbank's recorded answer."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from meridian.operations import as_decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder

from bundesbank.answers import NotRead, parse
from bundesbank.portal import SyntheticPortal, path_for
from bundesbank.series import tenor_of

from conftest import AT, BUND, CODE, INSTANCE, feed, resolving, want

BERLIN = ZoneInfo("Europe/Berlin")


def checked(tmp: Path, *, held: bool = True) -> Recorder:
    plugin = resolving(Recorder(INSTANCE), held=held)
    asyncio.run(feed(tmp, plugin).check())
    return plugin


def rates_of(plugin: Recorder, want_id: str | None = None) -> list[ops.Rate]:
    return [
        r
        for b in plugin.on("RecordRates")
        if want_id is None or b.want_id == want_id
        for r in b.rates
    ]


def heard(tmp: Path, *asked: object, plugin: Recorder | None = None) -> Recorder:
    """The current range checked, then each want heard."""
    held = plugin or resolving(Recorder(INSTANCE))
    work = feed(tmp, held)
    asyncio.run(work.check())
    for one in asked:
        held.answer("ObservationsWanted", lambda _, w=one: w.message)  # type: ignore[misc]
        asyncio.run(held.hear(work))
    return held


def test_the_current_range_pushed_as_continuous_zero_rates(tmp_path: Path) -> None:
    rates = rates_of(checked(tmp_path))
    # 9 to 19 November: nine trading days, sixty maturities each.
    assert len(rates) == 9 * 60
    assert {r.meta.business_date for r in rates} >= {"2026-11-09", "2026-11-19"}
    assert "2026-11-15" not in {r.meta.business_date for r in rates}
    ten = next(
        r
        for r in rates
        if r.meta.business_date == "2026-11-18"
        and (r.tenor.count, r.tenor.unit) == (10, ops.TENOR_UNIT_YEAR)
    )
    assert ten.kind == ops.RATE_KIND_ZERO and str(as_decimal(ten.value.value)) == "3.43"
    assert ten.value.unit == ops.VALUE_UNIT_PERCENT and ten.meta.subjects[0].entity_id == BUND
    assert ten.convention.compounding == ops.COMPOUNDING_CONTINUOUS
    assert ten.convention.day_count == ops.DAY_COUNT_ACT_365_FIXED
    assert not ten.meta.source_times and ten.meta.raw.key.endswith(
        "-zero-20261109-20261119.json.gz"
    )
    assert ten.meta.source.dataset == f"{INSTANCE}:bbk_curves"
    half = {(r.tenor.count, r.tenor.unit) for r in rates if r.meta.business_date == "2026-11-19"}
    assert (6, ops.TENOR_UNIT_MONTH) in half and (18, ops.TENOR_UNIT_MONTH) in half
    assert (30, ops.TENOR_UNIT_YEAR) in half and len(half) == 60


def test_an_earlier_day_wanted_read_for_its_range(tmp_path: Path) -> None:
    plugin = resolving(Recorder(INSTANCE))
    portal = SyntheticPortal(lambda: AT)
    work = feed(tmp_path, plugin, portal=portal)
    asyncio.run(work.check())
    asked = want("w-1", [BUND], day="2026-10-01")
    plugin.answer("ObservationsWanted", lambda _: asked.message)
    asyncio.run(plugin.hear(work))
    assert portal.asked[-1] == path_for(date(2026, 10, 1), date(2026, 10, 1))
    first = rates_of(plugin, "w-1")
    assert len(first) == 60 and {r.meta.business_date for r in first} == {"2026-10-01"}
    ten = next(r for r in first if (r.tenor.count, r.tenor.unit) == (10, ops.TENOR_UNIT_YEAR))
    assert str(as_decimal(ten.value.value)) == "3.66"


def test_a_range_wanted(tmp_path: Path) -> None:
    start = datetime(2026, 11, 13, tzinfo=BERLIN)
    asked = want(
        "w-r",
        [BUND],
        valid_from_ns=int(start.timestamp()) * 10**9,
        valid_until_ns=int((start + timedelta(days=4)).timestamp()) * 10**9,
    )
    rates = rates_of(heard(tmp_path, asked), "w-r")
    assert {r.meta.business_date for r in rates} == {"2026-11-13", "2026-11-16"}


def test_the_latest_wanted(tmp_path: Path) -> None:
    rates = rates_of(heard(tmp_path, want("w-l", [BUND])), "w-l")
    assert len(rates) == 60 and {r.meta.business_date for r in rates} == {"2026-11-19"}


def test_the_record_not_held_is_reported_missing_and_waits(tmp_path: Path) -> None:
    plugin = checked(tmp_path, held=False)
    missed = [
        (i.value, i.source) for p in plugin.on("ReportMissingInstrument") for i in p.identifiers
    ]
    assert missed == [(CODE, "bbk")] and not rates_of(plugin)


def test_wants_declined(tmp_path: Path) -> None:
    plugin = heard(
        tmp_path,
        want("w-1", [BUND], day="2026-11-17"),
        want("w-2", ["INS-ELSE"], day="2026-11-17"),
        want("w-3", [BUND], day="2026-11-15"),
        want("w-4", [BUND], day="2026-11-21"),
        want("w-5", [BUND], day="2026-11-17", data_type="meridian.v1.Price"),
        want("w-6", [BUND], day="2026-11-17", kinds=(ops.RATE_KIND_PAR_YIELD,)),
    )
    against = rates_of(plugin, "w-1")
    assert len(against) == 60 and {r.meta.business_date for r in against} == {"2026-11-17"}
    reasons = [(d.want_id, ops.UnansweredReason.Name(d.reason)) for d in plugin.on("DeclineWant")]
    assert reasons == [
        ("w-2", "UNANSWERED_REASON_NOT_COVERED"),
        ("w-3", "UNANSWERED_REASON_SOURCE_SILENT"),
        ("w-4", "UNANSWERED_REASON_SOURCE_SILENT"),
        ("w-5", "UNANSWERED_REASON_NOT_COVERED"),
        ("w-6", "UNANSWERED_REASON_NOT_COVERED"),
    ]


def test_nothing_recorded_twice_in_a_process(tmp_path: Path) -> None:
    plugin = resolving(Recorder(INSTANCE))
    work = feed(tmp_path, plugin)
    asyncio.run(work.check())
    before = len(plugin.on("RecordRates"))
    asyncio.run(work.check())
    assert len(plugin.on("RecordRates")) == before


def test_the_answers_read_as_written() -> None:
    held = SyntheticPortal(lambda: AT).recordings["zero"].body.decode()
    read = parse(held, "zero")
    assert read.days[0].isoformat() == "2026-08-03" and not read.unread
    assert read.days[-1].isoformat() == "2026-11-19"
    assert not parse("﻿DATAFLOW\n\n\n", "zero").observations
    with pytest.raises(NotRead):
        parse("<html>Not found</html>", "zero")
    odd = parse(
        "BBK_SEIS_MATURITY,TIME_PERIOD,OBS_VALUE\nR01XX,2026-11-19,3.02\nR01XX,2026-11-20,x\n"
        "R99ZZ,2026-11-19,1\nR02XX,19.11.2026,1\nR03XX,2026-11-19,.\n",
        "zero",
    )
    assert [o.text for o in odd.observations] == ["3.02"] and len(odd.unread) == 3
    assert [tenor_of(c) for c in ("R005X", "R015X", "R01XX", "R105X", "R30XX", "R000X")] == [
        "6M", "18M", "1Y", "126M", "30Y", "",
    ]  # fmt: skip
