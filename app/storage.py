from __future__ import annotations
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

HEADER_RE = re.compile(r"(?s)\A---\n(.*?)\n---\n(.*)\Z")
KV_RE = re.compile(r"^([A-Za-z0-9_\-]+):\s*(.*)\s*$")

def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()

@dataclass
class NoteMeta:
    note_id: str
    title: str
    created: str
    updated: str

@dataclass
class Note:
    path: Path
    meta: NoteMeta
    body: str

def _render(meta: NoteMeta, body: str) -> str:
    header = "\n".join([
        "---",
        f"id: {meta.note_id}",
        f"title: {meta.title}",
        f"created: {meta.created}",
        f"updated: {meta.updated}",
        "---",
        "",
    ])
    return header + body

def load_note(path: Path) -> Note:
    txt = path.read_text(encoding="utf-8", errors="replace")
    m = HEADER_RE.match(txt)
    if not m:
        now = _now_iso()
        meta = NoteMeta(note_id=path.stem, title=path.stem, created=now, updated=now)
        return Note(path=path, meta=meta, body=txt)
    header_txt, body = m.group(1), m.group(2)
    kv = {}
    for line in header_txt.splitlines():
        km = KV_RE.match(line.strip())
        if km:
            kv[km.group(1).strip()] = km.group(2).strip()
    note_id = kv.get("id") or path.stem
    title = kv.get("title") or path.stem
    created = kv.get("created") or _now_iso()
    updated = kv.get("updated") or created
    meta = NoteMeta(note_id=note_id, title=title, created=created, updated=updated)
    return Note(path=path, meta=meta, body=body)

def _safe_title_to_slug(title: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()
    return slug[:60] or "note"

def save_new_note(notes_dir: Path, title: str, body: str) -> Note:
    now = _now_iso()
    yyyy = now[:4]
    mm = now[5:7]
    folder = notes_dir / yyyy / f"{yyyy}-{mm}"
    folder.mkdir(parents=True, exist_ok=True)
    note_id = uuid.uuid4().hex[:10]
    slug = _safe_title_to_slug(title)
    filename = f"{now.replace(':','-')}_{slug}_{note_id}.md"
    path = folder / filename
    meta = NoteMeta(note_id=note_id, title=title, created=now, updated=now)
    path.write_text(_render(meta, body), encoding="utf-8")
    return Note(path=path, meta=meta, body=body)

def update_note(path: Path, title: str, body: str) -> Note:
    note = load_note(path)
    now = _now_iso()
    meta = NoteMeta(note_id=note.meta.note_id, title=title, created=note.meta.created, updated=now)
    path.write_text(_render(meta, body), encoding="utf-8")
    return Note(path=path, meta=meta, body=body)

def delete_note(path: Path) -> None:
    path.unlink(missing_ok=True)

def list_notes(notes_dir: Path) -> Iterable[Path]:
    paths = sorted(notes_dir.glob("**/*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return paths
