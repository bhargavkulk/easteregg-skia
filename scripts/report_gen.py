import argparse
import base64
import html
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats as sp

# TODO, parse the optimzied skps to json as well, and pass that to the table


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate an HTML report for nanobench results.')
    parser.add_argument('--nanobench-dir', type=Path, default=Path('report/nanobench'))
    parser.add_argument('--json-dir', type=Path, default=Path('jsons'))
    parser.add_argument('--png-dir', type=Path, default=Path('report/pngs'))
    parser.add_argument('--output', type=Path, default=Path('report/index.html'))
    parser.add_argument('--optbench-stats', type=Path, default=Path('report/optbench.json'))
    parser.add_argument('--title', type=str, default='Easteregg Benchmark Report')
    return parser.parse_args()


FLOAT_RE = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')


def run_compare(png1: Path, png2: Path, diff: Path) -> float | None:
    diff.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'compare',
        '-metric',
        'AE',
        '-fuzz',
        '5%',  # adjust percentage as needed
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


def format_name(name: str) -> str:
    return name.replace('__', ' | ').replace('_', ' ')


def empirical_cdf_png_base64_logx(ratios: np.ndarray) -> tuple[str, str | None]:
    ratios = np.asarray(ratios, dtype=float)
    ratios = ratios[np.isfinite(ratios) & (ratios > 0)]
    n = int(ratios.size)
    if n == 0:
        return '<p>No speed ratios to plot.</p>', None

    try:
        import matplotlib

        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.ticker import PercentFormatter
    except ImportError:
        return '<p>matplotlib is not available; cannot render the CDF plot.</p>', None

    ratios.sort()
    y = np.arange(1, n + 1, dtype=float) / n

    q_low = float(np.quantile(ratios, 0.05))
    q_high = float(np.quantile(ratios, 0.95))
    x_min = min(q_low, 1.0, float(ratios[0]))
    x_max = max(q_high, 1.0, float(ratios[-1]))
    if x_min == x_max:
        x_min -= 0.05
        x_max += 0.05
    pad = 0.05 * (x_max - x_min)
    x_min -= pad
    x_max += pad

    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=150)
    ax.step(ratios, y, where='post', linewidth=2, color='#1f77b4')
    ax.axvline(1.0, color='#c00', linewidth=1.5, linestyle='--')
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0.0, 1.0)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.grid(True, which='both', color='#eee')
    ax.set_xlabel('Baseline / Optimized')
    ax.set_ylabel('Percent of benchmarks ≤ x')
    ax.set_title(f'Empirical CDF of speed ratios (n={n})', loc='left', fontsize=10)

    fig.tight_layout()
    png_buf = io.BytesIO()
    fig.savefig(png_buf, format='png', bbox_inches='tight')
    svg_buf = io.BytesIO()
    fig.savefig(svg_buf, format='svg', bbox_inches='tight')
    plt.close(fig)

    img_b64 = base64.b64encode(png_buf.getvalue()).decode('ascii')
    svg_text = svg_buf.getvalue().decode('utf-8', errors='replace')

    img_html = (
        '<img alt="Speed ratio CDF plot" style="max-width:100%;height:auto" '
        f'src="data:image/png;base64,{img_b64}"/>'
    )
    return img_html, svg_text


