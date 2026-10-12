#!/usr/bin/env python3
"""Print a CSV file as a Markdown table ready for a Feishu doc (pipes in cells escaped).

    python3 csv_table.py data.csv [--max-rows N] > _table.md
"""
import argparse
import csv
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv")
    parser.add_argument("--max-rows", type=int, default=200)
    args = parser.parse_args()
    with open(args.csv, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return 1
    width = max(len(r) for r in rows)
    cell = lambda v: v.replace("|", "\\|").strip()  # noqa: E731
    header = [cell(v) for v in rows[0]] + [""] * (width - len(rows[0]))
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * width)
    for row in rows[1:args.max_rows + 1]:
        row = [cell(v) for v in row] + [""] * (width - len(row))
        print("| " + " | ".join(row) + " |")
    if len(rows) - 1 > args.max_rows:
        print(f"\n({len(rows) - 1 - args.max_rows} more rows not shown)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
