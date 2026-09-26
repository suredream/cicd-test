# Remy 规格说明（初版）

## 1. 目标与边界

Remy 是一个本地 Markdown 知识库管理工具。它将知识数据与程序代码分离：

- **导入**：从 `~/Downloads` 发现 Markdown，基于开头内容自动补全元数据并移动入库。
- **检索与浏览**：Web 和 CLI 都能搜索、过滤和显示 `$KM` 中的笔记。
- **归档**：以 `archive` 标签为唯一触发条件，将符合条件的笔记移动到 Archive。
- **链接完整性**：移动、重命名后修复 `$KM` 内受影响的 Markdown 链接和 Wiki 链接。

Remy 不负责同步、云存储、全文编辑器、自动删除笔记或自动扩充标签词表。

## 2. 仓库与知识库位置

项目名为 `remy`。程序仓库与知识库目录必须分离。

```text
remy/
├── src/
│   ├── web/                  # 浏览、搜索和展示界面
│   ├── cli/                  # 面向终端的查询和维护命令
│   └── skill/                # Agent 可调用的受控工作流
├── docs/                     # 开发与产品文档（可选）
└── spec.md
```

知识库根目录由环境变量 `KM` 指定：

```sh
export KM="/absolute/path/to/Knowledge"
```

启动任何会读取或写入知识库的 Remy 功能前，必须校验 `KM` 已定义、是绝对路径、存在且可读；写操作还必须可写。不得把 `KM` 默认为项目目录、当前目录或用户主目录。

## 3. `$KM` 目录结构

```text
$KM/
├── Notes/                    # 活跃的非项目笔记；不再分目录
├── Projects/
│   ├── remy/                 # 活跃项目；一个项目一个目录
│   └── <project-slug>/
├── Archive/
│   ├── 2026/                 # 已归档的普通笔记
│   ├── 2025/
│   └── projects/             # 已归档项目笔记，按文件名扁平保存
├── _meta/                    # Remy 管理的内部数据，非笔记正文
├── TAGS.md                   # 允许使用的标签词表
└── MANAGEMENT.md             # 人与 Agent 共用的操作规则
```

目录结构原则：

- Markdown 正文只允许位于 `Notes/`、`Projects/<project-slug>/`、`Archive/<year>/` 或 `Archive/projects/`。
- 只有 `Projects/<project-slug>/` 与 `Archive/<group>/` 使用第二层目录；不得创建更深的笔记目录。
- `Notes/` 不分子目录。项目结束或不活跃时，笔记使用 Archive，而非创建年份、主题或标签目录。
- `_meta/` 可保存索引缓存、操作日志与待确认的标签建议；它不是用户笔记位置，搜索默认忽略其内容。

## 4. 笔记格式和标签

每一篇由 Remy 导入的笔记应具有如下最小 Frontmatter：

```markdown
---
title: Remy CLI 设计
tags: [remy, cli, design]
created: 2026-09-26
updated: 2026-09-26
---

# Remy CLI 设计
```

规则：

- `title` 是展示标题，并应与首个 H1 一致；若原文没有 H1，导入时创建一个。
- `tags` 为零个或多个标签；所有实际写入的标签都必须出现于 `$KM/TAGS.md`。
- `created` 记录首次入库日期；`updated` 记录 Remy 最后一次改变正文或元数据的日期，格式固定为 `YYYY-MM-DD`。
- 没有可信标签时，使用 `tags: []`，仍可导入。
- 已有 Frontmatter 的导入文件保留未被 Remy 管理的字段；`title`、`tags`、`created`、`updated` 按本规范归一化。
- 标签为小写短横线标识符，例如 `machine-learning`。`archive` 是保留标签，用于触发归档。

`TAGS.md` 是允许标签的唯一来源，建议按主题维护：

```markdown
# Allowed Tags

## Content type
- meeting
- decision
- idea
- reference
- how-to

## Topic
- remy
- cli
- web
- design
```

