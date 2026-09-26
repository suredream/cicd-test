# SPEC.md — Daily Task Log

## 1. Product Overview

**Working Name:** Daily Task Log  
**Platform:** Windows  
**Primary Language:** Python  
**Product Type:** Keyboard-first daily ToDo and completion log  
**Primary Goal:** Provide a minimal, fast way to capture today's tasks, complete them, carry unfinished work forward automatically, and review completion history from both a popup UI and Windows Terminal.

The product is intentionally not a full project-management system. It is a lightweight daily work log with a ToDo layer.

Core workflow:

```text
Ctrl + Shift + Z
→ popup opens on Today
→ type a task
→ Enter
→ task is added
→ Space / checkbox marks it complete
→ completion time is recorded
→ completed task moves to the lower completed section
→ Esc closes the popup
```

Unfinished work automatically moves forward to the current day until completed.

---

## 2. Product Principles

1. **Keyboard-first**
   - Core workflows must work without a mouse.
   - Mouse interaction is supported but not required.

2. **Today-first**
   - Opening the app always starts on Today.
   - The primary purpose is managing current-day work.

3. **Minimal**
   - No project hierarchy, tags, priorities, reminders, cloud sync, or complex configuration in MVP.

4. **Local-first**
   - All data is stored locally in SQLite.
   - No account or network connection is required.

5. **Completion log, not just ToDo**
   - Completing a task records when the work was finished.
   - Historical views emphasize completed work.

6. **Low friction**
   - Global hotkey opens the UI immediately.
   - Creating and completing tasks should take only a few keystrokes.

---

## 3. Target User

The product is designed for a Windows user who:

- works primarily from a keyboard;
- wants a lightweight daily task list;
- wants unfinished tasks to follow them automatically;
- wants to review what was completed on previous days;
- frequently uses Windows Terminal;
- prefers local tools with minimal runtime dependencies;
- does not want a full-featured task management application.

---

## 4. Technical Constraints

The technical stack must stay within the same tool constraints as ClipSeek.

### Required Stack

```text
Python 3.x
tkinter
sqlite3
ctypes
datetime
argparse
json
pathlib
```

### Windows Integration

Use Win32 APIs through `ctypes` where needed.

Preferred APIs:

```text
RegisterHotKey
GetMessageW
PostMessageW
SetForegroundWindow
CreateMutexW
```

### Runtime Dependency Goal

No third-party Python package should be required for the MVP.

The app should run using the Python standard library plus Windows APIs.

---

## 5. Core User Experience

The application runs in the background.

Default global hotkey:

```text
Ctrl + Shift + Z
```

When triggered:

1. Open the popup.
2. Navigate to Today regardless of the last viewed date.
3. Focus the task input field.
4. Show today's unfinished tasks first.
5. Show today's completed tasks below them.

Example:

```text
┌──────────────────────────────────────────────┐
│ Add a task...                               │
├──────────────────────────────────────────────┤
│ ☐ Review sandbox DB             carried 2d │
│ ☐ Update permit pipeline             today │
│ ☐ Write API notes                    today │
│──────────────────────────────────────────────│
│ ☑ Reply to Jun                      10:42  │
│ ☑ Review API design                 09:15  │
├──────────────────────────────────────────────┤
│       ←      Sep 26      Today      →       │
└──────────────────────────────────────────────┘
```

---

## 6. UI Layout

The UI is a small popup window implemented in `tkinter`.

### Components

The popup contains:

1. Task input field
2. Unfinished task list
3. Completed task list
4. Date navigation controls
5. Today button

### Date Navigation

Bottom navigation:

```text
←      Sep 26      Today      →
```

Behavior:

- `←` moves to the previous day.
- `→` moves to the next day.
- `Today` jumps immediately to the current local date.
- Opening the popup always resets the current view to Today.
- Future dates are valid views.

---

## 7. Task Creation

### Today

When viewing Today:

1. User types a title in the input field.
2. User presses Enter.
3. A new task is created for Today.
4. Input field is cleared.
5. New task appears in the unfinished section.

