from pathlib import Path
from app.config import default_config
from app.web import create_app

def main():
    cfg = default_config(Path(__file__).resolve().parent)
    app = create_app(cfg)
    app.run(host=cfg.host, port=cfg.port, debug=False, threaded=True)

if __name__ == "__main__":
    main()
