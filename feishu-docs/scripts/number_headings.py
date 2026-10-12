#!/usr/bin/env python3
"""Turn on Feishu's automatic heading numbering for every heading of a docx.

    python3 number_headings.py <doc URL or document_id> [--dry-run] [--as bot|user]

Reads the document once and, for each heading that is not yet auto-numbered, replaces the
block with the same heading content plus seq="auto" (one `lark-cli docs +update --command
block_replace` per heading; inline formatting and links inside the heading are kept because
the heading's own XML is reused). Headings already numbered are left alone. Block ids of
replaced headings change: rerun anchors.py afterwards. Stdlib only.
"""
import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HEADINGS = {f"h{i}" for i in range(1, 10)}


def run(argv: list) -> dict:
    out = subprocess.run(argv, capture_output=True, text=True, check=False)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": {"message": (out.stdout or out.stderr).strip()[:500]}}


def numbered_copy(el: ET.Element) -> str:
    """The heading's XML with seq="auto" and without ids / server-side markers."""
    keep = {k: v for k, v in el.attrib.items() if k not in ("id", "seq", "seq-marker")}
    keep["seq"] = "auto"
    xml = ET.tostring(el, encoding="unicode")
    inner = re.sub(r"^<[^>]*>|</h\d>$", "", xml)
    inner = re.sub(r'\s+id="[^"]*"', "", inner)
    attrs = "".join(f' {k}="{v}"' for k, v in keep.items())
    return f"<{el.tag}{attrs}>{inner}</{el.tag}>"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("doc", help="document URL or document_id")
    parser.add_argument("--dry-run", action="store_true", help="print the replacements only")
    parser.add_argument("--as", dest="identity", default="bot", choices=("bot", "user"))
    args = parser.parse_args()
    reply = run(["lark-cli", "docs", "+fetch", "--as", args.identity, "--doc", args.doc,
                 "--detail", "full", "--doc-format", "xml"])
    if not reply.get("ok"):
        print(json.dumps(reply.get("error"), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    root = ET.fromstring(f"<root>{reply['data']['document']['content']}</root>")
    todo = [el for el in root if el.tag in HEADINGS and el.get("id")
            and el.get("seq") != "auto" and not el.get("seq-marker")]
    print(f"headings to number: {len(todo)}")
    failures = 0
    for el in todo:
        block_id = el.get("id")
        text = "".join(el.itertext()).strip()
        content = numbered_copy(el)
        if args.dry_run:
            print(f"would replace {block_id}: {content}")
            continue
        result = run(["lark-cli", "docs", "+update", "--as", args.identity, "--doc", args.doc,
                      "--command", "block_replace", "--block-id", block_id, "--content", content])
        data = result.get("data") or {}
        status = data.get("result") if result.get("ok") else "FAILED"
        warnings = data.get("warnings") or []
        print(f"{el.tag} {text!r}: {status}{' ' + json.dumps(warnings) if warnings else ''}")
        if status != "success":
            failures += 1
            print(json.dumps(result.get("error") or data, ensure_ascii=False)[:400])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
