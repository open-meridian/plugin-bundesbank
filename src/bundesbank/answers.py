"""The Deutsche Bundesbank's answers, read as the Bundesbank wrote them.

Its SDMX web service answers a request for the term structure as SDMX-CSV
(`application/vnd.sdmx.data+csv;version=1.0.0`, `detail=dataonly`): a
header naming each column -- the key's dimensions, `TIME_PERIOD`,
`OBS_VALUE` and the observation's attributes -- then one line a series and
day, separated by `;` (or `,`, as the header shows). `BBK_SEIS_MATURITY`
names the residual maturity, `TIME_PERIOD` the day (`2026-11-19`),
`OBS_VALUE` the rate in per cent, `.` where it states none that day (a
weekend or a holiday, status `K`): no value, never a zero.

A value is kept as the text the Bundesbank wrote, and read as a `Decimal`
from it, never a float; a value that does not read is kept as not read, and
never recorded.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from .series import months_in, tenor_of

MISSING = {"", ".", "NaN"}
MATURITY, DAY, VALUE = "BBK_SEIS_MATURITY", "TIME_PERIOD", "OBS_VALUE"


class NotRead(Exception):  # noqa: N818 - what the answer was not
    """An answer that is not what was asked for."""


@dataclass(frozen=True)
class Observation:
    """One value as the Bundesbank stated it: its day, tenor and text."""

    day: date
    tenor: str
    text: str

    @property
    def value(self) -> Decimal:
        return Decimal(self.text)


@dataclass
class Observations:
    """An answer read: its values in order, and the values that did not read."""

    source: str
    observations: list[Observation] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)

    @property
    def days(self) -> list[date]:
        return sorted({o.day for o in self.observations})

    def on(self, day: date) -> dict[str, Observation]:
        return {o.tenor: o for o in self.observations if o.day == day}


def _number(text: str) -> bool:
    try:
        return Decimal(text).is_finite()
    except InvalidOperation:
        return False


def parse(text: str, source: str) -> Observations:
    """An SDMX-CSV answer, read; NotRead where it is not one. A range with
    no value -- answered with `DATAFLOW` alone, or a header and no line --
    reads as empty."""
    read = Observations(source)
    body = text.lstrip("﻿")
    first = body.partition("\n")[0]
    delimiter = ";" if first.count(";") > first.count(",") else ","
    rows = [r for r in csv.reader(io.StringIO(body), delimiter=delimiter) if r]
    header = [h.strip() for h in rows[0]] if rows else []
    if len(rows) == 1 and header == ["DATAFLOW"]:
        return read  # a range with no value: the header's first column alone
    if not {MATURITY, DAY, VALUE} <= set(header):
        raise NotRead(f"the answer is not the web service's SDMX-CSV: {text[:80]!r}")
    at = {name: header.index(name) for name in (MATURITY, DAY, VALUE)}
    for row in rows[1:]:
        if len(row) < len(header):
            read.unread.append(f"{source}: a short line {';'.join(row)[:40]!r}")
            continue
        maturity, stated, said = (row[at[n]].strip() for n in (MATURITY, DAY, VALUE))
        tenor = tenor_of(maturity)
        if not tenor:
            read.unread.append(f"{source}: a maturity {maturity[:20]!r}")
            continue
        try:
            day = date.fromisoformat(stated)
        except ValueError:
            read.unread.append(f"{source}: a day {stated[:20]!r}")
            continue
        if said in MISSING:
            continue
        if not _number(said):
            read.unread.append(f"{maturity} {day}: {said[:40]!r}")
            continue
        read.observations.append(Observation(day, tenor, said))
    read.observations.sort(key=lambda o: (o.day, months_in(o.tenor)))
    return read