def main() -> None:
    args = parse_args()

    def collect_stats(stem: str, benchmark_name: str):
        bench_file = args.nanobench_dir / f'{stem}__nanobench.json'

        with bench_file.open(encoding='utf-8') as f:
            timing_data = json.load(f)

        gl_data = timing_data['results'][benchmark_name]['gl']
        samples: list[float] = gl_data['samples']

        return np.asarray(samples, dtype=float)

    def geom_mean(times):
        return float(np.exp(np.mean(np.log(times))))

    def pval(your_times, baseline_times):
        your = np.asarray(your_times, dtype=float)
        base = np.asarray(baseline_times, dtype=float)
        t_stat, p_value = sp.ttest_rel(
            np.log(base), np.log(your), alternative='two-sided', nan_policy='raise'
        )
        return p_value

    optbench_by_stem: dict[str, float] = {}
    optbench_timer_overhead_ns: float | None = None
    if args.optbench_stats.is_file():
        with args.optbench_stats.open(encoding='utf-8') as f:
            optbench_data = json.load(f)
        optbench_timer_overhead_ns = optbench_data.get('timer_overhead_ns')
        for entry in optbench_data.get('results', []):
            name = entry.get('name')
            stats = entry.get('stats_ns', {})
            geomean_ns = stats.get('geomean')
            if isinstance(name, str) and isinstance(geomean_ns, (int, float)):
                stem = Path(name).stem
                optbench_by_stem[stem] = float(geomean_ns) / 1_000_000.0

    s: list[tuple[str, float, float, Optional[float], Optional[str], int, float, float | None]] = []

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
        easteregg = f'{base_name}__ee{suffix}'
        baseline = f'{base_name}{suffix}'

        baseline_png = args.png_dir / f'{base_name}.png'
        ee_png = args.png_dir / f'{base_name}__ee.png'
        diff_png = args.png_dir / f'{base_name}__diff.png'

        diff_metric: float | None = None
        diff_href: str | None = None
        if baseline_png.is_file() and ee_png.is_file():
            diff_metric = run_compare(baseline_png, ee_png, diff_png)
            diff_href = f'./pngs/{diff_png.name}'

        eesamples = collect_stats(base_name, easteregg)
        blsamples = collect_stats(base_name, baseline)

        eemean = geom_mean(eesamples)
        blmean = geom_mean(blsamples)

        p = pval(eesamples, blsamples)

        s.append(
            (
                base_name,
                eemean,
                blmean,
                diff_metric,
                diff_href,
                length,
                p,
                optbench_by_stem.get(base_name),
            )
        )

    table_rows = [
        '<tr><th>Benchmark</th><th>#cmds</th><th>easteregg</th><th>baseline</th><th>optbench (ms)</th><th>diff</th><th>speedup</th><th>p</th></tr>'
    ]
    for name, eemean, blmean, diff_metric, diff_href, cmds_len, p, optbench_ms in s:
        speedup = blmean / eemean
        if diff_metric is not None and diff_href:
            diff_display = f'<a href="{html.escape(diff_href)}"><code>{diff_metric:g}</code></a>'
        elif diff_href:
            diff_display = f'<a href="{html.escape(diff_href)}">view</a>'
        else:
            diff_display = '&mdash;'
        if optbench_ms is None:
            optbench_display = '&mdash;'
        else:
            optbench_display = f'<code>{optbench_ms:.3f}</code>'

        table_rows.append(
            '<tr>'
            f'<td>{html.escape(format_name(name))}</td>'
            f'<td style="text-align:end"><a href=./jsons/{name}.json><code>{cmds_len}</code></a></td>'
            f'<td style="text-align:end"><code>{eemean:.3f}</code></td>'
            f'<td style="text-align:end"><code>{blmean:.3f}</code></td>'
            f'<td style="text-align:end">{optbench_display}</td>'
            f'<td style="text-align:end">{diff_display}</td>'
            f'<td style="text-align:end;color:{"green" if speedup > 1.0 else "red"}"><code>{speedup:.3f}</code></td>'
            f'<td style="text-align:end"><code>{p:.4g}</code></td>'
            '</tr>'
        )

    body_content = (
        '\n'.join(table_rows) if s else '<p>No benchmarks with save layers were found.</p>'
    )

    # Per-benchmark speed ratios: baseline_geomean / optimized_geomean (optimized = easteregg).
    ratios = np.asarray([blmean / eemean for _name, eemean, blmean, *_rest in s], dtype=float)
    if isinstance(optbench_timer_overhead_ns, (int, float)):
        overhead_display = f'{optbench_timer_overhead_ns:.2f}'
    else:
        overhead_display = 'n/a'
    cdf_png_html, cdf_svg_text = empirical_cdf_png_base64_logx(ratios)
    cdf_svg_href = None
    if cdf_svg_text:
        assets_dir = args.output.parent / 'assets'
        assets_dir.mkdir(parents=True, exist_ok=True)
        cdf_svg_path = assets_dir / 'speed_ratio_cdf.svg'
        cdf_svg_path.write_text(cdf_svg_text, encoding='utf-8')
        cdf_svg_href = f'./assets/{cdf_svg_path.name}'

    if cdf_svg_href:
        cdf_plot = (
            cdf_png_html
            + '<p style="margin-top:8px">'
            + f'<a class="button" download="{html.escape(Path(cdf_svg_href).name)}" href="{html.escape(cdf_svg_href)}">'
            + 'Download SVG</a>'
            + '</p>'
        )
    else:
        cdf_plot = cdf_png_html

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
    font-size: 16px;
    color: #444;
    padding: 0 10px;
}}
table {{
    border-collapse: collapse;
}}
table th {{
    background-color: #a9a9a9;
}}
table th,
table td {{
    border: 1px solid #444;
    padding: 0 5px;
}}
table tr:hover {{
    background-color: #d3d3d3;
}}
.button {{
    display: inline-block;
    padding: 6px 10px;
    border: 1px solid #444;
    border-radius: 4px;
    background: #f2f2f2;
    color: #222;
    text-decoration: none;
    font-size: 14px;
}}
.button:hover {{
    background: #e6e6e6;
}}
</style>
<script src="https://cdn.jsdelivr.net/npm/table-sort-js/table-sort.min.js"></script>
</head>
<body>
<h1>{html.escape(args.title)}</h1>
<p><em>All time units are in ms</em></p>
<p><em>Optbench timer overhead: {html.escape(overhead_display)} ns</em></p>
<table class="table-sort table-arrows remember-sort">
{body_content}
</table>
<h2>Baseline vs Optimized Speed Ratios</h2>
<p>Each benchmark contributes one point: <code>baseline_geomean / optimized_geomean</code>. Values &gt; 1 mean optimized is faster.</p>
{cdf_plot}
</body>
</html>
"""

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_output, encoding='utf-8')


if __name__ == '__main__':
    main()
