# Beyond the body: comments, history, export, import, sharing, search

All verified with lark-cli 1.0.96 as the bot. `--as bot` everywhere unless a user is logged in.

## Comments — leave a trail or answer one

```bash
# anchored to a block (id from anchors.py or a with-ids fetch); omit --block-id for a whole-doc comment
lark-cli drive +add-comment --as bot --doc "<doc url>" --block-id <block_id> \
  --content '[{"type":"text","text":"Updated the table from run 42; "},{"type":"mention_user","text":"ou_xxx"},{"type":"text","text":" please check."}]'
lark-cli drive +list-comments --as bot --token "<doc url>" \
  --jq '.data.items[] | {comment_id, is_solved, text: [.reply_list.replies[].content.elements[].text_run.text]}'
lark-cli drive +add-reply --as bot --doc "<doc url>" --comment-id <id> --content '[{"type":"text","text":"Done."}]'
lark-cli drive +resolve-comment --as bot --doc "<doc url>" --comment-id <id>
```
A plain `docs +fetch` does not include comments (verified as bot on 1.0.96); `+list-comments`
is the way to see what reviewers asked for before editing. A good habit after a substantive
edit the user did not watch: one short comment on the changed block saying what changed and
from which data.

## Version history — the undo button

```bash
lark-cli docs +history-list --as bot --doc "<doc>" --jq '.data.entries[:5][] | {history_version_id, revision_id, edit_time}'
lark-cli docs +history-revert --as bot --doc "<doc>" --history-version-id <id>   # waits up to 30 s, returns status
```
Take the newest `history_version_id` **before** a risky batch; if the result is wrong, revert
to it. Reverting is itself a new revision (nothing is lost), but tell the user when you do it.

## Export and import

```bash
lark-cli drive +export --as bot --url "<doc url>" --file-extension pdf --output-dir ./export --overwrite   # pdf | docx | markdown
lark-cli drive +import --as bot --file ./report.md --type docx --name "Report"                             # .md/.docx/.html/.txt → new doc
```
Export is the way to *see* the rendered result (open the PDF; figures, captions, numbering
and tables show as the reader sees them). An imported Markdown file arrives with unnumbered
headings: run `number_headings.py` afterwards. A bot-imported doc is app-owned: share it back.

## Where a new doc lives

```bash
lark-cli docs +create --as bot --title "T" --doc-format markdown --content @./body.md               # app's root folder
lark-cli docs +create --as bot --title "T" --parent-token <folder or wiki node token> --content @./body.xml
lark-cli drive +inspect --as bot --url "<any feishu url>"      # type, title, canonical token; unwraps /wiki/ links
lark-cli drive +update-title --as bot --token "<doc url>" --title "New title"
```
For a wiki, the parent token is the wiki node the user shares (the bot needs edit rights on
that node). `+media-insert` wants the bare docx `document_id`, which `+inspect` returns for a
wiki URL.

## Sharing and access

```bash
lark-cli drive +member-list --as bot --token "<doc url>" --jq '.data.items[] | {member_type, member_id, perm}'
lark-cli drive +member-add  --as bot --token "<doc url>" --member-type email --member-id a@b.c --perm edit --yes   # high-risk-write: only when asked
lark-cli drive +member-remove --as bot --token "<doc url>" --member-type email --member-id a@b.c --yes
lark-cli drive +permission-get-setting --as bot --token "<doc url>"
```
`--member-type` also takes `openid`, `unionid`, `openchat` (a group chat), `appid`.

## Finding documents

`lark-cli drive +search --as bot --query "title words"` needs the `search:docs:read` scope on
the app (error 99991672 names the missing scope); `docs +search` is user-identity only. Without
the scope, ask the user for the link — the bot can only open what it was invited to anyway.

## Reading other things in the doc

```bash
lark-cli docs +media-download --as bot --doc "<doc>" --token <file token> --output ./x.png   # an image/attachment out of the doc
lark-cli whiteboard +export --as bot --whiteboard-token <token> --output-type preview --output ./board.jpg
```
