import threading
import time
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from app.config import default_config
from app.web import create_app


def _make_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 6, 58, 58), radius=12, outline=(30, 99, 206, 255), width=4)
    d.text((20, 18), "N", fill=(30, 99, 206, 255))
    return img


def main():
    cfg = default_config(Path(__file__).resolve().parent)
    flask_app = create_app(cfg)

    def run_server():
        flask_app.run(host=cfg.host, port=cfg.port, debug=False, threaded=True)

    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(0.6)

    url = f"http://{cfg.host}:{cfg.port}"

    # Define callbacks RIGHT HERE so they definitely exist before menu is built
    open_ui = lambda icon=None, item=None: webbrowser.open(url)
    new_note = lambda icon=None, item=None: webbrowser.open(url + "/new")
    browse = lambda icon=None, item=None: webbrowser.open(url + "/browse")
    tasks = lambda icon=None, item=None: webbrowser.open(url + "/tasks")
    copilot = lambda icon=None, item=None: webbrowser.open(url + "/copilot")

    def quit_app(icon, item):
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Open", open_ui, default=True),
        pystray.MenuItem("New note", new_note),
        pystray.MenuItem("Browse", browse),
        pystray.MenuItem("Tasks", tasks),
        pystray.MenuItem("Copilot", copilot),
        pystray.MenuItem("Quit", quit_app),
    )

    icon = pystray.Icon("fireforget", _make_icon(), "Fire & Forget Notes", menu)
    icon.run()


if __name__ == "__main__":
    main()
