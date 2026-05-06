import argparse
import json
import math
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

FLOAT_RE = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')


@dataclass
class Args:
    report: Path
    apple: bool
    cullmax: int


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
    bl_rt: float
    ee_rt: float
    pixel_diff: float | None
    speedup: float
    pass_counts: dict[str, int]


@dataclass
class Stats:
    total_benchmarks: int
    bl_geomean: float
    ee_geomean: float
    pass_match_counts: dict[str, int]
    most_frequent_pass: str | None
    most_frequent_pass_matches: int
    speedup_count: int
    speedup_with_rewrites_count: int
    slowdown_count: int
    slowdown_with_rewrites_count: int


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

    for json_file in jsons.glob('*.json'):
        name = json_file.stem
        skp = json_file.stem + '.skp'

        nanobench = report / 'nanobench' / (name + '__nanobench.json')
        assert nanobench.exists()
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

        nb_bl_key = f'{name}.skp_1_{width}_{height}'
        nb_ee_key = f'{name}__ee.skp_1_{width}_{height}'
        with nanobench.open('rb') as fp:
            nb_data = json.load(fp)
        nb_bl_data = nb_data['results'][nb_bl_key][backend]
        nb_ee_data = nb_data['results'][nb_ee_key][backend]

        bl_geomean: float = math.exp(
            sum(math.log(x) for x in nb_bl_data['samples']) / len(nb_bl_data['samples'])
        )
        ee_geomean: float = math.exp(
            sum(math.log(x) for x in nb_ee_data['samples']) / len(nb_ee_data['samples'])
        )

        speedup = bl_geomean / ee_geomean
        pixel_diff = run_compare(bl, ee, diff)

        pass_counts = passes_data[skp]

        table.append(
            Row(name, num_cmds, opt_time, bl_geomean, ee_geomean, pixel_diff, speedup, pass_counts)
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

    stats = Stats(
        total_benchmarks=total_benchmarks,
        bl_geomean=math.exp(sum(math.log(row.bl_rt) for row in table) / len(table)),
        ee_geomean=math.exp(sum(math.log(row.ee_rt) for row in table) / len(table)),
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
            {'stats': asdict(gn_stats), 'results': [asdict(row) for row in gn_table]}, indent=2
        )
        + '\n',
        encoding='utf-8',
    )
    (graphite / 'report.json').write_text(
        json.dumps(
            {'stats': asdict(gr_stats), 'results': [asdict(row) for row in gr_table]}, indent=2
        )
        + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
