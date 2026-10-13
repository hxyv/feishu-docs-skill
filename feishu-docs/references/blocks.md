# Block vocabulary (DocxXML) — verified round-trips

Everything here was written with `docs +update --content` (XML, the default `--doc-format`)
and read back with `+fetch`. Use XML when a block has no Markdown form or needs attributes;
Markdown covers paragraphs, headings (unnumbered), lists, tables, code fences, quotes, links,
images and `$…$` formulas. Attribute values always in double quotes.

## Structure

| Block | XML | Notes |
|---|---|---|
| Numbered heading | `<h2 seq="auto">Title</h2>` | h1–h9, levels must not skip. `seq="auto"` = Feishu numbering (1, 1.1, 1.2.1). The server reports it back as `seq-marker="1.2"`. |
| Paragraph | `<p align="center">text</p>` | `align` left/center/right also on headings, list items, checkboxes |
| Quote | `<blockquote>text</blockquote>` | fetches back as `> text` |
| Divider | `<hr/>` | Markdown `---` |
| Columns | `<grid><column width-ratio="0.5"><p>…</p></column><column width-ratio="0.5">…</column></grid>` | ratios sum to 1; any blocks inside |
| Callout | `<callout emoji="💡" background-color="light-blue" border-color="blue"><p>…</p></callout>` | children: `p`, `ol`, `ul`, `checkbox`, inline tags only — no tables, images, code |
| Code | `<pre lang="python" caption="file.py"><code>…</code></pre>` | a code block is `<pre>` with the code in `<code>`; escape `<`, `&` as `&lt;`, `&amp;`. Inline code is `<code>` inside text (`<p>run <code>make</code></p>`) |
| Checklist | `<checkbox done="true">Done item</checkbox><checkbox done="false">Open item</checkbox>` | Markdown `- [x]` / `- [ ]` also works |
| Lists | `<ol><li>First<ul><li>nested</li></ul></li><li>Second</li></ol>` | nested lists go inside the parent `<li>`; a list wrapper has **no block id**, only its items do (see "Lists and ranges") |
| Table | `<table><colgroup><col width="160"/><col width="120"/></colgroup><thead><tr><th background-color="light-gray"><p>H</p></th></tr></thead><tbody><tr><td background-color="light-green"><p>v</p></td></tr></tbody></table>` | cell content wrapped in `<p>`; `colspan`/`rowspan`/`vertical-align`; colours: `light-{red,orange,yellow,green,blue,purple,gray}`, `medium-gray`. Markdown tables are fine for plain data. |
| Page layout | — | default width ≈ 820 px; a full-width image is ≈ 900 px |

## Inline

`<b>`, `<em>`, `<u>`, `<del>`, `<br/>`, `<a href="URL">text</a>`,
`<a type="url-preview" href="URL">title</a>` (link card),
`<latex>E = mc^2</latex>` (inline formula; Markdown `$E = mc^2$`),
`<span background-color="light-yellow" text-color="red">text</span>` (highlight / colour),
`<cite type="user" user-id="ou_xxx"/>` (@mention, needs the person's open_id; never fake a
mention with plain text), `<cite type="doc" doc-id="DOC_TOKEN"/>` (document mention rendered
with its title).

## Media

| What | XML | Notes |
|---|---|---|
| Local image | `<img path="@./figures/x.png" width="600" align="center" caption="Figure 1. …"/>` | path relative to cwd; PNG/JPEG/GIF/WebP ≤ 20 MiB; omit width for full width; the caption comes back with a trailing newline (`&#xA;`), so match on it with care. Swap the picture of an existing block without touching id or caption: `scripts/media_at.py <doc> new.png --replace <img block id> [--width 600]` (`docs +media-upload --parent-node` + block patch `replace_image` with the new pixel size; without a size Feishu keeps the old block's display size, so a bigger plot would show as a thumbnail) |
| Web image | `<img href="https://…/x.png"/>` | the CLI downloads and uploads it |
| Copy of an existing image | `<img src="<file token>"/>` | token from a `with-ids`/`full` fetch (`src=`) |
| Attachment | `<source path="@./data.csv" name="data.csv"/>` | or `docs +media-insert --type file --file …` at the end of the doc, `media_at.py --after <block>` at a position, `media_at.py --replace <source block id>` to swap the file in place; `<figure view-type="Card">` around it for a card |
| Diagram from Mermaid | `<whiteboard type="mermaid">flowchart LR; A--&gt;B</whiteboard>` (write `>` as `&gt;`; the renderer fails intermittently with degrade code 2107 on valid input, retry the same write) | or `path="@./diagram.mmd"`; flowchart, sequence, class, pie, gantt, mindmap. Rendered by Feishu as an editable board; preview with `lark-cli whiteboard +export --whiteboard-token <block_token> --output-type preview --output ./x.jpg` (extension must be .jpg) |
| Diagram from SVG / PlantUML | `<whiteboard type="svg" path="@./d.svg"/>`, `type="plantuml"` | SVG must be self-contained with a viewBox |
| Update an existing board | `scripts/board_update.py <doc> <board id or token> d.puml\|d.svg\|d.mmd` (PlantUML/SVG: `docs +whiteboard-update --overwrite` by token, id and token kept; Mermaid: the block is replaced in place with a new id, because `+whiteboard-update --input_format mermaid` fails with "Unsupported color format" in lark-cli 1.0.96 and 1.0.97) | token from the fetch (`<whiteboard … token>`) or `new_blocks[].block_token` |

## How blocks come back from `+fetch --doc-format markdown`

Headings lose their numbers (`## Section B`, the number is only in XML `seq-marker`);
callout and grid come back as XML islands inside the Markdown (`<callout …>`, `<grid …>`);
checkboxes as `- [x]`; code as fences with the language; formula as `$…$`; images as
`![caption](https://feishu.cn/file/<token>)`; highlight/underline colour is dropped. For
anything you intend to edit, fetch XML with `--detail with-ids`.

## Lists and ranges

A `<ul>`/`<ol>` wrapper has no id; its `<li>` items do. Consequences:

- a `block_replace`/`block_delete` **range across a list is refused** ("an intermediate
  sibling has no block ID"); delete the list through its items (`--start-block-id <first li>
  --end-block-id <last li>`) and the neighbours as separate ranges — `scripts/sync_section.py`
  does exactly this;
- `block_insert_after --block-id <last li>` with a `<p>` lands **after the list** as a
  sibling (verified), so a list can still be an anchor; `anchors.py` reports the last item's
  id for a section that ends in a list and says so.

## Markdown escaping (when writing `--doc-format markdown`)

Escape literal `*`, `_`, `[`, `]`, `$`, `~`, backtick and `<` with a backslash; `#`, `-`,
`+`, `>` only at the start of a line; `|` inside table cells. Text fetched back is already
escaped — keep its backslashes. Nothing needs escaping inside code spans or fences. XML tags
inside Markdown are parsed, so `\<b>` shows a literal tag. Prefer `--content @./file.md` over
inline strings; the `@` path must be relative to the cwd.
