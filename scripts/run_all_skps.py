import argparse
import json
import subprocess
from pathlib import Path
from typing import Optional


def parse_args():
    parser = argparse.ArgumentParser(description='Run optimizer + nanobench for every SKP.')
    parser.add_argument('--skp-dir', type=Path, default=Path('skps'))
    parser.add_argument('--optimizer', type=Path, default=Path('out/Debug/optimizer'))
    parser.add_argument('--nanobench', type=Path, default=Path('out/Debug/nanobench'))
    parser.add_argument('--opt-dir', type=Path, default=Path('opt'))
    parser.add_argument('--report-dir', type=Path, default=Path('report'))
    parser.add_argument('--nanobench-dir', type=Path, default=Path('report/nanobench'))
    parser.add_argument('--json-dir', type=Path, default=Path('jsons'))
    parser.add_argument('--samples', type=int, default=100)
    parser.add_argument('--renderer', type=Path, default=Path('out/Debug/dm'))
    parser.add_argument(
        '--render-tool',
        type=str,
        choices=('dm', 'renderer'),
        default='dm',
        help='Tool used to rasterize SKPs into PNGs.',
    )
    parser.add_argument('--png-dir', type=Path, default=Path('report/pngs'))
    parser.add_argument('--backend', type=str, default='gl')
    return parser.parse_args()


def collect_skps(skp_dir: Path) -> list[Path]:
    if not skp_dir.is_dir():
        raise RuntimeError(f'SKP directory does not exist: {skp_dir}')
    skps = sorted(path for path in skp_dir.iterdir() if path.suffix.lower() == '.skp')
    if not skps:
        raise RuntimeError(f'No SKP files found in {skp_dir}')
    return skps


def run_cmd(cmd: list[str]) -> None:
    result = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f'Command failed ({result.returncode}): {" ".join(cmd)}\n{stderr}')


def run_optimizer(binary: Path, skp: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(binary), '--input', str(skp), '--output', str(output)]
    run_cmd(cmd)


def run_nanobench(
    binary: Path,
    skp_paths: list[Path],
    results_path: Path,
    clip: Optional[str],
    samples: int,
    backend: str,
) -> None:
    results_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(binary),
        '--sourceType',
        'skp',
        '--benchType',
        'playback',
        '--samples',
        str(samples),
        '--skps',
        *map(str, skp_paths),
        '--config',
        backend,
    ]
    if clip:
        cmd.extend(['--clip', clip])
    cmd.extend(['--outResultsFile', str(results_path)])
    subprocess.run(cmd, check=True)


def run_renderer(binary: Path, input: Path, png_dir: Path, render_tool: str) -> None:
    png_dir.mkdir(parents=True, exist_ok=True)

    if render_tool == 'dm':
        cmd = [
            str(binary),
            '--src',
            'skp',
            '--skps',
            str(input),
            '--config',
            '8888',
            '--writePath',
            str(png_dir),
            '-q',
        ]
    else:
        output = png_dir / f'{input.stem}.png'
        cmd = [
            str(binary),
            '--input',
            str(input),
            '--output',
            str(output),
        ]

    subprocess.run(cmd, check=True)


def read_metadata(json_dir: Path, stem: str) -> tuple[str, bool]:
    json_path = json_dir / f'{stem}.json'
    if not json_path.is_file():
        raise RuntimeError(f'Missing metadata JSON: {json_path}')
    try:
        with json_path.open(encoding='utf-8') as handle:
            data = json.load(handle)
        dim = data.get('dim')
        if isinstance(dim, list) and len(dim) == 2:
            width, height = dim
            if isinstance(width, int) and isinstance(height, int):
                clip = f'0,0,{width},{height}'
            else:
                raise ValueError
        else:
            raise ValueError
        should_run = bool(data.get('has_save_layer'))
    except json.JSONDecodeError as err:
        raise RuntimeError(f'Invalid JSON in {json_path}: {err}') from err
    except ValueError as err:
        raise RuntimeError(f'Missing or invalid dim in {json_path}') from err
    return clip, should_run


def main():
    args = parse_args()
    skp_paths = collect_skps(args.skp_dir)
    args.opt_dir.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    args.nanobench_dir.mkdir(parents=True, exist_ok=True)
    bench_count = 0

    for skp in skp_paths:
        stem = skp.stem
        clip, should_run = read_metadata(args.json_dir, stem)
        print(clip)

        if not should_run:
            continue

        bench_count += 1

        ee_output: Path = args.opt_dir / f'{stem}__ee.skp'
        run_optimizer(args.optimizer, skp, ee_output)

        results_file = args.nanobench_dir / f'{stem}__nanobench.json'
        run_nanobench(
            args.nanobench, [skp, ee_output], results_file, clip, args.samples, args.backend
        )

        run_renderer(args.renderer, skp, args.png_dir, args.render_tool)
        run_renderer(args.renderer, ee_output, args.png_dir, args.render_tool)

    print(f'Ran {bench_count} nanobench suites')


if __name__ == '__main__':
    main()