### Future Date

Users may navigate to a future date and add tasks there.

Example:

```text
Sep 28
```

Typing:

```text
Prepare project review
```

and pressing Enter creates:

```text
task_date = 2026-09-28
```

### Past Dates

Past dates are intended primarily for historical review.

MVP behavior:

- editing existing task titles is allowed;
- deleting is allowed;
- completed tasks may be reopened;
- creating new historical tasks is not required.

---

## 8. Task Data Model

Recommended schema:

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    title TEXT NOT NULL,

    task_date TEXT NOT NULL,
    original_date TEXT NOT NULL,

    created_at TEXT NOT NULL,
    updated_at TEXT,

    completed_at TEXT,
    deleted_at TEXT
);
```

### Field Semantics

#### `task_date`

The date on which the task currently belongs.

This field changes when an unfinished task is carried forward.

#### `original_date`

The date on which the task was originally created.

This never changes.

Used to calculate carry-over age.

#### `created_at`

Exact timestamp when the task was created.

#### `updated_at`

Timestamp of the most recent title edit or other meaningful mutation.

#### `completed_at`

```text
NULL
```

means unfinished.

A timestamp means completed.

No separate `is_completed` field is required.

#### `deleted_at`

```text
NULL
```

means active.

A timestamp means soft-deleted.

---

## 9. Carry-Over Behavior

Carry-over is a core feature.

### Rule

Any unfinished task whose:

```text
task_date < today
```

must automatically move to Today.

This continues every day until the task is completed.

Example:

```text
Sep 24
Create:
☐ Update sandbox DB
```

If unfinished:

```text
Sep 25
task_date → Sep 25
```

Still unfinished:

```text
Sep 26
task_date → Sep 26
```

If completed on Sep 26:

```text
completed_at = Sep 26 10:42
task_date = Sep 26
```

The task stops moving forward.

### Important Historical Rule

Carry-over is a **move**, not a copied historical record.

Therefore:

```text
Sep 24
```

will no longer show the task after it has moved to a later day.

Historical views should not display carried-forward tasks on their previous dates.

### Original Date Preservation

Even though `task_date` moves, retain:

```text
original_date
created_at
```

This allows UI and CLI to show:

```text
carried 2d
```

without creating duplicate records.

---

## 10. When Carry-Over Runs

Carry-over should run:

1. at application startup;
2. whenever the popup is opened;
3. when the Today button is pressed;
4. before CLI queries that include Today.

Recommended operation:

```sql
UPDATE tasks
SET task_date = :today
WHERE completed_at IS NULL
  AND deleted_at IS NULL
  AND task_date < :today;
```

Do not modify:

```text
original_date
created_at
```

---

## 11. Task Ordering

### Unfinished Section

Unfinished tasks appear at the top.

Recommended ordering:

```text
older carried-over tasks first
→ newer carried-over tasks
→ today's newly created tasks
```

SQL concept:

```sql
ORDER BY
    original_date ASC,
    created_at ASC
