# Minimal Hierarchical Notes Web App — SPEC.md

## 1. Product Goal

构建一个极简、keyboard-first 的层级笔记 Web 工具。

核心目标：

> 用户可以在 5 秒内创建、定位、编辑、整理一条笔记。

产品不区分“目录”和“笔记”。

所有内容统一使用一种对象：

`Node`

一个 Node 可以同时：

- 有标题
- 有正文
- 有子节点
- 作为导航节点
- 作为普通笔记

因此避免传统笔记工具中的：

- New Folder
- New Section
- New Page
- Move to Folder
- Create Subpage

等高摩擦操作。

---

# 2. Product Principles

## 2.1 One Object Model

系统只有一种核心对象：

```text
Node
```

例如：

```text
Work
  Wells Fargo
    CI/CD
      Migration parity #today #todo
      Release process #followup
```

`Work`、`Wells Fargo`、`CI/CD` 和具体笔记在数据结构上完全相同。

---

## 2.2 Keyboard First

核心操作必须可以完全通过键盘完成。

鼠标用于：

- 点击导航
- 拖动排序
- 可选的 UI 操作

但不能成为主要操作方式。

---

## 2.3 No Modal for Common Actions

以下行为不得使用 modal：

- 创建 Node
- 创建 child
- 重命名
- 移动层级
- 编辑正文
- 添加标签
- 搜索
- 删除

目标是尽可能使用：

- inline editing
- keyboard command
- direct manipulation

---

## 2.4 Capture First, Organize Later

用户可以随时创建笔记，而不需要先决定目录。

全局新建默认进入：

```text
Inbox
```

以后再重新组织。

---

## 2.5 Hierarchy + Dynamic Tags

系统有两套互补的信息组织方式。

### Physical hierarchy

```text
Work
  Wells Fargo
    CI/CD
```

用于表达：

> 这条信息属于哪里？

### Dynamic tags

```text
#today
#tomo
#todo
#followup
```

用于表达：

> 现在需要关注什么？

---

# 3. Technology Stack

V0.1 使用：

```text
Python 3.12+
uv
FastAPI
SQLite
Jinja2
HTMX
Vanilla JavaScript
CSS
```

不使用：

```text
React
Vue
Next.js
Node.js backend
Redux
复杂 frontend build pipeline
```

除非后续证明 Vanilla JS + HTMX 无法满足交互需求。

---

# 4. Runtime Model

应用是一个 Python Web Server。

本地运行：

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8080
```

浏览器打开：

```text
http://127.0.0.1:8080
```

局域网 / Tailscale 模式可以运行：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
```

V0.1 不实现：

- public Internet hosting
- multi-user authentication
- collaboration
- cloud sync

---

# 5. Repository Structure

建议：

```text
notes/
├── pyproject.toml
├── README.md
├── SPEC.md
├── data/
│   └── notes.db
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── db.py
│   ├── models.py
│   ├── repository.py
│   ├── services/
│   │   ├── node_service.py
│   │   ├── tag_service.py
│   │   └── search_service.py
│   ├── routes/
│   │   ├── pages.py
│   │   ├── nodes.py
│   │   └── search.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── partials/
│   │       ├── tree.html
│   │       ├── tree_node.html
│   │       ├── editor.html
│   │       └── search_results.html
│   └── static/
│       ├── app.js
│       └── app.css
└── tests/
    ├── test_nodes.py
    ├── test_tags.py
    └── test_search.py
```

---

# 6. Core Data Model

## 6.1 nodes

```sql
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,

    parent_id TEXT NULL,

    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',

    position REAL NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY(parent_id)
        REFERENCES nodes(id)
        ON DELETE CASCADE
);
```

---

## 6.2 tags

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
```

---

## 6.3 node_tags

```sql
CREATE TABLE node_tags (
    node_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,

    PRIMARY KEY(node_id, tag_id),

    FOREIGN KEY(node_id)
        REFERENCES nodes(id)
        ON DELETE CASCADE,

    FOREIGN KEY(tag_id)
        REFERENCES tags(id)
        ON DELETE CASCADE
);
```

---

# 7. Node Semantics

任何 Node 都可以同时有：

```text
title
content
children
tags
```

禁止增加：

```text
is_folder
is_note
node_type
```

这类字段。

Node 的行为完全由：

```text
有没有 content
有没有 children
```

自然决定。

---

# 8. Tree Depth

数据库允许任意深度。

UI 主要针对：

```text
Level 1
  Level 2
    Level 3
