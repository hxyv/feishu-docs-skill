# feishu-docs: a Claude Code skill for editing Feishu docs

Invite your Feishu (Lark) bot to a document, then ask Claude Code to edit it: sections, tables
and locally generated figures land in the right place, existing blocks are revised rather
than duplicated, and headings carry Feishu's own numbering.
The skill teaches the agent to drive [lark-cli](https://github.com/larksuite/cli) (the
official Feishu/Lark command line) as the bot identity, which is what makes "invite the bot
and let the agent manage the doc" work without a user login.

```
you:    I've invited the bot to https://xxx.feishu.cn/docx/ABC... — add a "Throughput" section
        at the end of Results with a plot of these numbers.
agent:  (reads the outline, makes the PNG with matplotlib, inserts a numbered heading, text
        and the figure after the last block of Results, fetches the doc back, reports the link)
```

## What the agent learns

- **Access model.** The bot can only open documents it was invited to; the skill recognises
  the "not invited" error instead of retrying, checks collaborators, and shares back any
  document the bot created itself.
- **Where edits land.** Directly after a heading = top of the section; after the section's
  last block = end of the section. `scripts/anchors.py` prints both ids for every heading,
  with the number Feishu shows for it.
- **Section sync.** `scripts/sync_section.py <doc> "Heading" body.md` replaces one section's
  body from a local Markdown or XML file in place (lists handled, heading and its number
  kept), or creates the section if it is missing. This is the primitive for "regenerate the
  Results section from the new run".
- **Feishu-native numbering.** Automatic heading numbers (1, 1.1, 1.2.1 …) are the XML
  attribute `seq="auto"`; `scripts/number_headings.py` turns them on for every heading of a
  document in one run.
- **The whole block vocabulary**, verified: callouts, quotes, code blocks, checklists, columns,
  coloured tables, inline formulas, highlights, @mentions and document mentions, local and web
  images with width and caption, file attachments, and diagrams from Mermaid, PlantUML or SVG
  rendered as editable Feishu boards (`references/blocks.md`).
- **Collaboration.** Comments anchored to blocks (add, list, reply, resolve), version history
  as an undo button, PDF/Word/Markdown export to see the rendered result, importing local
  Markdown or Word files as new docs, folder targets, renaming, permissions, and what the
  search command needs (`references/collaboration.md`).
- **Wiki spaces.** The difference between a page's node token and the document it wraps,
  which spaces the bot can see, browsing a space's page tree (`scripts/wiki_tree.py`),
  creating a page under a given node and filling it, moving a Drive doc into the wiki,
  moving, copying, renaming and deleting pages, files under a page, members
  (`references/wiki.md`).
- **In-place regeneration.** `scripts/media_at.py` swaps the picture or file of an existing
  block (id, position and caption kept) or inserts one after a chosen block; `scripts/board_update.py`
  redraws an existing board from PlantUML, SVG or Mermaid instead of adding a second one.
- **Preflight.** `scripts/preflight_xml.py` checks an XML body before it is written: strict
  well-formedness, Feishu's tag vocabulary, nesting rules, local files, board escaping and
  numbering, then lark-cli's own parse for the block profile. The section sync refuses to
  delete anything when the new body fails it.
- **Safety.** Replace existing figures and tables in place instead of appending duplicates;
  never `overwrite` a shared document; high-risk operations only when the user asked.

Everything in the skill was verified against a live document with lark-cli 1.0.96.

## Prerequisites

1. **lark-cli** installed and bound to a Feishu/Lark custom app:
   ```bash
   npm install -g @larksuite/cli      # or see the lark-cli README
   lark-cli config init               # app id + app secret of your app
   lark-cli auth status               # "Bot identity: ready" is enough for this skill
   ```