```

This naturally gives older backlog higher visibility.

### Completed Section

Completed tasks appear below unfinished tasks.

Completed tasks:

- show a checked checkbox;
- use strikethrough title styling;
- display completion time;
- sort by completion time descending.

Example:

```text
☑ Reply to Jun             10:42
☑ Review API design        09:15
```

Recommended ordering:

```sql
ORDER BY completed_at DESC
```

---

## 12. Completion Behavior

A task can be completed using:

```text
checkbox click
```

or:

```text
Space
```

when selected.

When completed:

```text
completed_at = current timestamp
updated_at = current timestamp
```

The task:

1. becomes visually checked;
2. title receives strikethrough styling;
3. moves from unfinished section to completed section;
4. displays completion time.

---

## 13. Reopening a Completed Task

If a completed task is unchecked:

```text
completed_at = NULL
updated_at = now
task_date = today
```

Important rule:

> Reopened tasks always return to Today.

This applies even when the task is reopened while browsing a historical date.

Example:

```text
Viewing Sep 20
☑ Review API
```

User unchecks it on Sep 26:

```text
task_date = Sep 26
completed_at = NULL
```

The task disappears from Sep 20 and appears in today's unfinished list.

---

## 14. Editing Task Titles

Users may edit both unfinished and completed tasks.

Preferred interaction:

```text
F2
```

Optional mouse interaction:

```text
double-click task title
```

Editing a task title updates:

```text
title
updated_at
```

Editing does **not** change:

```text
created_at
original_date
completed_at
```

Completed status remains unchanged.

A completed task remains struck through after its title is edited.

---

## 15. Soft Delete

Tasks are never immediately hard-deleted from SQLite.

When user presses:

```text
Delete
```

set:

```text
deleted_at = current timestamp
```

Deleted tasks are excluded from normal UI and CLI queries.

Example query condition:

```sql
WHERE deleted_at IS NULL
```

Potential future functionality:

```text
Undo delete
Restore deleted tasks
Permanent cleanup
```

These are not required in MVP.

---

## 16. Keyboard Controls

Required shortcuts:

```text
Ctrl+Shift+Z    Open popup and jump to Today

Enter           Create task from input field

↑               Move selection up
↓               Move selection down

Space           Complete / reopen selected task

F2              Edit selected task title

Delete          Soft-delete selected task

Left Arrow      Previous date
Right Arrow     Next date

Ctrl+T          Jump to Today

Escape          Close popup
```

### Focus Behavior

When popup opens:

```text
focus = task input
```

When navigating tasks with arrow keys:

```text
focus may move to task list
```

The interaction should remain usable without mouse input.

---

## 17. Checkbox Behavior

Every task displays a checkbox.

Examples:

```text
☐ unfinished
☑ completed
```

The checkbox may be implemented with:

```text
tkinter.Checkbutton
```

or a custom row widget.

Requirements:

- checkbox state reflects completion status;
- clicking the checkbox changes completion state;
- keyboard Space provides equivalent behavior;
- completed title uses strikethrough.

---

## 18. Strikethrough Rendering

Completed items must visibly show a crossed-out title.

Use a tkinter Font configured with:

```text
overstrike = True
```

Completion time should remain readable and should not be struck through.

---

## 19. Date Semantics

All dates and timestamps use local Windows system time.

Use:

```python
datetime.datetime.now()
datetime.date.today()
```

Persist timestamps in ISO-8601 compatible strings.

Recommended:

```text
2026-09-26T10:42:18
```

Task date:

```text
2026-09-26
```

---

## 20. Historical Browsing

Users may browse:

```text
previous day
next day
future dates
```

### Past Date View

Historical dates display tasks whose final `task_date` remains that date.

Because unfinished tasks are carried forward, past dates generally contain completed tasks.

A task originally created Sep 24 but carried to Sep 26 does not appear on Sep 24.

This is intentional.

---

## 21. Today Button

The UI must include an explicit Today button.

Layout:

```text
←      Sep 26      Today      →
```

Clicking Today:

1. changes the current view date to the system date;
2. runs carry-over processing;
3. reloads the task list;
4. focuses the task input field.

Keyboard equivalent:

```text
Ctrl + T
```

---

## 22. CLI

The same SQLite database is accessible from Windows Terminal.

CLI command name:

```text
todo
```

The CLI is primarily for viewing history and completion status.

MVP does not require the CLI to manage tasks.

---

## 23. CLI Commands

### Today

```bash
todo
```

or:

```bash
todo today
```

Example:

```text
2026-09-26

○ Update sandbox DB        carried 2d
○ Write SPEC                    today
✓ Reply to Jun                  10:42
✓ Review API design             09:15

