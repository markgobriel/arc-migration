# <img src="https://upload.wikimedia.org/wikipedia/commons/3/37/Arc_%28browser%29_logo.svg" alt="Arc logo" width="24" height="24"> Arc Migration Exporter

Arc is **pretty**. Migrating off it is… **not**.

This script helps you escape by exporting your **Spaces**, **folders**, and **tabs** into a classic **Netscape bookmarks HTML** file that **Firefox-** or **Chromium-based** browsers can import ✅

## ✅ Requirements

- Python 3.10+
- Local access to Arc's `StorableSidebar.json` (read-only)

## ⚡ Usage

### 🔍 Default auto-detection

```bash
python3 arc_export.py --output arc_bookmarks.html
```

### 🧭 Specify input path

```bash
python3 arc_export.py --input "/path/to/StorableSidebar.json" --output arc_bookmarks.html
```

### 🧩 Export all containers and include unpinned spaces

```bash
python3 arc_export.py --all-containers --include-unpinned --output arc_bookmarks.html
```

### 🧾 Verbose diagnostics

```bash
python3 arc_export.py --verbose
```

## 📁 Where Arc stores sidebar data

- macOS (common path):
  `~/Library/Application Support/Arc/StorableSidebar.json`
- Windows (common path):
  `%LOCALAPPDATA%\Packages\TheBrowserCompany.Arc*\LocalCache\Local\Arc\StorableSidebar.json`

If auto-detection fails, locate `StorableSidebar.json` manually and pass it with `--input`.

## 📥 Importing the HTML file

- Firefox-based: Library -> Bookmarks -> Manage Bookmarks -> Import and Backup -> Import Bookmarks from HTML
- Chromium-based: Bookmarks manager -> Import (or Settings -> Import bookmarks)

## ✨ What it exports

- 🗂️ **Spaces** (as top-level folders when possible)
- 📁 **Folders / tab groups** (best-effort, keeps structure)
- 🔗 **Tab titles + URLs**
- 📄 Outputs **one** `bookmarks.html` you can import anywhere

## 🧪 Tests

```bash
python3 -m unittest test_arc_export.py
```
