---
name: feishu-docs
description: >-
  Read, write, restructure and illustrate Feishu/Lark cloud documents (飞书文档, docx) with lark-cli
  acting as your Feishu bot. Use it whenever the user mentions a Feishu or Lark doc, pastes a
  feishu.cn or larksuite.com /docx/ or /wiki/ link, says "put this in the doc", "write this into
  Feishu", "update the document", "regenerate the results section", "insert these
  figures/plots/tables into the doc", "add a diagram", "leave a comment", "export the doc", "undo
  that edit", "create a page in the wiki", "move this doc into the knowledge base", "what is in
  this wiki space", or has invited the bot to a document and wants it filled, revised, synced from
  local files or appended, even if they do not say "lark-cli". Covers wiki spaces (知识库: browse the
  page tree, create pages under a node, move or copy pages, upload files under a page),
  section-level sync from local Markdown/XML, Feishu's automatic heading numbering, local figures
  and attachments, callouts/code/checklists/columns/formulas, Mermaid diagrams as boards,
  @mentions, comments, version history, PDF/Word export, importing local files, creating docs in
  folders or wikis and sharing them back. Not for Bitable/Base tables, spreadsheets or IM
  messages.
---

# Feishu docs with lark-cli

`lark-cli` is bound to one Feishu/Lark app. The app's **bot** identity is what edits documents
here (`lark-cli auth status` shows which identities are ready). Facts that shape every step:

- pass `--as bot` on every call (lark-cli's embedded guide suggests `--as user`; use that only
  when `auth status` shows a logged-in user and the person wants edits attributed to them);
- the bot can only open documents it has been **invited to**. The user invites it from the doc's
  Share dialog by adding the app's bot (the name shown in the app console) as a collaborator
  with edit rights. A doc the bot cannot see answers `ok: false`, code `3380002`, "Invalid
  document_id or document not found": that is the signal to ask the user to invite the bot,
  not to retry;
- a doc the bot *creates* is owned by the app and invisible to the user until shared back.

Results are JSON. Check the `ok` field (use `--jq`; its output is raw text, not JSON-quoted),
not the shell exit status. The `_notice` update nag can be ignored.

## Capability map

| Need | Tool | Where it is explained |
|---|---|---|
| Outline with the ids edits anchor to, and each heading's number | `scripts/anchors.py <doc>` | below, step 1 |
| Replace or create one section from a local `.md`/`.xml` file | `scripts/sync_section.py <doc> "Heading" file [--level N]` | step 3 |
| Insert at a position, replace or delete blocks, inline text edits | `lark-cli docs +update` | steps 3–4 |
| Feishu numbering on every heading | `scripts/number_headings.py <doc>` | step 3 |
| CSV → Markdown table | `scripts/csv_table.py data.csv` | step 3 |
| Check an XML body before writing it (well-formed, known tags, nesting, local files, board escaping) | `scripts/preflight_xml.py body.xml` | step 3 |
| Put a figure or attachment after a given block, or swap the file of an existing image/attachment block in place | `scripts/media_at.py <doc> fig.png --after <id>` / `--replace <id>` | step 4 |
| Redraw an existing board (Mermaid/PlantUML/SVG) instead of inserting a second one | `scripts/board_update.py <doc> <board id> d.mmd` | step 4 |
| Figures, attachments, diagrams (Mermaid/SVG), callouts, code, checklists, columns, formulas, mentions, coloured tables | DocxXML | `references/blocks.md` |
| Comments, version history (undo), PDF/Word export, importing files, folders, sharing, search | `lark-cli drive …`, `docs +history-*` | `references/collaboration.md` |
| Wiki spaces: page tree, create a page under a node, move/copy/rename/delete pages, files under a page | `scripts/wiki_tree.py <space or url>`, `lark-cli wiki +node-*` | `references/wiki.md` |

Read a reference file the first time a task needs it, not up front.

## Workflow for editing a Feishu doc

