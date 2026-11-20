# meridian-bundesbank

The Deutsche Bundesbank's Bund zero curve for
[Open Meridian](https://open-meridian.com): an Open Meridian plugin that puts
the Bundesbank's daily term structure of interest rates on listed Federal
securities -- zero rates at 0.5 to 30 years -- into a deployment's lake. It
reads the Bundesbank's SDMX web service and holds the `data` role, a data
plugin. This is release 0.1.0, a draft for the product owner. How to set it
up and use it is in [docs/](docs/README.md).

It is built on the SDK it pins, `open-meridian==0.37.1` (contract 30).

## What it records

- **`<instance>:bbk_curves`** (pushed as published, and pulled): each
  trading day's zero rates on (theoretical) zero-coupon Federal securities,
  estimated by the Svensson method, at residual maturities of 0.5 to 30
  years in half years, each a `zero` at its tenor on one curve record, in
  per cent as the Bundesbank writes them. The Bundesbank states "% p.a."
  and no compounding in words; its published rates are Svensson's spot
  rates at its own published parameters, so the plugin states them
  continuously compounded, actual/365 (its statement). The last ten days
  are read every hour; any earlier day when the lake wants it.
- **The record:** the curve is asked of the deployment by its code at `bbk`
  (`bbk:Term structure of interest rates on listed Federal securities`);
  the platform seeds none yet, so it is reported missing, never minted, and
  its rates wait.
- **Not presented:** the Svensson parameters and forward rates (ruling 131:
  derived later from the points); the monthly series (the daily ones carry
  every day); the Bundesbank's real-time macroeconomic series (they wait for
  the series slice). No published time is recorded: the Bundesbank states
  none on a value.

## Deploying it

On a deployment, with the `meridian` CLI connected (`meridian connect`):

    meridian plugin upload              # from this directory
    meridian plugin launch bundesbank   # a deployment admin approves its one role, data

No key and no account. A deployment admin then licenses its dataset and
entitles the plugins that read it on the Data sources page
([docs/setup.md](docs/setup.md)).

## Checking it

    make ci-local                  # lint, tests, plugin check, image, e2e: the pre-push gate
    make preview SHOTS=<dir>       # each page in a browser with the kit, at 375, 582 and 1280 px

`tests/test_suite.py` runs the SDK's data suite on the plugin's own
conversion, and it passes; a case about what the Bundesbank never states
here is not presented, with why.

## The terms, summarised

Not legal advice; read the Bundesbank's own words
([reuse of ESCB statistics](https://www.bundesbank.de/en/homepage/user-information/terms-of-use-regarding-the-reuse-of-escb-statistics-621188))
before relying on them. The ESCB's statistics may be reused free of charge,
commercially or not, quoting the source, with the statistics and their
metadata unmodified; third-party data are excluded without the originator's
permission; there is no right to a statistic's continuity. The dataset says
so in words, and declares no licence: the deployment admin's licence is the
one enforced. This project is not affiliated with or endorsed by the
Deutsche Bundesbank.

## Licence

Apache-2.0 (LICENSE, NOTICE). The Bundesbank's answer under
`src/bundesbank/responses/` is as received on 2026-11-19.
