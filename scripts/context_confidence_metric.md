# Context: Multi-Run Nanobench

- Current pipeline
  - `scripts/run_measurements.py` produces raw `nanobench` JSON, optimized SKPs, and PNGs.
  - `scripts/collate_data.py` computes derived metrics and writes `report.json`.
  - `scripts/generate_html.py` renders HTML from `report.json`.

- Current problem
  - each benchmark currently gets one `nanobench` invocation
  - that gives many inner samples, but only from one outer run
  - this measures within-run noise only
  - it does not measure run-to-run noise

- Why this matters
  - some benchmarks with zero optimizer rewrites still show slowdowns
  - that suggests noise across whole `nanobench` runs
  - likely sources include order effects, thermal drift, scheduler variance, GPU state, and machine noise

- Goal
  - add repeated `nanobench` invocations per benchmark
  - preserve per-run benchmark values in `report.json`
  - show repeated-run-derived point estimates in the report
  - use `25` repeated `nanobench` runs per benchmark by default

- Non-goals for now
  - do not move responsibilities between scripts
  - do not add interval calculations
  - do not add classification labels
  - do not add extra noise summaries or metrics

- Required shape of the data
  - each benchmark has `N` outer `nanobench` runs
  - each outer run produces one baseline value, one optimized value, and one run-level speedup
  - default `N` is `25`
  - report one point estimate for baseline runtime
  - report one point estimate for optimized runtime
  - report one point estimate for speedup

- Point-estimate convention
  - within one `nanobench` run, reduce a variant's inner `samples` with a geomean
  - across repeated outer runs, report the median of those per-run geomeans
  - compute one per-run speedup as `baseline_run_geomean / optimized_run_geomean`
  - report the median of the per-run speedups as the table speedup value

- Important constraint
  - do not add statistical significance or interval calculations yet

- Why the TODO items exist
  - repeated runs are needed to preserve outer-run behavior
  - alternating order is needed to reduce measurement bias
  - per-run parsing is needed before repeated-run values can be surfaced
  - report fields are needed so HTML does not invent analysis logic
  - validation is needed so the new metric is not misleading
