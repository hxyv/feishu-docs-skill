---
name: feishu-docs
description: Write, edit and illustrate Feishu/Lark cloud documents (飞书文档, docx) with lark-cli acting as your Feishu bot. Use it whenever the user mentions a Feishu or Lark doc, pastes a feishu.cn or larksuite.com /docx/ or /wiki/ link, says "put this in the doc", "write the report into Feishu", "update the document", "insert these figures/plots into the doc", or has invited the bot to a document and wants it filled, revised or appended, even if they do not say "lark-cli". Covers reading a doc, inserting Markdown or XML content at a chosen heading, Feishu's automatic heading numbering, uploading local PNG figures as image blocks, replacing an existing figure or table, creating a new doc and sharing it back. Not for Bitable/Base tables, spreadsheets or IM messages.
---

# Feishu docs with lark-cli

`lark-cli` is bound to one Feishu/Lark app. The app's **bot** identity is what edits documents
here (`lark-cli auth status` shows which identities are ready). Facts that shape every step:

- pass `--as bot` on every call (lark-cli's embedded guide suggests `--as user`; use that only
  when `auth status` shows a logged-in user and the person wants edits attributed to them);
- the bot can only open documents it has been **invited to**. The user invites it from the doc's
  Share dialog by adding the app's bot (the name shown in `lark-cli auth status` / the app's
  console) as a collaborator with edit rights. A doc the bot cannot see answers `ok: false`,
  code `3380002`, "Invalid document_id or document not found": that is the signal to ask the
  user to invite the bot, not to retry;
- a doc the bot *creates* is owned by the app and invisible to the user until shared back
  (see "New document").

Results are JSON. Check the `ok` field (use `--jq`), not the shell exit status. The `_notice`
update nag can be ignored.

## Workflow for "manage this doc / write the report with my figures"

1. **Observe.** Run the bundled helper to get the outline with the ids edits need:
   ```bash
   python3 <skill dir>/scripts/anchors.py "<doc URL or document_id>"
   ```
   It prints, per heading, the heading id (anchor for inserting at the *top* of the section),
   the section's last block id (anchor for appending at the *end* of the section; for an h2 it
   spans the nested h3 subsections, so it is the right anchor for "end of Section B"), the
   number Feishu shows for it (`-` = not auto-numbered) and the document's last block id.
   Stdlib only; it shells out to one read-only `lark-cli docs +fetch`.
   For inserting at the top or end of a section that is all you need. Fetch the XML of a
   section only when you must pick a *specific* block to replace or delete (a figure, a
   table), or read the prose in Markdown to match its tone:
   ```bash
   lark-cli docs +fetch --as bot --doc "<doc>" --doc-format markdown --jq .data.document.content
   lark-cli docs +fetch --as bot --doc "<doc>" --scope section --start-block-id <hid> --detail with-ids
   ```
   Block ids appear only in the XML format (`--detail with-ids`), not in Markdown output.
   `+fetch` accepts `/docx/` and `/wiki/` URLs; `+media-insert` needs a bare `document_id`
   (`lark-cli drive +inspect --as bot --url "<wiki url>"` unwraps it).

2. **Produce the figures first**, as PNG, in a directory you will `cd` into (e.g. the report's
   folder with `figures/` beneath it). matplotlib: `matplotlib.use("Agg")`, `dpi=150`, one idea
   per figure, axis labels and units. A Markdown image is shown at full width (about 900 px);
   when you want a smaller figure (600 px reads well for a single plot) use the XML `<img
   width=...>` form or `+media-insert --width`.