```

进行优化。

但不得在 schema 或 backend 中限制：

```text
max_depth = 3
```

---

# 9. Default Root Nodes

第一次初始化数据库时自动创建：

```text
Inbox
Work
Personal
```

这些也是普通 Node。

其中：

`Inbox`

具有特殊语义：

全局快速创建的 Node 默认成为 Inbox child。

数据库不需要特殊 node type。

可以通过固定配置保存 Inbox node ID。

---

# 10. Tags

## 10.1 Tag Syntax

Tag 直接写在 title 中：

```text
Migration parity check #today #todo
```

也允许正文中存在 tag，但 V0.1 只解析 title 中的 tag。

支持：

```text
#today
#tomo
#todo
#followup
#done
#reading
#idea
```

同时允许任意自定义标签：

```text
#wf
#sonar2
#research
```

---

## 10.2 Tag Parsing

保存 title 时自动提取：

```regex
#([A-Za-z0-9_-]+)
```

Tag name 存储时：

- 去掉 `#`
- 转 lowercase
- 去重

例如：

```text
Follow Jason #Today #FOLLOWUP
```

存储：

```text
today
followup
```

---

## 10.3 Tag Synchronization

每次 title 更新后：

1. parse title tags
2. 获取当前 node_tags
3. 添加新增 tag
4. 删除 title 中已经不存在的 tag
5. 删除孤立 tag 可延后处理

---

# 11. Special Tags

V0.1 内置以下约定：

```text
#today
#tomo
#todo
#followup
#done
```

但它们本质仍然是普通 tag。

禁止创建复杂 task schema，例如：

```text
due_date
task_status
priority
reminder
```

V0.1 不做 task manager。

---

# 12. Main UI

布局：

```text
┌──────────────────────────────────────────────────────┐
│  App name                     Search / command        │
├───────────────────┬──────────────────────────────────┤
│                   │                                  │
│ Tree              │ Editor                           │
│                   │                                  │
│ Inbox             │ Node title                       │
│ Work              │                                  │
│   Wells Fargo     │ Content                          │
│     CI/CD         │                                  │
│                   │                                  │
│ Personal          │                                  │
│                   │                                  │
│ ─────────────     │                                  │
│ #today            │                                  │
│ #tomo             │                                  │
│ #todo             │                                  │
│ #followup         │                                  │
│                   │                                  │
└───────────────────┴──────────────────────────────────┘
```

---

# 13. Tree View

每个 Node 显示：

```text
▸ CI/CD
```

或者：

```text
▾ CI/CD
    Migration #today
    Release #followup
```

要求：

- child indentation 清晰
- title inline editable
- tags 视觉弱化
- 当前选中 Node 高亮
- parent 有 children 时可折叠

---

# 14. Editor

右侧 Editor 包含：

```text
Title
Content
```

Title：

- 单行输入
- 自动保存
- 实时解析 tags

Content：

V0.1 使用：

```text
plain textarea
```

或简单 Markdown textarea。

暂时不要加入：

- rich text
- block editor
- WYSIWYG
- slash commands

Markdown rendering 可以以后加入。

---

# 15. Core Keyboard Interaction

## 15.1 Navigation

```text
Arrow Up
```

选择上一个可见 Node。

```text
Arrow Down
```

选择下一个可见 Node。

```text
Arrow Right
```

展开当前 Node。

若已经展开，则进入第一个 child。

```text
Arrow Left
```

折叠当前 Node。

若已经折叠，则选择 parent。

---

# 16. Creation

## 16.1 Enter

当焦点位于 Tree：

```text
Enter
```

在当前 Node 后面创建 sibling。

例如：

```text
CI/CD
Migration
```

当前选中 `CI/CD`。

按 Enter：

```text
CI/CD
Untitled
Migration
```

新 Node title 立即进入编辑状态。

---

## 16.2 Tab

当刚创建 Node 或当前 Node 被选中：

```text
Tab
```

将当前 Node indent 一级。

例如：

```text
CI/CD
Migration
```

选择 `Migration`，按 Tab：

```text
CI/CD
  Migration
```

---

## 16.3 Shift+Tab

提升一级：

```text
CI/CD
  Migration
```

变为：

```text
CI/CD
Migration
```

---

# 17. Global Create

快捷键：

```text
Cmd+N
```

Windows/Linux：

```text
Ctrl+N
```

行为：

