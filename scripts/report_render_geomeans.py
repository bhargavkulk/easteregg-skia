#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def geomean(values: list[float]) -> float:
    if not values:
        raise ValueError('cannot compute geomean of empty list')
    return math.exp(sum(math.log(v) for v in values) / len(values))


def geomean_from_samples(samples: list[float]) -> float | None:
    vals = [float(x) for x in samples if isinstance(x, (int, float)) and x > 0]
    if not vals:
        return None
    return geomean(vals)


def extract_samples(bench_payload: dict, backend: str | None) -> list[float] | None:
    if backend:
        candidate = bench_payload.get(backend)
        if isinstance(candidate, dict) and isinstance(candidate.get('samples'), list):
            return candidate['samples']
        return None

    for candidate in bench_payload.values():
        if isinstance(candidate, dict) and isinstance(candidate.get('samples'), list):
            return candidate['samples']
    return None


def canonical_name(bench_name: str) -> str:
    return bench_name.replace('__ee.skp_', '.skp_')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Compute geomean baseline render, optimized render, and speedup from a report folder.'
    )
    parser.add_argument('report_dir', type=Path, help='Path to report folder (contains nanobench/)')
    parser.add_argument('--backend', default=None, help='Backend key (e.g. gl, grmtl). Auto-detect if omitted.')
    parser.add_argument('--nanobench-subdir', default='nanobench', help='Nanobench subdirectory name')
    parser.add_argument('--no-table', action='store_true', help='Suppress per-benchmark table output')
    args = parser.parse_args()

    nanobench_dir = args.report_dir / args.nanobench_subdir
    if not nanobench_dir.is_dir():
        raise SystemExit(f'No nanobench directory found: {nanobench_dir}')

    baseline_by_name: dict[str, float] = {}
    optimized_by_name: dict[str, float] = {}

    for path in sorted(nanobench_dir.glob('*__nanobench.json')):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        results = data.get('results', {})
        if not isinstance(results, dict):
            continue

        for bench_name, bench_payload in results.items():
            if not isinstance(bench_name, str) or not isinstance(bench_payload, dict):
                continue
            if '.skp_' not in bench_name:
                continue

            samples = extract_samples(bench_payload, args.backend)
            if samples is None:
                continue

            sample_gm = geomean_from_samples(samples)
            if sample_gm is None:
                continue

            key = canonical_name(bench_name)
            if '__ee.skp_' in bench_name:
                optimized_by_name[key] = sample_gm
            else:
                baseline_by_name[key] = sample_gm

    common = sorted(set(baseline_by_name) & set(optimized_by_name))
    if not common:
        raise SystemExit('No matching baseline/optimized benchmark pairs found')

    baseline_vals = [baseline_by_name[k] for k in common]
    optimized_vals = [optimized_by_name[k] for k in common]
    speedups = [baseline_by_name[k] / optimized_by_name[k] for k in common]

    gm_baseline = geomean(baseline_vals)
    gm_optimized = geomean(optimized_vals)
    gm_speedup = geomean(speedups)

    print(f'report_dir={args.report_dir}')
    print(f'benchmarks={len(common)}')
    print(f'geomean_baseline_render_ms={gm_baseline:.9f}')
    print(f'geomean_optimized_render_ms={gm_optimized:.9f}')
    print(f'geomean_speedup={gm_speedup:.9f}')

    if not args.no_table:
        rows = [
            (k, baseline_by_name[k], optimized_by_name[k], baseline_by_name[k] / optimized_by_name[k])
            for k in common
        ]
        rows.sort(key=lambda r: r[3], reverse=True)

        print('\nbenchmark\tgeomean_baseline_ms\tgeomean_optimized_ms\tspeedup')
        for benchmark, baseline_ms, optimized_ms, speedup in rows:
            print(f'{benchmark}\t{baseline_ms:.9f}\t{optimized_ms:.9f}\t{speedup:.9f}')


if __name__ == '__main__':
    main()