3. **Write content from files, with the cwd set to the report folder.** `--content @./file`
   accepts only cwd-relative paths (an absolute `@/...` path is refused as unsafe), and local
   images in the content are resolved the same way. Markdown is the easy format for prose,
   lists and tables; XML gives exact control (headings with numbering, captions, width,
   callouts).

   Insert a section body with a figure directly after a heading (= top of that section):
   ```bash
   cd <report folder>
   cat > _sec.md <<'MD'
   Intake latency fell from 23 s to 4.8 s with a warm configuration cache.

   ![Figure 1. Intake latency per release](@./figures/latency.png)

   | Run | Sessions | Seconds |
   |---|---|---|
   | before | 14 | 23.0 |
   | warm | 3 | 4.8 |
   MD
   lark-cli docs +update --as bot --doc "<doc>" --command block_insert_after \
     --block-id <heading_id> --doc-format markdown --content @./_sec.md
   ```
   The `alt` text of a Markdown image becomes its caption. To append at the *end* of a section
   use `--block-id <section_last_id>` instead; `--command append` adds at the end of the
   document (`--block-id -1` is the same anchor).

   XML when you need width/alignment/caption on the image or a paragraph caption of your own:
   ```bash
   lark-cli docs +update --as bot --doc "<doc>" --command block_insert_after --block-id <id> \
     --content '<p>Figure 2 shows the fit per node.</p><img path="@./figures/fit.png" align="center" width="600" caption="Figure 2. Node fit"/>'
   ```
   A one-off image at the very end of the document takes any path, absolute included:
   ```bash
   lark-cli docs +media-insert --as bot --doc <document_id> --file /abs/path/fig.png --width 600 --caption "Figure 3. ..."
   ```

   **Every heading at every level is numbered by Feishu, never by the text.** Sections
   (`#`, `##`, `###` … = h1, h2, h3 …) carry Feishu's automatic numbering (1, 1.1, 1.2.1 …),
   which is the XML attribute `seq="auto"` on each heading block; Feishu derives the hierarchy
   from the heading levels. Markdown `##` headings are NOT numbered, and a typed "2.1" in the
   heading text is wrong (it will not renumber when sections move). So write every new
   heading, whatever its level, in XML, then anchor the body after it:
   ```bash
   lark-cli docs +update --as bot --doc "<doc>" --command block_insert_after --block-id <section_last_id> \
     --content '<h3 seq="auto">Throughput test</h3>'
   python3 <skill dir>/scripts/anchors.py "<doc>"      # the new heading's id
   lark-cli docs +update --as bot --doc "<doc>" --command block_insert_after --block-id <new_h3_id> \
     --doc-format markdown --content @./_body.md
   ```
   or write the whole section in XML in one call (`<h3 seq="auto">…</h3><p>…</p><img …/>`,
   lists as `<ul><li>…</li></ul>`, tables as in the XML reference). Levels must not skip
   (an h3 only under an h2). If a doc has unnumbered headings at any level (yours or an
   earlier Markdown import), number them all at once; a doc where only some headings are
   numbered shows inconsistent markers:
   ```bash
   python3 <skill dir>/scripts/number_headings.py "<doc>" --dry-run   # shows the replacements
   python3 <skill dir>/scripts/number_headings.py "<doc>"
   ```
   It keeps the headings' text and inline formatting; the replaced headings get new ids.
   (If the user's existing document deliberately has no numbering, follow the document.)

4. **Revise instead of duplicating.** When the report already has the figure or table, replace
   the block in place so the doc does not grow a second copy:
   ```bash
   lark-cli docs +update --as bot --doc "<doc>" --command block_replace --block-id <img_or_table_id> \
     --content '<img path="@./figures/fit.png" width="600" caption="Figure 2. Node fit (rerun)"/>'
   lark-cli docs +update --as bot --doc "<doc>" --command block_replace --block-id <table_id> \
     --doc-format markdown --content @./_table.md
   lark-cli docs +update --as bot --doc "<doc>" --command str_replace --pattern "old sentence" --content "new sentence"
   lark-cli docs +update --as bot --doc "<doc>" --command block_delete --block-id <id>
   ```
   `str_replace` is for short inline text only; `--pattern` cannot read a file. Every write
   invalidates ids after the touched position: rerun `anchors.py` before the next structural
   edit rather than reusing ids from before the write. The update response's `new_blocks`
   lists only resource blocks (images, boards), not the headings and paragraphs inserted with
   them; `result: success` with no warnings means the whole payload landed, and the text
   blocks' ids come from the next `anchors.py` run.

5. **Verify** with a Markdown fetch (step 1) and tell the user what changed and where (the
   doc URL; `<url>#<block_id>` links straight to a block). Delete the `_sec.md`-style scratch
   files you wrote into the report folder.

## Rules of the house

- Never `--command overwrite` on a document the user shares with you: it discards comments,
  images and blocks Markdown cannot express. Edit by block.
- `drive +member-add` and anything lark-cli marks `high-risk-write` need `--yes`; run them only
  when the user asked for that specific sharing or deletion.
- Markdown written to a doc is parsed: escape literal `*`, `_`, `[`, `]`, `$`, `~`, backtick
  and `<` with a backslash (`\<b>` to show a tag literally); `#`, `-`, `+`, `>` only at line
  start. Text fetched back is already escaped; keep its backslashes when you write it again.
  Inside code spans and fences nothing needs escaping.
- Keep figures and content files in the cwd; never put credentials or tokens into a doc.
- Exotic blocks (callout, grid/columns, whiteboard, checkbox, coloured text) exist only in XML:
  read `lark-cli skills read lark-doc/references/lark-doc-xml.md` when you need one. The full
  update reference is `lark-cli skills read lark-doc/references/lark-doc-update.md`.

## New document

`docs +create` as the bot makes an app-owned doc; share it back or the user never sees it:
```bash
lark-cli docs +create --as bot --title "Report title" --doc-format markdown --content @./report.md \
  --jq '.data.document | {document_id, url}'
lark-cli drive +member-add --as bot --token "<url>" --member-type email \
  --member-id user@example.com --perm full_access --yes      # or --member-type unionid/openid
```
The create command warns "auto-grant was skipped" when no user is logged in; that warning is
expected. Create from Markdown, then run `number_headings.py` on the new doc (or author the
XML with `seq="auto"` headings from the start) so the sections are numbered. Prefer appending
to a doc the user already shared over creating new ones.

## Checking access without writing

```bash
lark-cli drive +member-list --as bot --token "<doc url>" --jq '.data.items[] | {member_type, member_id, perm}'
```
The bot appears as `member_type: appid` with the app id from `lark-cli auth status`; `perm`
must be `edit` or `full_access` for writes.
