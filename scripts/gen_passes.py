import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Args:
    skp_dir: Path
    json_dir: Path
    output: Path


def parse_args() -> Args:
    parser = argparse.ArgumentParser()
    parser.add_argument('skp_dir', type=Path)
    parser.add_argument('json_dir', type=Path)
    parser.add_argument('output', type=Path)
    return Args(**vars(parser.parse_args()))


def read_skp_metadata(json_dir: Path, stem) -> bool:
    json_path = json_dir / f'{stem}.json'
    assert json_path.exists(), f'{json_path} does not exist'

    with json_path.open(encoding='utf-8') as fp:
        data = json.load(fp)

    return bool(data.get('has_save_layer'))


def run_optimizer_stdout(skp: Path) -> dict[str, int]:
    command = [
        'out/Debug/optimizer_stdout',
        '--input',
        str(skp),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)['passes']


def main():
    args = parse_args()

    assert args.json_dir.exists(), f'{args.json_dir} does not exist'
    assert args.json_dir.is_dir(), f'{args.json_dir} is not a dir'
    assert args.skp_dir.exists(), f'{args.skp_dir} does not exist'
    assert args.skp_dir.is_dir(), f'{args.skp_dir} is not a dir'

    passes_by_input: dict[str, dict[str, int]] = {}
    skps = list(args.skp_dir.rglob('*.skp'))

    assert len(skps) != 0, f'{args.skp_dir} is empty'

    for skp in skps:
        stem = skp.stem
        has_save_layer = read_skp_metadata(args.json_dir, stem)

        if not has_save_layer:
            continue

        passes_by_input[skp.name] = run_optimizer_stdout(skp)

    args.output.write_text(json.dumps(passes_by_input, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
