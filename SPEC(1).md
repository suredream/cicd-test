# ClipSeek — SPEC.md

## 1. Product Overview

**Product Name:** ClipSeek  
**Platform:** Windows  
**Primary Language:** Python  
**Product Type:** Keyboard-first clipboard history manager  
**Primary Goal:** Let users instantly search and reuse previous clipboard text without opening a traditional desktop application.

ClipSeek runs quietly in the background, records clipboard text history, and opens a compact search window when the user presses a global hotkey.

Default workflow:

```text
Copy text
→ ClipSeek records it
→ Press Ctrl+Shift+V
→ Type a search query
→ Use ↑ / ↓ to select
→ Press Enter
→ ClipSeek pastes the selected item
→ Search window disappears
```

The application should require little or no mouse interaction during normal use.

---

## 2. Product Principles

1. **Keyboard-first**
   - All primary operations must be possible without a mouse.

2. **Invisible until needed**
   - ClipSeek should remain in the background during normal work.
   - No permanent main window.

3. **Fast**
   - Hotkey-to-search-window latency should feel near-instant.
   - Search should update while typing.

4. **Local-first**
   - Clipboard contents are stored locally.
   - No cloud dependency in MVP.

5. **Minimal**
   - Avoid unnecessary settings screens, dashboards, accounts, or complex navigation.

6. **Safe by default**
   - Avoid storing obvious passwords, OTPs, tokens, and other sensitive clipboard content when possible.

---

## 3. Target User

ClipSeek is designed for Windows users who:

- copy and paste frequently;
- work with code, URLs, documents, emails, or repetitive text;
- prefer keyboard shortcuts over mouse-driven UI;
- want searchable clipboard history;
- do not want a large desktop application;
- prefer local data storage.

---

## 4. MVP Scope

### 4.1 Clipboard Monitoring

ClipSeek continuously monitors the Windows clipboard.

For each supported clipboard event:

- capture plain text;
- normalize line endings;
- ignore empty values;
- calculate content hash;
- detect duplicates;
- store clipboard entry in SQLite.

MVP supports:

- plain text;
- multi-line text;
- URLs;
- file paths copied as text;
- code snippets.

MVP does **not** need to support:

- images;
- files;
- rich text;
- HTML clipboard payloads;
- cloud sync.

---

## 5. Clipboard History

Each clipboard record should contain at minimum:

```text
id
content
content_hash
created_at
last_used_at
use_count
is_pinned
content_type
```

Optional future fields:

```text
source_application
source_window
tags
preview
metadata_json
```

### Retention

Default maximum history:

```text
10,000 entries
```

When the limit is exceeded:

- pinned entries are preserved;
- oldest non-pinned entries are deleted first.

Retention count should eventually be configurable.

---

## 6. Duplicate Handling

Clipboard duplication should be minimized.

Example:

```text
Copy A
Copy B
Copy A
```

Preferred behavior:

- do not create a second independent A record;
- update A's timestamp and move it to the top.

Duplicate identity should initially be based on:

```text
SHA-256(normalized_content)
```

Normalization may include:

- trimming trailing whitespace;
- normalizing CRLF/LF;
- preserving meaningful internal whitespace.

---

## 7. Global Hotkey

Default hotkey:

```text
Ctrl + Shift + V
```

Behavior:

1. Detect the global shortcut.
2. Save the currently focused application/window.
3. Open ClipSeek search popup.
4. Automatically focus the search input.
5. Show recent clipboard entries.

The hotkey should work while ClipSeek is running in the background.

Future configuration may allow custom hotkeys.

---

## 8. Search Popup

ClipSeek has no traditional main window.

Its primary UI is a compact temporary popup.

Example:

```text
┌────────────────────────────────────────────┐
│ Search clipboard...                       │
├────────────────────────────────────────────┤
│  PG&E 400A upgrade                        │
│  Jun sandbox database design              │
│  https://example.com/...                  │
│  SELECT * FROM parcel...                  │
│  ...                                      │
└────────────────────────────────────────────┘
```

### Window Behavior

The search popup should:

- open quickly;
- appear near the active screen center or cursor;
- stay above normal windows while active;
- disappear after selection;
- disappear when Escape is pressed;
- not appear in the Windows taskbar if possible;
- immediately focus the search field.

---

## 9. Keyboard Interaction

Required keyboard commands:

```text
Ctrl+Shift+V   Open ClipSeek
↑              Previous result
↓              Next result
Enter          Paste selected item
Escape         Close ClipSeek
Delete         Delete selected item
Ctrl+P         Pin / unpin selected item
```

Optional:

