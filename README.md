# Fire & Forget Notes

Local-first notes for ADHD brains: write now, find later.

- Tray icon launches a local web UI (`http://127.0.0.1:17831`)
- Notes are plain `.md` files on disk
- Browse by date + semantic search
- Paste images into the editor and get a local image link
- Inline one-line tasks:
  - Open task: a line starting with `**`
  - Completed task: a line starting with `***`
  - Task notes: lines under a task starting with `@` (created) or `!` (in progress)

## Quick start

### Windows
```bat
run.bat
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python tray.py
```

If your system tray is not supported, run the web app directly:
```bash
python app.py
```

## Data location
Notes are stored under `data/notes/YYYY/YYYY-MM/*.md` in the app folder.
Pasted images are stored under `data/images/`.
The `data/` folder is ignored by git to keep personal notes out of the repo.

## Configuration
Settings live in `config.json` (host, port, search chunking, max results).

## License
MIT. See `LICENSE`.
