from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Tuple

@dataclass
class TaskItem:
    note_path: Path
    note_title: str
    note_created: str
    line_no: int
    text: str
    done: bool
    status: str | None = None
    notes: list["TaskNote"] = field(default_factory=list)

@dataclass
class TaskNote:
    line_no: int
    prefix: str
    text: str

def _status_from_prefix(prefix: str) -> str | None:
    if prefix == "@":
        return "created"
    if prefix == "!":
        return "in_progress"
    return None

def extract_tasks(body: str) -> List[Tuple[int, str, bool, str | None, list[TaskNote]]]:
    out: List[Tuple[int, str, bool, str | None, list[TaskNote]]] = []
    lines = (body or "").splitlines()
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        done = False
        if s.startswith("***"):
            txt = s[3:].strip()
            done = True
        elif s.startswith("**"):
            # IMPORTANT: check *** first so we don't treat it as open
            txt = s[2:].strip()
        else:
            i += 1
            continue

        if not txt:
            i += 1
            continue

        notes: list[TaskNote] = []
        status: str | None = None
        j = i + 1
        while j < len(lines):
            note_line = lines[j].strip()
            if not note_line.startswith(("@", "!")):
                break
            prefix = note_line[0]
            note_txt = note_line[1:].strip()
            if note_txt:
                notes.append(TaskNote(line_no=j + 1, prefix=prefix, text=note_txt))
                status = _status_from_prefix(prefix) or status
            j += 1

        out.append((i + 1, txt, done, status, notes))
        i = j
    return out

def toggle_complete_in_file(path: Path, line_no: int) -> bool:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    # Find body start after frontmatter
    body_start = 0
    if lines and lines[0].startswith("---"):
        # find second --- line
        dash_count = 0
        for idx, ln in enumerate(lines):
            if ln.strip() == "---":
                dash_count += 1
                if dash_count == 2:
                    body_start = idx + 1
                    break
    # line_no refers to body lines (1-based) as shown in UI
    target_idx = body_start + (line_no - 1)
    if target_idx < 0 or target_idx >= len(lines):
        return False
    raw = lines[target_idx]
    stripped = raw.lstrip()
    prefix = raw[:len(raw)-len(stripped)]
    if stripped.startswith("***"):
        # already done; do nothing for now
        return False
    if stripped.startswith("**"):
        lines[target_idx] = prefix + "***" + stripped[2:]
        path.write_text("".join(lines), encoding="utf-8")
        return True
    return False