```text
Ctrl+1..9      Select top 1–9 result
Ctrl+C         Copy selected item without pasting
Ctrl+Enter     Copy only and close
Tab            Switch search mode
```

Mouse support may exist but is not required for core operation.

---

## 10. Search

### MVP Search

Initially support case-insensitive substring matching.

Example:

Query:

```text
sandbox
```

Matches:

```text
Jun sandbox database design
GCP sandbox architecture
sandbox-db-test
```

### Recommended Production Search

Use SQLite FTS5.

Example architecture:

```text
clipboard_items
       │
       └── clipboard_fts
```

FTS index:

```sql
CREATE VIRTUAL TABLE clipboard_fts
USING fts5(content);
```

Desired behavior:

- search updates on every keystroke;
- debounce approximately 50–100 ms if needed;
- return maximum 50 visible results;
- rank pinned and recent results highly.

Suggested ranking:

```text
Pinned
→ exact match
→ prefix match
→ full-text relevance
→ recent usage
→ frequency
```

---

## 11. Result Display

Each result should show:

```text
Primary:
content preview

Secondary:
optional timestamp / content type
```

Example:

```text
SELECT * FROM parcel WHERE...
SQL · 2 min ago
```

Maximum preview should be truncated visually without truncating stored content.

Recommended:

```text
1–3 lines per result
```

Long clipboard content remains fully stored.

---

## 12. Paste Workflow

When the user presses Enter:

1. Retrieve selected clipboard entry.
2. Put its content onto the Windows clipboard.
3. Update:
   - `last_used_at`
   - `use_count`
4. Hide ClipSeek.
5. Restore focus to the previously active window.
6. Send:
   ```text
   Ctrl+V
   ```

A small delay may be required between focus restoration and paste.

Suggested configurable delay:

```text
50–150 ms
```

---

## 13. Pinning

Users can pin important clipboard items.

Shortcut:

```text
Ctrl+P
```

Pinned items:

- are not automatically deleted;
- rank above normal results;
- remain searchable;
- may optionally appear first when the search box is empty.

Typical pinned entries:

- email address;
- project names;
- frequently used URLs;
- SQL snippets;
- standard text;
- signatures.

---

## 14. Delete

Press:

```text
Delete
```

to remove the selected clipboard entry.

Expected behavior:

- delete immediately from SQLite;
- remove from FTS index;
- move selection to nearest remaining result.

Optional future feature:

```text
Ctrl+Z
```

undo last deletion.

---

## 15. Sensitive Content Protection

ClipSeek should avoid persisting obvious secrets.

Possible detection rules:

### OTP

Examples:

```text
123456
849203
```

Short numeric strings copied briefly may be excluded.

### Password fields

When technically possible, ignore clipboard data originating from recognized password contexts.

### Tokens

Patterns to consider:

```text
Bearer ...
AWS access keys
JWT
GitHub tokens
OpenAI-style API keys
private keys
```

Example detection:

```text
-----BEGIN PRIVATE KEY-----
```

### User-controlled ignore mode

Future shortcut:

```text
Ctrl+Shift+X
```

Temporarily pause clipboard recording.

Privacy filters should be conservative to avoid destroying legitimate clipboard history.

---

## 16. Data Storage

Use SQLite.

Recommended location:

```text
%LOCALAPPDATA%\ClipSeek\
```

Example:

```text
C:\Users\<user>\AppData\Local\ClipSeek\
    clipseek.db
    settings.json
    logs\
```

Do not store application data next to the executable.

---

## 17. Database Schema

Suggested MVP schema:

```sql
CREATE TABLE clipboard_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    content_type TEXT DEFAULT 'text',
    created_at TEXT NOT NULL,
    last_used_at TEXT,
    use_count INTEGER DEFAULT 0,
    is_pinned INTEGER DEFAULT 0
);
```

Indexes:

```sql
CREATE INDEX idx_clipboard_created_at
ON clipboard_items(created_at DESC);

CREATE INDEX idx_clipboard_last_used
ON clipboard_items(last_used_at DESC);

CREATE INDEX idx_clipboard_pinned
ON clipboard_items(is_pinned);
```

FTS:

```sql
CREATE VIRTUAL TABLE clipboard_fts
USING fts5(
    content,
    content='clipboard_items',
    content_rowid='id'
);
```

---

## 18. Technical Stack

### Core

```text
Python 3.12+
PySide6
SQLite
SQLite FTS5
```

### Responsibilities

#### PySide6

Use for:

- application event loop;
- clipboard monitoring;
- popup window;
- search input;
- result list;
- system tray;
- timers;
- keyboard events inside popup.

Important components:

```text
QApplication
QClipboard
QLineEdit
QListView / QListWidget
QAbstractListModel
QSystemTrayIcon
QTimer
```

