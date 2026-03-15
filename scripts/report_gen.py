import argparse
import base64
import html
import io
import json
import os
import re
import subprocess
import sys
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
    parser.add_argument('--table-json', type=Path, default=None)
    parser.add_argument('--optbench-stats', type=Path, default=Path('report/optbench.json'))
    parser.add_argument('--title', type=str, default='Easteregg Benchmark Report')
    parser.add_argument('--backend', type=str, default='gl')
    parser.add_argument('--backend-name', type=str, default='ganesh-opengl')
    parser.add_argument('--latex-prefix', type=str, default=None)
    parser.add_argument('--skp-dir', type=Path, default=Path('skps'))
    parser.add_argument('--optimizer-stdout', type=Path, default=Path('out/Debug/optimizer_stdout'))
    return parser.parse_args()


FLOAT_RE = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')
PLOT_DPI = 320


def backend_macro_prefix(backend: str) -> str:
    token_map = {
        'graphite': 'gr',
        'ganesh': 'ga',
        'opengl': 'gl',
        'metal': 'metal',
        'vulkan': 'vk',
        'dawn': 'dawn',
        'angle': 'angle',
    }
    tokens = [t for t in re.split(r'[^a-z0-9]+', backend.lower()) if t]
    prefix = ''.join(token_map.get(t, t[:3]) for t in tokens)
    if not prefix:
        prefix = 'backend'
    if prefix[0].isdigit():
        prefix = f'b{prefix}'
    return prefix


def latex_escape_text(value: str) -> str:
    return (
        value.replace('\\', r'\textbackslash{}')
        .replace('{', r'\{')
        .replace('}', r'\}')
        .replace('_', r'\_')
        .replace('%', r'\%')
        .replace('&', r'\&')
        .replace('#', r'\#')
    )


def latex_macro_value(value: object) -> str:
    if value is None:
        return 'n/a'
    if isinstance(value, float):
        return f'{value:.3f}'
    if isinstance(value, int):
        return str(value)
    return latex_escape_text(str(value))


def run_compare(png1: Path, png2: Path, diff: Path) -> float | None:
    diff.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'compare',
        '-metric',
        'AE',
        '-fuzz',
        '1%',  # adjust percentage as needed
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


def resolve_png_path(png_dir: Path, base_name: str, optimized: bool) -> Path | None:
    suffix = '__ee' if optimized else ''

    # Legacy renderer layout.
    legacy = png_dir / f'{base_name}{suffix}.png'
    if legacy.is_file():
        return legacy

    # dm layout (most common config first).
    dm = png_dir / '8888' / 'skp' / f'{base_name}{suffix}.skp.png'
    if dm.is_file():
        return dm

    # dm layout fallback for any config directory.
    matches = sorted(png_dir.glob(f'*/skp/{base_name}{suffix}.skp.png'))
    if matches:
        return matches[0]

    return None


def _rel_href(from_dir: Path, to_path: Path) -> str:
    return os.path.relpath(to_path, from_dir).replace(os.sep, '/')


def write_comparison_page(
    report_index: Path,
    benchmark: str,
    baseline_png: Path,
    optimized_png: Path,
    diff_png: Path | None,
) -> str:
    comparisons_dir = report_index.parent / 'comparisons'
    comparisons_dir.mkdir(parents=True, exist_ok=True)
    page_path = comparisons_dir / f'{benchmark}.html'

    baseline_href = _rel_href(page_path.parent, baseline_png)
    optimized_href = _rel_href(page_path.parent, optimized_png)
    diff_href = _rel_href(page_path.parent, diff_png) if diff_png is not None else None

    if diff_href is not None:
        diff_section = (
            '<div class="panel"><h2>Diff</h2>'
            + f'<p><a class="button" href="{html.escape(diff_href)}">Open PNG</a></p>'
            + f'<img alt="{html.escape(benchmark)} diff" src="{html.escape(diff_href)}"/></div>'
        )
    else:
        diff_section = '<div class="panel"><h2>Diff</h2><p>Not generated.</p></div>'

    page_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(benchmark)} image comparison</title>