1. **Observe.** Run the bundled helper to get the outline with the ids edits need:
   ```bash
   python3 <skill dir>/scripts/anchors.py "<doc URL or document_id>"
   ```
   It prints, per heading, the heading id (anchor for inserting at the *top* of the section),
   the section's last block id (anchor for appending at the *end* of the section; for an h2 it
   spans the nested h3 subsections; if the section ends in a list it reports the last item,
   which also works as an anchor), the number Feishu shows for it (`-` = not auto-numbered)
   and the document's last block id. Stdlib only; one read-only `lark-cli docs +fetch`.
   For inserting at the top or end of a section, or syncing a section, that is all you need.
   Fetch the XML of a section only when you must pick a *specific* block to replace or delete
   (a figure, a table), and the prose in Markdown to match its tone:
   ```bash
   lark-cli docs +fetch --as bot --doc "<doc>" --doc-format markdown --jq .data.document.content
   lark-cli docs +fetch --as bot --doc "<doc>" --scope section --start-block-id <hid> --detail with-ids
   ```
   Block ids appear only in the XML format, not in Markdown output. `+fetch` accepts `/docx/`
   and `/wiki/` URLs; `+media-insert` needs a bare `document_id` (`lark-cli wiki +node-get --as bot
   --node-token "<wiki url>"` returns it as `obj_token`, with the space and parent; see
   `references/wiki.md` when the task is about the wiki itself, not just one page in it). Before editing, list the open comments: they are
   usually the brief (`lark-cli drive +list-comments --as bot --token "<doc url>"`, see
   `references/collaboration.md`; a plain fetch does not include them).

2. **Produce local assets first** (figures as PNG, data files, diagrams), when the task has
   any, in a directory you will `cd` into (the document's working folder with `figures/`
   beneath it). matplotlib: `matplotlib.use("Agg")`, `dpi=150`, one idea per figure, axis
   labels and units. A Markdown image is shown at full width (about 900 px); for a smaller
   figure (600 px reads well for a single plot) use XML `<img width="600" …>`. A process,
   architecture or dependency is often clearer as a Mermaid diagram than as prose: Feishu
   renders `<whiteboard type="mermaid">` as an editable board (`references/blocks.md`).
   Inside `<whiteboard>` text write `>` as `&gt;` (a raw `-->` makes the server reject the
   board). Every `.xml` body goes through `scripts/preflight_xml.py` before it is written:
   lark-cli's own parser repairs malformed XML silently and the server then drops what it
   cannot place, so the strict local check is the only thing that catches an unclosed tag,
   an unknown tag, a table inside a callout or a missing figure file. `sync_section.py`
   runs it for you; run it yourself before a hand-written `docs +update --content @./x.xml`.

