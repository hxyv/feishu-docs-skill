#!/usr/bin/env python3
"""Replace the content of an existing board (whiteboard) in a Feishu doc instead of inserting
a second one.

    board_update.py <doc> <board block id | board token> <diagram.puml|.svg|.mmd> [--append] [--as bot|user]

Two routes, chosen by the file extension (both verified on lark-cli 1.0.96):

  .puml / .svg  `docs +whiteboard-update --overwrite` by board token. The board keeps its
                token and block id; nothing else in the doc changes. `--append` draws on top of
                the existing content instead of replacing it.
  .mmd          Mermaid cannot go through +whiteboard-update (the Mermaid conversion emits
                colours the server rejects, in 1.0.96 and 1.0.97 alike), so the board block is
                replaced in place with `<whiteboard type="mermaid">…</whiteboard>`. Same
                position, no duplicate, but a NEW block id and token (printed). `>` in the
                diagram is escaped for you. Feishu's Mermaid renderer fails intermittently
                (degrade code 2107 on input it accepted a moment earlier), so this route
                retries up to 8 times; a failure leaves the old board untouched.

Prints JSON: {block_id, token, route, result, warnings}. Verify with
`lark-cli whiteboard +export --as bot --whiteboard-token <token> --output-type preview --output board.jpg`.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

MERMAID_TRIES = 8   # the Mermaid renderer rejects identical input intermittently (about 1 call in 3 succeeds)


def lark(args, as_):
    proc = subprocess.run(["lark-cli", *args, "--as", as_, "--format", "json"], capture_output=True, text=True)
    for s in (proc.stdout, proc.stderr):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            continue
    sys.exit(f"lark-cli {' '.join(args)}: {(proc.stderr or proc.stdout).strip()[:300]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc")
    ap.add_argument("board", help="block id (doxcn…) or board token of the existing whiteboard")
    ap.add_argument("file", help=".puml, .svg or .mmd under the current directory")
    ap.add_argument("--append", action="store_true", help="keep existing content (puml/svg only)")
    ap.add_argument("--as", dest="as_", default="bot", choices=["bot", "user"])
    a = ap.parse_args()

    ext = os.path.splitext(a.file)[1].lower()
    if ext not in (".puml", ".svg", ".mmd"):
        sys.exit("file must be .puml, .svg or .mmd")
    rel = os.path.relpath(a.file)
    if rel.startswith(".."):
        sys.exit("the diagram file must be under the current directory (lark-cli refuses @/absolute)")

    data = lark(["docs", "+fetch", "--doc", a.doc, "--detail", "full", "--doc-format", "xml"], a.as_)
    if not data.get("ok"):
        sys.exit(f"fetch failed: {data.get('error', {}).get('message')}")
    root = ET.fromstring("<root>" + data["data"]["document"]["content"] + "</root>")
    board = next((el for el in root.iter("whiteboard")
                  if a.board in (el.get("id"), el.get("token"))), None)
    if board is None:
        sys.exit(f"no whiteboard with id or token {a.board} in {a.doc}; boards present: "
                 + ", ".join(f"{el.get('id')}/{el.get('token')}" for el in root.iter("whiteboard")))
    block_id, token = board.get("id"), board.get("token")

    if ext in (".puml", ".svg"):
        args = ["docs", "+whiteboard-update", "--whiteboard-token", token,
                "--input_format", "plantuml" if ext == ".puml" else "svg", "--source", "@./" + rel]
        if not a.append:
            args.append("--overwrite")
        res = lark(args, a.as_)
        out = {"block_id": block_id, "token": token, "route": "whiteboard-update",
               "result": "success" if res.get("ok") else "failed",
               "warnings": [] if res.get("ok") else [res.get("error", {}).get("message")]}
    else:
        if a.append:
            sys.exit("--append is only possible for .puml/.svg")
        src = open(a.file, encoding="utf-8").read().strip()
        esc = src.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        body = "_board_body.xml"
        with open(body, "w", encoding="utf-8") as f:
            f.write(f'<whiteboard type="mermaid">{esc}</whiteboard>')
        tries = 0
        try:
            while True:
                tries += 1
                res = lark(["docs", "+update", "--doc", a.doc, "--command", "block_replace",
                            "--block-id", block_id, "--content", "@./" + body], a.as_)
                d = res.get("data", {})
                flaky = any("2107" in str(w) for w in d.get("warnings", []))
                if d.get("result") == "success" or not flaky or tries >= MERMAID_TRIES:
                    break
                time.sleep(2)   # 2107 "content parse failed" is intermittent server-side; same input passes on retry
        finally:
            os.remove(body)
        new = next((b for b in d.get("document", {}).get("new_blocks", []) if b.get("block_type") == "whiteboard"), {})
        out = {"block_id": new.get("block_id", block_id), "token": new.get("block_token", token),
               "route": f"block_replace (new id and token; {tries} attempt(s))",
               "result": d.get("result", "failed" if not res.get("ok") else "?"),
               "warnings": d.get("warnings", [res.get("error", {}).get("message")] if not res.get("ok") else [])}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    sys.exit(0 if out["result"] == "success" else 1)


if __name__ == "__main__":
    main()
