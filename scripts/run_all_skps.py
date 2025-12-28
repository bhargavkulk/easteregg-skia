import argparse
import json
import shutil
import subprocess
from pathlib import Path


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


def run_optimizer(binary: Path, skp: Path, output: Path, transform: str | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(binary), '--input', str(skp), '--output', str(output)]
    if transform:
        cmd.extend(['--transform', transform])
    run_cmd(cmd)


def copy_to_report(dest_dir: Path, paths: list[Path]) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        shutil.copy2(path, dest_dir / path.name)


def run_nanobench(
    binary: Path, skp_paths: list[Path], results_path: Path, clip: str | None, samples: int
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
        'gl',
    ]
    if clip:
        cmd.extend(['--clip', clip])
    cmd.extend(['--outResultsFile', str(results_path)])
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

        if not should_run:
            continue

        bench_count += 1

        ee_output = args.opt_dir / f'{stem}_ee.skp'
        sk_output = args.opt_dir / f'{stem}_sk.skp'

        run_optimizer(args.optimizer, skp, ee_output)
        run_optimizer(args.optimizer, skp, sk_output, transform='skrecordopt')

        copy_to_report(args.report_dir, [skp, ee_output, sk_output])

        results_file = args.nanobench_dir / f'{stem}_nanobench.json'
        run_nanobench(args.nanobench, [skp, ee_output, sk_output], results_file, clip, args.samples)

    print(f'Ran {bench_count} nanobench suites')


if __name__ == '__main__':
    main()