2 / 4 completed
```

### Yesterday

```bash
todo yesterday
```

### Specific Date

```bash
todo 2026-09-20
```

### Week View

```bash
todo week
```

Suggested output:

```text
Sep 20    8 / 10
Sep 21    6 / 8
Sep 22    7 / 7
Sep 23    4 / 6
Sep 24    9 / 11
Sep 25    5 / 5
Sep 26    2 / 4
```

Today may include unfinished tasks.

Past dates normally reflect completed work because incomplete tasks have moved forward.

---

## 24. CLI Carry-Over Indicator

For unfinished tasks on Today, display how long the task has been carried.

Examples:

```text
○ Update sandbox DB        carried 2d
○ Review project notes     carried 5d
○ Write SPEC                    today
```

Calculate:

```text
today - original_date
```

If difference is `0 days`, display:

```text
today
```

If greater than zero, display:

```text
carried Nd
```

---

## 25. CLI Implementation

Use:

```text
argparse
```

Suggested structure:

```text
todo
todo today
todo yesterday
todo week
todo YYYY-MM-DD
```

---

## 26. Shared Database

UI and CLI must use the same database.

Recommended location:

```text
%LOCALAPPDATA%\DailyTaskLog\
```

Example:

```text
C:\Users\<user>\AppData\Local\DailyTaskLog\
    tasks.db
    settings.json
    logs\
```

Do not store the database next to the source code or executable.

---

## 27. Application Architecture

Recommended project structure:

```text
daily_task_log/
│
├── main.py
├── cli.py
│
├── app.py
│
├── db/
│   ├── database.py
│   ├── repository.py
│   └── migrations.py
│
├── tasks/
│   ├── service.py
│   └── carry_over.py
│
├── ui/
│   ├── popup.py
│   ├── task_row.py
│   └── date_nav.py
│
├── windows/
│   └── hotkey.py
│
├── config/
│   └── settings.py
│
└── tests/
    ├── test_repository.py
    ├── test_carry_over.py
    ├── test_completion.py
    └── test_cli.py
```

---

## 28. Component Responsibilities

### `TaskRepository`

Responsibilities:

```text
create task
load tasks by date
edit title
complete task
reopen task
soft delete task
carry tasks forward
weekly completion queries
```

### `CarryOverService`

Responsibilities:

```text
find unfinished tasks before today
move them to today
preserve original_date
preserve created_at
```

### `PopupWindow`

Responsibilities:

```text
display input field
display unfinished tasks
display completed tasks
navigate dates
Today button
keyboard shortcuts
task editing
completion handling
```

### `GlobalHotkeyManager`

Responsibilities:

```text
register Ctrl+Shift+Z
receive Windows hotkey message
request popup display
```

### `CLI`

Responsibilities:

```text
parse command
resolve target date
run carry-over when necessary
query shared database
format console output
```

---

## 29. Global Hotkey

Use Windows native:

```text
RegisterHotKey
```

through:

```python
ctypes.windll.user32
```

Default:

```text
Ctrl + Shift + Z
```

Requirements:

- work globally while background process runs;
- not require administrator privileges under normal use;
- detect registration failure;
- avoid third-party hotkey libraries.

---

## 30. App Lifecycle

At startup:

```text
start application
↓
single-instance check
↓
initialize database
↓
run carry-over
↓
register Ctrl+Shift+Z
↓
hide popup
↓
wait for hotkey
```

Hotkey event:

```text
Ctrl+Shift+Z
↓
run carry-over
↓
set view = Today
↓
load today's tasks
↓
show popup
↓
focus input
```

---

## 31. Single Instance

Only one background UI instance should run.

Preferred Windows implementation:

```text
CreateMutexW
```

through `ctypes`.

CLI must still be able to access SQLite while the background process is running.

---

## 32. SQLite Concurrency

Both UI and CLI may access the database.

Recommended SQLite configuration:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=3000;
```

Benefits:

- CLI reads can coexist with the background app;
- lower chance of `database is locked`;
- simple shared local database architecture.

Each process should create its own SQLite connection.

---

## 33. Transaction Rules

Each mutation should use a short transaction.

Examples:

```text
create task
complete task
reopen task
edit task
soft delete
carry-over
```

Transactions should be committed immediately.

Avoid long-running transactions in the UI process.

