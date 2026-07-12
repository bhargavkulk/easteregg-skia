#!/usr/bin/env python3
"""Generate LaTeX statistic macros from one backend report."""

import argparse
import json
from pathlib import Path
from typing import Any


STAT_NAMES = (
    'GeoSpeedup',
    'MaxOptTime',
    'MaxSpeedup',
    'NumBench',
    'NumWithSpeedup',
    'NumWithSpeedupMatched',
    'PctSlower',
    'NumWithPixDiff',
    'MinSpeedupMatched',
    'MaxSpeedupMatched',
    'MinSpeedupNoMatched',
    'MaxSpeedupNoMatched',
)
SPEEDUP_NAMES = {
    'GeoSpeedup',
    'MaxSpeedup',
    'MinSpeedupMatched',
    'MaxSpeedupMatched',
    'MinSpeedupNoMatched',
    'MaxSpeedupNoMatched',
}


def parse_args() -> argparse.Namespace:
    """Parse a report path and required macro-name prefix."""
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('prefix')
    return parser.parse_args()


def is_rewritten(result: dict[str, Any]) -> bool:
    """Return whether any optimizer pass matched this benchmark."""
    return any(count > 0 for count in result['pass_counts'].values())


def collect_stats(results: list[dict[str, Any]]) -> dict[str, int | float]:
    """Calculate requested statistics from backend result rows."""
    speedups = [result['speedup'] for result in results]
    matched = [result for result in results if is_rewritten(result)]
    unmatched = [result for result in results if not is_rewritten(result)]
    matched_speedups = [result['speedup'] for result in matched]
    unmatched_speedups = [result['speedup'] for result in unmatched]

    return {
        'GeoSpeedup': sum(speedups) / len(speedups),
        'MaxOptTime': max(result['opt_time'] for result in results),
        'MaxSpeedup': max(speedups),
        'NumBench': len(results),
        'NumWithSpeedup': sum(speedup > 1.0 for speedup in speedups),
        'NumWithSpeedupMatched': sum(
            result['speedup'] > 1.0 and is_rewritten(result) for result in results
        ),
        'PctSlower': 100.0 * sum(speedup < 1.0 for speedup in speedups) / len(results),
        'NumWithPixDiff': sum(result['pixel_diff'] > 0 for result in results),
        'MinSpeedupMatched': min(matched_speedups),
        'MaxSpeedupMatched': max(matched_speedups),
        'MinSpeedupNoMatched': min(unmatched_speedups),
        'MaxSpeedupNoMatched': max(unmatched_speedups),
    }


def format_value(name: str, value: int | float) -> str:
    """Format values with units required by the LaTeX macros."""
    if name.startswith('Num'):
        return str(value)
    if name in SPEEDUP_NAMES:
        return f'{value:.2f}×'
    if name == 'PctSlower':
        return f'{value:.2f}\\%'
    return f'{value:.2f}'


def write_macros(output: Path, prefix: str, stats: dict[str, int | float]) -> None:
    """Write one newcommand definition for each calculated statistic."""
    lines = [
        f'\\newcommand{{\\{prefix}{name}}}{{\\fillin{{{format_value(name, stats[name])}}}\\xspace}}'
        for name in STAT_NAMES
    ]
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> None:
    """Read report JSON and write macros.tex beside it."""
    args = parse_args()
    report = json.loads(args.report.read_text(encoding='utf-8'))
    stats = collect_stats(report['results'])
    write_macros(args.report.parent / 'macros.tex', args.prefix, stats)


if __name__ == '__main__':
    main()
