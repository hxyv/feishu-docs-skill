# Wiki spaces (知识库)

A wiki is a tree of pages. Every page is a **node** that wraps an ordinary cloud object (a
docx, sheet, base, slides, mindnote or uploaded file). Two tokens matter and they are easy to
confuse:

| Token | Where it appears | Used by |
|---|---|---|
| **node token** (`wikcn…`) | the `/wiki/<token>` URL | `wiki +node-*`, `+move`, `drive +upload --wiki-token`, `+update-title --url` |
| **object token** (`doxcn…` for a docx) | `obj_token` in node details | `docs +fetch`, `+update`, `+media-insert`, `+history-*`, comments |

`docs +fetch`/`+update` accept a `/wiki/` URL and resolve it, but the lower-level commands
want the bare object token. Resolve once and keep both:

```bash
lark-cli wiki +node-get --as bot --node-token "<wiki url | node token | obj token>" \
  --jq '.data | {space_id, node_token, obj_token, obj_type, parent_node_token, has_child, title}'
```
Error 131014 "document is not in wiki" means the link is a plain Drive doc: use the docs
commands directly. 131006 means the bot has no access to that node or space: ask the owner to
grant it; retrying or switching identity does not help.

## What the bot can see

Two levels of access, both verified:

- **Invited to one page** (the user shares a wiki page with the bot, edit rights). The bot
  can then resolve that node, list and create pages **under it**, move pages within the
  subtree, copy, rename, delete, upload files under it, export, and read the space's member
  list. It cannot list the space root or read the space's details (131006), and
  `+space-list` stays empty. This is enough for "manage this part of the wiki": ask the user
  to share the page that should be the root of the bot's work.
- **Member of the space** (a space admin adds the app under the space's settings → members,
  or `lark-cli wiki +member-add --space-id <id> --member-type appid --member-id <app id>
  --member-role member --as user`; a bot cannot add itself). Then the whole tree is listable
  and the space appears in `+space-list`.

```bash
lark-cli wiki +space-list --as bot --jq '.data.spaces[] | {space_id, name}'        # spaces the bot is a member of
lark-cli wiki +node-get   --as bot --node-token "<wiki url>"                        # ok = at least page-level access
```

## Browse the tree

```bash
python3 <skill dir>/scripts/wiki_tree.py <space_id | wiki url | node token> [--depth 1]
```
prints every page under the start point as `title  [docx]  node=…  doc=…`, so the agent can
pick a parent to create under, find the page a user described by name, or audit what exists.
Under the hood it pages through `lark-cli wiki +node-list --space-id <id>
[--parent-node-token <node>] --page-all`; `--space-id` must be the numeric id, never a URL or
title. Large spaces: start from the node the user linked and use `--depth`.

## Create a page in the wiki

```bash
lark-cli wiki +node-create --as bot --parent-node-token <node token> --title "Page title" \
  --jq '.data | {node_token, obj_token, url}'        # bare node token (a URL here fails with 131013); --space-id <id> = space root
lark-cli docs +update --as bot --doc <obj_token> --command append --content @./body.xml   # <h1 seq="auto">…</h1> headings: numbered in one write
# or: --doc-format markdown --content @./body.md, then scripts/number_headings.py <obj_token> (two writes, heading ids change)
```
The node is created empty, then filled with the usual update commands on its `obj_token` (or
`sync_section.py` per section; `+media-insert --doc <obj_token>` for figures, it answers with
a `block_id`). The parent may be any node type: a page under a Bitable or sheet node works (such nodes may
report `title: ""` from `+node-get`, shown as `(untitled)` by `wiki_tree.py`; the token is
still right).
Because the page lives in the space, every space member sees it at once: no share-back is
needed, unlike a Drive doc made with `docs +create`. The response's `permission_grant` says
`skipped` when no user is logged in; that is expected. `--obj-type sheet|bitable|slides|
mindnote` creates other kinds of pages; `--node-type shortcut --origin-node-token <node>`
places a link to an existing page.

Prefer `wiki +node-create` over `docs +create --parent-token <wiki node>` for wiki targets:
the former returns both tokens and resolves the space itself.

## Move, copy, rename, delete

```bash
lark-cli wiki +move --as bot --node-token <node> --target-parent-token <node>        # reorder / re-parent (same or other space)
lark-cli wiki +move --as bot --obj-type docx --obj-token <doc id> --target-space-id <id> [--target-parent-token <node>]   # Drive doc → wiki
lark-cli wiki +move-to-drive --as bot --node-token <node> [--folder-token <folder>]  # wiki page → Drive (async; polls)
lark-cli wiki +node-copy --as bot --space-id <id> --node-token <node> --target-parent-node-token <node> --title "Copy" --yes
lark-cli drive +update-title --as bot --url "<wiki url>" --title "New title"         # keeps the node token
lark-cli wiki +node-delete --as bot --node-token "<wiki url>" --yes                   # deletes the SUBTREE too; a bare token needs --obj-type wiki
```
`+node-copy` and `+node-delete` are high-risk writes (`--yes`): only when the user asked for
exactly that, and say what the subtree contains first (`wiki_tree.py <node>`). Copy is
non-recursive: children are not copied. `--include-children=false` on delete lifts the
children to the parent instead. Moving a Drive doc into a wiki needs rights on both sides;
`--apply` files a request instead when the bot cannot move it directly. Both directions were
verified: `+move-to-drive` answers within seconds with the doc's new `/docx/` URL, and
`+move --obj-type docx` brings it back under a node. A doc moved out of the wiki by the bot
becomes app-owned in Drive: share it back if it is to stay there.

## Files under a page

```bash
lark-cli drive +upload --as bot --file ./report.pdf --wiki-token <node>      # becomes a child node of type file (title = file name)
lark-cli drive +download --as bot --url "<wiki url of a file node>" --output-dir ./dl
lark-cli drive +export --as bot --url "<wiki url of a docx page>" --file-extension pdf --output-dir ./out
```

## Members of a space

```bash
lark-cli wiki +member-list --as bot --space-id <id> --page-all
lark-cli wiki +member-add --as bot --space-id <id> --member-type email --member-id a@b.c --member-role member   # only when asked
lark-cli wiki +member-remove --as bot --space-id <id> --member-type email --member-id a@b.c --member-role member
```
A bot cannot add a department (`opendepartmentid`); that needs `--as user`. Creating a space
(`+space-create`) is user-only as well: ask the user to create it and add the bot.

## Scopes

Reading: `wiki:space:retrieve` (list spaces), `wiki:node:read` (resolve a node),
`wiki:node:retrieve` (list children), `wiki:member:retrieve`. Writing: `wiki:node:create`
(also required by delete), `wiki:node:copy`, `wiki:node:move`. Or the umbrella `wiki:wiki`
(`wiki:wiki:readonly` for reads). A missing scope shows as error 99991672 with the scope named.

## Error codes worth recognising

| Code | Meaning | Do |
|---|---|---|
| 131005 | node does not exist | ask for a current link |
| 131006 | no access to node/space | ask the owner to add the bot; do not retry |
| 131012 | node deleted | rediscover it |
| 131014 | not a wiki page | use the docs/drive commands on it |
| 131011 | delete needs approval in the UI | stop |
| 131009 | lock contention on the parent | wait, retry once, no parallel writes under one parent |
