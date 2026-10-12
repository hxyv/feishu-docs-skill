#!/usr/bin/env python3
"""Print the page tree of a Feishu wiki space (or of one subtree) with the tokens edits need.

    wiki_tree.py <space_id | wiki URL | node_token> [--depth N] [--as bot|user]

A wiki page has two tokens: the *node* token (what `/wiki/<token>` URLs carry; used to list,
create, move or delete nodes) and the *object* token (the docx `document_id` the content lives
in; what `docs +fetch`/`+update`/`+media-insert` edit). Each line shows both:

    <title>  [docx]  node=wikcn…  doc=doxcn…

Given a URL or node token the tree starts at that node; given a numeric space id it starts at
the space root. `--depth 1` lists only direct children (default: whole subtree, breadth-first
page by page, so large spaces take a while).
"""
import argparse
import json
import subprocess
import sys


def lark(args, as_):
    proc = subprocess.run(["lark-cli", *args, "--as", as_, "--format", "json"],
                          capture_output=True, text=True)
    data = None
    for text in (proc.stdout, proc.stderr):          # errors are JSON on stderr
        try:
            data = json.loads(text)
            break
        except json.JSONDecodeError:
            continue
    if data is None:
        sys.exit(f"lark-cli {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}")
    if not data.get("ok", True):
        err = data.get("error", {})
        sys.exit(f"lark-cli {' '.join(args)}: {err.get('code')} {err.get('message')}"
                 f"\n{err.get('hint', '')}".rstrip())
    return data.get("data", data)


def children(space_id, parent, as_):
    args = ["wiki", "+node-list", "--space-id", space_id, "--page-all", "--page-limit", "0"]
    if parent:
        args += ["--parent-node-token", parent]
    return lark(args, as_).get("nodes", [])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("start", help="numeric space_id, a /wiki/ URL or a wiki node token")
    ap.add_argument("--depth", type=int, default=0, help="levels to descend (0 = all)")
    ap.add_argument("--as", dest="as_", default="bot", choices=["bot", "user"])
    a = ap.parse_args()

    if a.start.isdigit():
        space_id, root = a.start, None
        print(f"space_id={space_id}")
    else:
        node = lark(["wiki", "+node-get", "--node-token", a.start], a.as_)
        space_id, root = node["space_id"], node["node_token"]
        print(f"space_id={space_id}")
        print(f"{node.get('title', '')}  [{node.get('obj_type')}]  node={root}  doc={node.get('obj_token')}")

    def walk(parent, level):
        if a.depth and level > a.depth:
            return
        for n in children(space_id, parent, a.as_):
            kind = n.get("obj_type", "")
            if n.get("node_type") == "shortcut":
                kind += " shortcut"
            print(f"{'  ' * level}{n.get('title') or '(untitled)'}  [{kind}]  "
                  f"node={n['node_token']}  doc={n.get('obj_token')}")
            if n.get("has_child"):
                walk(n["node_token"], level + 1)

    walk(root, 1 if root else 0)


if __name__ == "__main__":
    main()
