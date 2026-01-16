from __future__ import annotations
from dataclasses import dataclass
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

def extract_tasks(body: str) -> List[Tuple[int, str, bool]]:
    out: List[Tuple[int, str, bool]] = []
    for i, line in enumerate((body or "").splitlines(), start=1):
        s = line.strip()
        if s.startswith("***"):
            txt = s[3:].strip()
            if txt:
                out.append((i, txt, True))
        elif s.startswith("**"):
            # IMPORTANT: check *** first so we don't treat it as open
            txt = s[2:].strip()
            if txt:
                out.append((i, txt, False))
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
