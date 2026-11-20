# Changelog

## 0.1.0

On open-meridian 0.36.0, contract 30, on core aae501d's harness. The
product owner's items 128, 131 and 140 (2026-11-19): Tier 1, the Bund zero
curve alone; the real-time macroeconomic series wait for the series slice.
The dataset key, the record's code and the source `bbk` are proposed here,
the product owner's to approve.

- **`bbk_curves`** (push and pull): the term structure of interest rates on
  listed Federal securities (method by Svensson), `zero` points at 0.5 to 30
  years in half years on one `rate_curve` record, from the SDMX web
  service's `BBSIS` dataflow. Continuously compounded, actual/365: the
  plugin's statement, since the Bundesbank states "% p.a." and its published
  rates are Svensson's spot rates at its own parameters. A day written `.`
  is no row.
- **Kept:** the ESCB's reuse conditions allow commercial reuse, quoting the
  source, unmodified; every answer is kept as received.
- **No record minted;** no published time (the Bundesbank states none on a
  value). No Svensson parameters or forwards (ruling 131).
- **Terms in words** (`declared.TERMS`).
- **Pages:** the data role's Connection (with Sources) and Datasets (with
  Records).
- **Sample data:** the Bundesbank's answer as received on 2026-11-19, 3
  August to 19 November 2026.

SDK 0.37.0: waits for a lost sidecar; its storage is read once registered,
on an instance run as shards or with a standby pod the shard's own folder.

SDK 0.37.1: a raw record kept from two threads at once waits instead of being dropped.