1. 在 Inbox 创建 child Node
2. 自动选中
3. title 进入编辑状态
4. 用户直接输入

不弹窗。

---

# 18. Focus Editor

推荐：

```text
Cmd+Enter
```

或：

```text
Ctrl+Enter
```

行为：

从 Tree 转到 Editor content。

---

# 19. Search

快捷键：

```text
Cmd+K
```

Windows/Linux：

```text
Ctrl+K
```

打开轻量 search overlay。

搜索支持：

```text
migration
Jason
#today
#todo
#today migration
```

V0.1 搜索字段：

```text
title
content
tags
```

---

# 20. Search Semantics

搜索：

```text
#today
```

仅返回含有 tag：

```text
today
```

的 Node。

搜索：

```text
migration
```

匹配：

```text
title
content
```

搜索：

```text
migration #today
```

相当于：

```text
text contains "migration"
AND
tag = "today"
```

---

# 21. Dynamic Tag Views

左侧树底部固定显示：

```text
#today
#tomo
#todo
#followup
```

点击后不是进入一个真实 Node。

而是打开 Dynamic View。

例如：

```text
#today
```

显示：

```text
TODAY

Work / Wells Fargo / CI/CD
Migration parity

Personal / House
Call contractor
```

每个结果必须显示 path：

```text
Work / Wells Fargo / CI/CD
```

便于理解上下文。

---

# 22. Autosave

编辑必须自动保存。

禁止：

```text
Save
Apply
Confirm
```

按钮作为主要工作流。

---

## 22.1 Title Autosave

推荐 debounce：

```text
300 ms
```

---

## 22.2 Content Autosave

推荐 debounce：

```text
500 ms
```

---

## 22.3 Save Status

Editor 可以显示非常弱的状态：

```text
Saving...
Saved
```

正常状态下不应抢视觉注意力。

---

# 23. Reordering

V0.1 支持 drag-and-drop：

```text
Node A
Node B
Node C
```

拖动改变：

```text
position
```

同时支持键盘：

```text
Cmd+ArrowUp
Cmd+ArrowDown
```

用于 sibling reorder。

Windows/Linux：

```text
Ctrl+ArrowUp
Ctrl+ArrowDown
```

---

# 24. Position Strategy

推荐使用稀疏数值 position。

例如：

```text
1000
2000
3000
```

插入中间：

```text
1500
```

避免每次插入都更新大量记录。

必要时后台重新 normalize。

---

# 25. Moving Nodes

改变 hierarchy 本质上是修改：

```text
parent_id
position
```

Tab：

```text
parent_id = previous_visible_sibling.id
```

并成为其最后一个 child。

Shift+Tab：

当前：

```text
A
  B
```

变成：

```text
A
B
```

其中 B 的新 parent 是 A 的 parent。

---

# 26. Delete

快捷键：

```text
Cmd+Backspace
```

Windows/Linux：

```text
Ctrl+Backspace
```

如果 Node：

- 没有 children：直接删除，可提供短暂 Undo
- 有 children：V0.1 可以要求二次确认

避免意外删除整个 subtree。

---

# 27. Undo Delete

建议 V0.1 做简单 soft delete，而不是立即永久删除。

nodes 增加：

```sql
deleted_at TEXT NULL
```

正常查询：

```sql
WHERE deleted_at IS NULL
```

删除后：

```text
Deleted — Undo
```

保留约：

```text
5 seconds
```

V0.1 不需要 Trash UI。

---

# 28. API Design

## Page

```http
GET /
```

返回主界面。

---

## Tree

```http
GET /api/nodes/tree
```

返回 Node tree。

---

## Get Node

```http
GET /api/nodes/{id}
```

---

## Create Node

```http
POST /api/nodes
```

Payload：

```json
{
  "parent_id": "...",
  "after_id": "...",
  "title": ""
}
```

返回创建的 Node。

---

## Update Node

```http
PATCH /api/nodes/{id}
```

支持：

```json
{
  "title": "...",
  "content": "...",
  "parent_id": "...",
  "position": 1500
}
```

---

## Delete Node

```http
DELETE /api/nodes/{id}
```

执行 soft delete。

---

## Undo Delete

```http
POST /api/nodes/{id}/restore
```

---

## Search

```http
GET /api/search?q=...
```

例如：

```text
/api/search?q=%23today
```

---

## Tag View

```http
GET /api/tags/{tag}/nodes
```

例如：

```text
/api/tags/today/nodes
```

