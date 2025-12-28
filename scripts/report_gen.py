#!/usr/bin/env python3
#
# Generate an HTML report summarizing nanobench runs.

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate an HTML report for nanobench results.')
    parser.add_argument('--nanobench-dir', type=Path, default=Path('report/nanobench'))
    parser.add_argument('--json-dir', type=Path, default=Path('jsons'))
    parser.add_argument('--output', type=Path, default=Path('report/index.html'))
    parser.add_argument('--title', type=str, default='Easteregg Benchmark Report')
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    def collect_stats(stem: str, benchmark_name: str) -> float:
        bench_file = args.nanobench_dir / f'{stem}__nanobench.json'

        with bench_file.open(encoding='utf-8') as f:
            timing_data = json.load(f)

        gl_data = timing_data['results'][benchmark_name]['gl']
        samples: list[float] = gl_data['samples']

        return sum(samples) / len(samples)

    stats: list[tuple[str, float, float, float]] = []  # list[name, skmean, eemean, blmean]

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

        skmean = collect_stats(base_name, skrecordopt)
        eemean = collect_stats(base_name, easteregg)
        blmean = collect_stats(base_name, baseline)
        stats.append((base_name, skmean, eemean, blmean))

    table_rows = [
        '<tr><th>Benchmark</th><th>skrecordopt (ms)</th><th>easteregg (ms)</th><th>baseline (ms)</th><th>speedup</th></tr>'
    ]
    for name, skmean, eemean, blmean in stats:
        speedup = skmean / eemean
        table_rows.append(
            '<tr>'
            f'<td>{html.escape(name)}</td>'
            f'<td>{skmean:.3f}</td>'
            f'<td>{eemean:.3f}</td>'
            f'<td>{blmean:.3f}</td>'
            f'<td style="color:{"green" if speedup > 1.0 else "red"}">{speedup:.3f}</td>'
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
<script src="https://cdn.jsdelivr.net/npm/table-sort-js/table-sort.min.js"></script>
</head>
<body>
<h1>{html.escape(args.title)}</h1>
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
