import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def read_bounds(binary: Path, skp_path: Path) -> tuple[int, int]:
    """Invoke print_bounds binary and return parsed (width, height)."""
    result = subprocess.run(
        [str(binary), str(skp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f'print_bounds failed for {skp_path}:\n{result.stderr or result.stdout}')
    output = result.stdout.strip()
    try:
        width_str, height_str = output.split(',', maxsplit=1)
        return int(width_str), int(height_str)
    except ValueError as exc:
        raise RuntimeError(
            f'Unexpected output from print_bounds for {skp_path}: {output!r}'
        ) from exc


def write_json(entries: list[tuple[str, int, int, bool]], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        name: {'width': width, 'height': height, 'has_savelayer': has_save_layer}
        for name, width, height, has_save_layer in entries
    }
    output_file.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def collect_skps(skp_folder: Path) -> list[Path]:
    if not skp_folder.is_dir():
        raise RuntimeError(f'Input path is not a directory: {skp_folder}')
    skps = sorted(path for path in skp_folder.iterdir() if path.suffix.lower() == '.skp')
    if not skps:
        raise RuntimeError(f'No SKP files found in {skp_folder}')
    return skps


def find_command(json_data: dict[str, Any], target_command: str) -> bool:
    for command in json_data['commands']:
        if command['command'] == target_command:
            return True
    return False


def load_json(json_folder: Path, stem: str) -> tuple[Path, dict[str, Any]]:
    json_path = json_folder / f'{stem}.json'
    if not json_path.is_file():
        raise RuntimeError(f'JSON file not found for {stem}: {json_path}')
    with json_path.open(encoding='utf-8') as handle:
        return json_path, json.load(handle)


def update_json_dim(
    json_folder: Path,
    stem: str,
    width: int,
    height: int,
) -> bool:
    json_path, data = load_json(json_folder, stem)
    has_savelayer = find_command(data, 'SaveLayer')
    data['dim'] = [width, height]
    data['has_save_layer'] = has_savelayer
    json_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return has_savelayer


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Gather SKP bounds via print_bounds and write them to JSON.'
    )
    parser.add_argument('skp_folder', type=Path, help='Folder containing SKP files')
    parser.add_argument('json_folder', type=Path, help='Folder containing JSON files')
    parser.add_argument('output_json', type=Path, help='Where to write the JSON summary')
    parser.add_argument(
        'print_bounds',
        type=Path,
        help='Path to the print_bounds binary',
    )
    args = parser.parse_args()

    if not args.json_folder.is_dir():
        raise RuntimeError(f'Input path is not a directory: {args.json_folder}')

    skp_paths = collect_skps(args.skp_folder)
    bounds_entries: list[tuple[str, int, int, bool]] = []

    for skp_path in skp_paths:
        width, height = read_bounds(args.print_bounds, skp_path)
        stem = skp_path.stem
        has_save_layer = update_json_dim(args.json_folder, stem, width, height)
        bounds_entries.append((stem, width, height, has_save_layer))

    write_json(bounds_entries, args.output_json)


if __name__ == '__main__':
    main()
