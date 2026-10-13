#!/usr/bin/env python3
"""Check a DocxXML body before it is written to a Feishu doc.

    preflight_xml.py <body.xml> [--no-profile]

Exit 0 = safe to write (warnings may be listed), exit 1 = do not write.

Why a local check: `lark-cli docs +script --command parse` repairs malformed XML in memory
and reports `passed` for unclosed tags, unknown tags and bad nesting, and the server then
silently drops or mangles what it could not place. This script is the strict gate:
  1. strict XML well-formedness (unclosed tags, bare `&`, stray `<`), with line and column;
  2. every tag is one Feishu accepts (an unknown tag is dropped silently by the server);
  3. nesting Feishu refuses (tables/images/code inside a callout, `code` outside `pre`,
     `li` outside a list, block elements inside `p`, `column` outside `grid`);
  4. local resources exist (`path="@./..."` relative to the cwd) and `<img>` has a source;
  5. `<whiteboard>` text uses `&gt;` for `>` (a raw `-->` makes the server reject the board);
  6. headings carry `seq="auto"` (warning: Feishu numbering is the house rule);
  7. then `docs +script --command parse` for the block profile (word count, block counts),
     unless --no-profile.
The file must be under the current directory (lark-cli refuses absolute `@/` paths).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

BLOCK = {"h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8", "h9", "p", "ul", "ol", "li",
         "callout", "blockquote", "pre", "checkbox", "grid", "column", "hr", "table",
         "colgroup", "col", "thead", "tbody", "tr", "th", "td", "img", "source", "whiteboard",
         "figure", "button", "title"}
INLINE = {"span", "u", "del", "s", "b", "i", "em", "strong", "a", "code", "latex", "cite", "br"}
KNOWN = BLOCK | INLINE
CALLOUT_OK = {"p", "ol", "ul", "checkbox"} | INLINE
HEADINGS = {f"h{i}" for i in range(1, 10)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--no-profile", action="store_true", help="skip the lark-cli parse step")
    a = ap.parse_args()
    errors, warnings = [], []

    rel = os.path.relpath(a.file)
    if rel.startswith(".."):
        errors.append(f"{a.file} is outside the current directory; lark-cli needs @./relative paths")
    try:
        text = open(a.file, encoding="utf-8").read()
    except OSError as e:
        sys.exit(json.dumps({"ok": False, "errors": [str(e)]}, indent=2))

    # 1. strict well-formedness; the body is a sequence of blocks, so wrap it in one root
    try:
        root = ET.fromstring("<root>" + text + "</root>")
    except ET.ParseError as e:
        line, col = e.position
        src = text.splitlines()[line - 1] if 0 < line <= len(text.splitlines()) else ""
        errors.append(f"not well-formed XML at line {line} col {col}: {e.msg}\n    {src.strip()[:160]}")
        root = None

    if root is not None:
        def walk(el, parents):
            tag = el.tag
            if tag not in KNOWN:
                errors.append(f"<{tag}> is not a Feishu DocxXML tag (the server drops it silently)")
            if parents:
                parent = parents[-1]
                if parent == "callout" and tag not in CALLOUT_OK:
                    errors.append(f"<{tag}> inside <callout>: a callout allows only p, ol, ul, checkbox and inline tags")
                if tag == "code" and parent != "pre" and parent not in INLINE | {"p", "li", "td", "th", "callout", "blockquote"}:
                    errors.append("<code> must sit inside <pre> (a code block) or inline text")
                if tag == "li" and parent not in {"ul", "ol"}:
                    errors.append("<li> must be inside <ul> or <ol>")
                if tag == "column" and parent != "grid":
                    errors.append("<column> must be inside <grid>")
                if tag in {"tr"} and parent not in {"table", "thead", "tbody"}:
                    errors.append("<tr> must be inside <table>, <thead> or <tbody>")
                if tag in {"td", "th"} and parent != "tr":
                    errors.append(f"<{tag}> must be inside <tr>")
                if parent == "p" and tag in BLOCK:
                    errors.append(f"<{tag}> inside <p>: block elements cannot nest in a paragraph")
                if tag == "pre" and parent != "root" and parent not in {"td", "th", "column", "li"}:
                    warnings.append(f"<pre> inside <{parent}> may be refused")
            if tag in HEADINGS and el.get("seq") != "auto":
                warnings.append(f"<{tag}> '{(el.text or '').strip()[:40]}' has no seq=\"auto\" (Feishu numbering)")
            if tag == "img" and not (el.get("path") or el.get("src") or el.get("href")):
                errors.append("<img> needs path=\"@./file\", src=\"<token>\" or href=\"https://…\"")
            if tag in {"img", "source"} and el.get("path"):
                p = el.get("path")
                if p.startswith("@/"):
                    warnings.append(f"{tag} path {p}: absolute paths work inside XML but not for --content; prefer @./relative")
                elif p.startswith("@"):
                    if not os.path.isfile(p[1:]):
                        errors.append(f"{tag} path {p}: file not found relative to {os.getcwd()}")
                else:
                    errors.append(f"{tag} path {p!r} must start with @ (e.g. @./figures/x.png)")
            if tag == "whiteboard":
                raw = re.search(r"<whiteboard[^>]*>(.*?)</whiteboard>", text, re.S)
                if raw and ">" in raw.group(1):
                    errors.append("<whiteboard> text contains a raw '>' (e.g. '-->'); write it as &gt; or the server rejects the board")
                if not (el.text or "").strip():
                    errors.append("<whiteboard> is empty")
            for child in el:
                walk(child, parents + [tag])
        for child in root:
            walk(child, ["root"])
        if len(root) == 0:
            errors.append("the body contains no blocks")

    profile = None
    if not a.no_profile and not errors:
        proc = subprocess.run(["lark-cli", "docs", "+script", "--command", "parse", "--content",
                               "@./" + rel.replace(os.sep, "/"), "--format", "json"],
                              capture_output=True, text=True)
        try:
            data = json.loads(proc.stdout or proc.stderr)
        except json.JSONDecodeError:
            data = {"ok": False, "error": {"message": (proc.stderr or proc.stdout).strip()[:300]}}
        if not data.get("ok"):
            errors.append("lark-cli parse: " + str(data.get("error", {}).get("message", data)))
        else:
            d = data.get("data", {})
            profile = {"status": d.get("assessment", {}).get("status"),
                       **{k: d.get("profile", {}).get(k) for k in ("word_count", "block_count")},
                       "blocks": {b["type"]: b["count"] for b in d.get("profile", {}).get("blocks", [])},
                       "diagnostics": d.get("diagnostics")}

    out = {"ok": not errors, "file": rel, "errors": errors, "warnings": warnings, "profile": profile}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
