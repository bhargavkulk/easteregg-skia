import argparse
import json
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
    backend: str
    cullmax: int


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description='Run optimizer + nanobench for every SKP.')
    parser.add_argument('skp_dir', type=Path)
    parser.add_argument('json_dir', type=Path)
    parser.add_argument('opt_dir', type=Path)
    parser.add_argument('report_dir', type=Path)
    parser.add_argument('--samples', type=int, default=100)
    parser.add_argument('--backend', default='gl')
    parser.add_argument('--cullmax', type=int, default=0)
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


def run_nanobench(skps: list[Path], result: Path, clip: str, samples: int, backend: str):
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

    nanobench_results = args.report_dir / 'nanobench'
    nanobench_results.mkdir(parents=True, exist_ok=True)

    pngs = args.report_dir / 'png'
    pngs.mkdir(parents=True, exist_ok=True)

    bench_count = 0

    skps = list(args.skp_dir.rglob('*.skp'))

    assert len(skps) != 0, f'{args.skp_dir} is empty'

    for skp in skps:
        stem = skp.stem
        clip, has_save_layer = read_skp_metadata(args.json_dir, stem, args.cullmax)

        if not has_save_layer:
            continue

        bench_count += 1

        bl_output: Path = args.opt_dir / f'{stem}.skp'
        ee_output: Path = args.opt_dir / f'{stem}__ee.skp'

        run_optimizer(skp, bl_output, 'none')
        run_optimizer(skp, ee_output, 'easteregg')

        nanobench_file = nanobench_results / f'{stem}__nanobench.json'
        run_nanobench(
            [bl_output, ee_output],
            nanobench_file,
            clip,
            args.samples,
            args.backend,
        )

        bl_png: Path = pngs / f'{stem}.png'
        ee_png: Path = pngs / f'{stem}__ee.png'

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
