#!/usr/bin/env python3
#
# Generate an HTML report summarizing nanobench runs.

from __future__ import annotations

import argparse
import html
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


Transform = str


@dataclass
class BenchmarkStats:
    stem: str
    size: int | None = None
    means: dict[Transform, float] = field(default_factory=dict)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an HTML report for nanobench results.")
    parser.add_argument("--nanobench-dir", type=Path, default=Path("report/nanobench"))
    parser.add_argument("--json-dir", type=Path, default=Path("jsons"))
    parser.add_argument("--output", type=Path, default=Path("report/index.html"))
    parser.add_argument("--title", type=str, default="Easteregg Benchmark Report")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def classify_transform(name: str) -> Transform | None:
    lower = name.lower()
    if lower.endswith("_ee.skp"):
        return "easteregg"
    if lower.endswith("_sk.skp"):
        return "skrecordopt"
    if lower.endswith(".skp"):
        return "baseline"
    return None


def canonical_label(result_key: str) -> tuple[str, str]:
    prefix = result_key
    clip_suffix = ""
    if ".skp_" in result_key:
        prefix, clip_suffix = result_key.split(".skp_", 1)
    elif result_key.endswith(".skp"):
        prefix = result_key[:-4]
    if prefix.endswith("_ee"):
        prefix = prefix[:-3]
    elif prefix.endswith("_sk"):
        prefix = prefix[:-3]
    label = prefix
    if clip_suffix:
        label = f"{prefix}_{clip_suffix}"
    return label, prefix


def compute_mean(samples: Iterable[float] | None) -> float | None:
    if not samples:
        return None
    total = 0.0
    count = 0
    for value in samples:
        if not isinstance(value, (float, int)):
            continue
        total += float(value)
        count += 1
    if not count:
        return None
    return total / count


def load_benchmarks(nanobench_dir: Path) -> dict[str, BenchmarkStats]:
    if not nanobench_dir.is_dir():
        raise RuntimeError(f"Nanobench directory does not exist: {nanobench_dir}")
    entries: dict[str, BenchmarkStats] = {}
    for path in sorted(nanobench_dir.glob("*.json")):
        data = load_json(path)
        results = data.get("results", data)
        if not isinstance(results, dict):
            continue
        for bench_key, bench_data in results.items():
            if not isinstance(bench_data, dict):
                continue
            label, stem = canonical_label(bench_key)
            entry = entries.setdefault(label, BenchmarkStats(stem=stem))
            for backend_info in bench_data.values():
                if not isinstance(backend_info, dict):
                    continue
                options = backend_info.get("options", {})
                transform_name = options.get("name") or bench_key
                transform = classify_transform(str(transform_name))
                if transform is None:
                    continue
                mean_value = compute_mean(backend_info.get("samples"))
                if mean_value is None:
                    continue
                entry.means[transform] = mean_value
    return entries


def count_commands(json_dir: Path, stem: str, cache: dict[str, int]) -> int:
    if stem in cache:
        return cache[stem]
    json_path = json_dir / f"{stem}.json"
    if not json_path.is_file():
        raise RuntimeError(f"Missing command JSON for {stem}: {json_path}")
    data = load_json(json_path)
    commands = data.get("commands")
    if not isinstance(commands, list):
        raise RuntimeError(f"Invalid commands array in {json_path}")
    cache[stem] = len(commands)
    return cache[stem]


def attach_sizes(entries: dict[str, BenchmarkStats], json_dir: Path) -> None:
    if not json_dir.is_dir():
        raise RuntimeError(f"JSON directory does not exist: {json_dir}")
    cache: dict[str, int] = {}
    for entry in entries.values():
        entry.size = count_commands(json_dir, entry.stem, cache)


def geometric_mean_speedup(entries: dict[str, BenchmarkStats]) -> float | None:
    ratios: list[float] = []
    for entry in entries.values():
        ee = entry.means.get("easteregg")
        sk = entry.means.get("skrecordopt")
        if ee is not None and sk is not None and ee > 0 and sk > 0:
            ratios.append(sk / ee)
    if not ratios:
        return None
    log_sum = sum(math.log(ratio) for ratio in ratios)
    return math.exp(log_sum / len(ratios))


def total_runtime_difference(entries: dict[str, BenchmarkStats]) -> float | None:
    diffs: list[float] = []
    for entry in entries.values():
        ee = entry.means.get("easteregg")
        sk = entry.means.get("skrecordopt")
        if ee is not None and sk is not None:
            diffs.append(sk - ee)
    if not diffs:
        return None
    return sum(diffs)


def format_ms(value: float | None) -> str:
    if value is None:
        return "&mdash;"
    return f"{value:.3f}"


def format_delta(delta: float | None) -> str:
    if delta is None:
        return "&mdash;"
    return f"{delta:+.2f}%"


def render_html(
    title: str,
    entries: dict[str, BenchmarkStats],
    geom_speedup: float | None,
    runtime_diff: float | None,
) -> str:
    total = len(entries)
    speedup_text = "&mdash;"
    if geom_speedup is not None:
        speedup_text = f"{geom_speedup:.3f}x"
    runtime_text = "&mdash;"
    if runtime_diff is not None:
        runtime_text = f"{runtime_diff:.3f} ms"

    rows: list[str] = []
    for name in sorted(entries.keys()):
        entry = entries[name]
        baseline = entry.means.get("baseline")
        sk = entry.means.get("skrecordopt")
        ee = entry.means.get("easteregg")
        delta_sk = ((ee - sk) / sk * 100) if ee is not None and sk is not None and sk != 0 else None
        delta_base = (
            ((ee - baseline) / baseline * 100)
            if ee is not None and baseline is not None and baseline != 0
            else None
        )
        size_text = str(entry.size) if entry.size is not None else "&mdash;"
        row = (
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{size_text}</td>"
            f"<td>{format_ms(baseline)}</td>"
            f"<td>{format_ms(sk)}</td>"
            f"<td>{format_ms(ee)}</td>"
            f"<td>{format_delta(delta_sk)}</td>"
            f"<td>{format_delta(delta_base)}</td>"
            "</tr>"
        )
        rows.append(row)

    table = "\n".join(rows) if rows else ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p>Total benchmarks: {total}. Geometric mean speedup (skrecordopt / easteregg): {speedup_text}. Total runtime saved: {runtime_text}.</p>
<table>
<thead>
<tr>
<th>Benchmark</th>
<th>Size (#cmds)</th>
<th>Baseline ms (mean)</th>
<th>Skrecordopt ms (mean)</th>
<th>Easteregg ms (mean)</th>
<th>&#916; vs Skrecordopt</th>
<th>&#916; vs Baseline</th>
</tr>
</thead>
<tbody>
{table}
</tbody>
</table>
</body>
</html>
"""
    return html


def main() -> None:
    args = parse_args()
    entries = load_benchmarks(args.nanobench_dir)
    if not entries:
        raise RuntimeError(f"No benchmarks found in {args.nanobench_dir}")
    attach_sizes(entries, args.json_dir)
    geom_speedup = geometric_mean_speedup(entries)
    runtime_diff = total_runtime_difference(entries)
    html = render_html(args.title, entries, geom_speedup, runtime_diff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
