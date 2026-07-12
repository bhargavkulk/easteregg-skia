import argparse
import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from mako.template import Template

matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


@dataclass
class Args:
    report: Path
    platform: str


def existing_path(value: str):
    path = Path(value)

    if not path.exists():
        raise argparse.ArgumentTypeError('path does not exist')

    return path


def parse_args() -> Args:
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=existing_path)
    parser.add_argument('--platform', required=True)
    return Args(**vars(parser.parse_args()))


def format_name(name: str) -> str:
    return name.replace('__', ' | ').replace('_', ' ')


def format_float(value: float | None, digits: int = 4) -> str:
    if value is None:
        return '-'
    return f'{value:.{digits}f}'.rstrip('0').rstrip('.')


def format_pass_counts(pass_counts: dict[str, int], *, include_zero_counts: bool = False) -> str:
    items = [
        (name, count)
        for name, count in sorted(pass_counts.items())
        if include_zero_counts or count > 0
    ]
    if not items:
        return '-'
    return ' | '.join(f'{name} x{count}' for name, count in items)


def format_percent(value: float) -> str:
    return f'{value:.2f}%'


def format_count_ratio(count: int, denominator: int) -> str:
    if denominator == 0:
        return f'0.00% ({count} / {denominator})'
    return f'{format_percent(100.0 * count / denominator)} ({count} / {denominator})'


def format_run_series(values: list[float]) -> str:
    return ', '.join(format_float(value) for value in values)


def format_confidence_interval(low: float, high: float) -> str:
    return f'[{format_float(low)}, {format_float(high)}]'


def format_latex_macros(macros: dict[str, str]) -> str:
    """Escape macro definitions for a read-only HTML textarea."""
    return html.escape('\n'.join(macros.values()), quote=False)


def format_stats(stats: dict[str, Any]) -> list[dict[str, str]]:
    total_benchmarks = stats['total_benchmarks']
    hottest_pass = stats['most_frequent_pass']
    hottest_pass_matches = stats['most_frequent_pass_matches']
    hottest_pass_display = (
        f'{hottest_pass} x{hottest_pass_matches}' if hottest_pass is not None else '-'
    )
    pass_stat_rows = [
        {'label': f'#{pass_name}', 'value': str(count)}
        for pass_name, count in sorted(stats['pass_match_counts'].items())
    ]

    return [
        {'label': 'Benchmark Count', 'value': str(total_benchmarks)},
        {'label': 'Baseline Geomean', 'value': format_float(stats['bl_geomean'])},
        {'label': 'Easteregg Geomean', 'value': format_float(stats['ee_geomean'])},
        {
            'label': 'Max Total Speedup',
            'value': format_float(stats['max_total_speedup']),
        },
        {
            'label': 'Benchmarks With Speedups',
            'value': format_count_ratio(stats['speedup_count'], total_benchmarks),
        },
        {
            'label': 'Speedups With Rewrites',
            'value': format_count_ratio(stats['speedup_with_rewrites_count'], total_benchmarks),
        },
        {
            'label': 'Benchmarks With Slowdowns',
            'value': format_count_ratio(stats['slowdown_count'], total_benchmarks),
        },
        {
            'label': 'Slowdowns With Rewrites',
            'value': format_count_ratio(stats['slowdown_with_rewrites_count'], total_benchmarks),
        },
        {'label': 'Most Frequent Pass', 'value': hottest_pass_display},
        *pass_stat_rows,
    ]


