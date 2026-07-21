import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Args:
    skp_dir: Path
    json_dir: Path
    opt_dir: Path
    report_dir: Path
    samples: int
    nanobench_runs: int
    backend: str
    cullmax: int
    resume: bool


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description='Run optimizer + nanobench for every SKP.')
    parser.add_argument('skp_dir', type=Path)
    parser.add_argument('json_dir', type=Path)
    parser.add_argument('opt_dir', type=Path)
    parser.add_argument('report_dir', type=Path)
    parser.add_argument('--samples', type=int, default=100)
    parser.add_argument('--nanobench-runs', type=int, default=25)
    parser.add_argument('--backend', default='gl')
    parser.add_argument('--cullmax', type=int, default=0)
    parser.add_argument(
        '--resume',
        action='store_true',
        help='skip benchmarks with complete reports and restart incomplete benchmarks',
    )
    return Args(**vars(parser.parse_args()))


def clamp_dim(dim: tuple[int, int], cullmax: int) -> tuple[int, int]:
    if cullmax <= 0:
        return dim
    return min(dim[0], cullmax), min(dim[1], cullmax)


def read_skp_metadata(json_dir: Path, stem, cullmax: int) -> tuple[str, bool]:
    json_path = json_dir / f'{stem}.json'

    assert json_path.exists(), f'{json_path} does not exist'

    with json_path.open(encoding='utf-8') as fp:
        data = json.load(fp)

    dim: tuple[int, int] = data.get('dim')
    width, height = clamp_dim(dim, cullmax)
    clip = f'0,0,{width},{height}'

    has_save_layer = bool(data.get('has_save_layer'))

    return clip, has_save_layer


def run_optimizer(skp: Path, out: Path, transform: str):
    command = [
        'out/Debug/optimizer',
        '--input',
        str(skp),
        '--output',
        str(out),
        '--transform',
        transform,
    ]
    subprocess.run(command, check=True)


def run_optimizer_stdout(skp: Path) -> dict[str, int]:
    command = [
        'out/Debug/optimizer_stdout',
        '--input',
        str(skp),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)['passes']


def nanobench_report_is_valid(path: Path) -> bool:
    """Return whether path contains a non-empty nanobench JSON report."""
    if not path.is_file() or path.stat().st_size == 0:
        return False

    try:
        with path.open(encoding='utf-8') as fp:
            report = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return False

    return isinstance(report, dict) and bool(report.get('results'))


def benchmark_is_complete(
    nanobench_root: Path,
    stem: str,
    nanobench_runs: int,
    baseline: Path,
    optimized: Path,
    baseline_png: Path,
    optimized_png: Path,
) -> bool:
    """Check that all requested reports and rendered outputs exist for one benchmark."""
    if not baseline.is_file() or not optimized.is_file():
        return False
    if not baseline_png.is_file() or not optimized_png.is_file():
        return False

    run_dir = nanobench_root / stem
    return all(
        nanobench_report_is_valid(run_dir / f'run_{run_index:03d}.json')
        for run_index in range(nanobench_runs)
    )


def reset_benchmark_reports(nanobench_root: Path, stem: str):
    """Remove prior reports so an incomplete benchmark restarts at run zero."""
    run_dir = nanobench_root / stem
    if run_dir.exists():
        shutil.rmtree(run_dir)


def run_nanobench(skps: list[Path], result: Path, clip: str, samples: int, backend: str):
    result.parent.mkdir(parents=True, exist_ok=True)
    command = [
        'out/Debug/nanobench',
        '--sourceType',
        'skp',
        '--benchType',
        'playback',
        '--samples',
        str(samples),
        '--skps',
        *[str(skp) for skp in skps],
        '--config',
        backend,
        '--purgeBetweenBenches',
        '--clip',
        clip,
        '--outResultsFile',
        str(result),
    ]
    subprocess.run(command, check=True)


def run_renderer(
    input: Path, output: Path, opt: bool, transform: str, backend: str, cullmax: int
):
    cmd = [
        'out/Debug/renderer_opt',
        '--input',
        str(input),
        '--output',
        str(output),
        '--backend',
        backend,
        '--opt',
        'true' if opt else 'false',
        '--transform',
        transform,
    ]
    if cullmax > 0:
        cmd.extend(['--cullmax', str(cullmax)])
    subprocess.run(cmd, check=True)


def main():
    args = parse_args()

    assert args.json_dir.exists(), f'{args.json_dir} does not exist'
    assert args.json_dir.is_dir(), f'{args.json_dir} is not a dir'
    assert args.skp_dir.exists(), f'{args.skp_dir} does not exist'
    assert args.skp_dir.is_dir(), f'{args.skp_dir} is not a dir'

    args.opt_dir.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)

    assert args.nanobench_runs > 0, '--nanobench-runs must be positive'

    nanobench_results = args.report_dir / 'nanobench'
    nanobench_results.mkdir(parents=True, exist_ok=True)

    pngs = args.report_dir / 'png'
    pngs.mkdir(parents=True, exist_ok=True)

    bench_count = 0

    skps = sorted(args.skp_dir.rglob('*.skp'))

    assert len(skps) != 0, f'{args.skp_dir} is empty'

    for skp in skps:
        stem = skp.stem
        clip, has_save_layer = read_skp_metadata(args.json_dir, stem, args.cullmax)

        if not has_save_layer:
            continue

        bench_count += 1

        bl_output: Path = args.opt_dir / f'{stem}.skp'
        ee_output: Path = args.opt_dir / f'{stem}__ee.skp'
        bl_png: Path = pngs / f'{stem}.png'
        ee_png: Path = pngs / f'{stem}__ee.png'

        if args.resume and benchmark_is_complete(
            nanobench_results,
            stem,
            args.nanobench_runs,
            bl_output,
            ee_output,
            bl_png,
            ee_png,
        ):
            print(f'[*] resume: skipping complete benchmark {stem}')
            continue

        if args.resume:
            reset_benchmark_reports(nanobench_results, stem)
            print(f'[*] resume: restarting benchmark {stem}')

        run_optimizer(skp, bl_output, 'none')
        run_optimizer(skp, ee_output, 'easteregg')

        nanobench_stem_dir = nanobench_results / stem
        for run_index in range(args.nanobench_runs):
            run_skps = [bl_output, ee_output]
            if run_index % 2 == 1:
                run_skps.reverse()

            nanobench_file = nanobench_stem_dir / f'run_{run_index:03d}.json'
            run_nanobench(
                run_skps,
                nanobench_file,
                clip,
                args.samples,
                args.backend,
            )

        run_renderer(
            skp, bl_png, opt=False, transform='none', backend=args.backend, cullmax=args.cullmax
        )
        run_renderer(
            skp,
            ee_png,
            opt=True,
            transform='easteregg',
            backend=args.backend,
            cullmax=args.cullmax,
        )

    print(f'[*] ran {bench_count} benchmarks')


if __name__ == '__main__':
    main()
