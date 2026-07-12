import argparse
import json
import math
import numpy as np
import re
import statistics
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from scipy.stats import bootstrap

FLOAT_RE = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')


@dataclass
class Args:
    report: Path
    apple: bool
    cullmax: int
    latex_prefix: str


def existing_path(value: str):
    path = Path(value)

    if not path.exists():
        raise argparse.ArgumentTypeError('path does not exist')

    return path


def parse_args() -> Args:
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=existing_path)
    parser.add_argument('--apple', action='store_true')
    parser.add_argument('--cullmax', type=int, default=0)
    parser.add_argument('--latex_prefix', default='latex')

    return Args(**vars(parser.parse_args()))


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
    print(f'[INFO] compare {png1.name} vs {png2.name}: {stderr}')

    match = FLOAT_RE.search(stderr)
    return float(match.group(0)) if match else None


def clamp_dim(dim: list[int], cullmax: int) -> tuple[int, int]:
    width, height = int(dim[0]), int(dim[1])
    if cullmax > 0:
        width = min(width, cullmax)
        height = min(height, cullmax)
    return width, height


# table contentes
# name, #cmds, opt time, bl rt, e rt, speedup, pass counts


@dataclass
class Row:
    name: str
    num_cmds: int
    opt_time: float
    nanobench_run_count: int
    bl_run_geomeans: list[float]
    ee_run_geomeans: list[float]
    speedup_runs: list[float]
    bl_rt: float
    ee_rt: float
    pixel_diff: float | None
    speedup: float
    speedup_ci_low: float
    speedup_ci_high: float
    pass_counts: dict[str, int]


@dataclass
class Stats:
    total_benchmarks: int
    bl_geomean: float
    ee_geomean: float
    max_total_speedup: float
    pass_match_counts: dict[str, int]
    most_frequent_pass: str | None
    most_frequent_pass_matches: int
    speedup_count: int
    speedup_with_rewrites_count: int
    slowdown_count: int
    slowdown_with_rewrites_count: int