def collate_stats(stats_by_backend: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    pass_names = sorted(
        {
            pass_name
            for stats in stats_by_backend.values()
            for pass_name in stats['pass_match_counts']
        }
    )
    labels = [
        'Benchmark Count',
        'Baseline Geomean',
        'Easteregg Geomean',
        'Max Total Speedup',
        'Benchmarks With Speedups',
        'Speedups With Rewrites',
        'Benchmarks With Slowdowns',
        'Slowdowns With Rewrites',
        'Most Frequent Pass',
        *(f'#{pass_name}' for pass_name in pass_names),
    ]

    collated_rows: list[dict[str, Any]] = []
    formatted_by_backend = {
        backend: {row['label']: row['value'] for row in format_stats(stats)}
        for backend, stats in stats_by_backend.items()
    }
    for label in labels:
        collated_rows.append(
            {
                'label': label,
                'values': {
                    backend: formatted_rows.get(label, '-')
                    for backend, formatted_rows in formatted_by_backend.items()
                },
            }
        )
    return collated_rows


def format_row(row: dict[str, Any]) -> dict[str, Any]:
    bl_run_series_display = format_run_series(row['bl_run_geomeans'])
    ee_run_series_display = format_run_series(row['ee_run_geomeans'])
    speedup_run_series_display = format_run_series(row['speedup_runs'])
    return {
        **row,
        'display_name': format_name(row['name']),
        'opt_time_display': format_float(row['opt_time']),
        'bl_rt_display': format_float(row['bl_rt']),
        'ee_rt_display': format_float(row['ee_rt']),
        'pixel_diff_display': format_float(row['pixel_diff']),
        'speedup_display': format_float(row['speedup']),
        'speedup_ci_display': format_confidence_interval(
            row['speedup_ci_low'], row['speedup_ci_high']
        ),
        'speedup_class': 'speedup-up' if row['speedup'] > 1 else 'speedup-down' if row['speedup'] < 1 else '',
        'pass_counts_display': format_pass_counts(row['pass_counts']),
        'nanobench_run_count_display': str(row['nanobench_run_count']),
        'bl_rt_title': f"Median of per-run geomeans from {row['nanobench_run_count']} runs: {bl_run_series_display}",
        'ee_rt_title': f"Median of per-run geomeans from {row['nanobench_run_count']} runs: {ee_run_series_display}",
        'speedup_title': f"Median of per-run speedups from {row['nanobench_run_count']} runs: {speedup_run_series_display}",
        'speedup_ci_title': (
            f"95% bootstrap CI from {row['nanobench_run_count']} per-run speedups: "
            f"{speedup_run_series_display}"
        ),
    }


def write_speedup_cdf(
    report_dir: Path, results: list[dict[str, Any]], backend: str, platform: str
) -> tuple[str, str]:
    assets_dir = report_dir / 'assets'
    assets_dir.mkdir(exist_ok=True)

    speedups = sorted(row['speedup'] for row in results)
    cumulative = [(index + 1) / len(speedups) for index in range(len(speedups))]

    fig, ax = plt.subplots(figsize=(5, 5), layout='constrained')
    ax.step(speedups, cumulative, where='post', linewidth=2)
    ax.axvline(1.0, color='red', linestyle='--', linewidth=1)
    ax.set_title(f'Empirical CDF of Speedup\n(on {backend}/{platform}, N = {len(results)})')
    ax.set_xlabel('Speedup (baseline / optimized)')
    ax.set_ylabel('Fraction of benchmarks ≤ x')
    ax.set_ylim(0, 1)
    png_path = assets_dir / 'speedup_cdf.png'
    svg_path = assets_dir / 'speedup_cdf.svg'
    fig.savefig(png_path, dpi=160)
    fig.savefig(svg_path)
    plt.close(fig)
    return f'assets/{png_path.name}', f'assets/{svg_path.name}'


def write_total_speedup_cdf(
    report_dir: Path, results: list[dict[str, Any]], backend: str, platform: str
) -> tuple[str, str]:
    assets_dir = report_dir / 'assets'
    assets_dir.mkdir(exist_ok=True)

    speedups = sorted(row['bl_rt'] / (row['ee_rt'] + row['opt_time']) for row in results)
    cumulative = [(index + 1) / len(speedups) for index in range(len(speedups))]

    fig, ax = plt.subplots(figsize=(5, 5), layout='constrained')
    ax.step(speedups, cumulative, where='post', linewidth=2)
    ax.axvline(1.0, color='red', linestyle='--', linewidth=1)
    ax.set_title(
        f'Empirical CDF of Total Speedup\n(on {backend}/{platform}, N = {len(results)})'
    )
    ax.set_xlabel('Total speedup (baseline / (optimized + optimization time))')
    ax.set_ylabel('Fraction of benchmarks ≤ x')
    ax.set_ylim(0, 1)
    png_path = assets_dir / 'total_speedup_cdf.png'
    svg_path = assets_dir / 'total_speedup_cdf.svg'
    fig.savefig(png_path, dpi=160)
    fig.savefig(svg_path)
    plt.close(fig)
    return f'assets/{png_path.name}', f'assets/{svg_path.name}'


def write_runtime_scatter(
    report_dir: Path, results: list[dict[str, Any]], backend: str, platform: str
) -> tuple[str, str]:
    assets_dir = report_dir / 'assets'
    assets_dir.mkdir(exist_ok=True)

    command_counts = np.asarray([row['num_cmds'] for row in results], dtype=float)
    optimization_times = np.asarray([row['opt_time'] for row in results], dtype=float)

    fig, ax = plt.subplots(figsize=(5, 5), layout='constrained')
    ax.scatter(command_counts, optimization_times, alpha=0.75, s=28)
    if len(command_counts) >= 2:
        slope, intercept = np.polyfit(command_counts, optimization_times, 1)
        xfit = np.linspace(float(np.min(command_counts)), float(np.max(command_counts)), 200)
        yfit = slope * xfit + intercept
        ax.plot(xfit, yfit, color='red', linestyle='--', linewidth=1.5)
    ax.set_title(
        f'Command Count vs Optimization Time\n(on {backend}/{platform}, N = {len(results)})'
    )
    ax.set_xlabel('Number of commands')
    ax.set_ylabel('Optimization time (μs)')
    png_path = assets_dir / 'runtime_scatter.png'
    svg_path = assets_dir / 'runtime_scatter.svg'
    fig.savefig(png_path, dpi=160)
    fig.savefig(svg_path)
    plt.close(fig)
    return f'assets/{png_path.name}', f'assets/{svg_path.name}'


def write_speedup_forest_plot(
    report_dir: Path, results: list[dict[str, Any]], backend: str, platform: str
) -> tuple[str, str]:
    assets_dir = report_dir / 'assets'
    assets_dir.mkdir(exist_ok=True)

    sorted_results = sorted(results, key=lambda row: row['speedup'])
    y_positions = np.arange(len(sorted_results))
    rewrite_mask = np.asarray(
        [any(count > 0 for count in row['pass_counts'].values()) for row in sorted_results],
        dtype=bool,
    )

    fig_height = max(5.0, min(12.0, 0.12 * len(sorted_results) + 1.5))
    fig, ax = plt.subplots(figsize=(8, fig_height), layout='constrained')

    for is_rewrite, color, marker, label in (
        (False, '#4c78a8', 'o', 'No Rewrite'),
        (True, '#f58518', '^', 'Rewrite'),
    ):
        rows = [row for row, flag in zip(sorted_results, rewrite_mask, strict=True) if flag == is_rewrite]
        if not rows:
            continue

        speedups = np.asarray([row['speedup'] for row in rows], dtype=float)
        ci_lows = np.asarray([row['speedup_ci_low'] for row in rows], dtype=float)
        ci_highs = np.asarray([row['speedup_ci_high'] for row in rows], dtype=float)
        y_values = np.asarray(
            [y for y, flag in zip(y_positions, rewrite_mask, strict=True) if flag == is_rewrite],
            dtype=float,
        )
        ax.errorbar(
            speedups,
            y_values,
            xerr=np.vstack([speedups - ci_lows, ci_highs - speedups]),
            fmt=marker,
            markersize=5.5,
            capsize=2,
            linewidth=1.2,
            color=color,
            label=label,
        )

    ax.axvline(1.0, color='red', linestyle='--', linewidth=1)
    ax.set_xscale('log')
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f'{value:g}'))
    ax.set_yticks(y_positions)
    ax.set_title(
        f'Speedup Confidence Intervals\n(on {backend}/{platform}, N = {len(results)})'
    )
    ax.set_xlabel('Speedup (baseline / optimized)')
    ax.set_ylabel('Benchmark')
    ax.set_yticklabels([])
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='x', linestyle=':', linewidth=0.8, alpha=0.7)
    ax.invert_yaxis()
    ax.legend(loc='best')

    png_path = assets_dir / 'speedup_forest.png'
    svg_path = assets_dir / 'speedup_forest.svg'
    fig.savefig(png_path, dpi=160)
    fig.savefig(svg_path)
    plt.close(fig)
    return f'assets/{png_path.name}', f'assets/{svg_path.name}'


