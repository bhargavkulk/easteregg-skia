#!/usr/bin/env python3
#
# Generate an HTML report summarizing nanobench runs.

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate an HTML report for nanobench results.')
    parser.add_argument('--nanobench-dir', type=Path, default=Path('report/nanobench'))
    parser.add_argument('--json-dir', type=Path, default=Path('jsons'))
    parser.add_argument('--png-dir', type=Path, default=Path('report/pngs'))
    parser.add_argument('--output', type=Path, default=Path('report/index.html'))
    parser.add_argument('--title', type=str, default='Easteregg Benchmark Report')
    return parser.parse_args()


FLOAT_RE = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')


def run_compare(png1: Path, png2: Path, diff: Path) -> float | None:
    diff.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'compare',
        '-metric',
        'AE',
        str(png1),
        str(png2),
        str(diff),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f'ImageMagick compare failed for {png1} vs {png2} ({result.returncode}): {result.stderr}'
        )

    stderr = result.stderr.strip()
    print(f'compare {png1.name} vs {png2.name}: {stderr}')

    match = FLOAT_RE.search(stderr)
    return float(match.group(0)) if match else None


def main() -> None:
    args = parse_args()

    def collect_stats(stem: str, benchmark_name: str) -> float:
        bench_file = args.nanobench_dir / f'{stem}__nanobench.json'

        with bench_file.open(encoding='utf-8') as f:
            timing_data = json.load(f)

        gl_data = timing_data['results'][benchmark_name]['gl']
        samples: list[float] = gl_data['samples']

        return sum(samples) / len(samples)

    stats: list[tuple[str, float, float, float, float | None, str | None]] = []

    for json_path in sorted(args.json_dir.glob('*.json')):
        with json_path.open(encoding='utf-8') as f:
            metadata = json.load(f)

        if not metadata.get('has_save_layer'):
            continue

        clip = metadata.get('dim')
        if not isinstance(clip, list) or len(clip) < 2:
            continue

        try:
            width, height = (int(clip[0]), int(clip[1]))
        except (TypeError, ValueError, IndexError):
            continue

        length = len(metadata.get('commands'))

        base_name = json_path.stem
        suffix = f'.skp_1_{width}_{height}'
        skrecordopt = f'{base_name}__sk{suffix}'
        easteregg = f'{base_name}__ee{suffix}'
        baseline = f'{base_name}{suffix}'

        baseline_png = args.png_dir / f'{base_name}.png'
        ee_png = args.png_dir / f'{base_name}__ee.png'
        diff_png = args.png_dir / f'{base_name}__diff.png'

        diff_metric: float | None = None
        diff_href: str | None = None
        if baseline_png.is_file() and ee_png.is_file():
            diff_metric = run_compare(baseline_png, ee_png, diff_png)
            diff_href = f'/pngs/{diff_png.name}'

        skmean = collect_stats(base_name, skrecordopt)
        eemean = collect_stats(base_name, easteregg)
        blmean = collect_stats(base_name, baseline)
        stats.append((base_name, skmean, eemean, blmean, diff_metric, diff_href))

    table_rows = [
        '<tr><th>Benchmark</th><th>skrecordopt</th><th>easteregg</th><th>baseline</th><th>diff AE</th><th>speedup</th></tr>'
    ]
    for name, skmean, eemean, blmean, diff_metric, diff_href in stats:
        speedup = skmean / eemean
        if diff_metric is not None and diff_href:
            diff_display = (
                f'<a href="{html.escape(diff_href)}"><code>{diff_metric:g}</code></a>'
            )
        elif diff_href:
            diff_display = f'<a href="{html.escape(diff_href)}">view</a>'
        else:
            diff_display = '&mdash;'

        table_rows.append(
            '<tr>'
            f'<td>{html.escape(name)}</td>'
            f'<td><code>{skmean:.3f}</code></td>'
            f'<td><code>{eemean:.3f}</code></td>'
            f'<td><code>{blmean:.3f}</code></td>'
            f'<td>{diff_display}</td>'
            f'<td style="color:{"green" if speedup > 1.0 else "red"}"><code>{speedup:.3f}</code></td>'
            '</tr>'
        )

    body_content = (
        '\n'.join(table_rows) if stats else '<p>No benchmarks with save layers were found.</p>'
    )

    html_output = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(args.title)}</title>
<style>
body {{
    margin: 40px auto;
    max-width: 800px;
    line-height: 1.6;
    font-size: 18px;
    color: #444;
    padding: 0 10px
}}
table {{
    border-collapse: collapse;
}}
table th {{
    background-color: #e0e0e0;
}}
table th,
table td {{
    border: 1px solid #444;
    padding: 4px 8px;
}}
</style>
<script src="https://cdn.jsdelivr.net/npm/table-sort-js/table-sort.min.js"></script>
</head>
<body>
<h1>{html.escape(args.title)}</h1>
<p><em>All time units are in ms</em></p>
<table class="table-sort table-arrows remember-sort">
{body_content}
</table>
</body>
</html>
"""

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_output, encoding='utf-8')


if __name__ == '__main__':
    main()
