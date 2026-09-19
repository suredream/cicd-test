# Kanbanchan — layout & interaction spec (from the prototype)

Visual system: **Broadsheet** (Source Serif 4 on paper ground `#f3f2f2`, cyan `#0088b0` primary / magenta `#d6006c` rare second spot). All values below come from the design-system tokens in `Kanbanchan.css`; do not introduce new hexes or fonts.

Companion files: `Kanbanchan.css` (tokens + component classes), `Kanbanchan-tree.css` (tree row rules).

---

## 1. Page frame

```
grid-template-rows: auto minmax(0, 1fr)   /* header, body */
height: 100vh; overflow: hidden            /* only the panes scroll */
```

### Header — front-page furniture
The one place rules are allowed. Thick-thin pair around a dateline row:

```
3px solid ink  ── top rule
[ Kanbanchan ]  HIERARCHY · TAGS · KEYBOARD          14 NODES   New note ⌘N   Search ⌘K
1px solid ink  ── bottom rule
padding: 14px 22px 0
```

- `Kanbanchan` — heading serif 600 / 21px.
- Dateline & counts — 11px, uppercase, `letter-spacing: .16em`, `--color-neutral-700`.
- Actions — 13px italic in `--color-accent-700`, hover `--color-accent-2-700`; the shortcut hint sits beside it in 11px neutral.

### Body

```
grid-template-columns: minmax(240px, 324px) minmax(0, 1fr)
```

Left = tree + attention rail. Right = editor / dynamic view, separated by a single hairline (`--color-divider`) — the only vertical rule in the app.

---

## 2. Tree column

```
grid-template-rows: minmax(0, 1fr) auto    /* scrolling tree, pinned rail */
padding: 16px 10px 0 14px
```

Scroll region fades at the bottom instead of clipping a row:

```
padding-bottom: 26px;
mask-image: linear-gradient(to bottom, #000 calc(100% - 22px), transparent);
```

### Row anatomy

```
[caret 11px] [ title (flex, min 96px) ] [ tags ] [ count ] [ + ]
```

| Part | Rule |
| --- | --- |
| Row | `display:flex; align-items:baseline; gap:7px; border-radius:2px` |
| Indent | `padding-left: 6 + depth * 12px` |
| Row height | `padding-block` 2 / 4 / 6px for very dense / dense / comfortable |
| Font size | 13 / 14.5 / 15.5px on the same three densities (default: comfortable) |
| Caret | `▶` / `▼` at 9px, `--color-neutral-600`; absent when no children |
| Title | `flex:1 1 auto; min-width:96px; ellipsis`. Depth 0 at weight 600, deeper at 400 |
| Tags | 10.5px uppercase, `letter-spacing:.1em`, **no `#`**, `flex:0 1 auto` so they clip before the title; `#today`/`#tomo` take magenta `--color-accent-2-700`, all others cyan `--color-accent-700` |
| Child count | shown only when a node is collapsed; 10.5px `--color-neutral-500`, tabular figures |
| `+` | selected row only; adds a child |
| Selected | `background: --color-accent-200`, text `--color-accent-900` |
| Drag target | `box-shadow` inset — top 2px = drop before, bottom 2px = after, left 2px = nest (all `--color-accent-2`) |
| Inline rename | input replaces the title span: `--color-neutral-100` fill, 1px `--color-accent` bottom border, no other chrome |

**Hierarchy rule:** the title is the only shrinkable child. Metadata never takes space from it.

### Attention rail (pinned)

```
hairline --color-divider
"⏎ new sibling · ⇥ nest · ⌘N to Inbox"   11px italic neutral-600
ATTENTION                                 10.5px uppercase, .16em
#today  #tomo  #todo  #followup   ← label 13px italic accent-700, count 11px neutral-600
```

Active view: `background --color-accent-200`, label `--color-accent-900`.

---

## 3. Editor pane

```
padding: 16px 40px 40px 34px; max-width: 660px; overflow-y: auto
```

Stacked, flush left, no boxes:

1. **Path + save status** on one baseline — `Work / Wells Fargo / CI/CD` (11px uppercase, `.14em`, neutral-600) left; `Saving…` (neutral-600) / `Saved` (accent-700) right, 11px uppercase. Empty in idle.
2. **Title** — borderless input, heading serif 600 / 31px, line-height 1.15; `:focus` draws a 1px accent underline only.
3. **Tag row** — parsed live from the title, 11px uppercase with `#`, same color split as the tree; click opens that dynamic view. Reserves 15px so nothing jumps.
4. **Body** — borderless textarea, body serif 16px / 1.62, `min-height: 46vh`, `resize: none`. Placeholder: *Write. Autosaves.*

### Dynamic tag view (replaces the editor)

```
DYNAMIC VIEW            11px uppercase neutral-600
TODAY                   heading 36px / 1.1
3 nodes tagged #today   13px italic neutral-700
── 26px space ──
per result, gap 20px:
  WORK / WELLS FARGO / CI/CD   11px uppercase .13em neutral-600
  Migration parity             heading 600 / 20px
  first content line (120 chars) 14px neutral-700 / 1.5
```

Path is mandatory on every result — it is the only context the view has.

---

## 4. Search overlay (⌘K)

Backdrop `color-mix(in srgb, #201e1d 34%, transparent)`; panel `min(620px, 90vw)`, 12vh from the top, `--shadow-lg`, `Kanbanchan-rise 120ms ease-out`.

```
3px ink rule
[ input 19px, 14px 18px padding, 1px ink bottom rule ]
results, max-height 46vh scroll:
  PATH (10.5px uppercase) / title (16px); active row --color-accent-200
footer: "3 matches" · "↑↓ move · ⏎ open · esc close"   11px uppercase neutral-600
```

Query grammar: `migration` = text in title+content; `#today` = tag; `migration #today` = both ANDed.

---

## 5. Toast (delete / undo / confirm)

Fixed, centered, 26px from the bottom; ink fill `--color-text`, paper text, `--shadow-md`, same rise animation. Label 14px; the action is 12px uppercase `--color-accent-300`, hover `--color-accent-2-300`.

- Leaf delete → `Deleted — Undo`, 5.2s window.
- Subtree delete → `Delete "X" and its children? — ⏎ Delete`.

---

## 6. Keyboard model

| Key | Tree scope | While renaming |
| --- | --- | --- |
| ↑ / ↓ | move selection | commit, then move |
| → | expand, else enter first child | — |
| ← | collapse, else select parent | — |
| ⏎ | new sibling after subtree, straight into rename | commit + new sibling |
| ⇥ / ⇧⇥ | indent under previous sibling / outdent after parent | same, on the edited node |
| ⌘↑ / ⌘↓ | reorder among siblings | — |
| ⌘⏎ | focus the body textarea | — |
| ⌘N | new child of Inbox, into rename | — |
| ⌘K | search overlay | — |
| ⌘⌫ / ⌦ | delete (confirm if it has children) | — |
| F2 / double-click | rename | — |
| esc | — | commit + leave rename (from the editor: return to tree) |

Autosave only: title debounce 300ms, content 500ms, status decays to blank after ~2.6s. No Save button anywhere.

## 7. Prohibitions

- No modal for create, rename, move, tag, or delete.
- No cards, panels, or section dividers — whitespace and the serif scale carry hierarchy. The three rules in the app (two header, one column hairline) are the entire budget.
- No sans-serif, no icon font for chrome, no second accent inside one small component.
- Tags never outrank the title, in size, weight, or space.