def write_report(report_dir: Path, title: str, backend: str, platform: str) -> None:
    template = Template(
        filename=str(Path(__file__).with_name('templates') / 'report_index.html.mako')
    )
    data = read_report_data(report_dir)

    cdf_png_path, cdf_svg_path = write_speedup_cdf(report_dir, data['results'], backend, platform)
    total_cdf_png_path, total_cdf_svg_path = write_total_speedup_cdf(
        report_dir, data['results'], backend, platform
    )
    scatter_png_path, scatter_svg_path = write_runtime_scatter(
        report_dir, data['results'], backend, platform
    )
    forest_png_path, forest_svg_path = write_speedup_forest_plot(
        report_dir, data['results'], backend, platform
    )

    html = template.render(
        title=title,
        stats=format_stats(data['stats']),
        latex_macros=format_latex_macros(data.get('latex_macros', {})),
        speedup_cdf_path=cdf_png_path,
        speedup_cdf_svg_path=cdf_svg_path,
        total_speedup_cdf_path=total_cdf_png_path,
        total_speedup_cdf_svg_path=total_cdf_svg_path,
        runtime_scatter_path=scatter_png_path,
        runtime_scatter_svg_path=scatter_svg_path,
        speedup_forest_path=forest_png_path,
        speedup_forest_svg_path=forest_svg_path,
        results=[format_row(row) for row in data['results']],
    )
    (report_dir / 'index.html').write_text(html, encoding='utf-8')


def read_report_data(report_dir: Path) -> dict[str, Any]:
    with (report_dir / 'report.json').open(encoding='utf-8') as fp:
        return json.load(fp)


def write_summary_report(report_root: Path, platform: str) -> None:
    template = Template(
        filename=str(Path(__file__).with_name('templates') / 'report_summary.html.mako')
    )
    backends = [
        {'label': 'Ganesh', 'path': 'ganesh/index.html'},
        {'label': 'Graphite', 'path': 'graphite/index.html'},
    ]
    stats_by_backend = {
        backend['label']: read_report_data(report_root / backend['label'].lower())['stats']
        for backend in backends
    }
    html = template.render(
        title=f'{platform} Report Summary',
        backends=backends,
        stats=collate_stats(stats_by_backend),
    )
    (report_root / 'index.html').write_text(html, encoding='utf-8')


def main():
    args = parse_args()
    write_report(args.report / 'ganesh', 'Ganesh Report', 'Ganesh', args.platform)
    write_report(args.report / 'graphite', 'Graphite Report', 'Graphite', args.platform)
    write_summary_report(args.report, args.platform)


if __name__ == '__main__':
    main()
