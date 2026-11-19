"""The data suite (meridian.suites), each case the Deutsche Bundesbank's
series present mapped to the plugin's own conversion of the Bundesbank's
recorded answer, the whole suite passing.

The term structure is a curve of zero rates, recorded as `Rate` rows
(contract v27). It presents `a-tenor-not-published` on a stand-in of the
recorded answer with the 30-year left out of 18 November -- the recording
itself states every maturity every trading day, as the Bundesbank's
history does not (it began with forty) -- and
`a-same-day-revision`: a rate the Bundesbank revises within the current
range is the same row key's next version. `a-curve-for-a-date` asks for par
yields, which the Bundesbank does not publish here, so it is not presented.
The cases a rates-only plugin never presents -- every case about a price, a
trade, a quote or an outcome -- are the SDK's `RATES_NOT_PRESENTED`, each
with why. Beside them this plugin names its own:

- the rates cases about what the Bundesbank never states here -- a fixing,
  a bill's two conventions, a rate index, another source's curve point, a
  par yield -- each with why;
- the calendars' two: its dataset declares no calendar (the platform holds
  none for the euro yet), and it never computes a settlement date;
- `reports-its-feed-delay`: the Bundesbank states no published time for a
  value;
- `records-a-datasets-liveness`: it polls hourly and records no liveness.

The cases every suite holds that the SDK answers (a replacement, the
template catalogue, an event group heard) are the SDK's.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles.data.testing import RATES_NOT_PRESENTED
from meridian.suites import ANSWERED_BY_SDK, Recorder, run

from bundesbank.portal import Fetched, SyntheticPortal

from conftest import AT, BUND, CURVES, INSTANCE, feed, resolving, want

PRESENTED = ("a-tenor-not-published", "a-same-day-revision")

NOT_PRESENTED = {
    **{c: why for c, why in RATES_NOT_PRESENTED.items() if c not in PRESENTED},
    "a-rate-fixing": "the Bundesbank publishes a curve of zero rates: no fixing",
    "a-curve-for-a-date": "the Bundesbank publishes zero rates here: no par yield",
    "two-conventions-one-tenor": "the Bundesbank publishes no bill here: one convention a point",
    "a-curve-point-from-another-source": (
        "the Bundesbank publishes its curve whole: no single-point series"
    ),
    "an-index-level": "the Bundesbank publishes no rate index here",
    "records-a-derived-series": "the Bundesbank's rates are rates: no derived series",
    "reads-a-calendar": (
        "its dataset declares no calendar: the platform holds none for the euro yet"
    ),
    "asks-for-a-settlement-date": (
        "records each value as published; never computes a settlement date"
    ),
    "reports-its-feed-delay": "the Bundesbank states no published time for a value",
    "records-a-datasets-liveness": (
        "it polls the Bundesbank hourly and records no liveness: its rates change once a day"
    ),
}


class Changed(SyntheticPortal):
    """The web service, the current range read twice: as recorded, then
    with the 10-year of 17 November revised; and, where `thinned`, the
    30-year of 18 November left out of every answer."""

    def __init__(self, *, thinned: bool = False) -> None:
        super().__init__(lambda: AT)
        self.reads = 0
        self.thinned = thinned

    async def get(self, path: str) -> Fetched:
        got = await super().get(path)
        text = got.text
        if self.thinned:
            text = "".join(
                line
                for line in text.splitlines(keepends=True)
                if not (";R30XX;" in line and ";2026-11-18;" in line)
            )
            return Fetched(path, 200, text.encode(), got.fetched_at, got.date)
        self.reads += 1
        if self.reads == 1:
            return got
        lines = [
            line.replace(";2026-11-17;3.42;", ";2026-11-17;3.49;") if ";R10XX;" in line else line
            for line in text.splitlines(keepends=True)
        ]
        body = "".join(lines)
        assert body != text
        return Fetched(path, 200, body.encode(), got.fetched_at, got.date)


def _heard(recorder: Recorder, message: Any) -> None:
    recorder.answer("ObservationsWanted", lambda _: message)


def producers(tmp: Path) -> dict[str, Callable[[Recorder], Awaitable[None]]]:
    async def two_records(recorder: Recorder) -> None:
        resolving(recorder, ambiguous=True)
        await feed(tmp, recorder).check()

    async def revised(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(tmp, recorder, portal=Changed())
        await work.check()
        await work.check()
        batches = [
            sorted(r.meta.row_key for r in b.rates if r.meta.business_date == "2026-11-17")
            for b in recorder.on("RecordRates")
        ]
        keys = [held for held in batches if held]
        assert len(keys) == 2 and keys[0] == keys[1]

    async def gap(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(tmp, recorder, portal=Changed(thinned=True))
        _heard(recorder, want("w-g", [BUND], day="2026-11-18").message)
        await recorder.hear(work)
        sent = [r for b in recorder.on("RecordRates") for r in b.rates]
        assert len(sent) == 59 and (30, ops.TENOR_UNIT_YEAR) not in {
            (r.tenor.count, r.tenor.unit) for r in sent
        }

    async def licences(recorder: Recorder) -> None:
        recorder.answer(
            "ListDatasets",
            lambda _: ops.ListDatasetsResult(licences=[ops.DatasetLicence(dataset=CURVES)]),
        )
        work = feed(tmp, recorder)
        await work.wants.read_licences()
        assert work.wants.licensed == {CURVES}

    async def declined(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(tmp, recorder)
        _heard(recorder, want("w-2", ["INS-NOT-CARRIED"], day="2026-11-17").message)
        await recorder.hear(work)

    async def withdrawn(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(tmp, recorder)
        recorder.answer(
            "WantWithdrawn",
            lambda _: ops.WantWithdrawnEvent(want_id="w-standing", dataset=CURVES),
        )
        await recorder.hear(work)

    return {
        "an-asset-that-does-not-resolve": two_records,
        "a-subject-declined": declined,
        "a-standing-want-withdrawn": withdrawn,
        "reads-its-datasets-licences": licences,
        "a-same-day-revision": revised,
        "a-tenor-not-published": gap,
    }


def test_the_data_suite_passes(tmp_path: Path) -> None:
    report = run("data", producers(tmp_path), not_presented=NOT_PRESENTED, instance_id=INSTANCE)
    assert report.passed, report.failures
    assert sorted(report.not_presented) == sorted(NOT_PRESENTED)
    assert len(report.passed_cases) == 6 + len(ANSWERED_BY_SDK)
    assert set(PRESENTED) <= set(report.passed_cases)
    assert report.answered_by_sdk == list(ANSWERED_BY_SDK)
