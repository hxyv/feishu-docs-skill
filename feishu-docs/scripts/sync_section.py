#!/usr/bin/env python3
"""Replace the body of one section of a Feishu docx with the content of a local file.

    python3 sync_section.py <doc> "<heading text>" <file.md|file.xml> [--level N] [--as bot|user]

Finds the heading whose text equals (or, failing that, uniquely contains) the given text,
deletes every block between it and the end of its section (nested subsections included)
and inserts the file's content after the heading. The heading block itself is kept, so its
Feishu numbering and id survive. Lists are deleted through their items (a list wrapper has
no block id of its own, so one block range across a list is refused by the server); other
blocks go in as few range deletes as possible, last range first. If no heading matches and --level N is given, a new
auto-numbered heading `<hN seq="auto">` is appended at the end of the document first, then
the body is inserted under it.

The format follows the extension: .md -> Markdown, anything else -> DocxXML. The file must
be under the current working directory (lark-cli reads `--content @./...` relative paths), and
so must any image it references.
"""
import argparse
import json
import os
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


def fail(reply: dict) -> int:
    print(json.dumps(reply.get("error") or reply, ensure_ascii=False, indent=2), file=sys.stderr)
    return 1


def outline(doc: str, identity: str):
    reply = run(["lark-cli", "docs", "+fetch", "--as", identity, "--doc", doc,
                 "--detail", "with-ids", "--doc-format", "xml"])
    if not reply.get("ok"):
        return None, reply
    root = ET.fromstring(f"<root>{reply['data']['document']['content']}</root>")
    return list(root), reply  # every top-level block; list wrappers (ul/ol) carry no id


def find_heading(top, wanted: str):
    heads = [(i, el) for i, el in enumerate(top) if el.tag in HEADINGS]
    text = lambda el: "".join(el.itertext()).strip()  # noqa: E731
    exact = [(i, el) for i, el in heads if text(el) == wanted]
    if len(exact) == 1:
        return exact[0]
    loose = [(i, el) for i, el in heads if wanted.lower() in text(el).lower()]
    if len(loose) == 1:
        return loose[0]
    if len(exact) > 1 or len(loose) > 1:
        names = ", ".join(repr(text(el)) for _, el in (exact or loose))
        raise SystemExit(f"ambiguous heading {wanted!r}: matches {names}")
    return None


def section_end(top, index: int) -> int:
    """Index of the last top-level block of the section that starts at top[index]."""
    level = int(top[index].tag[1:])
    end = index
    for j in range(index + 1, len(top)):
        if top[j].tag in HEADINGS and int(top[j].tag[1:]) <= level:
            break
        end = j
    return end


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("doc")
    parser.add_argument("heading", help="heading text to match")
    parser.add_argument("file", help="content file (.md = Markdown, else DocxXML), under cwd")
    parser.add_argument("--level", type=int, help="create the heading at this level if missing")
    parser.add_argument("--as", dest="identity", default="bot", choices=("bot", "user"))
    args = parser.parse_args()

    rel = os.path.relpath(os.path.abspath(args.file), os.getcwd())
    if rel.startswith(".."):
        raise SystemExit(f"{args.file} is outside the current directory; cd next to it first")
    fmt = "markdown" if args.file.lower().endswith(".md") else "xml"
    content = f"@./{rel}"

    top, reply = outline(args.doc, args.identity)
    if top is None:
        return fail(reply)
    found = find_heading(top, args.heading)
    if found is None:
        if not args.level:
            raise SystemExit(f"no heading matches {args.heading!r} (pass --level N to create it)")
        made = run(["lark-cli", "docs", "+update", "--as", args.identity, "--doc", args.doc,
                    "--command", "append",
                    "--content", f'<h{args.level} seq="auto">{args.heading}</h{args.level}>'])
        if not made.get("ok"):
            return fail(made)
        top, reply = outline(args.doc, args.identity)
        if top is None:
            return fail(reply)
        found = find_heading(top, args.heading)
        if found is None:
            raise SystemExit("created the heading but cannot find it again")
    index, head = found
    end = section_end(top, index)
    body = top[index + 1:end + 1]
    deletes = []  # (start_id, end_id) ranges, body order
    run_start = run_end = None
    for el in body:
        if el.get("id"):
            run_start = run_start or el.get("id")
            run_end = el.get("id")
            continue
        if run_start:
            deletes.append((run_start, run_end))
            run_start = run_end = None
        items = [c.get("id") for c in el if c.get("id")]
        if items:
            deletes.append((items[0], items[-1]))
    if run_start:
        deletes.append((run_start, run_end))
    for start, stop in reversed(deletes):
        gone = run(["lark-cli", "docs", "+update", "--as", args.identity, "--doc", args.doc,
                    "--command", "block_delete", "--start-block-id", start, "--end-block-id", stop])
        if not gone.get("ok") or (gone.get("data") or {}).get("result") != "success":
            return fail(gone)
    result = run(["lark-cli", "docs", "+update", "--as", args.identity, "--doc", args.doc,
                  "--doc-format", fmt, "--content", content,
                  "--command", "block_insert_after", "--block-id", head.get("id")])
    if not result.get("ok"):
        return fail(result)
    what = f"deleted {len(body)} block(s) in {len(deletes)} range(s), inserted after heading"
    data = result.get("data") or {}
    print(json.dumps({"heading": "".join(head.itertext()).strip(), "heading_id": head.get("id"),
                      "action": what, "result": data.get("result"),
                      "warnings": data.get("warnings") or [],
                      "revision_id": (data.get("document") or {}).get("revision_id")},
                     ensure_ascii=False, indent=2))
    return 0 if data.get("result") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
