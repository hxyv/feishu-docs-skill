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

- The bot can only open documents it was invited to, and how to recognise the "not invited"
  error instead of retrying.
- Where an insert lands: directly after a heading = top of the section; after the section's
  last block = end of the section (`scripts/anchors.py` prints both ids for every heading).
- Feishu's automatic heading numbering (1, 1.1, 1.2.1 …) is the XML attribute `seq="auto"`,
  so headings are written in XML, never as typed numbers; `scripts/number_headings.py` turns
  numbering on for every heading of an existing document in one run.
- Local PNG figures go in through `<img path="@./figures/x.png">` (XML, with width and
  caption), Markdown `![caption](@./figures/x.png)` (full width) or `docs +media-insert`
  (end of document, any path). Content files must be relative to the working directory.
- Replace an existing figure or table block in place instead of appending a second copy; never
  `overwrite` a shared document; share-back a bot-created document or the user never sees it.

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
   (inspect URLs) and `wiki:node:read` for `/wiki/` links. Grant them in the Feishu developer
   console, publish the app version, and ask the tenant admin to approve if required.
3. Python 3.8+ for the two helper scripts (standard library only). matplotlib or any plotting
   tool for the figures.

## Install

Copy or symlink the `feishu-docs` folder into Claude Code's skills directory:

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
python3 feishu-docs/scripts/anchors.py "<doc url>"                 # outline: heading id, section-last id, number
python3 feishu-docs/scripts/number_headings.py "<doc url>" --dry-run
python3 feishu-docs/scripts/number_headings.py "<doc url>"          # seq="auto" on every heading
```
Both default to `--as bot`; pass `--as user` when lark-cli has a logged-in user and the edits
should be attributed to them.

## Repository layout

```
feishu-docs/
  SKILL.md                  the skill (frontmatter + instructions the agent follows)
  scripts/anchors.py        outline with the block ids edits anchor to
  scripts/number_headings.py  switch on Feishu numbering for every heading
examples/
  make_figure.py            a matplotlib figure the way the skill expects it
  section.md                a Markdown section body with a local figure and a table
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