3. **Write content from files, with the cwd set to that working folder.** `--content @./file`
   accepts only cwd-relative paths (an absolute `@/...` path is refused as unsafe), and local
   images in the content are resolved the same way. Markdown is the easy format for prose,
   lists and tables; XML gives exact control (numbered headings, captions, width, callouts,
   diagrams).

   **The usual move is a section sync**: write the section body to a file and let the helper
   replace what is there (heading, its number and its id are kept; lists, images and
   subsections inside the old body are removed; an empty section just gets the body; with
   `--level N` a missing section is created at the end as an auto-numbered heading):
   ```bash
   cd <working folder>
   cat > _results.md <<'MD'
   Run time fell from 23 s to 4.8 s after the change.

   ![Figure 1. Run time per version](@./figures/runtime.png)

   | Version | Steps | Seconds |
   |---|---|---|
   | before | 14 | 23.0 |
   | after | 3 | 4.8 |
   MD
   python3 <skill dir>/scripts/sync_section.py "<doc>" "Results" _results.md
   python3 <skill dir>/scripts/sync_section.py "<doc>" "Changelog" _log.md --level 2
   python3 <skill dir>/scripts/sync_section.py "<doc>" "Pipeline" _pipeline.xml --level 2
   ```
   The body file's extension picks the format. Use an `.xml` body when the section needs
   what Markdown cannot say: a sized figure (`<img path="@./figures/x.png" width="600"
   caption="…"/>`), a Mermaid board, numbered sub-headings (`<h3 seq="auto">`), a callout.
   A `.md` body renders its images at full width.
   To add rather than replace, anchor an insert yourself: after the heading (top of the
   section) or after the section's last block (end of the section); `--command append`
   adds at the end of the document:
   ```bash
   lark-cli docs +update --as bot --doc "<doc>" --command block_insert_after \
     --block-id <section_last_id> --doc-format markdown --content @./_more.md
   lark-cli docs +update --as bot --doc "<doc>" --command block_insert_after --block-id <id> \
     --content '<p>Figure 2 shows the result per group.</p><img path="@./figures/groups.png" align="center" width="600" caption="Figure 2. Result per group"/>'
   lark-cli docs +media-insert --as bot --doc <document_id> --file /abs/path/fig.png --width 600 --caption "Figure 3. …"   # end of doc, any path
   ```
   The `alt` text of a Markdown image becomes its caption.

   **Every heading at every level is numbered by Feishu, never by the text.** Sections
   (`#`, `##`, `###` … = h1, h2, h3 …) carry Feishu's automatic numbering (1, 1.1, 1.2.1 …),
   the XML attribute `seq="auto"` on each heading block; Feishu derives the hierarchy from
   the heading levels. Markdown `##` headings are NOT numbered, and a typed "2.1" in the
   heading text is wrong (it will not renumber when sections move). So write new headings in
   XML (`<h3 seq="auto">Title</h3>`, levels must not skip) or let `sync_section.py --level N`
   create them, and keep section *bodies* in Markdown. If a doc has unnumbered headings at
   any level (yours or an earlier Markdown import), number them all at once; a doc where only
   some headings are numbered shows inconsistent markers:
   ```bash
   python3 <skill dir>/scripts/number_headings.py "<doc>" --dry-run   # shows the replacements
   python3 <skill dir>/scripts/number_headings.py "<doc>"
   ```
   It keeps the headings' text and inline formatting; the replaced headings get new ids.
   (If the user's existing document deliberately has no numbering, follow the document.)

4. **Revise instead of duplicating.** When the document already has the figure or table,
   replace the block in place so the doc does not grow a second copy:
   ```bash
   lark-cli docs +update --as bot --doc "<doc>" --command block_replace --block-id <img_or_table_id> \
     --content '<img path="@./figures/groups.png" width="600" caption="Figure 2. Result per group (updated)"/>'
   lark-cli docs +update --as bot --doc "<doc>" --command block_replace --block-id <table_id> \
     --doc-format markdown --content @./_table.md
   lark-cli docs +update --as bot --doc "<doc>" --command str_replace --pattern "old sentence" --content "new sentence"
   lark-cli docs +update --as bot --doc "<doc>" --command block_delete --block-id <id>
   ```
   `str_replace` is for short inline text only; `--pattern` cannot read a file. A block
   range (`--start-block-id`/`--end-block-id`) must not cross a list (its wrapper has no
   id); delete lists through their items, or use `sync_section.py`. Every write invalidates
   ids after the touched position: rerun `anchors.py` before the next structural edit. The
   update response's `new_blocks` lists only resource blocks (images, boards), not the
   headings and paragraphs inserted with them; `result: success` with no warnings means the
   whole payload landed.
   A regenerated figure goes into the existing image block (`scripts/media_at.py <doc> fig.png
   --replace <img block id>`: id, position and caption stay, only the picture changes; also
   for `<source>` attachments), a regenerated diagram into the existing board
   (`scripts/board_update.py <doc> <board block id or token> d.mmd|d.puml|d.svg`), and a new
   figure at a chosen position with `media_at.py --after <block id>`; `+media-insert` only
   appends at the end of the document.

5. **Verify and hand over.** Fetch the edited section back as Markdown (step 1); for a
   document the user will read as a whole, export it to PDF and look at the pages
   (`lark-cli drive +export --as bot --url "<doc or wiki url>" --file-extension pdf --output-dir ./out`):
   figures, captions, numbering, tables and boards show as the reader sees them, so no
   separate board preview is needed. Tell the user what changed and where (`<url>#<block_id>`
   links straight to a block). When you changed something substantive that the user did not
   watch, leave one short comment anchored to the block (`references/collaboration.md`).
   Delete the `_*.md` scratch files you wrote into the working folder.

## Undo

Before a risky batch, note the newest version:
`lark-cli docs +history-list --as bot --doc "<doc>" --jq '.data.entries[0]'`; if the result is
wrong, `lark-cli docs +history-revert --as bot --doc "<doc>" --history-version-id <id>`
restores it (a new revision; tell the user).

## Rules

- Never `--command overwrite` on a document the user shares with you: it discards comments,
  images and blocks Markdown cannot express. Edit by block or by section.
- `drive +member-add`, `+member-remove` and anything lark-cli marks `high-risk-write` need
  `--yes`; run them only when the user asked for that specific sharing or deletion.
- Markdown written to a doc is parsed: escape literal `*`, `_`, `[`, `]`, `$`, `~`, backtick
  and `<` with a backslash (`\<b>` to show a tag literally); `#`, `-`, `+`, `>` only at line
  start. Text fetched back is already escaped; keep its backslashes when you write it again.
  Inside code spans and fences nothing needs escaping.
- Keep figures and content files in the cwd; never put credentials or tokens into a doc.
- An @mention needs the person's real open_id (`<cite type="user" user-id="ou_…"/>`); never
  imitate one with plain text.
- lark-cli's own guides remain the reference for anything not covered here:
  `lark-cli skills read lark-doc/references/lark-doc-xml.md` (all tags),
  `…/lark-doc-update.md` (every update command).

## New document

**Inside a wiki** (the user gave a `/wiki/` link and wants a page under it): one write per
step, no share-back, full details in `references/wiki.md`:
```bash
lark-cli wiki +node-get --as bot --node-token "<parent wiki url>" --jq '.data | {node_token, obj_type, title}'
lark-cli wiki +node-create --as bot --parent-node-token <node token> --title "Page title" --jq '.data | {node_token, obj_token, url}'
lark-cli docs +update --as bot --doc <obj_token> --command append --content @./_body.xml     # headings as <h1 seq="auto">, figures as <img path="@./…">
python3 <skill dir>/scripts/wiki_tree.py "<parent wiki url>"                                # show the user what is there now
```
A parent whose `obj_type` is `bitable` or `sheet` may report an empty title; that is still
the right node. Then verify and export as in step 5.

**In Drive:** `docs +create` as the bot makes an app-owned doc; share it back or the user never sees it:
```bash
lark-cli docs +create --as bot --title "Document title" --doc-format markdown --content @./body.md \
  --jq '.data.document | {document_id, url}'                       # --parent-token <folder or wiki node> to place it
lark-cli drive +member-add --as bot --token "<url>" --member-type email \
  --member-id user@example.com --perm full_access --yes      # or --member-type unionid/openid
```
The create command warns "auto-grant was skipped" when no user is logged in; that warning is
expected. Then run `number_headings.py` on the new doc (or author the XML with `seq="auto"`
headings from the start). Prefer appending to a doc the user already shared over creating
new ones. A local `.md`/`.docx` file becomes a doc with `lark-cli drive +import --type docx`.

## Checking access without writing

```bash
lark-cli drive +member-list --as bot --token "<doc url>" --jq '.data.items[] | {member_type, member_id, perm}'
```
The bot appears as `member_type: appid` with the app id from `lark-cli auth status`; `perm`
must be `edit` or `full_access` for writes. For a wiki, `lark-cli wiki +node-get --as bot
--node-token "<wiki url>"` answers whether the bot can reach that page (131006 = no access);
sharing one page with the bot is enough to manage everything under it, membership of the
whole space (`wiki +space-list`) only adds listing the space root (`references/wiki.md`).
