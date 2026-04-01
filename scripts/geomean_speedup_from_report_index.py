#!/usr/bin/env python3
import argparse
import html
import math
import re
from html.parser import HTMLParser
from pathlib import Path


FLOAT_RE = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')


class FirstTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.done = False
        self.in_row = False
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if self.done:
            return
        if tag == 'table' and not self.in_table:
            self.in_table = True
            return
        if not self.in_table:
            return
        if tag == 'tr':
            self.in_row = True
            self.current_row = []
            return
        if self.in_row and tag in ('td', 'th'):
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if self.done:
            return
        if not self.in_table:
            return
        if self.in_row and tag in ('td', 'th') and self.in_cell:
            cell_text = html.unescape(''.join(self.current_cell)).strip()
            self.current_row.append(' '.join(cell_text.split()))
            self.in_cell = False
            self.current_cell = []
            return
        if tag == 'tr' and self.in_row:
            if self.current_row:
                self.rows.append(self.current_row)
            self.in_row = False
            self.current_row = []
            return
        if tag == 'table' and self.in_table:
            self.in_table = False
            self.done = True

    def handle_data(self, data: str) -> None:
        if self.done:
            return
        if self.in_table and self.in_row and self.in_cell:
            self.current_cell.append(data)


def geomean(values: list[float]) -> float:
    if not values:
        raise ValueError('no values for geomean')
    return math.exp(sum(math.log(v) for v in values) / len(values))


def parse_float(value: str) -> float | None:
    m = FLOAT_RE.search(value)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(
        description='Read Easteregg/Baseline from report/index.html and compute geomean speedup (baseline/optimized).'
    )
    ap.add_argument('index_html', nargs='?', default='report/index.html', type=Path)
    ap.add_argument('--print-speedups', action='store_true', help='Also print Python list: speedups = [...]')
    args = ap.parse_args()

    index_html = args.index_html
    if not index_html.is_file() and str(index_html) == 'report/index.html':
        for candidate in (Path('gnap/report/index.html'), Path('grmtl/report/index.html')):
            if candidate.is_file():
                index_html = candidate
                break

    if not index_html.is_file():
        raise SystemExit(f'index.html not found: {index_html}')

    text = index_html.read_text(encoding='utf-8')
    parser = FirstTableParser()
    parser.feed(text)

    rows = parser.rows
    if not rows:
        raise SystemExit('No table rows found in HTML')

    header = rows[0]
    try:
        optimized_idx = header.index('Easteregg')
        baseline_idx = header.index('Baseline')
    except ValueError:
        raise SystemExit('Could not find "Easteregg" and/or "Baseline" column in first table header')

    speedups: list[float] = []
    for row in rows[1:]:
        if optimized_idx >= len(row) or baseline_idx >= len(row):
            continue
        optimized = parse_float(row[optimized_idx])
        baseline = parse_float(row[baseline_idx])
        if optimized is None or baseline is None or optimized <= 0 or baseline <= 0:
            continue
        speedups.append(baseline / optimized)

    if not speedups:
        raise SystemExit('No valid baseline/optimized numeric pairs found')

    gm_speedup = geomean(speedups)

    print(f'index_html={index_html}')
    print(f'speedup_count={len(speedups)}')
    print(f'geomean_speedup={gm_speedup:.9f}')

    if args.print_speedups:
        joined = ', '.join(f'{x:.9f}' for x in speedups)
        print(f'speedups = [{joined}]')


if __name__ == '__main__':
    main()
