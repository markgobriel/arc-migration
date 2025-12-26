# Arc Migration Exporter

Export Arc Browser Spaces, folders, and tabs to a Netscape-style bookmarks HTML file that can be imported into Firefox, Edge, Zen, and Chrome.

## Requirements

- Python 3.10+
- Local access to Arc's `StorableSidebar.json` (read-only)

## Usage

### Default auto-detection

```bash
python3 arc_export.py --output arc_bookmarks.html
```

### Specify input path

```bash
python3 arc_export.py --input "/path/to/StorableSidebar.json" --output arc_bookmarks.html
```

### Export all containers and include unpinned spaces

```bash
python3 arc_export.py --all-containers --include-unpinned --output arc_bookmarks.html
```

### Verbose diagnostics

```bash
python3 arc_export.py --verbose
```

## Where Arc stores sidebar data

- macOS (common path):
  `~/Library/Application Support/Arc/StorableSidebar.json`
- Windows (common path):
  `%LOCALAPPDATA%\Packages\TheBrowserCompany.Arc*\LocalCache\Local\Arc\StorableSidebar.json`

If auto-detection fails, locate `StorableSidebar.json` manually and pass it with `--input`.

## Importing the HTML file

- Firefox / Zen: Library -> Bookmarks -> Manage Bookmarks -> Import and Backup -> Import Bookmarks from HTML
- Chrome: Settings -> Import bookmarks and settings (or Bookmarks manager -> Import)
- Edge: Settings -> Profiles -> Import browser data -> Import from file

## Tests

```bash
python3 -m unittest test_arc_export.py
```
