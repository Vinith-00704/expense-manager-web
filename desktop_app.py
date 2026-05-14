"""
desktop_app.py
==============
Launches FinanceOS as a standalone desktop application.

- Starts the Flask server on a random free port (background thread)
- Opens a native OS window via pywebview (no browser required)
- Double-clickable: run with  .venv/Scripts/pythonw desktop_app.py
- Or package into .exe with:  pyinstaller desktop_app.spec
"""
import os
import sys
import socket
import threading
import time
import logging

# Suppress Flask's console output in desktop mode
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

# ── Find a free port ─────────────────────────────────────────────────────────

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ── Start Flask in a background daemon thread ─────────────────────────────────

def _start_flask(port: int):
    from app import create_app
    flask_app = create_app()
    flask_app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def _wait_for_server(port: int, timeout: float = 15.0) -> bool:
    """Block until the Flask server accepts connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


# ── Main entry point ──────────────────────────────────────────────────────────

def main():
    port = _free_port()

    # Start Flask server in a background thread
    server_thread = threading.Thread(
        target=_start_flask, args=(port,), daemon=True
    )
    server_thread.start()

    # Wait until Flask is ready
    if not _wait_for_server(port):
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("FinanceOS", "Failed to start server. Check your database connection.")
        sys.exit(1)

    # Open the native window
    import webview

    window = webview.create_window(
        title       = "FinanceOS",
        url         = f"http://127.0.0.1:{port}",
        width       = 1280,
        height      = 800,
        min_size    = (900, 600),
        resizable   = True,
        text_select = False,
        background_color = "#000000",
    )

    # Start pywebview (this blocks until the window is closed)
    webview.start(
        debug     = False,    # set True to open DevTools
        gui       = "edgechromium",   # Windows: uses built-in EdgeHTML engine
    )


if __name__ == "__main__":
    main()