当模型推断出不在 `TAGS.md` 的标签时，绝不可写进目标笔记；应记录为“建议新增标签”，由用户手动批准后再写入 `TAGS.md`。

## 5. 文件名、冲突与链接

导入文件使用由标题生成的 kebab-case 文件名：

```text
remy-cli-design.md
```

同一目标目录内如已存在同名文件，Remy 必须保留两个文件，并按以下顺序尝试：

```text
remy-cli-design-2.md
remy-cli-design-3.md
```

直到获得未占用文件名。不得覆盖已有文件。

只要 Remy 移动或重命名 Markdown 文件，就必须扫描 `$KM` 中的用户笔记并更新指向该文件的链接：

- 相对 Markdown 链接，例如 `[设计](../Notes/remy-cli-design.md)`；
- Wiki 链接，例如 `[[remy-cli-design]]`、`[[remy-cli-design|CLI 设计]]`；
- 带锚点链接，例如 `[[remy-cli-design#命令设计]]`。

若一个 Wiki 链接的名称存在歧义，Remy 不得猜测替换；在操作报告中标记为需人工处理。外部 URL、附件链接和无法安全解析的表达式不得修改。

## 6. Skill：`ingest-downloads`

### 输入与范围

- 扫描目录：`~/Downloads` 的第一层普通文件，不递归扫描子目录。
- 候选文件：扩展名为 `.md` 或 `.markdown`，不区分大小写。
- 一个候选文件仅在成功入库后才从 Downloads 移除。

### 行为

对每个候选文件，Skill 自动执行下列步骤：

1. 读取 Frontmatter（若存在）、前 10 行及必要的首段正文。
2. 推断标题、现有允许标签、建议新增标签和所属项目。
3. 若能高置信度匹配现有项目目录，目标为 `$KM/Projects/<project-slug>/`；否则目标一律为 `$KM/Notes/`。
4. 生成或规范化 Frontmatter、补齐 H1、生成可用文件名。
5. 应用数字后缀解决重名冲突。
6. 将文件从 `~/Downloads` **移动**到目标位置，不保留源文件副本。
7. 写入操作记录，并返回每个文件的来源、目标、标题、实际标签与建议新增标签。

该工作流已经得到用户授权，可自动写入 Frontmatter 并移动符合范围的 Markdown。它仍不得删除内容、覆盖现有文件、创建项目目录、或把未经批准的新标签写入笔记。

项目匹配仅可命中已存在的 `$KM/Projects/<project-slug>/`。如果无法可靠判断项目，选择 `Notes/`；不需要询问，也不创建新的项目目录。

导入应尽量保持原正文顺序与内容。任何单个文件处理失败时，保留其原件在 Downloads，并继续处理其他候选文件；最终报告失败原因。

## 7. Skill：`archive-notes`

### 选择条件

扫描 `$KM/Notes/` 与 `$KM/Projects/*/` 中的 Markdown。只有 Frontmatter 的 `tags` 包含精确标签 `archive` 的笔记才是候选项。已经位于 `$KM/Archive/` 的文件必须跳过。

### 移动规则

- 来源为 `Notes/` 的笔记移动到 `$KM/Archive/<year>/`。
- `<year>` 优先取 `updated` 的年份；无有效 `updated` 时取 `created`；仍不可用时取当前年份。
- 来源为 `Projects/<slug>/` 的笔记移动到 `$KM/Archive/projects/`。
- 项目笔记的归档名为 `<slug>-<原文件名>`，例如 `remy-cli-design.md`，以维持 Archive 的两层目录限制。
- 所有归档目标均使用同样的 `-2`、`-3` 冲突规则。
- 保留全部 Frontmatter、正文和 `archive` 标签；不删除任何标签。
- 每次移动后执行链接修复。

工作流是幂等的：已归档文件不会在重复运行时再次移动或再次改名。

