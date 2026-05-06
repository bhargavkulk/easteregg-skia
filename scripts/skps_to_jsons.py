import argparse
import concurrent.futures
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Args:
    skps: Path
    out: Path


def existing_path(value: str):
    path = Path(value)

    if not path.exists():
        raise argparse.ArgumentTypeError('path does not exist')

    return path


def parse_args() -> Args:
    parser = argparse.ArgumentParser()
    parser.add_argument('skps', type=existing_path)
    parser.add_argument('out', type=Path)
    return Args(**vars(parser.parse_args()))


def process_skp(skp: Path, out: Path) -> Path:
    print(f'[INFO] converting {out.name}')
    result = subprocess.run(
        ['out/Debug/skp_parser', str(skp)], check=True, capture_output=True, text=True
    )
    json_skp_data = json.loads(result.stdout)

    result = subprocess.run(
        ['out/Debug/print_bounds', str(skp)], check=True, capture_output=True, text=True
    )
    dim = [int(i) for i in result.stdout.strip().split(',', maxsplit=1)]
    json_skp_data['dim'] = dim

    json_skp_data['has_save_layer'] = any(
        command.get('command') == 'SaveLayer' for command in json_skp_data.get('commands', [])
    )

    with out.open('w', encoding='utf-8') as fp:
        json.dump(json_skp_data, fp, indent=2)
        fp.write('\n')

    print(f'[INFO] wrote {out.name}')
    return out


def main():
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    skps = sorted(args.skps.glob('*.skp'))
    if not skps:
        raise SystemExit(f'[error] no .skp files found in: {args.skps}')

    workers = max(1, min(16, (os.cpu_count() or 1) * 2))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures: dict[concurrent.futures.Future[Path], Path] = {}

        for skp in skps:
            out = args.out / f'{skp.stem}.json'
            future = executor.submit(process_skp, skp, out)
            futures[future] = skp

        for future in concurrent.futures.as_completed(futures):
            out = future.result()


if __name__ == '__main__':
    main()