2. The app must have a **bot** capability and document scopes. The reference setup grants at
   least: `docx:document` (read and write blocks), `docs:document.content:read`,
   `docs:document.media:upload`, `docs:permission.member:readonly` (list collaborators),
   `docs:permission.member:create` (share a bot-created doc back), `drive:drive.metadata:readonly`
   (inspect URLs) and `wiki:node:read` for `/wiki/` links. Wiki work adds `wiki:space:retrieve`,
   `wiki:node:retrieve`, `wiki:node:create`, `wiki:node:move`, `wiki:node:copy` (or the umbrella
   `wiki:wiki`), and the bot must be added as a member of each wiki space it should manage. Grant them in the Feishu developer
   console, publish the app version, and ask the tenant admin to approve if required.
3. Python 3.8+ for the helper scripts (standard library only). matplotlib or any plotting
   tool for the figures.

## Install

The quickest way is the `skills` CLI, which finds the skill in this repo and copies it into
the agent's skills directory (it works for Claude Code, Codex, Cursor and others):

```bash
npx skills add hxyv/feishu-docs-skill            # pick the agent and scope interactively
npx skills add hxyv/feishu-docs-skill -g         # global (all projects)
```

Or copy or symlink the `feishu-docs` folder into Claude Code's skills directory yourself:

```bash
git clone https://github.com/hxyv/feishu-docs-skill
ln -s "$PWD/feishu-docs-skill/feishu-docs" ~/.claude/skills/feishu-docs       # all projects
# or: cp -r feishu-docs-skill/feishu-docs <project>/.claude/skills/            # one project
```

Claude Code picks the skill up automatically when a request mentions a Feishu doc, a
`/docx/` or `/wiki/` link, or putting text or figures into "the doc".

## Use

1. Open the document in Feishu, click **Share**, add your app's bot as a collaborator with
   **edit** permission (search for the app's name).
2. Ask Claude Code, with the document link, what to write or change.
3. The agent reads the outline, writes content from files in its working directory, uploads
   any figures, numbers the headings and fetches the result back for you to check.

### Helper scripts

```bash
python3 feishu-docs/scripts/anchors.py "<doc url>"                        # outline: heading id, section-last id, number
python3 feishu-docs/scripts/sync_section.py "<doc url>" "Results" body.md  # replace a section body from a file (--level 2 creates it)
python3 feishu-docs/scripts/number_headings.py "<doc url>" --dry-run       # then without --dry-run: seq="auto" on every heading
python3 feishu-docs/scripts/csv_table.py data.csv > _table.md             # CSV → Markdown table
```
All default to `--as bot`; pass `--as user` when lark-cli has a logged-in user and the edits
should be attributed to them. Standard library only.

## Repository layout

```
feishu-docs/
  SKILL.md                      the skill (frontmatter + the workflow the agent follows)
  references/blocks.md          DocxXML block vocabulary, media, diagrams, list/range rules, escaping
  references/collaboration.md   comments, history/undo, export/import, folders, sharing, search
  references/wiki.md            wiki spaces: tokens, access, page tree, create/move/copy/delete pages
  scripts/anchors.py            outline with the block ids edits anchor to
  scripts/sync_section.py       replace or create one section from a local file
  scripts/number_headings.py    switch on Feishu numbering for every heading
  scripts/csv_table.py          CSV to Markdown table
  scripts/wiki_tree.py          page tree of a wiki space or subtree with node and doc tokens
  scripts/preflight_xml.py      strict check of an XML body before writing (gate used by sync_section)
  scripts/media_at.py           image/attachment after a block, or swapped in place in an existing block
  scripts/board_update.py       redraw an existing board from .puml/.svg/.mmd
examples/
  make_figure.py                a matplotlib figure the way the skill expects it
  section.md                    a Markdown section body with a local figure and a table
```

## Notes and limits

- Only `docx` documents (the current Feishu doc format). Legacy `doc`, Bitable, sheets and
  slides are out of scope.
- Markdown headings are imported unnumbered; the skill therefore writes headings in XML or
  runs `number_headings.py` afterwards.
- `lark-cli` refuses `--content @/absolute/path`; the skill works from a working folder with
  relative paths. `docs +media-insert --file` accepts absolute paths.
- lark-cli's own embedded guides (`lark-cli skills read lark-doc`) remain the reference for
  exotic blocks (callouts, grids, whiteboards); the skill points the agent there when needed.

## License

MIT, see [LICENSE](LICENSE).