---

# 29. Backend Layers

## routes

负责：

```text
HTTP parsing
validation
response
```

---

## services

负责：

```text
create node
move node
indent
outdent
tag parsing
search parsing
```

---

## repository

负责：

```text
SQL queries
SQLite access
transactions
```

Business logic 不应直接写在 FastAPI route 中。

---

# 30. SQLite Requirements

启动时执行：

```sql
PRAGMA foreign_keys = ON;
```

推荐：

```sql
PRAGMA journal_mode = WAL;
```

原因：

浏览器 autosave 时可能产生短时间频繁写入。

---

# 31. Database Initialization

第一次运行：

1. 创建数据库
2. 创建 tables
3. 创建 indexes
4. 创建 root Nodes：

```text
Inbox
Work
Personal
```

数据库 migration V0.1 可以采用简单：

```text
schema_version
```

机制。

不要求引入 Alembic。

---

# 32. Indexes

至少增加：

```sql
CREATE INDEX idx_nodes_parent
ON nodes(parent_id);

CREATE INDEX idx_nodes_updated
ON nodes(updated_at);

CREATE INDEX idx_node_tags_node
ON node_tags(node_id);

CREATE INDEX idx_node_tags_tag
ON node_tags(tag_id);
```

---

# 33. Search Implementation

V0.1 数据规模预计较小。

可以先使用：

```sql
LIKE
```

搜索。

未来如果需要再迁移 SQLite FTS5。

不要在 V0.1 过早优化。

---

# 34. HTMX Responsibilities

HTMX 主要处理：

```text
load editor
refresh tree fragment
search results
tag views
CRUD partial updates
```

---

# 35. JavaScript Responsibilities

Vanilla JS 处理高频交互：

```text
keyboard shortcuts
tree selection
focus management
Enter create
Tab indent
Shift+Tab outdent
Arrow navigation
Cmd+K
autosave debounce
drag/drop
```

原则：

> 高频交互尽量不依赖 full page refresh。

---

# 36. State Model

Frontend 至少维护：

```text
selectedNodeId
editingNodeId
expandedNodeIds
searchOpen
saveState
```

V0.1 不引入全局 state management library。

---

# 37. URL Behavior

选中 Node 后 URL 可以更新为：

```text
/n/{id}
```

这样：

- 浏览器 refresh 不丢位置
- 可以 bookmark
- 可以复制链接

但页面仍保持 SPA-like interaction。

---

# 38. Initial UX Flow

用户打开：

```text
http://localhost:8080
```

看到：

```text
Inbox
Work
Personal
```

---

用户选：

```text
Work
```

按：

```text
Enter
```

输入：

```text
Wells Fargo
```

按：

```text
Tab
```

得到：

```text
Work
  Wells Fargo
```

再次：

```text
Enter
```

输入：

```text
CI/CD
```

继续：

```text
Enter
Migration parity #today #todo
```

整个 hierarchy 构建过程不出现任何 modal。

---

# 39. Example Final Tree

```text
Inbox
  Check article #today

Work
  Wells Fargo
    CI/CD
      Migration parity #today #todo
      Release process #followup

Personal
  House
    Call contractor #tomo #todo
```

点击：

```text
#today
```

看到：

```text
TODAY

Inbox
Check article

Work / Wells Fargo / CI/CD
Migration parity
```

---

# 40. Performance Goals

V0.1 设计目标：

```text
Page load:
< 500 ms local

Node open:
perceived instant

Create node:
< 100 ms local

Autosave:
< 200 ms typical DB operation

Search:
< 100 ms for 10,000 nodes
```

具体性能指标不作为硬实时 SLA，但实现应以此为目标。

---

# 41. UX Metrics

核心产品指标：

```text
Create new note:
<= 2 explicit actions

Create child:
<= 2 actions

Reorganize node:
<= 3 actions

Open global search:
1 shortcut

Add tag:
type directly into title
```

---

# 42. V0.1 Must Have

必须完成：

- Node tree
- Node CRUD
- title
- content
- parent-child hierarchy
- inline create
- Enter create sibling
- Tab indent
- Shift+Tab outdent
- keyboard navigation
- autosave
- tag extraction
- `#today`
- `#tomo`
- `#todo`
- `#followup`
- tag dynamic views
- search
- `Cmd/Ctrl+K`
- global Inbox create
- `Cmd/Ctrl+N`
- drag reorder
- SQLite persistence
- browser UI

