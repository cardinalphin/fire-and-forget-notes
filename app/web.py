from __future__ import annotations
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
import html
import re
import uuid

from .config import AppConfig
from .storage import load_note, save_new_note, update_note, delete_note, list_notes
from .indexer import build_index, load_index, save_index, search
from .tasks import extract_tasks, TaskItem, toggle_complete_in_file

def create_app(cfg: AppConfig) -> Flask:
    templates_dir = str(Path(__file__).resolve().parent.parent / "templates")
    app = Flask(__name__, template_folder=templates_dir)
    app.secret_key = "fireforget-local-only"
    images_dir = (cfg.base_dir / "data" / "images").resolve()
    images_dir.mkdir(parents=True, exist_ok=True)
    img_re = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>/images/[^\)]+)\)")

    def _reindex():
        notes = []
        for p in list_notes(cfg.notes_dir):
            n = load_note(p)
            notes.append({"id": n.meta.note_id, "path": p, "title": n.meta.title, "created": n.meta.created, "body": n.body})
        idx = build_index(notes)
        save_index(idx, cfg.index_path)
        return idx

    def _get_index():
        idx = load_index(cfg.index_path)
        if idx is None:
            idx = _reindex()
        return idx

    def _is_under_notes_dir(p: Path) -> bool:
        try:
            p.resolve().relative_to(cfg.notes_dir.resolve())
            return True
        except Exception:
            return False

    def _is_under_images_dir(p: Path) -> bool:
        try:
            p.resolve().relative_to(images_dir)
            return True
        except Exception:
            return False

    def _render_body(body: str) -> str:
        tokens: list[str] = []

        def _img_repl(m: re.Match) -> str:
            alt = html.escape(m.group("alt"))
            url = m.group("url")
            tokens.append(f'<img src="{url}" alt="{alt}" loading="lazy">')
            return f"@@IMG{len(tokens)-1}@@"

        text = img_re.sub(_img_repl, body)
        text = html.escape(text)
        for i, tag in enumerate(tokens):
            text = text.replace(f"@@IMG{i}@@", tag)
        return text.replace("\n", "<br>\n")

    @app.route("/")
    def home():
        return redirect(url_for("browse"))

    @app.route("/new", methods=["GET","POST"])
    def new_note():
        if request.method == "POST":
            title = request.form.get("title","").strip() or "Untitled"
            body = request.form.get("body","")
            note = save_new_note(cfg.notes_dir, title, body)
            _reindex()
            return redirect(url_for("view_note", path=str(note.path)))
        return render_template("new.html")

    @app.route("/browse")
    def browse():
        q = request.args.get("q","").strip().lower()
        notes = []
        for p in list_notes(cfg.notes_dir):
            n = load_note(p)
            snippet = (n.body.strip().splitlines()[0] if n.body.strip() else "")
            if q and q not in n.meta.title.lower() and q not in n.body.lower():
                continue
            notes.append({
                "path": str(p),
                "title": n.meta.title,
                "created": n.meta.created,
                "updated": n.meta.updated,
                "snippet": snippet[:160] + ("…" if len(snippet) > 160 else "")
            })
        return render_template("browse.html", notes=notes, q=request.args.get("q",""))

    @app.route("/note")
    def view_note():
        path = request.args.get("path","")
        p = Path(path)
        if not p.exists() or not _is_under_notes_dir(p):
            flash("Note not found.")
            return redirect(url_for("browse"))
        n = load_note(p)
        rendered_body = _render_body(n.body)
        return render_template("note.html", note=n, rendered_body=rendered_body)

    @app.route("/note/edit", methods=["GET","POST"])
    def edit_note():
        path = request.args.get("path","")
        p = Path(path)
        if not p.exists() or not _is_under_notes_dir(p):
            flash("Note not found.")
            return redirect(url_for("browse"))
        n = load_note(p)
        if request.method == "POST":
            title = request.form.get("title", n.meta.title)
            body = request.form.get("body","")
            update_note(p, title, body)
            _reindex()
            return redirect(url_for("view_note", path=str(p)))
        return render_template("edit.html", note=n)

    @app.post("/note/delete")
    def delete_note_route():
        path = request.form.get("path","")
        p = Path(path)
        if not p.exists() or not _is_under_notes_dir(p):
            flash("Note not found.")
            return redirect(url_for("browse"))
        delete_note(p)
        _reindex()
        flash("Note deleted.")
        return redirect(url_for("browse"))

    @app.route("/search")
    def search_page():
        q = request.args.get("q","").strip()
        results = []
        if q:
            idx = _get_index()
            for chunk, score in search(idx, q, top_k=12):
                excerpt = chunk.text.replace("\n"," ").strip()
                if len(excerpt) > 220:
                    excerpt = excerpt[:220] + "…"
                results.append({"path": chunk.note_path, "title": chunk.note_title,
                                "created": chunk.note_created, "excerpt": excerpt, "score": f"{score:.3f}"})
        return render_template("search.html", q=q, results=results)


    @app.route("/copilot")
    def copilot_page():
        q = request.args.get("q","").strip()
        try:
            k = int(request.args.get("k","10") or 10)
        except Exception:
            k = 10
        k = max(3, min(20, k))

        prompt = ""
        sources = []
        if q:
            idx = _get_index()
            hits = search(idx, q, top_k=k)
            # Build sources list (truncate excerpts for prompt)
            lines = []
            for i, (chunk, score) in enumerate(hits, start=1):
                excerpt = (chunk.text or "").strip()
                if len(excerpt) > 800:
                    excerpt = excerpt[:800] + "…"
                # URL to open the note
                url = url_for("view_note", path=chunk.note_path)
                sources.append({
                    "n": i,
                    "title": chunk.note_title or Path(chunk.note_path).name,
                    "created": chunk.note_created,
                    "excerpt": excerpt,
                    "url": url,
                })
                lines.append(f"[{i}] {chunk.note_created} — {chunk.note_title}\n{excerpt}\n")

            instruction = """You are my work assistant.
            Use ONLY the provided excerpts.
            If the answer is not supported by the excerpts, say 'Not found in my notes.'

            Be concise. Include a short 'Evidence' section citing excerpt numbers like [1], [2].

            Output format:
            • Answer:
            • Evidence:
            • Open questions / follow-ups (if any):
            """

            prompt = instruction + "\nQuestion: " + q + "\n\nExcerpts:\n" + "\n".join(lines)

        return render_template("copilot.html", q=q, k=k, prompt=prompt, sources=sources)

    @app.route("/tasks")
    def tasks_page():
        q = request.args.get("q","").strip().lower()
        status_filter = request.args.get("status","not_completed").strip().lower()
        if status_filter not in {"all", "not_completed", "completed", "created", "in_progress"}:
            status_filter = "not_completed"
        items: list[TaskItem] = []
        note_paths = list(reversed(list_notes(cfg.notes_dir)))  # oldest->newest
        for p in note_paths:
            n = load_note(p)
            for line_no, txt, done, status, notes in extract_tasks(n.body):
                if status_filter == "not_completed" and done:
                    continue
                if status_filter == "completed" and not done:
                    continue
                if status_filter == "created" and (done or status != "created"):
                    continue
                if status_filter == "in_progress" and (done or status != "in_progress"):
                    continue
                if q and q not in txt.lower() and q not in n.meta.title.lower():
                    continue
                items.append(TaskItem(note_path=p, note_title=n.meta.title, note_created=n.meta.created,
                                      line_no=line_no, text=txt, done=done, status=status, notes=notes))
        return render_template("tasks.html", items=items, q=request.args.get("q",""), status_filter=status_filter)

    @app.post("/tasks/complete")
    def complete_task():
        path = request.form.get("path","")
        line_no = int(request.form.get("line_no","0") or 0)
        p = Path(path)
        if not p.exists() or not _is_under_notes_dir(p):
            flash("Note not found.")
            return redirect(url_for("tasks_page"))
        if line_no <= 0:
            flash("Bad task line.")
            return redirect(url_for("tasks_page"))
        changed = toggle_complete_in_file(p, line_no)
        if changed:
            _reindex()
        return redirect(request.referrer or url_for("tasks_page"))

    @app.route("/images/<path:filename>")
    def serve_image(filename: str):
        file_path = (images_dir / filename).resolve()
        if not _is_under_images_dir(file_path) or not file_path.exists():
            return ("Not found", 404)
        return send_from_directory(images_dir, filename)

    @app.post("/upload")
    def upload_image():
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400
        f = request.files["image"]
        if not f:
            return jsonify({"error": "No image uploaded"}), 400

        ext_by_type = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        ext = ext_by_type.get(f.mimetype)
        if not ext:
            return jsonify({"error": "Unsupported image type"}), 400

        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = images_dir / filename
        f.save(file_path)
        return jsonify({"url": f"/images/{filename}"})

    return app