LATEX_STAT_NAMES = (
    'GeoSpeedup',
    'MaxOptTime',
    'MaxSpeedup',
    'MaxTotalSpeedup',
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
LATEX_SPEEDUP_NAMES = {
    'GeoSpeedup',
    'MaxSpeedup',
    'MaxTotalSpeedup',
    'MinSpeedupMatched',
    'MaxSpeedupMatched',
    'MinSpeedupNoMatched',
    'MaxSpeedupNoMatched',
}


def geomean(values: list[float]) -> float:
    assert values, 'expected at least one value'
    return math.exp(sum(math.log(x) for x in values) / len(values))


def latex_prefix(backend: str, apple: bool, requested_prefix: str) -> str:
    """Choose a backend/platform prefix unless the caller supplied an override."""
    if requested_prefix != 'latex':
        return requested_prefix
    return f"{backend}{'Apple' if apple else 'Intel'}"


def latex_value(name: str, value: int | float) -> str:
    """Format one statistic with its LaTeX display unit."""
    if name.startswith('Num'):
        return str(value)
    if name in LATEX_SPEEDUP_NAMES:
        return f'{value:.2f}×'
    if name == 'PctSlower':
        return f'{value:.2f}\\%'
    return f'{value:.2f}'


def latex_macros(table: list[Row], prefix: str) -> dict[str, str]:
    """Build LaTeX macro definitions from backend result rows."""
    speedups = [row.speedup for row in table]
    matched = [row for row in table if any(count > 0 for count in row.pass_counts.values())]
    unmatched = [row for row in table if not any(count > 0 for count in row.pass_counts.values())]
    matched_speedups = [row.speedup for row in matched]
    unmatched_speedups = [row.speedup for row in unmatched]
    values: dict[str, int | float] = {
        'GeoSpeedup': sum(speedups) / len(speedups),
        'MaxOptTime': max(row.opt_time for row in table),
        'MaxSpeedup': max(speedups),
        'MaxTotalSpeedup': max(
            row.bl_rt / (row.ee_rt + row.opt_time) for row in table
        ),
        'NumBench': len(table),
        'NumWithSpeedup': sum(speedup > 1.0 for speedup in speedups),
        'NumWithSpeedupMatched': sum(
            row.speedup > 1.0 and any(count > 0 for count in row.pass_counts.values())
            for row in table
        ),
        'PctSlower': 100.0 * sum(speedup < 1.0 for speedup in speedups) / len(table),
        'NumWithPixDiff': sum(row.pixel_diff > 0 for row in table),
        'MinSpeedupMatched': min(matched_speedups),
        'MaxSpeedupMatched': max(matched_speedups),
        'MinSpeedupNoMatched': min(unmatched_speedups),
        'MaxSpeedupNoMatched': max(unmatched_speedups),
    }
    return {
        name: f'\\newcommand{{\\{prefix}{name}}}{{\\fillin{{{latex_value(name, values[name])}}}\\xspace}}'
        for name in LATEX_STAT_NAMES
    }


def speedup_confidence_interval(speedup_runs: list[float]) -> tuple[float, float]:
    assert speedup_runs, 'expected at least one speedup run'

    if len(set(speedup_runs)) == 1:
        value = speedup_runs[0]
        return value, value

    result = bootstrap(
        data=(np.asarray(speedup_runs, dtype=float),),
        statistic=np.median,
        axis=0,
        rng=np.random.default_rng(0),
    )
    return float(result.confidence_interval.low), float(result.confidence_interval.high)


def collect_nanobench_runs(nanobench_root: Path, stem: str) -> list[Path]:
    stem_dir = nanobench_root / stem
    assert stem_dir.exists(), f'missing nanobench run directory for {stem}'
    assert stem_dir.is_dir(), f'{stem_dir} exists but is not a directory'
    run_files = sorted(stem_dir.glob('run_*.json'))
    assert run_files, f'no nanobench runs found in {stem_dir}'
    return run_files


def resolve_nanobench_result(results: dict, variant_name: str, backend: str) -> dict:
    matches = [
        value
        for key, value in results.items()
        if key.startswith(f'{variant_name}_1_') and backend in value
    ]
    assert matches, f'missing nanobench result for {variant_name} [{backend}]'
    assert len(matches) == 1, f'ambiguous nanobench result for {variant_name} [{backend}]'
    return matches[0][backend]


def collate_report(
    report: Path, jsons: Path, optbench: Path, passes: Path, backend: str, cullmax: int
) -> tuple[list[Row], Stats]:
    pngs = report / 'png'
    assert pngs.exists()
    assert pngs.is_dir()

    with optbench.open('rb') as fp:
        optbench_data = json.load(fp)

    with passes.open('rb') as fp:
        passes_data = json.load(fp)

    optdict: dict[str, float] = {}
    for result in optbench_data['results']:
        optdict[result['name']] = (
            math.exp(sum(math.log(x) for x in result['samples_ns']) / len(result['samples_ns']))
            / 1_000_000
        )

    table: list[Row] = []
    nanobench_root = report / 'nanobench'

    for json_file in jsons.glob('*.json'):
        name = json_file.stem
        skp = json_file.stem + '.skp'

        bl = report / 'png' / (name + '.png')
        assert bl.exists()
        ee = report / 'png' / (name + '__ee.png')
        assert ee.exists()
        diff = pngs / (name + '__diff.png')

        with json_file.open('rb') as fp:
            json_data = json.load(fp)

        width, height = clamp_dim(json_data['dim'], cullmax)
        num_cmds = len(json_data['commands'])

        opt_time = optdict[skp]

        bl_run_geomeans: list[float] = []
        ee_run_geomeans: list[float] = []
        speedup_runs: list[float] = []
        nanobench_runs = collect_nanobench_runs(nanobench_root, name)
        for nanobench_run in nanobench_runs:
            with nanobench_run.open('rb') as fp:
                nb_data = json.load(fp)
            nb_bl_data = resolve_nanobench_result(nb_data['results'], f'{name}.skp', backend)
            nb_ee_data = resolve_nanobench_result(nb_data['results'], f'{name}__ee.skp', backend)

            bl_run_geomean = geomean(nb_bl_data['samples'])
            ee_run_geomean = geomean(nb_ee_data['samples'])
            bl_run_geomeans.append(bl_run_geomean)
            ee_run_geomeans.append(ee_run_geomean)
            speedup_runs.append(bl_run_geomean / ee_run_geomean)

        bl_geomean = statistics.median(bl_run_geomeans)
        ee_geomean = statistics.median(ee_run_geomeans)
        speedup = statistics.median(speedup_runs)
        speedup_ci_low, speedup_ci_high = speedup_confidence_interval(speedup_runs)
        pixel_diff = run_compare(bl, ee, diff)

        pass_counts = passes_data[skp]

        table.append(
            Row(
                name=name,
                num_cmds=num_cmds,
                opt_time=opt_time,
                nanobench_run_count=len(nanobench_runs),
                bl_run_geomeans=bl_run_geomeans,
                ee_run_geomeans=ee_run_geomeans,
                speedup_runs=speedup_runs,
                bl_rt=bl_geomean,
                ee_rt=ee_geomean,
                pixel_diff=pixel_diff,
                speedup=speedup,
                speedup_ci_low=speedup_ci_low,
                speedup_ci_high=speedup_ci_high,
                pass_counts=pass_counts,
            )
        )

    total_benchmarks = len(table)
    pass_match_counts: dict[str, int] = {}
    for row in table:
        for pass_name, count in row.pass_counts.items():
            pass_match_counts[pass_name] = pass_match_counts.get(pass_name, 0) + count

    hottest_pass: str | None = None
    hottest_pass_matches = 0
    active_passes = [(name, count) for name, count in pass_match_counts.items() if count > 0]
    if active_passes:
        hottest_pass, hottest_pass_matches = min(
            active_passes,
            key=lambda item: (-item[1], item[0]),
        )

    speedup_count = sum(1 for row in table if row.speedup > 1.0)
    speedup_with_rewrites_count = sum(
        1 for row in table if row.speedup > 1.0 and any(count > 0 for count in row.pass_counts.values())
    )
    slowdown_count = sum(1 for row in table if row.speedup < 1.0)
    slowdown_with_rewrites_count = sum(
        1 for row in table if row.speedup < 1.0 and any(count > 0 for count in row.pass_counts.values())
    )
    max_total_speedup = max(
        row.bl_rt / (row.ee_rt + row.opt_time) for row in table
    )

    stats = Stats(
        total_benchmarks=total_benchmarks,
        bl_geomean=math.exp(sum(math.log(row.bl_rt) for row in table) / len(table)),
        ee_geomean=math.exp(sum(math.log(row.ee_rt) for row in table) / len(table)),
        max_total_speedup=max_total_speedup,
        pass_match_counts=dict(sorted(pass_match_counts.items())),
        most_frequent_pass=hottest_pass,
        most_frequent_pass_matches=hottest_pass_matches,
        speedup_count=speedup_count,
        speedup_with_rewrites_count=speedup_with_rewrites_count,
        slowdown_count=slowdown_count,
        slowdown_with_rewrites_count=slowdown_with_rewrites_count,
    )

    return table, stats


def main():
    args = parse_args()

    optbench = args.report / 'optbench.json'
    assert optbench.exists()

    passes = args.report / 'passes.json'
    assert passes.exists()

    jsons = args.report / 'jsons'
    assert jsons.exists()
    assert jsons.is_dir()

    ganesh = args.report / 'ganesh'
    assert ganesh.exists()
    assert ganesh.is_dir()

    graphite = args.report / 'graphite'
    assert graphite.exists()
    assert graphite.is_dir()

    gn_table, gn_stats = collate_report(ganesh, jsons, optbench, passes, 'gl', args.cullmax)
    gr_table, gr_stats = collate_report(
        graphite,
        jsons,
        optbench,
        passes,
        'grmtl' if args.apple else 'grvk',
        args.cullmax,
    )

    (ganesh / 'report.json').write_text(
        json.dumps(
            {
                'stats': asdict(gn_stats),
                'results': [asdict(row) for row in gn_table],
                'latex_macros': latex_macros(
                    gn_table, latex_prefix('ganesh', args.apple, args.latex_prefix)
                ),
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )
    (graphite / 'report.json').write_text(
        json.dumps(
            {
                'stats': asdict(gr_stats),
                'results': [asdict(row) for row in gr_table],
                'latex_macros': latex_macros(
                    gr_table, latex_prefix('graphite', args.apple, args.latex_prefix)
                ),
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
