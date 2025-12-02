#!/usr/bin/env python3
"""Generate an HTML report for easteregg output."""

import argparse
import difflib
import html
import os
import sys

SECTION_PREFIX = "-----BEGIN "
SECTION_SUFFIX = "-----"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Path to report_data.txt")
    parser.add_argument("--before", required=True, help="Path to before.png")
    parser.add_argument("--after", required=True, help="Path to after.png")
    parser.add_argument("--output", required=True, help="Path where HTML should be written")
    return parser.parse_args()


def parse_report_data(path: str):
    before_count = None
    after_count = None
    sections = {}
    current_section = None

    def section_key(header: str) -> str:
        return header.replace(" ", "_").lower()

    with open(path, "r", encoding="utf-8") as src:
        for raw_line in src:
            line = raw_line.rstrip("\n")
            if current_section:
                if line.startswith("-----END "):
                    current_section = None
                else:
                    sections[current_section].append(raw_line)
                continue

            if line.startswith("before_count:"):
                before_count = int(line.split(":", 1)[1])
            elif line.startswith("after_count:"):
                after_count = int(line.split(":", 1)[1])
            elif line.startswith(SECTION_PREFIX):
                header = line[len(SECTION_PREFIX):-len(SECTION_SUFFIX)]
                current_section = section_key(header)
                sections[current_section] = []
            elif not line.strip():
                continue
            else:
                raise ValueError(f"Unexpected line in report data: {line}")

    if current_section:
        raise ValueError("Unterminated section in report data")

    required_sections = ["before_commands", "after_commands", "save_layer_log"]
    for key in required_sections:
        if key not in sections:
            raise ValueError(f"Missing section {key} in report data")

    if before_count is None or after_count is None:
        raise ValueError("Missing command counts in report data")

    return {
        "before_count": before_count,
        "after_count": after_count,
        "before_commands": "".join(sections["before_commands"]),
        "after_commands": "".join(sections["after_commands"]),
        "save_layer_log": "".join(sections["save_layer_log"]),
    }


def make_diff(before: str, after: str) -> str:
    before_lines = before.rstrip("\n").splitlines()
    after_lines = after.rstrip("\n").splitlines()
    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "\n".join(diff)


def html_block(title: str, body: str) -> str:
    return f"<h1>{html.escape(title)}</h1>\n<pre>{html.escape(body)}</pre>\n"


def relpath(path: str, output_path: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(output_path))
    return os.path.relpath(os.path.abspath(path), base_dir)


def build_html(data, before_image: str, after_image: str, output_path: str) -> str:
    before_section = html_block(
        f"Record Commands Before Transform ({data['before_count']} total)",
        data["before_commands"],
    )
    after_section = html_block(
        f"Record Commands After Transform ({data['after_count']} total)",
        data["after_commands"],
    )
    diff_section = html_block("Record Command Diff", make_diff(data["before_commands"], data["after_commands"]))
    log_section = html_block("SaveLayer / Restore Log", data["save_layer_log"])

    before_rel = html.escape(relpath(before_image, output_path))
    after_rel = html.escape(relpath(after_image, output_path))

    images = (
        "<h1>Record Snapshots</h1>\n"
        f"<h2>Before</h2><img src=\"{before_rel}\" alt=\"Before transform\" />\n"
        f"<h2>After</h2><img src=\"{after_rel}\" alt=\"After transform\" />\n"
    )

    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\" />\n"
        "<title>SKP Comparison</title>\n"
        "<style>body{font-family:monospace;}pre{background:#f4f4f4;padding:1em;overflow:auto;}"
        "img{max-width:100%%;height:auto;}h1{font-size:1.5em;}h2{font-size:1.2em;}</style>\n"
        "</head><body>\n"
        f"{before_section}\n{after_section}\n{diff_section}\n{log_section}\n{images}"
        "</body></html>\n"
    )


def main() -> int:
    args = parse_args()
    try:
        data = parse_report_data(args.data)
    except Exception as err:  # noqa: BLE001
        print(f"Failed to read report data: {err}", file=sys.stderr)
        return 1

    html_output = build_html(data, args.before, args.after, args.output)
    with open(args.output, "w", encoding="utf-8") as dst:
        dst.write(html_output)
    print(f"Wrote HTML report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