#### SQLite

Use for:

- persistence;
- history;
- pin state;
- usage metrics;
- search index.

#### Global Hotkey

Possible choices:

```text
keyboard
pynput
Windows API via ctypes
```

Recommended MVP:

```text
keyboard
```

Recommended later production implementation:

```text
Windows RegisterHotKey API
```

Using the Windows native hotkey API can reduce dependency and permission issues.

#### Paste Simulation

Possible implementations:

```text
keyboard
pyautogui
Windows SendInput API
```

Recommended longer-term:

```text
Windows SendInput via ctypes
```

This keeps the application Windows-native while remaining Python-only.

---

## 19. Recommended Architecture

```text
clipseek/
│
├── main.py
│
├── app.py
│
├── clipboard/
│   ├── monitor.py
│   ├── classifier.py
│   └── sanitizer.py
│
├── database/
│   ├── db.py
│   ├── repository.py
│   └── migrations.py
│
├── search/
│   └── search_engine.py
│
├── ui/
│   ├── popup.py
│   ├── result_model.py
│   └── tray.py
│
├── windows/
│   ├── hotkey.py
│   ├── focus.py
│   └── paste.py
│
├── config/
│   └── settings.py
│
└── tests/
    ├── test_database.py
    ├── test_search.py
    ├── test_clipboard.py
    └── test_sensitive_filter.py
```

---

## 20. Core Components

### ClipboardMonitor

Responsibilities:

```text
listen for clipboard changes
normalize text
reject unsupported content
run sensitive-content filter
generate content hash
send valid item to repository
```

### ClipboardRepository

Responsibilities:

```text
insert clipboard entries
deduplicate
delete
pin
update use count
enforce retention limit
```

### SearchEngine

Responsibilities:

```text
search FTS index
rank results
return recent entries for empty query
```

### PopupWindow

Responsibilities:

```text
receive keyboard focus
display search field
display results
manage selection
process Enter/Escape/Delete/Ctrl+P
```

### GlobalHotkeyManager

Responsibilities:

```text
register Ctrl+Shift+V
capture currently focused window
open popup
```

### PasteManager

Responsibilities:

```text
set clipboard
restore previous application focus
send Ctrl+V
```

---

## 21. Application Lifecycle

At Windows login:

```text
ClipSeek.exe
    ↓
single-instance check
    ↓
initialize SQLite
    ↓
initialize clipboard listener
    ↓
register global hotkey
    ↓
create tray icon
    ↓
wait
```

User presses:

```text
Ctrl+Shift+V
```

Then:

```text
record foreground window
↓
show popup
↓
load recent clipboard history
↓
focus search field
```

User types:

```text
permit
```

Then:

```text
FTS query
↓
rank results
↓
render top results
```

User presses:

```text
Enter
```

Then:

```text
selected content
↓
Windows clipboard
↓
hide popup
↓
restore previous window
↓
Ctrl+V
```

---

## 22. Startup

ClipSeek should support Windows auto-start.

Preferred approach:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

Alternative:

```text
Windows Startup folder
```

Do not require administrator privileges for normal installation or startup.

---

## 23. Single Instance

Only one ClipSeek process should run.

Possible implementation:

```text
QLocalServer / QLocalSocket
```

or Windows mutex through:

```text
ctypes
```

If ClipSeek is already running, starting it again should not create a second clipboard monitor.

---

## 24. System Tray

Although ClipSeek does not have a normal application UI, it should have a minimal tray menu.

Example:

```text
ClipSeek

Open
Pause history
Clear unpinned history
Settings
Exit
```

The tray is primarily for lifecycle control, not normal clipboard usage.

---

## 25. Settings

MVP settings may live in:

```text
settings.json
```

Example:

```json
{
  "hotkey": "ctrl+shift+v",
  "history_limit": 10000,
  "max_result_count": 50,
  "paste_delay_ms": 80,
  "launch_on_startup": true,
  "sensitive_filter": true
}
```

A graphical settings page is not required for MVP.

Settings may initially be edited directly in the file.

---

## 26. Logging

Store application logs under:

```text
%LOCALAPPDATA%\ClipSeek\logs\
```

Log:

```text
startup
shutdown
database errors
hotkey registration errors
clipboard monitor errors
paste errors
```

Do **not** log full clipboard content.

Prefer:

```text
content length
content hash prefix
content type
```

instead.

---

## 27. Performance Targets

Target:

```text
Startup                         < 1 second
Popup appearance                < 100 ms perceived
Search response                 < 50 ms typical
Clipboard capture               < 50 ms
Memory                          < 100 MB preferred
Database                        capable of 100k+ records
```

