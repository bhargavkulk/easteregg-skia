import argparse
import subprocess
from pathlib import Path
from typing import Iterable


def convert_skps(skp_files: Iterable[Path], parser_bin: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for skp_path in skp_files:
        json_path = output_dir / f'{skp_path.stem}.json'
        print(f'[*] converting {skp_path} -> {json_path}')
        with json_path.open('w', encoding='utf-8') as dest:
            proc = subprocess.run(
                [str(parser_bin), str(skp_path)],
                stdout=dest,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )


def main():
    parser = argparse.ArgumentParser(description='Convert SKP files to JSON using skp_parser.')
    parser.add_argument('input_dir', type=Path, help='Directory containing .skp files')
    parser.add_argument('output_dir', type=Path, help='Directory to write .json outputs')
    parser.add_argument(
        'parser_bin',
        type=Path,
        help='Path to skp_parser executable (e.g. ./out/Debug/skp_parser)',
    )
    args = parser.parse_args()

    skp_files = sorted(args.input_dir.glob('*.skp'))
    convert_skps(skp_files, args.parser_bin, args.output_dir)


if __name__ == '__main__':
    main()