---

## 34. Settings

MVP settings may be stored in:

```text
settings.json
```

Example:

```json
{
  "hotkey": "ctrl+shift+z",
  "start_with_windows": true,
  "window_width": 520,
  "window_height": 500
}
```

A settings GUI is not required.

---

## 35. Startup With Windows

Optional but recommended MVP functionality.

Possible implementation:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

No administrator permission should be required.

---

## 36. Popup Window Behavior

The window should:

- stay above normal windows while active;
- not require taskbar navigation;
- be compact;
- close with Escape;
- open centered on the active screen;
- focus the task input;
- show Today by default;
- avoid behaving like a large desktop application.

Preferred feel:

```text
launcher / command palette
```

rather than:

```text
traditional task manager
```

---

## 37. Error Handling

Handle gracefully:

```text
database unavailable
database locked
hotkey registration failure
invalid CLI date
corrupt settings file
failed migration
```

CLI errors should be concise.

Example:

```text
Invalid date. Use YYYY-MM-DD.
```

The UI should avoid modal error dialogs when possible.

---

## 38. Logging

Store logs under:

```text
%LOCALAPPDATA%\DailyTaskLog\logs\
```

Log:

```text
startup
shutdown
database errors
hotkey errors
carry-over execution
unexpected exceptions
```

Do not log unnecessary task titles by default.

---

## 39. MVP Features

MVP includes:

1. Background Windows app.
2. `Ctrl+Shift+Z` global shortcut.
3. Popup opens to Today.
4. Text input for creating tasks.
5. Checkbox on every task.
6. Keyboard completion via Space.
7. Completion timestamp.
8. Completed items moved below unfinished items.
9. Completed items shown with strikethrough.
10. Task title editing with F2.
11. Reopening completed tasks.
12. Reopened tasks return to Today.
13. Automatic carry-over of unfinished tasks.
14. Original date preserved for carried tasks.
15. Previous / next day navigation.
16. Explicit Today button.
17. Future-date task creation.
18. Soft delete.
19. Shared SQLite database.
20. CLI: `todo`, `todo today`, `todo yesterday`, `todo YYYY-MM-DD`, `todo week`.
21. CLI carry-over age indicator.
22. No manual drag ordering.

---

## 40. Explicitly Out of Scope for MVP

Do not add:

```text
priority levels
tags
projects
subtasks
notes
attachments
reminders
notifications
due times
recurring tasks
calendar integration
Kanban
cloud sync
accounts
multi-device support
team collaboration
AI
productivity scores
streaks
gamification
manual drag-and-drop ordering
```

---

## 41. Edge Cases

### App Was Not Running for Several Days

Example:

```text
Task created Sep 20
App next opened Sep 26
Task still unfinished
```

Result:

```text
task_date = Sep 26
original_date = Sep 20
```

CLI / UI displays:

```text
carried 6d
```

### Future Task Reaches Today

A future task becomes a normal Today task when its date arrives.

### Reopen Historical Task

Given:

```text
task_date = Sep 20
completed_at = Sep 20 14:00
today = Sep 26
```

After reopening:

```text
task_date = Sep 26
completed_at = NULL
```

### Edit Completed Historical Task

Edit only changes the title. The task remains completed on its historical date with its original `completed_at`.

### Delete Carried Task

Soft delete occurs at its current `task_date`. Historical dates do not show it.

---

## 42. Recommended SQL Queries

### Unfinished Tasks

```sql
SELECT *
FROM tasks
WHERE task_date = ?
  AND completed_at IS NULL
  AND deleted_at IS NULL
ORDER BY original_date ASC, created_at ASC;
```

### Completed Tasks

```sql
SELECT *
FROM tasks
WHERE task_date = ?
  AND completed_at IS NOT NULL
  AND deleted_at IS NULL
ORDER BY completed_at DESC;
```

### Carry Forward

```sql
UPDATE tasks
SET task_date = ?,
    updated_at = ?
WHERE task_date < ?
  AND completed_at IS NULL
  AND deleted_at IS NULL;
```

