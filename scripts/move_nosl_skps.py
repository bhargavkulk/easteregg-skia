import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Args:
    skps: Path
    jsons: Path
    skps_nosl: Path
    jsons_nosl: Path
    summary: Path


def existing_path(value: str):
    path = Path(value)

    if not path.exists():
        raise argparse.ArgumentTypeError('path does not exist')

    return path


def parse_args() -> Args:
    parser = argparse.ArgumentParser()
    parser.add_argument('skps', type=existing_path)
    parser.add_argument('jsons', type=existing_path)
    parser.add_argument('skps_nosl', type=Path)
    parser.add_argument('jsons_nosl', type=Path)
    parser.add_argument('summary', type=Path)
    return Args(**vars(parser.parse_args()))


def move_jsons(jsons: Path, jsons_nosl: Path) -> list[str]:
    moved_stems: list[str] = []

    for json_path in sorted(jsons.glob('*.json')):
        with json_path.open(encoding='utf-8') as fp:
            json_data = json.load(fp)

        if json_data.get('has_save_layer'):
            continue

        dst = jsons_nosl / json_path.name
        print(f'[INFO] moving {json_path.name} -> {dst.parent.name}/')
        json_path.rename(dst)
        moved_stems.append(json_path.stem)

    return moved_stems


def move_skps(skps: Path, skps_nosl: Path, stems: list[str]) -> None:
    for stem in stems:
        skp_path = skps / f'{stem}.skp'
        dst = skps_nosl / skp_path.name
        print(f'[INFO] moving {skp_path.name} -> {dst.parent.name}/')
        skp_path.rename(dst)


def stem_to_site(stem: str) -> str:
    return stem.rsplit('__layer_', maxsplit=1)[0]


def write_summary(
    skps: Path,
    jsons: Path,
    skps_nosl: Path,
    jsons_nosl: Path,
    summary_path: Path,
) -> None:
    kept_skps = sorted(skps.glob('*.skp'))
    kept_jsons = sorted(jsons.glob('*.json'))
    moved_skps = sorted(skps_nosl.glob('*.skp'))
    moved_jsons = sorted(jsons_nosl.glob('*.json'))
    nosl_sites = sorted({stem_to_site(path.stem) for path in moved_jsons})

    lines = [
        f'skps: {len(kept_skps)}',
        f'jsons: {len(kept_jsons)}',
        f'skps_nosl: {len(moved_skps)}',
        f'jsons_nosl: {len(moved_jsons)}',
        '',
        'no_save_layer_sites:',
    ]
    lines.extend(nosl_sites)
    summary_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[INFO] wrote {summary_path}')


def main():
    args = parse_args()

    args.jsons_nosl.mkdir(parents=True, exist_ok=True)
    args.skps_nosl.mkdir(parents=True, exist_ok=True)

    moved_stems = move_jsons(args.jsons, args.jsons_nosl)
    move_skps(args.skps, args.skps_nosl, moved_stems)
    write_summary(
        args.skps,
        args.jsons,
        args.skps_nosl,
        args.jsons_nosl,
        args.summary,
    )

    print(f'[INFO] moved {len(moved_stems)} jsons')
    print(f'[INFO] moved {len(moved_stems)} skps')


if __name__ == '__main__':
    main()
