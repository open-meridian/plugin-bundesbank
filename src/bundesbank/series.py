"""The Deutsche Bundesbank's series this version carries, what each one is,
and the record it is recorded against: the plugin's series map.

**The Bund zero curve** (`bbk_curves`, the Bundesbank's SDMX web service,
dataflow `BBSIS`). The "Term structure of interest rates on listed Federal
securities (method by Svensson)", daily: "Interest rates on (theoretical)
zero-coupon bonds without a default risk", in "% p.a.", at residual
maturities of 0.5 to 30 years in half years, sixty series
`BBSIS.D.I.ZST.ZI.EUR.S1311.B.A604.<maturity>.R.A.A._Z._Z.A`, the maturity
`R005X` (0.5 years), `R01XX` (1 year) to `R30XX` (30 years). Each is a
`zero` rate at its tenor on one `rate_curve` record (ruling 131: the
Svensson parameters and forward rates are not recorded; they are derived
later from the points).

**Convention.** The Bundesbank states "% p.a." and the Svensson method; it
states no compounding in words. Its published rates are Svensson's spot
rate function at the parameters it publishes beside them (the 1, 5, 10, 20
and 30-year rates of 19 November 2026, 3.02, 3.19, 3.45, 3.73 and 3.83,
are the function's 3.023, 3.193, 3.446, 3.731 and 3.834), and Svensson's
spot rates are continuously compounded. So the plugin states them
continuously compounded, actual/365 -- the plugin's statement, read from
the Bundesbank's own figures, and said on the Datasets page. A value the
Bundesbank writes as `.` (a day with none, status `K`) is no row.

The record is asked of the deployment by the Bundesbank's name for it,
"Term structure of interest rates on listed Federal securities", as a
`symbol` at the source `bbk`, a name **proposed** with this version for
the platform's seed; the platform seeds none yet, so until a deployment
holds the record its values wait, reported missing, never minted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from meridian.roles.data import rates

SOURCE = "bbk"
RATE_CURVE = "rate_curve"

#: Continuously compounded, actual/365: the plugin's statement.
CONTINUOUS = rates.CONTINUOUS
#: The dataflow and the key of the sixty series, the maturity left open.
FLOW = "BBSIS"
KEY = "D.I.ZST.ZI.EUR.S1311.B.A604..R.A.A._Z._Z.A"
#: A maturity's code: `R005X` half a year, `R01XX` a year, `R105X` ten and a half.
_MATURITY = re.compile(r"R(\d\d)(5X|XX)")


@dataclass(frozen=True)
class Record:
    """A referential record, by the code proposed for it at `bbk`."""

    code: str
    instrument_type: str
    description: str

    @property
    def identifier(self) -> tuple[str, str, str]:
        return ("symbol", self.code, SOURCE)


BUND_RECORD = Record(
    "Term structure of interest rates on listed Federal securities",
    RATE_CURVE,
    "Bund zero curve: interest rates on (theoretical) zero-coupon Federal securities "
    "(Deutsche Bundesbank, method by Svensson)",
)
RECORDS = (BUND_RECORD,)


def tenor_of(maturity: str) -> str:
    """A maturity's code as a tenor: `R005X` is 6M, `R015X` 18M, `R10XX`
    10Y; empty where it is not one."""
    found = _MATURITY.fullmatch(maturity)
    if found is None:
        return ""
    months = int(found.group(1)) * 12 + (6 if found.group(2) == "5X" else 0)
    if months == 0:
        return ""
    return f"{months // 12}Y" if months % 12 == 0 else f"{months}M"


def months_in(tenor: str) -> int:
    """A tenor's months, for ordering: 6M is 6, 10Y 120."""
    return int(tenor[:-1]) * (12 if tenor.endswith("Y") else 1)