---

# 43. Explicit Non-Goals

V0.1 不实现：

- authentication
- multiple users
- collaboration
- sharing
- mobile native app
- cloud sync
- attachments
- images
- audio
- tables
- rich text editor
- block editor
- backlinks
- graph view
- templates
- calendar
- recurring tasks
- reminders
- notifications
- AI assistant
- embeddings
- semantic search
- browser extension
- import OneNote
- import Notion
- export PDF
- public deployment

---

# 44. Security Assumption

V0.1 假定：

```text
trusted local environment
```

默认监听：

```text
127.0.0.1
```

如果用户使用：

```text
0.0.0.0
```

则应明确知道服务可能被局域网其他设备访问。

Tailscale deployment 可以后续增加简单 authentication。

---

# 45. Testing Requirements

至少覆盖：

## Node

```text
create root
create child
create sibling
delete
restore
```

## Hierarchy

```text
indent
outdent
move
reorder
prevent cycles
```

特别要防止：

```text
A
  B
```

把 A 移动到 B 下：

```text
B
  A
```

这种 cycle。

---

## Tags

测试：

```text
#today
#Today
duplicate tags
remove tag
multiple tags
```

---

## Search

测试：

```text
title search
content search
tag search
text + tag search
```

---

# 46. Tree Integrity Rules

必须保证：

1. Node 不能成为自己的 parent
2. Node 不能移动到自己的 descendant 下
3. deleted node 默认不出现在 tree 中
4. sibling position 必须可排序
5. parent 删除时 descendants 同时 soft-delete 或保持一致策略

V0.1 推荐：

删除 parent：

```text
soft-delete entire subtree
```

restore parent：

```text
restore entire subtree
```

---

# 47. Markdown

V0.1：

正文按照 Markdown 文本存储。

编辑器只需要：

```text
textarea
```

可以选择增加：

```text
Edit | Preview
```

但不是 Must Have。

---

# 48. Visual Design

整体风格：

```text
dense
minimal
quiet
keyboard-centric
```

参考方向：

```text
Linear
Obsidian
Apple Notes
VS Code command palette
```

避免：

```text
Notion-like block chrome
large cards
heavy borders
oversized typography
complex toolbar
```

树应该尽可能容纳大量信息。

---

# 49. Tag Visual Style

用户输入：

```text
Migration parity #today #todo
```

Tree 中可以渲染为：

```text
Migration parity   today  todo
```

Tag 视觉应弱于 title。

点击 tag：

进入对应 Dynamic View。

---

# 50. Product Definition

V0.1 产品定义：

> 一个 keyboard-first hierarchical notes tool，通过单一 Node 模型消除“目录”和“笔记”的区别，通过 tags 提供动态工作视图，让用户能够在几秒内 capture、organize 和 retrieve 信息。

核心设计公式：

```text
Hierarchy
=
Where does this belong?

Tags
=
What needs my attention?
```

最终目标：

```text
minimum structure friction
+
maximum retrieval speed
```

---

# 51. Implementation Order

推荐严格按照以下顺序实现。

## Phase 1 — Data Foundation

实现：

```text
SQLite
schema
repository
Node CRUD
tree query
tests
```

完成标准：

backend 可以完整创建和查询 hierarchy。

---

## Phase 2 — Basic Web UI

实现：

```text
FastAPI
Jinja2
tree
editor
click node
edit title
edit content
```

---

## Phase 3 — Inline Tree Operations

实现：

```text
Enter
Tab
Shift+Tab
Arrow navigation
autosave
```

这是 V0.1 最核心阶段。

---

## Phase 4 — Tags

实现：

```text
tag parsing
node_tags sync
#today
#tomo
#todo
#followup
dynamic views
```

---

## Phase 5 — Search

实现：

```text
Cmd+K
text search
tag search
text + tag filtering
```

---

## Phase 6 — Polish

实现：

```text
drag/drop
undo delete
save status
URL state
responsive layout
```

---

# 52. Definition of Done

V0.1 完成时，用户必须可以只用键盘完成：

```text
打开应用

Cmd+N

输入：
Follow Jason about migration #today #followup

Enter

输入正文

Cmd+K

输入：
#today

找到刚才的笔记

进入 Work / Wells Fargo

Tab / Shift+Tab
调整 hierarchy
```

整个过程中：

```text
不需要 modal
不需要 Save
不需要选择 Folder 类型
不需要打开 Tag Manager
```
