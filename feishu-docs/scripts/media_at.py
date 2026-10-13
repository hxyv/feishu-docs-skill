#!/usr/bin/env python3
"""Put an image or attachment at a specific block of a Feishu doc.

    media_at.py <doc> <file> --after <block_id>   [--caption C] [--width W] [--type image|file]
    media_at.py <doc> <file> --replace <block_id> [--type image|file]

--after    inserts a new image (`<img>`) or attachment (`<source>`) block right after the
           given block (a heading = top of its section; the section's last block = its end,
           see anchors.py). The file must be under the current directory. Prints the new
           block id.
--replace  swaps the file of an EXISTING image or attachment block in place: the block id,
           position and caption stay, only the picture or file changes. The block is resized
           to the new picture's pixel size (or `--width`, height scaled), because Feishu
           otherwise keeps the old block's display size and a bigger plot shows as a thumbnail. This is the move
           for "regenerate figure 3": no delete, no re-insert, no duplicate. Implemented as
           `docs +media-upload --parent-node <block>` + the block patch `replace_image` /
           `replace_file` (both verified). Any path is accepted here.

`--type` is inferred from the extension (png/jpg/jpeg/gif/webp = image, else file).
Prints JSON {block_id, file_token, action, size, result, revision_id, warnings}.
"""
import argparse
import json
import os
import subprocess
import sys

IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def pixel_size(path):
    """(width, height) of a PNG or JPEG without any imaging library; None otherwise."""
    import struct
    with open(path, "rb") as f:
        head = f.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        if head[:2] == b"\xff\xd8":
            f.seek(2)
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF:
                    return None
                if marker[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    f.read(3)
                    h, w = struct.unpack(">HH", f.read(4))
                    return w, h
                (seg_len,) = struct.unpack(">H", f.read(2))
                f.seek(seg_len - 2, 1)
    return None


def lark(args, as_):
    proc = subprocess.run(["lark-cli", *args, "--as", as_, "--format", "json"], capture_output=True, text=True)
    for s in (proc.stdout, proc.stderr):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            continue
    sys.exit(f"lark-cli {' '.join(args)}: {(proc.stderr or proc.stdout).strip()[:300]}")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc", help="document_id or doc URL (for --replace the bare document_id is needed)")
    ap.add_argument("file")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--after", metavar="BLOCK_ID")
    g.add_argument("--replace", metavar="BLOCK_ID")
    ap.add_argument("--caption")
    ap.add_argument("--width", type=int)
    ap.add_argument("--type", choices=["image", "file"])
    ap.add_argument("--as", dest="as_", default="bot", choices=["bot", "user"])
    a = ap.parse_args()

    kind = a.type or ("image" if os.path.splitext(a.file)[1].lower() in IMAGES else "file")
    if not os.path.isfile(a.file):
        sys.exit(f"{a.file}: not a file")

    if a.after:
        rel = os.path.relpath(a.file)
        if rel.startswith(".."):
            sys.exit("for --after the file must be under the current directory (lark-cli refuses @/absolute)")
        path = "@./" + rel.replace(os.sep, "/")
        if kind == "image":
            attrs = f'path="{path}"' + (f' width="{a.width}"' if a.width else "") + ' align="center"' \
                    + (f' caption="{esc(a.caption)}"' if a.caption else "")
            xml = f"<img {attrs}/>"
        else:
            xml = f'<source path="{path}" name="{esc(os.path.basename(a.file))}"/>'
        body = "_media_body.xml"
        with open(body, "w", encoding="utf-8") as f:
            f.write(xml)
        try:
            res = lark(["docs", "+update", "--doc", a.doc, "--command", "block_insert_after",
                        "--block-id", a.after, "--content", "@./" + body], a.as_)
        finally:
            os.remove(body)
        d = res.get("data", {})
        new = next(iter(d.get("document", {}).get("new_blocks", [])), {})
        out = {"block_id": new.get("block_id"), "file_token": new.get("block_token"), "action": f"insert {kind} after {a.after}",
               "result": d.get("result", "failed"), "revision_id": (d.get("document") or {}).get("revision_id"), "warnings": d.get("warnings", [res.get("error", {}).get("message")] if not res.get("ok") else [])}
    else:
        doc_id = a.doc.rstrip("/").split("/")[-1].split("?")[0]
        up = lark(["docs", "+media-upload", "--doc-id", doc_id, "--file", a.file,
                   "--parent-type", "docx_image" if kind == "image" else "docx_file", "--parent-node", a.replace], a.as_)
        if not up.get("ok"):
            sys.exit(f"upload failed: {up.get('error', {}).get('message')}")
        token = up["data"]["file_token"]
        key = "replace_image" if kind == "image" else "replace_file"
        payload = {"token": token}
        if kind == "image":
            size = pixel_size(a.file)
            if a.width and size:
                payload.update(width=a.width, height=round(size[1] * a.width / size[0]))
            elif a.width:
                payload.update(width=a.width)
            elif size:
                payload.update(width=size[0], height=size[1])
        patch = lark(["api", "PATCH", f"/open-apis/docx/v1/documents/{doc_id}/blocks/{a.replace}",
                      "--data", json.dumps({key: payload})], a.as_)
        pd = patch.get("data", {})
        out = {"block_id": a.replace, "file_token": token, "action": f"{key} in place",
               "size": {k: payload[k] for k in ("width", "height") if k in payload} or None,
               "result": "success" if patch.get("ok") else "failed",
               "revision_id": pd.get("document_revision_id") or (pd.get("document") or {}).get("revision_id"),
               "warnings": [] if patch.get("ok") else [patch.get("error", {}).get("message")]}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    sys.exit(0 if out["result"] == "success" else 1)


if __name__ == "__main__":
    main()