## 8. CLI 初步接口

所有命令均从环境变量读取 `$KM`，并在启动时执行路径校验。

```sh
remy search <query> [--tag <tag>] [--path notes|projects|archive] [--json]
remy show <path-or-id>
remy ingest downloads [--dry-run] [--json]
remy archive [--dry-run] [--json]
remy links check [--json]
remy tags list
remy tags suggest
```

- `search` 搜索标题、Tag、正文与路径，默认排除 `_meta/`，默认包含 Archive；`--path` 可缩小范围。
- `show` 显示 Frontmatter、路径与渲染前的 Markdown 原文。
- `ingest downloads` 对应 `ingest-downloads`；`--dry-run` 必须显示预计 Frontmatter、目标路径、冲突改名与标签建议，但不写入或移动。
- `archive` 对应 `archive-notes`；`--dry-run` 仅报告将归档的文件及链接改动。
- `links check` 只报告失效、歧义或未能自动修复的内部链接。
- `tags suggest` 汇总 `_meta/` 中待确认的新标签建议，不会修改 `TAGS.md`。

所有修改型命令应产生机器可读的变更记录；`--json` 输出稳定的 JSON，便于 Web 和 Skill 复用。普通输出应简洁地报告新增、移动、跳过、冲突与失败。

## 9. Web 初步设计

Web 是 `$KM` 的只读优先浏览与搜索界面；第一版不需要内置正文编辑器。

### 页面

1. **Search**：全文搜索框、Tag 过滤、位置过滤（Notes / Projects / Archive）、结果列表与高亮摘要。
2. **Note detail**：标题、路径、Tag、日期、渲染后的 Markdown、反向链接和原文件入口。
3. **Projects**：现有项目目录列表；进入后列出该目录第一层笔记。
4. **Archive**：按年份与 `projects` 分组浏览。
5. **Maintenance**：展示最近导入、归档结果、待确认标签、失效链接与歧义 Wiki 链接；操作按钮应先展示 dry-run 计划，再明确执行。

Web 和 CLI 必须共用同一个 Markdown 解析、Frontmatter 校验、索引与搜索层，避免两套标签或链接解释规则。

## 10. Skill 接口初步设计

Skill 不直接拥有业务规则，而是调用与 CLI 相同的核心能力，并返回结构化结果。

```ts
type IngestDownloadsInput = {
  dryRun?: boolean;
};

type ArchiveNotesInput = {
  dryRun?: boolean;
};

type OperationResult = {
  changed: Array<{
    source: string;
    destination: string;
    action: "imported" | "archived" | "renamed";
    title?: string;
    tags?: string[];
    proposedTags?: string[];
    linksUpdated?: number;
  }>;
  skipped: Array<{ path: string; reason: string }>;
  failures: Array<{ path: string; reason: string }>;
  linkWarnings: Array<{ path: string; link: string; reason: string }>;
};
```

接口要求：

- `dryRun: true` 不得产生任何文件变更。
- 返回值必须区分成功变更、跳过项、失败项和链接警告。
- 新标签只能存在于 `proposedTags`，直到用户编辑 `TAGS.md` 批准。
- 每次写入前后应记录足够的变更信息，供 Maintenance 页面与人工回溯使用。

## 11. 安全与维护约束

- Remy 从不删除用户笔记。
- Remy 从不覆盖已存在文件；所有冲突均以数值后缀消解。
- `Archive` 是终态位置：归档任务不会再次移动其中的文件。
- 无法解析的文件、Frontmatter 或链接应该被报告，而不是通过猜测改写。
- 索引和操作日志位于 `_meta/`，可随时重建；用户笔记始终是事实来源。
- 用户可以手工编辑任何 Markdown、`TAGS.md` 和 `MANAGEMENT.md`；下一次 Remy 操作应重新从磁盘读取真实状态，不依赖过期缓存。
