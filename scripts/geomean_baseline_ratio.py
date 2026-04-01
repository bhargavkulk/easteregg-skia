#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def geomean(values: list[float]) -> float:
    if not values:
        raise ValueError("No values provided for geomean")
    return math.exp(sum(math.log(v) for v in values) / len(values))


def extract_baseline_min_ms(nanobench_dir: Path) -> dict[str, float]:
    out: dict[str, float] = {}

    for path in sorted(nanobench_dir.glob("*__nanobench.json")):
        data = json.loads(path.read_text())
        results = data.get("results", {})

        for bench_name, bench_payload in results.items():
            # Keep baseline render benchmarks only.
            # Exclude optimized/easteregg runs named like "...__ee.skp_...".
            if ".skp_" not in bench_name or "__ee.skp_" in bench_name:
                continue

            # bench_payload is usually {"gl": {...}} or {"grmtl": {...}}.
            backend_payload = None
            for k, v in bench_payload.items():
                if isinstance(v, dict) and "min_ms" in v:
                    backend_payload = v
                    break

            if backend_payload is None:
                continue

            min_ms = backend_payload.get("min_ms")
            if isinstance(min_ms, (int, float)) and min_ms > 0:
                out[bench_name] = float(min_ms)

    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compute geomean baseline render time for two nanobench directories "
            "and print ratio: geomean(lhs) / geomean(rhs)."
        )
    )
    parser.add_argument("--lhs", default="report/nanobench", help="LHS nanobench dir (default: report/nanobench)")
    parser.add_argument("--rhs", default="grmtl/report/nanobench", help="RHS nanobench dir (default: grmtl/report/nanobench)")
    args = parser.parse_args()

    lhs = extract_baseline_min_ms(Path(args.lhs))
    rhs = extract_baseline_min_ms(Path(args.rhs))

    common = sorted(set(lhs) & set(rhs))
    if not common:
        raise SystemExit("No common baseline tests found between LHS and RHS")

    lhs_values = [lhs[name] for name in common]
    rhs_values = [rhs[name] for name in common]

    lhs_gm = geomean(lhs_values)
    rhs_gm = geomean(rhs_values)
    ratio = lhs_gm / rhs_gm

    print(f"common_tests={len(common)}")
    print(f"geomean_baseline_lhs_ms={lhs_gm:.9f}")
    print(f"geomean_baseline_rhs_ms={rhs_gm:.9f}")
    print(f"ratio_lhs_div_rhs={ratio:.9f}")


if __name__ == "__main__":
    main()
