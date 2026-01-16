from pathlib import Path
from app.config import load_config
from app.web import create_app

def main():
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "config.json")
    cfg = cfg.__class__(
        data_dir=(root / cfg.data_dir).resolve(),
        notes_dir=(root / cfg.notes_dir).resolve(),
        index_path=(root / cfg.index_path).resolve(),
        host=cfg.host,
        port=cfg.port,
        chunk_min_chars=cfg.chunk_min_chars,
        chunk_max_chars=cfg.chunk_max_chars,
        chunk_overlap_chars=cfg.chunk_overlap_chars,
        max_results=cfg.max_results,
    )
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.notes_dir.mkdir(parents=True, exist_ok=True)
    app = create_app(cfg)
    app.run(host=cfg.host, port=cfg.port, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
