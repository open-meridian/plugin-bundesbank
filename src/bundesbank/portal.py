"""The Deutsche Bundesbank's SDMX web service, where its term structure of
interest rates is served, and its stand-in.

One kind of request is made, and nothing else
(https://www.bundesbank.de/en/statistics/time-series-databases/help-for-sdmx-web-service):
the sixty zero rates of the term structure on listed Federal securities for
a range of days --
`/rest/data/BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604..R.A.A._Z._Z.A?detail=dataonly`
with `startPeriod` and `endPeriod` (`2026-11-09`), as SDMX-CSV.

Read from the Bundesbank itself: no key, no account. Its terms are the
ESCB's for reusing its statistics (docs/terms.md), which state no rate
limit; the plugin asks one request at a time, at most one every two seconds,
says who it is in its User-Agent, and checks the current range every hour.

`SyntheticPortal` answers from the real response committed under
responses/ (responses/index.json), recorded on 2026-11-19: the sixty
series from 3 August to 19 November 2026. A range is answered with the
recorded lines in it; the current range ends on the recording's last day
whatever the clock says, so the plugin's tests and its e2e run on it,
offline, the same on any day.
"""

from __future__ import annotations

import asyncio
import csv
import gzip
import io
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from importlib import resources
from typing import Protocol

from .series import FLOW, KEY

BASE = "https://api.statistiken.bundesbank.de"
ZERO = "zero"
SOURCES = (ZERO,)
#: The address of the sixty series, before its range.
PATH = f"/rest/data/{FLOW}/{KEY}?detail=dataonly"
#: The answer asked for: SDMX-CSV.
ACCEPT = "application/vnd.sdmx.data+csv;version=1.0.0"
USER_AGENT = "meridian-bundesbank (+https://github.com/open-meridian/plugin-bundesbank)"
SPACING = 2.0
TIMEOUT = 120.0
#: The most an answer may be: a year of the sixty series is some 2 MB.
MOST_BYTES = 16 * 1024 * 1024
#: How far the current range reaches back: ten days.
CURRENT_DAYS = 10


def path_for(start: date, end: date) -> str:
    """The address of the zero rates from `start` to `end`."""
    return f"{PATH}&startPeriod={start.isoformat()}&endPeriod={end.isoformat()}"


def source_of(path: str) -> str:
    """Which source an address asks: zero, or none."""
    return ZERO if path.startswith(PATH) else ""


class PortalUnreachable(Exception):  # noqa: N818 - what the Bundesbank's web service was
    """The web service could not be asked: no answer, or not in time."""


@dataclass(frozen=True)
class Fetched:
    """One answer, as received."""

    path: str
    status: int
    body: bytes
    fetched_at: datetime
    date: str = ""

    @property
    def url(self) -> str:
        return BASE + self.path

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class Portal(Protocol):
    mode: str

    def current(self, today: date) -> tuple[date, date]: ...

    async def get(self, path: str) -> Fetched: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


class LivePortal:
    """The Bundesbank's web service itself."""

    mode = "live"

    def __init__(self, now: Callable[[], datetime] = utc_now) -> None:
        self._now = now
        self._lock = asyncio.Lock()
        self._last = 0.0

    def current(self, today: date) -> tuple[date, date]:
        return today - timedelta(days=CURRENT_DAYS), today

    async def get(self, path: str) -> Fetched:
        async with self._lock:
            wait = self._last + SPACING - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                return await asyncio.to_thread(self._get, path)
            finally:
                self._last = time.monotonic()

    def _get(self, path: str) -> Fetched:
        request = urllib.request.Request(
            BASE + path, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT}
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310 - the Bundesbank's https address
                body = answer.read(MOST_BYTES + 1)
                status = answer.status
                said = answer.headers
        except urllib.error.HTTPError as refused:
            body = refused.read(MOST_BYTES + 1) if refused.fp else b""
            status, said = refused.code, refused.headers
        except (urllib.error.URLError, TimeoutError, OSError) as failed:
            reason = getattr(failed, "reason", failed)
            raise PortalUnreachable(f"{BASE}{path[:80]}: {type(reason).__name__}") from failed
        if len(body) > MOST_BYTES:
            raise PortalUnreachable(f"{BASE}{path[:80]}: answered more than {MOST_BYTES} bytes")
        return Fetched(path, status, body, self._now(), date=said.get("Date", "") if said else "")


@dataclass(frozen=True)
class Recording:
    """One recorded answer, its Date and last day."""

    body: bytes
    said: str
    last_day: date


class SyntheticPortal:
    """The response committed under responses/: each range answered with
    the recorded lines in it, under its recording's Date."""

    mode = "synthetic"

    def __init__(self, now: Callable[[], datetime] = utc_now) -> None:
        self._now = now
        held = resources.files(__package__).joinpath("responses")
        index = json.loads(held.joinpath("index.json").read_text(encoding="utf-8"))
        self.recordings = {}
        for source in SOURCES:
            body = held.joinpath(index[source]["file"]).read_bytes()
            self.recordings[source] = Recording(
                gzip.decompress(body) if index[source]["file"].endswith(".gz") else body,
                str(index[source]["date"]),
                date.fromisoformat(index[source]["last_day"]),
            )
        self.asked: list[str] = []

    def current(self, today: date) -> tuple[date, date]:
        last = self.recordings[ZERO].last_day
        return last - timedelta(days=CURRENT_DAYS), last

    async def get(self, path: str) -> Fetched:
        self.asked.append(path)
        recording = self.recordings.get(source_of(path))
        if recording is None:
            return Fetched(path, 404, b"Not found", self._now())
        query = dict(p.partition("=")[::2] for p in path.partition("?")[2].split("&"))
        try:
            start = date.fromisoformat(query.get("startPeriod", ""))
            end = date.fromisoformat(query.get("endPeriod", ""))
        except ValueError:
            return Fetched(path, 400, b"Bad date", self._now())
        body = _within(recording.body.decode("utf-8"), start, end)
        return Fetched(path, 200, body.encode(), self._now(), recording.said)


def _within(text: str, start: date, end: date) -> str:
    """The recorded lines from `start` to `end`, under the header."""
    rows = [r for r in csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";") if r]
    day = rows[0].index("TIME_PERIOD")
    kept = [r for r in rows[1:] if start.isoformat() <= r[day] <= end.isoformat()]
    out = io.StringIO()
    csv.writer(out, delimiter=";", lineterminator="\n").writerows([rows[0], *kept])
    return out.getvalue()


def portal(synthetic: bool, now: Callable[[], datetime] = utc_now) -> Portal:
    return SyntheticPortal(now) if synthetic else LivePortal(now)
