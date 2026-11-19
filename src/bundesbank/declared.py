"""What this version declares beside its role, `data` (W8.1, W4.1; the
catalogue from contract v18), built from code and used twice: `__main__`
registers with it, and `meridian plugin upload` reads it from the built image
(pyproject.toml's `[tool.meridian] declaration`).

**The catalogue: one dataset** (the product owner, items 128, 131 and 140,
2026-11-19: Tier 1, the Bund zero curve alone; its key proposed, the
product owner's to approve):

- **`bbk_curves`**: the term structure of interest rates on listed Federal
  securities, `zero` rates at each residual maturity on the curve's record,
  daily, from the Bundesbank's SDMX web service; pushed as the Bundesbank
  publishes them and any past day pulled when the lake wants it.

**Kept.** The ESCB's conditions for reusing its statistics allow reuse,
commercial or not, quoting the source and with the statistics unmodified;
the term structure is the Bundesbank's own estimate, and nothing in ruling
132 names the Bundesbank. So the dataset is pushed and its answers kept,
as plugin-ecb's rates are. Its real-time macroeconomic series wait for the
series slice (ruling 133) and are not declared.

`vendor` the Deutsche Bundesbank, no aggregator; `cadence` a day; its day
Frankfurt's (the Bundesbank's business day), ending at midnight; no
calendar (the platform holds none for the euro yet); no venue; `history` 0,
as each series states; its terms and pricing (contract 30, ruling 1032) the
ESCB's, in plain words, and no licence declared -- a deployment's licence,
set on the Data sources page, is the one enforced; a gap asked again
(`gap_recovery` `backfill`, W10.14).

**Storage:** the Bundesbank's answers (raw.py), archivable, ten years by
default.
"""

from __future__ import annotations

from meridian import DatasetDeclaration
from meridian.declaration import RecordKind

from .raw import DEFAULT_WINDOW_DAYS, RESPONSES

BBK_CURVES = "bbk_curves"
KEYS = (BBK_CURVES,)
VENDOR = "Deutsche Bundesbank"
RATE = "meridian.v1.Rate"
CADENCE = 86_400
DAY_TIME_ZONE = "Europe/Berlin"
DAY_END_MINUTE = 0

#: The ESCB's terms, in plain words (contract 30, ruling 1032), from the
#: Bundesbank's page on reusing ESCB statistics
#: (https://www.bundesbank.de/en/homepage/user-information/terms-of-use-regarding-the-reuse-of-escb-statistics-621188),
#: read on 2026-11-19.
TERMS = {
    BBK_CURVES: (
        "The Deutsche Bundesbank's SDMX web service: free, no key or account. The ESCB's "
        "statistics may be reused free of charge, whether commercially or not, provided the "
        "source is quoted and the statistics, metadata included, are not modified; the free "
        "reuse does not cover third-party data without the originator's prior permission. "
        "There is no right to the continuity of any statistic: figures may be revised, and "
        "access may be restricted in exceptional cases. The term structure is the "
        "Bundesbank's own estimate from the prices of listed Federal securities. The values "
        "are recorded as the Bundesbank writes them, unmodified."
    ),
}


def _dataset(key: str, data_types: list[str], modes: list[str]) -> DatasetDeclaration:
    return DatasetDeclaration(
        key=key,
        vendor=VENDOR,
        data_types=data_types,
        modes=modes,
        cadence=CADENCE,
        history=0,
        terms_and_pricing=TERMS[key],
        gap_recovery="backfill",
        day_time_zone=DAY_TIME_ZONE,
        day_end_minute=DAY_END_MINUTE,
    )


CATALOGUE = [_dataset(BBK_CURVES, [RATE], ["push", "pull"])]

RESPONSES_KIND = RecordKind(RESPONSES, "Raw responses", window_days=DEFAULT_WINDOW_DAYS)
