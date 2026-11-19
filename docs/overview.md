# Overview

The Deutsche Bundesbank publishes the rates this plugin puts into your
deployment's lake:

- **The Bund zero curve** (`<instance>:bbk_curves`): each trading day, the
  term structure of interest rates on listed Federal securities -- the
  rates on (theoretical) zero-coupon Federal securities without a default
  risk, estimated by the Svensson method -- at residual maturities of 0.5
  to 30 years, every half year.

It reads the Bundesbank's public SDMX web service: no key, no account. It
reads the last ten days every hour; any earlier day is read when your lake
asks for it.

## What it records

- **Each value as the Bundesbank writes it,** made an exact decimal from its
  text. A day the Bundesbank states nothing for is no value, never a zero.
- **Zero rates.** Each rate is a zero rate at its tenor on the curve's
  record, in per cent. The Bundesbank states "% p.a."; its published rates
  are Svensson's spot rates at the parameters it publishes beside them, so
  the plugin states them continuously compounded, actual/365.
- **Against your deployment's record.** The curve is asked of your
  deployment by a code at `bbk`; the plugin never makes a record: if your
  deployment does not hold it, it is reported missing, and its values wait.
- **No published time:** the Bundesbank states none on a value.
- **Not carried:** the Svensson parameters and forward rates, which are
  derived later from the points; the Bundesbank's other statistics.

## What it never does

It records no trade and shows no value on its pages. It holds no account and
uses no key. It never modifies a value.
