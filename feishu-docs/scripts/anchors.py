#!/usr/bin/env python3
"""Print a Feishu docx outline with the block ids an edit needs.

    python3 anchors.py <doc URL or document_id> [--as bot|user]

For every heading it prints: level, heading id (anchor for "insert at the top of this
section"), the id of the section's last top-level block (anchor for "append to the end of
this section"; when that block is a list, the id of its last item, which also works as an
anchor), the heading's number as Feishu shows it (seq-marker, "-" when the heading is not
auto-numbered) and the heading text. Also prints the id of the document's last top-level
block. Stdlib only; runs one read-only `lark-cli docs +fetch` (identity: --as, default bot).
"""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

HEADINGS = {f"h{i}" for i in range(1, 10)}


def fetch_xml(doc: str, identity: str) -> dict:
    out = subprocess.run(
        ["lark-cli", "docs", "+fetch", "--as", identity, "--doc", doc,
         "--detail", "full", "--doc-format", "xml"],
        capture_output=True, text=True, check=False)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": {"message": (out.stdout or out.stderr).strip()[:500]}}


def block_id(el: ET.Element) -> str:
    """The id to anchor on: the block's own, or for a list wrapper (ul/ol, which has no id)
    its last item's; inserting after the last item lands after the list (verified)."""
    if el.get("id"):
        return el.get("id")
    items = [c for c in el if c.get("id")]
    return items[-1].get("id") if items else "?"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("doc", help="document URL or document_id")
    parser.add_argument("--as", dest="identity", default="bot", choices=("bot", "user"))
    args = parser.parse_args()
    reply = fetch_xml(args.doc, args.identity)
    if not reply.get("ok"):
        print(json.dumps(reply.get("error"), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    doc = reply["data"]["document"]
    root = ET.fromstring(f"<root>{doc['content']}</root>")
    top = list(root)  # every top-level block, list wrappers included
    print(f"document_id={doc['document_id']} revision={doc['revision_id']} "
          f"top_level_blocks={len(top)}")
    print(f"{'lvl':<4}{'heading_id':<30}{'section_last_id':<48}{'num':<8}text")
    for index, el in enumerate(top):
        if el.tag not in HEADINGS or not el.get("id"):
            continue
        level = int(el.tag[1:])
        last = el
        for nxt in top[index + 1:]:
            if nxt.tag in HEADINGS and int(nxt.tag[1:]) <= level:
                break
            last = nxt
        text = "".join(el.itertext()).strip()
        marker = el.get("seq-marker", "-")
        tail = block_id(last) + ("" if last.get("id") else " (last list item)")
        print(f"{el.tag:<4}{el.get('id'):<30}{tail:<48}{marker:<8}{text}")
    if top:
        print(f"last_block_id={block_id(top[-1])} ({top[-1].tag})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
