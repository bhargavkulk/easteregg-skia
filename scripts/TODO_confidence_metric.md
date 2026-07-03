# TODO: Nanobench Confidence Metric

- [x] Multi-run collection in `scripts/run_measurements.py`
  - [x] Add `--nanobench-runs` with default `25`.
  - [x] Run `nanobench` `N` times per benchmark instead of once.
  - [x] Store one raw JSON file per outer run.
  - [x] Use a stable layout like `nanobench/<stem>/run_000.json`.
  - [x] Alternate benchmark order across runs to reduce order bias.
  - [x] Keep this script limited to raw artifact generation.

- [x] Multi-run aggregation in `scripts/collate_data.py`
  - [x] Read repeated `nanobench` runs from the new layout.
  - [x] For each outer run, reduce baseline samples to one run-level value.
  - [x] For each outer run, reduce optimized samples to one run-level value.
  - [x] For each outer run, compute one run-level speedup.
  - [x] Do not pool all inner samples across outer runs.
  - [x] Add `nanobench_run_count`.
  - [x] Add `bl_run_geomeans`.
  - [x] Add `ee_run_geomeans`.
  - [x] Add `speedup_runs`.
  - [x] Add one reported point estimate for baseline runtime.
  - [x] Add one reported point estimate for optimized runtime.
  - [x] Add one reported point estimate for speedup.

- [x] HTML updates in `scripts/generate_html.py`
  - [x] Show the repeated-run point estimates in the table.
  - [x] Keep statistical decisions out of this script.

- [x] Template updates
  - [x] Update `scripts/templates/report_index.html.mako`.
  - [x] Leave `scripts/templates/report_summary.html.mako` unchanged because summary fields did not change.