---

## 43. CLI Output Rules

Symbols:

```text
○ unfinished
✓ completed
```

Examples:

```text
○ Update sandbox DB        carried 2d
○ Write SPEC                    today
✓ Reply to Jun                  10:42
```

Footer:

```text
2 / 4 completed
```

For no tasks:

```text
No tasks.
```

---

## 44. Testing Requirements

### Unit Tests

Test:

```text
task creation
title editing
completion timestamp
reopen behavior
soft delete
carry-over
original_date preservation
future tasks
weekly summary
CLI date parsing
```

### Carry-Over Test

Given:

```text
original_date = Sep 24
task_date = Sep 24
completed_at = NULL
today = Sep 26
```

After carry-over:

```text
original_date = Sep 24
task_date = Sep 26
completed_at = NULL
```

### Reopen Test

Given:

```text
task_date = Sep 20
completed_at = Sep 20 14:00
today = Sep 26
```

After reopening:

```text
task_date = Sep 26
completed_at = NULL
```

### Soft Delete Test

After delete:

```text
deleted_at != NULL
```

Task should not appear in UI, CLI date views, or week summary.

---

## 45. Manual Windows Tests

Verify UI and hotkey behavior while working in:

```text
Windows Terminal
Edge
Chrome
VS Code
Notepad
Word
Excel
Outlook
```

Verify:

```text
Ctrl+Shift+Z consistently opens popup
Escape closes it
focus returns reasonably to previous work
```

---

## 46. Performance Targets

Target behavior:

```text
Popup open              < 150 ms perceived
Task creation           immediate
Completion toggle       immediate
Date navigation         < 100 ms typical
CLI output              < 200 ms typical
```

The expected dataset is small enough that ordinary indexed SQLite queries are sufficient.

FTS is not required.

---

## 47. Development Order

Recommended implementation sequence:

```text
1. SQLite schema
2. Repository layer
3. Carry-over logic
4. CLI read-only commands
5. tkinter popup
6. Task creation
7. Completion / reopen behavior
8. Task title editing
9. Soft delete
10. Date navigation
11. Today button
12. Windows RegisterHotKey
13. Single-instance handling
14. Startup integration
15. Polish and testing
```

This order validates task semantics before Windows UI integration.

---

## 48. Acceptance Criteria

The MVP is complete when all of the following work:

1. Running the background process registers `Ctrl+Shift+Z`.
2. Hotkey opens the popup.
3. Popup always opens on Today.
4. User can type a task and press Enter.
5. Task appears in today's unfinished section.
6. Every task displays a checkbox.
7. Space or checkbox completes a task.
8. Completion stores an exact timestamp.
9. Completed task moves below unfinished tasks.
10. Completed title is struck through.
11. Completion time is displayed.
12. F2 edits a task title.
13. Unchecking a completed task clears completion time.
14. Reopened task moves to Today.
15. Yesterday's unfinished tasks automatically move to Today.
16. Original creation date survives carry-over.
17. Old historical dates do not display carried-away tasks.
18. Previous and next date navigation work.
19. Today button returns to current date.
20. Future date task creation works.
21. Delete performs a soft delete.
22. `todo` displays Today.
23. `todo yesterday` displays yesterday.
24. `todo YYYY-MM-DD` displays a requested date.
25. `todo week` displays a seven-day summary.
26. CLI displays carry-over age for unfinished tasks.
27. UI and CLI share the same SQLite database.
28. No third-party runtime dependency is required.

---

## 49. Definition of Success

The tool succeeds if the user can manage daily work with almost no workflow interruption.

Ideal capture loop:

```text
Ctrl+Shift+Z
→ type task
→ Enter
→ Esc
```

Ideal completion loop:

```text
Ctrl+Shift+Z
→ select task
→ Space
→ Esc
```

Ideal historical review:

```text
todo yesterday
```

or:

```text
todo week
```

The application should feel like an additional Windows capability, not another task-management system that itself requires management.