Only the configured retention limit needs to remain active by default.

---

## 28. Packaging

Use:

```text
PyInstaller
```

Target output:

```text
ClipSeek.exe
```

Recommended build:

```bash
pyinstaller ^
  --noconsole ^
  --onefile ^
  --name ClipSeek ^
  main.py
```

During development, prefer `--onedir` for easier debugging.

Production may use either:

```text
onefile
```

or:

```text
onedir + installer
```

---

## 29. Testing

### Unit Tests

Test:

```text
normalization
hash generation
duplicate handling
database retention
pin behavior
search ranking
sensitive-content detection
```

### Integration Tests

Test:

```text
clipboard event → database

hotkey → popup

search → result list

selection → clipboard → paste
```

### Manual Windows Tests

Verify behavior in:

```text
Chrome
Edge
VS Code
Notepad
Word
Excel
Outlook
Windows Terminal
```

---

## 30. MVP Acceptance Criteria

MVP is considered complete when:

1. ClipSeek starts on Windows.
2. It runs without a permanent visible window.
3. Copying text records it into SQLite.
4. Duplicate clipboard entries are handled correctly.
5. `Ctrl+Shift+V` opens the search popup.
6. Search results update while typing.
7. `↑` and `↓` navigate results.
8. `Enter` pastes the selected content into the previously active application.
9. `Escape` closes the popup.
10. `Delete` removes an item.
11. `Ctrl+P` pins an item.
12. History survives application restart.
13. Old non-pinned history is automatically removed.
14. Obvious sensitive content can be excluded.
15. Application can be packaged as a Windows executable.

---

## 31. Not in MVP

Explicitly exclude:

```text
cloud synchronization
user accounts
mobile apps
browser extensions
team sharing
image clipboard history
OCR
AI features
semantic/vector search
cross-device synchronization
rich-text rendering
large settings GUI
plugins
```

These may be considered after the core clipboard workflow is stable.

---

## 32. Phase 2

Potential additions:

### Clipboard Types

```text
URL
email
SQL
JSON
code
file path
phone number
address
```

Examples:

```text
type:url
type:sql
type:code
```

### Search Operators

```text
pin:
url:
code:
after:
before:
```

Example:

```text
pin: database
```

### Quick Slots

```text
Alt+1
Alt+2
...
Alt+9
```

paste pinned clipboard slots.

### Source Application Tracking

Store:

```text
Chrome
VS Code
Outlook
Terminal
```

Allow queries such as:

```text
app:vscode parcel
```

### Smart Actions

Example:

```text
Ctrl+Shift+V
→ select item
→ press Tab
```

Actions:

```text
Paste
Copy only
Pin
Delete
Open URL
```

---

## 33. Phase 3 — AI Features

AI features should remain optional.

Possible capabilities:

```text
summarize selected clipboard item
translate
rewrite
fix grammar
convert to Markdown
extract tasks
explain code
generate JSON
```

Possible command workflow:

```text
Copy text
→ Ctrl+Alt+T
→ translate
→ replace clipboard
→ paste
```

Semantic clipboard search could eventually use embeddings, but SQLite FTS should remain the default search system.

---

## 34. Future Command Mode

ClipSeek may eventually combine clipboard history with the user's existing text-expansion system.

Example:

```text
;;v1
```

Paste most recent clipboard item.

```text
;;clip sandbox
```

Search for most recent clipboard entry containing `sandbox`.

```text
;;url
```

Paste most recent URL.

```text
;;pin1
```

Paste first pinned entry.

This would turn ClipSeek into both:

```text
Clipboard Manager
+
Keyboard Command Engine
```

while keeping the same keyboard-first philosophy.

---

## 35. Development Priority

Recommended implementation order:

```text
1. SQLite repository
2. Clipboard monitoring
3. Basic popup
4. Recent clipboard list
5. Global hotkey
6. Search
7. Paste-to-previous-window
8. Delete
9. Pin
10. Deduplication
11. Retention
12. Sensitive-content filtering
13. Startup
14. Packaging
15. FTS5 optimization
```

Do not begin with AI, images, or advanced classification.

The key product loop to perfect first is:

```text
Copy
→ Ctrl+Shift+V
→ Search
→ Enter
→ Paste
```

---

## 36. Definition of Success

ClipSeek succeeds if a user who frequently copies text can retrieve an item from hours or days earlier in a few keystrokes, without navigating away from their current application.

The ideal experience is:

```text
I remember part of what I copied
        ↓
Ctrl+Shift+V
        ↓
type 3–6 characters
        ↓
Enter
        ↓
done
```

The application should feel less like opening software and more like adding a new capability to Windows.