<style>
body {{
    margin: 40px auto;
    max-width: 800px;
    line-height: 1.6;
    font-size: 16px;
    color: #444;
    padding: 0 10px;
}}
a {{ color: #0366d6; }}
.grid {{ display: grid; grid-template-columns: repeat(3, minmax(240px, 1fr)); gap: 16px; }}
.panel {{ border: 1px solid #444; padding: 10px; background: #fff; }}
.panel h2 {{ margin-top: 0; font-size: 16px; }}
img {{ max-width: 100%; height: auto; border: 1px solid #444; background: white; }}
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
@media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<p><a class="button" href="{html.escape(_rel_href(page_path.parent, report_index))}">← Back to report</a></p>
<h1>{html.escape(benchmark)}</h1>
<div class="grid">
  <div class="panel">
    <h2>Pre (Baseline)</h2>
    <p><a class="button" href="{html.escape(baseline_href)}">Open PNG</a></p>
    <img alt="{html.escape(benchmark)} baseline" src="{html.escape(baseline_href)}"/>
  </div>
  <div class="panel">
    <h2>Post (Optimized)</h2>
    <p><a class="button" href="{html.escape(optimized_href)}">Open PNG</a></p>
    <img alt="{html.escape(benchmark)} optimized" src="{html.escape(optimized_href)}"/>
  </div>
  {diff_section}
</div>
</body>
</html>
"""
    page_path.write_text(page_html, encoding='utf-8')
    return _rel_href(report_index.parent, page_path)


def empirical_cdf_png_base64_logx(
    ratios: np.ndarray,
    backend_name: str,
    title_prefix: str,
    line_label: str,
    x_label: str,
    line_color: str = '#1f77b4',
    line_style: str = '-',
) -> tuple[str, str | None]:
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

    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=PLOT_DPI)
    ax.step(
        ratios,
        y,
        where='post',
        linewidth=2,
        color=line_color,
        linestyle=line_style,
        label=f'{line_label} (n={n})',
        zorder=3,
    )
    ax.axvline(1.0, color='#c00', linewidth=1.5, linestyle='--', zorder=1)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0.0, 1.0)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_xlabel(x_label)
    ax.set_ylabel('Benchmarks at or below this speedup')
    ax.set_title(
        f'{title_prefix}\n(on {backend_name}, n={n})',
        loc='center',
        x=0.5,
        ha='center',
        fontsize=10,
    )
    fig.tight_layout()
    png_buf = io.BytesIO()
    fig.savefig(png_buf, format='png', dpi=PLOT_DPI, bbox_inches='tight')
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


def opt_time_vs_commands_png_base64(
    command_counts: np.ndarray, opt_times_ms: np.ndarray, backend_name: str
) -> tuple[str, str | None]:
    x = np.asarray(command_counts, dtype=float)
    y = np.asarray(opt_times_ms, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y >= 0)
    x = x[valid]
    y = y[valid]
    n = int(x.size)
    if n == 0:
        return '<p>No opt-time data to plot.</p>', None

    try:
        import matplotlib

        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return '<p>matplotlib is not available; cannot render the opt-time plot.</p>', None

    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=PLOT_DPI)
    ax.scatter(x, y, s=14, alpha=0.8, color='#1f77b4')

    if n >= 2:
        slope, intercept = np.polyfit(x, y, 1)
        xfit = np.linspace(float(np.min(x)), float(np.max(x)), 200)
        yfit = slope * xfit + intercept
        ax.plot(xfit, yfit, linewidth=1.8, color='#c00', linestyle='--')

    ax.set_xlabel('No. of commands in SKP')
    ax.set_ylabel('Optimization Time (ms)')
    ax.set_title(
        f'Optimization Time vs Program Size\n(on {backend_name}, n={n})',
        loc='center',
        x=0.5,
        ha='center',
        fontsize=10,
    )

    fig.tight_layout()
    png_buf = io.BytesIO()
    fig.savefig(png_buf, format='png', dpi=PLOT_DPI, bbox_inches='tight')
    svg_buf = io.BytesIO()
    fig.savefig(svg_buf, format='svg', bbox_inches='tight')
    plt.close(fig)

    img_b64 = base64.b64encode(png_buf.getvalue()).decode('ascii')
    svg_text = svg_buf.getvalue().decode('utf-8', errors='replace')

    img_html = (
        '<img alt="OptTime vs command count plot" style="max-width:100%;height:auto" '
        f'src="data:image/png;base64,{img_b64}"/>'
    )
    return img_html, svg_text


def baseline_vs_optimized_speed_xy_png_base64(
    baseline_ms: np.ndarray, optimized_ms: np.ndarray, backend_name: str
) -> tuple[str, str | None]:
    base = np.asarray(baseline_ms, dtype=float)
    opt = np.asarray(optimized_ms, dtype=float)
    valid = np.isfinite(base) & np.isfinite(opt) & (base > 0) & (opt > 0)
    base = base[valid]
    opt = opt[valid]
    n = int(base.size)
    if n == 0:
        return '<p>No baseline/optimized speed pairs to plot.</p>', None

    try:
        import matplotlib

        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return '<p>matplotlib is not available; cannot render the speed-pair plot.</p>', None

    x = base
    y = opt

    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=PLOT_DPI)
    ax.scatter(x, y, s=14, alpha=0.8, color='#1f77b4', zorder=3)

    lo = float(min(np.min(x), np.min(y)))
    hi = float(max(np.max(x), np.max(y)))
    if lo == hi:
        pad = 0.05 * lo if lo > 0 else 0.05
        lo -= pad
        hi += pad
    ax.plot([lo, hi], [lo, hi], linewidth=1.5, color='#c00', linestyle='--', zorder=1)

    # Constant-factor speedup guide: y = x / 2 (optimized is 2x faster than baseline).
    x_half_start = max(lo, 2.0 * lo)
    x_half_end = hi
    if x_half_start <= x_half_end:
        ax.plot(
            [x_half_start, x_half_end],
            [x_half_start / 2.0, x_half_end / 2.0],
            linewidth=1.3,
            color='#808080',
            linestyle='--',
            zorder=1,
        )

    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xscale('log', base=2)
    ax.set_yscale('log', base=2)
    ax.set_aspect('equal', adjustable='box')

    ax.set_xlabel('Baseline time (ms)')
    ax.set_ylabel('Optimized time (ms)')
    ax.set_title(
        f'Baseline vs Optimized time pairs\n(on {backend_name}, n={n})',
        loc='center',
        x=0.5,
        ha='center',
        fontsize=10,
    )

    fig.tight_layout()
    png_buf = io.BytesIO()
    fig.savefig(png_buf, format='png', dpi=PLOT_DPI, bbox_inches='tight')
    svg_buf = io.BytesIO()
    fig.savefig(svg_buf, format='svg', bbox_inches='tight')
    plt.close(fig)

    img_b64 = base64.b64encode(png_buf.getvalue()).decode('ascii')
    svg_text = svg_buf.getvalue().decode('utf-8', errors='replace')

    img_html = (
        '<img alt="Baseline vs optimized time pairs plot" style="max-width:100%;height:auto" '
        f'src="data:image/png;base64,{img_b64}"/>'
    )
    return img_html, svg_text


def run_optimizer_stdout(binary: Path, skp: Path) -> tuple[Optional[int], dict[str, int]]:
    if not binary.is_file() or not skp.is_file():
        return None, {}

    cmd = [str(binary), '--input', str(skp)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        print(
            f'optimizer_stdout failed for {skp} ({result.returncode}): {stderr}',
            file=sys.stderr,
        )
        return None, {}

    output = result.stdout.strip()
    if not output:
        return None, {}

    # New format: JSON object with total and per-pass counts.
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict):
            total_matches = payload.get('total_matches')
            if not isinstance(total_matches, int):
                total_matches = None

            pass_counts_raw = payload.get('passes')
            pass_counts: dict[str, int] = {}
            if isinstance(pass_counts_raw, dict):
                for name, count in pass_counts_raw.items():
                    if isinstance(name, str) and isinstance(count, int):
                        pass_counts[name] = count

            return total_matches, pass_counts

    # Legacy format: a single integer on stdout.
    match = re.search(r'\d+', output)
    return (int(match.group(0)) if match else None), {}


def format_pass_counts(pass_counts: dict[str, int]) -> str:
    if not pass_counts:
        return '&mdash;'

    pieces = [f'{name}:{count}' for name, count in sorted(pass_counts.items())]
    return f'<code>{html.escape(", ".join(pieces))}</code>'


def main() -> None:
    args = parse_args()

    def collect_stats(stem: str, benchmark_name: str) -> Optional[np.ndarray]:
        bench_file = args.nanobench_dir / f'{stem}__nanobench.json'

        with bench_file.open(encoding='utf-8') as f:
            timing_data = json.load(f)

        results = timing_data.get('results', {})
        bench_result = results.get(benchmark_name)
        if not isinstance(bench_result, dict):
            print(
                f'skipping {stem}: benchmark key not found in nanobench file ({benchmark_name})',
                file=sys.stderr,
            )
            return None

        backend_data = bench_result.get(args.backend)
        if not isinstance(backend_data, dict):
            print(
                f'skipping {stem}: backend {args.backend!r} missing in nanobench file',
                file=sys.stderr,
            )
            return None

        samples = backend_data.get('samples')
        if not isinstance(samples, list) or not samples:
            print(
                f'skipping {stem}: no samples for backend {args.backend!r}',
                file=sys.stderr,
            )
            return None

        return np.asarray(samples, dtype=float)

    def geom_mean(times):
        return float(np.exp(np.mean(np.log(times))))

    def pval(your_times, baseline_times):
        your = np.asarray(your_times, dtype=float)
        base = np.asarray(baseline_times, dtype=float)
        t_stat, p_value = sp.ttest_ind(
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

    s: list[
        tuple[
            str,
            float,
            float,
            Optional[float],
            Optional[float],
            Optional[str],
            int,
            float,
            Optional[int],
            dict[str, int],
        ]
    ] = []

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

        baseline_png = resolve_png_path(args.png_dir, base_name, optimized=False)
        ee_png = resolve_png_path(args.png_dir, base_name, optimized=True)
        diff_png = args.png_dir / f'{base_name}__diff.png'

        diff_metric: float | None = None
        diff_href: str | None = None
        if baseline_png is not None and ee_png is not None:
            diff_metric = run_compare(baseline_png, ee_png, diff_png)
            generated_diff_png = diff_png if diff_png.is_file() else None
            diff_href = write_comparison_page(
                args.output,
                base_name,
                baseline_png,
                ee_png,
                generated_diff_png,
            )

        eesamples = collect_stats(base_name, easteregg)
        blsamples = collect_stats(base_name, baseline)
        if eesamples is None or blsamples is None:
            continue

        eemean = geom_mean(eesamples)
        blmean = geom_mean(blsamples)

        p = pval(eesamples, blsamples)

        opt_geomean = optbench_by_stem.get(base_name)
        skp_path = args.skp_dir / f'{base_name}.skp'
        matches, pass_counts = run_optimizer_stdout(args.optimizer_stdout, skp_path)
        s.append(
            (
                base_name,
                eemean,
                blmean,
                opt_geomean,
                diff_metric,
                diff_href,
                length,
                p,
                matches,
                pass_counts,
            )
        )

    table_rows = [
        '<tr><th>Benchmark</th><th>#cmds</th><th>Easteregg</th><th>Baseline</th><th>OptTime</th><th>Diff</th><th>Speedup</th><th>#matches</th><th>Pass Counts</th><th>p</th></tr>'
    ]
    for (
        name,
        eemean,
        blmean,
        opt_geomean,
        diff_metric,
        diff_href,
        cmds_len,
        p,
        matches,
        pass_counts,
    ) in s:
        speedup = blmean / eemean
        if diff_metric is not None and diff_href:
            diff_display = f'<a href="{html.escape(diff_href)}"><code>{diff_metric:g}</code></a>'
        elif diff_href:
            diff_display = f'<a href="{html.escape(diff_href)}">view</a>'
        else:
            diff_display = '&mdash;'

        if isinstance(opt_geomean, (int, float)):
            opt_geomean_display = f'<code>{opt_geomean:.3f}</code>'
        else:
            opt_geomean_display = '&mdash;'

        if isinstance(matches, int):
            matches_display = f'<code>{matches}</code>'
        else:
            matches_display = '&mdash;'
        pass_counts_display = format_pass_counts(pass_counts)

        table_rows.append(
            '<tr>'
            f'<td>{html.escape(format_name(name))}</td>'
            f'<td style="text-align:end"><a href=./jsons/{name}.json><code>{cmds_len}</code></a></td>'
            f'<td style="text-align:end"><code>{eemean:.3f}</code></td>'
            f'<td style="text-align:end"><code>{blmean:.3f}</code></td>'
            f'<td style="text-align:end">{opt_geomean_display}</td>'
            f'<td style="text-align:end">{diff_display}</td>'
            f'<td style="text-align:end;color:{"green" if speedup > 1.0 else "red"}"><code>{speedup:.3f}</code></td>'
            f'<td style="text-align:end">{matches_display}</td>'
            f'<td>{pass_counts_display}</td>'
            f'<td style="text-align:end"><code>{p:.4g}</code></td>'
            '</tr>'
        )

    body_content = (
        '\n'.join(table_rows) if s else '<p>No benchmarks with save layers were found.</p>'
    )
    benchmark_count = len(s)

    table_json = None
    if args.table_json is not None:
        columns = [
            {'key': 'benchmark', 'label': 'Benchmark'},
            {'key': 'cmds', 'label': '#cmds'},
            {'key': 'easteregg_ms', 'label': 'Easteregg'},
            {'key': 'baseline_ms', 'label': 'Baseline'},
            {'key': 'opt_time_ms', 'label': 'OptTime'},
            {'key': 'diff_metric', 'label': 'Diff'},
            {'key': 'speedup', 'label': 'Speedup'},
            {'key': 'matches', 'label': '#matches'},
            {'key': 'pass_counts', 'label': 'Pass Counts'},
            {'key': 'p_value', 'label': 'p'},
        ]
        rows = []
        for (
            name,
            eemean,
            blmean,
            opt_geomean,
            diff_metric,
            diff_href,
            cmds_len,
            p,
            matches,
            pass_counts,
        ) in s:
            rows.append(
                {
                    'benchmark': format_name(name),
                    'benchmark_id': name,
                    'commands_json': f'./jsons/{name}.json',
                    'cmds': cmds_len,
                    'easteregg_ms': eemean,
                    'baseline_ms': blmean,
                    'opt_time_ms': opt_geomean,
                    'diff_metric': diff_metric,
                    'diff_href': diff_href,
                    'speedup': blmean / eemean,
                    'matches': matches,
                    'pass_counts': pass_counts,
                    'p_value': p,
                }
            )
        table_json = {
            'title': args.title,
            'backend': args.backend,
            'units': {'time': 'ms', 'speedup': 'ratio', 'p_value': 'unitless'},
            'columns': columns,
            'rows': rows,
        }

    # Per-benchmark speed ratios: baseline_geomean / optimized_geomean (optimized = easteregg).
    ratios = np.asarray([blmean / eemean for _name, eemean, blmean, *_rest in s], dtype=float)
    total_ratios = np.asarray(
        [
            (row[2] / (row[1] + row[3]))
            for row in s
            if isinstance(row[3], (int, float)) and np.isfinite(row[3]) and (row[1] + row[3]) > 0
        ],
        dtype=float,
    )
    backend_prefix = args.latex_prefix if args.latex_prefix is not None else backend_macro_prefix(args.backend)
    if ratios.size > 0:
        pct_speedup_gt_one = 100.0 * float(np.mean(ratios > 1.0))
        speedup_gt_one_display = f'{pct_speedup_gt_one:.1f}%'
        pct_slowdowns = 100.0 * float(np.mean(ratios < 1.0))
        slowdowns_display = f'{pct_slowdowns:.1f}%'
        max_speedup = float(np.max(ratios))
        max_speedup_display = f'{max_speedup:.3f}x'
    else:
        pct_speedup_gt_one = None
        pct_slowdowns = None
        max_speedup = None
        speedup_gt_one_display = 'n/a'
        slowdowns_display = 'n/a'
        max_speedup_display = 'n/a'

    slowdown_rows = [row for row in s if (row[2] / row[1]) < 1.0]
    slowdown_count = len(slowdown_rows)
    slowdown_no_match_count = sum(1 for row in slowdown_rows if row[8] == 0)
    if slowdown_count > 0:
        pct_slowdown_no_matches = 100.0 * slowdown_no_match_count / slowdown_count
        slowdown_no_matches_fraction_display = (
            f'{slowdown_no_match_count}/{slowdown_count} ({pct_slowdown_no_matches:.1f}%)'
        )
    else:
        pct_slowdown_no_matches = None
        slowdown_no_matches_fraction_display = 'n/a'

    speedup_rows = [row for row in s if (row[2] / row[1]) > 1.0]
    speedup_count = len(speedup_rows)
    speedup_with_match_count = sum(
        1 for row in speedup_rows if isinstance(row[8], int) and row[8] > 0
    )
    speedup_without_match_count = sum(1 for row in speedup_rows if row[8] == 0)
    speedup_with_match_values = [
        (row[2] / row[1]) for row in speedup_rows if isinstance(row[8], int) and row[8] > 0
    ]
    speedup_without_match_values = [(row[2] / row[1]) for row in speedup_rows if row[8] == 0]
    if benchmark_count > 0:
        pct_benchmarks_with_matches_and_speedup = 100.0 * speedup_with_match_count / benchmark_count
        benchmarks_with_matches_and_speedup_display = (
            f'{speedup_with_match_count}/{benchmark_count} '
            f'({pct_benchmarks_with_matches_and_speedup:.1f}%)'
        )
    else:
        pct_benchmarks_with_matches_and_speedup = None
        benchmarks_with_matches_and_speedup_display = 'n/a'
    if speedup_count > 0:
        pct_speedup_with_matches = 100.0 * speedup_with_match_count / speedup_count
        pct_speedup_without_matches = 100.0 * speedup_without_match_count / speedup_count
        speedup_with_matches_fraction_display = (
            f'{speedup_with_match_count}/{speedup_count} ({pct_speedup_with_matches:.1f}%)'
        )
        speedup_without_matches_fraction_display = (
            f'{speedup_without_match_count}/{speedup_count} ({pct_speedup_without_matches:.1f}%)'
        )
    else:
        pct_speedup_with_matches = None
        pct_speedup_without_matches = None
        speedup_with_matches_fraction_display = 'n/a'
        speedup_without_matches_fraction_display = 'n/a'
    if speedup_with_match_values:
        speedup_with_matches_min = min(speedup_with_match_values)
        speedup_with_matches_max = max(speedup_with_match_values)
        speedup_with_matches_range_display = (
            f'{speedup_with_matches_min:.3f}x to {speedup_with_matches_max:.3f}x'
        )
    else:
        speedup_with_matches_min = None
        speedup_with_matches_max = None
        speedup_with_matches_range_display = 'n/a'
    if speedup_without_match_values:
        speedup_without_matches_min = min(speedup_without_match_values)
        speedup_without_matches_max = max(speedup_without_match_values)
        speedup_without_matches_range_display = (
            f'{speedup_without_matches_min:.3f}x to {speedup_without_matches_max:.3f}x'
        )
    else:
        speedup_without_matches_min = None
        speedup_without_matches_max = None
        speedup_without_matches_range_display = 'n/a'

    non_slowdown_nonzero_match_rows = [
        row for row in speedup_rows if isinstance(row[8], int) and row[8] > 0
    ]
    if non_slowdown_nonzero_match_rows:
        min_nonzero_matches = min(int(row[8]) for row in non_slowdown_nonzero_match_rows)
        min_speedup_at_min_matches = min(
            (row[2] / row[1])
            for row in non_slowdown_nonzero_match_rows
            if row[8] == min_nonzero_matches
        )
        min_speedup_for_min_nonzero_matches_display = (
            f'matches={min_nonzero_matches}, min speedup={min_speedup_at_min_matches:.3f}x'
        )
    else:
        min_nonzero_matches = None
        min_speedup_at_min_matches = None
        min_speedup_for_min_nonzero_matches_display = 'n/a'

    pass_totals: dict[str, int] = {}
    for row in s:
        for pass_name, count in row[9].items():
            if count > 0:
                pass_totals[pass_name] = pass_totals.get(pass_name, 0) + count

    if pass_totals:
        most_common_name, most_common_count = max(
            sorted(pass_totals.items()), key=lambda item: item[1]
        )
        total_firings = sum(pass_totals.values())
        pct_most_common_optimization = 100.0 * most_common_count / total_firings
        most_common_optimization_display = (
            f'{most_common_name} ({most_common_count}/{total_firings}, '
            f'{pct_most_common_optimization:.1f}%)'
        )
    else:
        most_common_name = None
        most_common_count = None
        total_firings = None
        pct_most_common_optimization = None
        most_common_optimization_display = 'n/a'

    if isinstance(optbench_timer_overhead_ns, (int, float)):
        timer_overhead_ns = float(optbench_timer_overhead_ns)
        overhead_display = f'{optbench_timer_overhead_ns:.2f}'
    else:
        timer_overhead_ns = None
        overhead_display = 'n/a'
    latex_macros = [
        ('numbench', benchmark_count),
        ('numspeed', speedup_count),
        ('numslow', slowdown_count),
        ('pctspeed', pct_speedup_gt_one),
        ('pctslow', pct_slowdowns),
        ('numspmatch', speedup_with_match_count),
        ('numspnomatch', speedup_without_match_count),
        ('pctspmatch', pct_speedup_with_matches),
        ('pctspnomatch', pct_speedup_without_matches),
        ('numbenchspmatch', speedup_with_match_count),
        ('pctbenchspmatch', pct_benchmarks_with_matches_and_speedup),
        ('spmatchmin', speedup_with_matches_min),
        ('spmatchmax', speedup_with_matches_max),
        ('spnomatchmin', speedup_without_matches_min),
        ('spnomatchmax', speedup_without_matches_max),
        ('numslownomatch', slowdown_no_match_count),
        ('pctslownomatch', pct_slowdown_no_matches),
        ('minmatch', min_nonzero_matches),
        ('minspminmatch', min_speedup_at_min_matches),
        ('maxspeed', max_speedup),
        ('topoptname', most_common_name),
        ('topoptnum', most_common_count),
        ('topopttotal', total_firings),
        ('topoptpct', pct_most_common_optimization),
        ('timerovhns', timer_overhead_ns),
    ]
    speedup_macro_names = {
        'spmatchmin',
        'spmatchmax',
        'spnomatchmin',
        'spnomatchmax',
        'minspminmatch',
        'maxspeed',
    }
    percentage_macro_names = {
        'pctspeed',
        'pctslow',
        'pctspmatch',
        'pctspnomatch',
        'pctbenchspmatch',
        'pctslownomatch',
        'topoptpct',
    }

    def latex_macro_suffix(name: str, value: object) -> str:
        if value is None:
            return ''
        suffix = ''
        if name in speedup_macro_names:
            suffix += r'\texttimes'
        if name in percentage_macro_names:
            suffix += r'\%'
        return suffix

    latex_macros_text = '\n'.join(
        f'\\newcommand{{\\{backend_prefix}{name}}}'
        f'{{\\fillin{{{latex_macro_value(value)}{latex_macro_suffix(name, value)}}}\\xspace}}'
        for name, value in latex_macros
    )
    cdf_png_html, cdf_svg_text = empirical_cdf_png_base64_logx(
        ratios,
        args.backend_name,
        'Empirical CDF of speedup',
        'Baseline / Optimized',
        'Baseline / Optimized',
        line_color='#1f77b4',
        line_style='-',
    )
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
    cdf_total_png_html, cdf_total_svg_text = empirical_cdf_png_base64_logx(
        total_ratios,
        args.backend_name,
        'Empirical CDF of total speedup',
        'Baseline / (Optimized + OptTime)',
        'Baseline / (Optimized + Optimization Time)',
        line_color='#1f77b4',
        line_style='-',
    )
    cdf_total_svg_href = None
    if cdf_total_svg_text:
        assets_dir = args.output.parent / 'assets'
        assets_dir.mkdir(parents=True, exist_ok=True)
        cdf_total_svg_path = assets_dir / 'speed_ratio_total_cdf.svg'
        cdf_total_svg_path.write_text(cdf_total_svg_text, encoding='utf-8')
        cdf_total_svg_href = f'./assets/{cdf_total_svg_path.name}'

    if cdf_total_svg_href:
        cdf_total_plot = (
            cdf_total_png_html
            + '<p style="margin-top:8px">'
            + f'<a class="button" download="{html.escape(Path(cdf_total_svg_href).name)}" href="{html.escape(cdf_total_svg_href)}">'
            + 'Download SVG</a>'
            + '</p>'
        )
    else:
        cdf_total_plot = cdf_total_png_html

    baseline_times = np.asarray([row[2] for row in s], dtype=float)
    optimized_times = np.asarray([row[1] for row in s], dtype=float)
    speed_pair_png_html, speed_pair_svg_text = baseline_vs_optimized_speed_xy_png_base64(
        baseline_times, optimized_times, args.backend_name
    )
    speed_pair_svg_href = None
    if speed_pair_svg_text:
        assets_dir = args.output.parent / 'assets'
        assets_dir.mkdir(parents=True, exist_ok=True)
        speed_pair_svg_path = assets_dir / 'baseline_vs_optimized_speed_xy.svg'
        speed_pair_svg_path.write_text(speed_pair_svg_text, encoding='utf-8')
        speed_pair_svg_href = f'./assets/{speed_pair_svg_path.name}'

    if speed_pair_svg_href:
        speed_pair_plot = (
            speed_pair_png_html
            + '<p style="margin-top:8px">'
            + f'<a class="button" download="{html.escape(Path(speed_pair_svg_href).name)}" href="{html.escape(speed_pair_svg_href)}">'
            + 'Download SVG</a>'
            + '</p>'
        )
    else:
        speed_pair_plot = speed_pair_png_html

    cmd_counts = np.asarray([row[6] for row in s], dtype=float)
    opt_times = np.asarray(
        [(row[3] if isinstance(row[3], (int, float)) else np.nan) for row in s],
        dtype=float,
    )
    opt_time_png_html, opt_time_svg_text = opt_time_vs_commands_png_base64(
        cmd_counts, opt_times, args.backend_name
    )
    opt_time_svg_href = None
    if opt_time_svg_text:
        assets_dir = args.output.parent / 'assets'
        assets_dir.mkdir(parents=True, exist_ok=True)
        opt_time_svg_path = assets_dir / 'opt_time_vs_commands.svg'
        opt_time_svg_path.write_text(opt_time_svg_text, encoding='utf-8')
        opt_time_svg_href = f'./assets/{opt_time_svg_path.name}'

    if opt_time_svg_href:
        opt_time_plot = (
            opt_time_png_html
            + '<p style="margin-top:8px">'
            + f'<a class="button" download="{html.escape(Path(opt_time_svg_href).name)}" href="{html.escape(opt_time_svg_href)}">'
            + 'Download SVG</a>'
            + '</p>'
        )
    else:
        opt_time_plot = opt_time_png_html

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
.stats-box {{
    border: 1px solid #444;
    background: #f8f8f8;
    padding: 10px 12px;
    margin: 12px 0 16px 0;
}}
.stats-box h2 {{
    margin: 0 0 8px 0;
    font-size: 18px;
}}
.stats-box ul {{
    margin: 0;
    padding-left: 22px;
}}
.stats-box h3 {{
    margin: 10px 0 6px 0;
    font-size: 14px;
}}
.latex-macros {{
    width: 100%;
    min-height: 220px;
    box-sizing: border-box;
    font-family: monospace;
    font-size: 12px;
    line-height: 1.4;
}}
</style>
<script src="https://cdn.jsdelivr.net/npm/table-sort-js/table-sort.min.js"></script>
</head>
<body>
<h1>{html.escape(args.title)}</h1>
<p><strong>Benchmarks:</strong> <code>{benchmark_count}</code></p>
<p><em>All time units are in ms</em></p>
<p><em>Optbench timer overhead: {html.escape(overhead_display)} ns</em></p>
<div class="stats-box">
  <h2>Stats</h2>
  <ul>
    <li>Overall: speedups (&gt; 1.0) <code>{html.escape(speedup_gt_one_display)}</code>; slowdowns (&lt; 1.0) <code>{html.escape(slowdowns_display)}</code>.</li>
    <li>Matched speedups: all benchmarks <code>{html.escape(benchmarks_with_matches_and_speedup_display)}</code>; among speedups <code>{html.escape(speedup_with_matches_fraction_display)}</code>.</li>
    <li>Unmatched speedups (among speedups): <code>{html.escape(speedup_without_matches_fraction_display)}</code>.</li>
    <li>Speedup ranges: matched <code>{html.escape(speedup_with_matches_range_display)}</code>; unmatched <code>{html.escape(speedup_without_matches_range_display)}</code>.</li>
    <li>Slowdowns with no matches: <code>{html.escape(slowdown_no_matches_fraction_display)}</code>.</li>
    <li>Matched-speedup floor: <code>{html.escape(min_speedup_for_min_nonzero_matches_display)}</code>.</li>
    <li>Most common optimization: <code>{html.escape(most_common_optimization_display)}</code>.</li>
    <li>Maximum speedup: <code>{html.escape(max_speedup_display)}</code>.</li>
  </ul>
  <h3>LaTeX Macros</h3>
  <textarea class="latex-macros" readonly>{html.escape(latex_macros_text)}</textarea>
</div>
<table class="table-sort table-arrows remember-sort">
{body_content}
</table>
<h2>Baseline vs Optimized Speed Ratios</h2>
<p>Each benchmark contributes one point: <code>baseline_geomean / optimized_geomean</code>. Values &gt; 1 mean optimized is faster.</p>
{cdf_plot}
<h2>Baseline vs (Optimized + OptTime) Speed Ratios</h2>
<p>Each benchmark contributes one point: <code>baseline_geomean / (optimized_geomean + opt_time_ms)</code>. Values &gt; 1 include optimization-time overhead and still beat baseline end-to-end.</p>
{cdf_total_plot}
<h2>Baseline vs Optimized Time</h2>
<p>Each benchmark contributes one point: x = baseline time (ms), y = optimized time (ms). Points below <code>y = x</code> indicate optimized is faster.</p>
{speed_pair_plot}
<h2>OptTime vs Command Count</h2>
<p>Each point is one benchmark: x-axis is command count from metadata, y-axis is optbench optimization time in ms.</p>
{opt_time_plot}
</body>
</html>
"""

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_output, encoding='utf-8')
    if table_json is not None and args.table_json is not None:
        args.table_json.parent.mkdir(parents=True, exist_ok=True)
        args.table_json.write_text(json.dumps(table_json, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
