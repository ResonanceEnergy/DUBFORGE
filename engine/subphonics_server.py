"""
DUBFORGE — SUBPHONICS Web Server

HTTP server that powers the SUBPHONICS browser chatbot interface.
Pure Python implementation — no Flask, no FastAPI, no external deps.

Endpoints:
  GET  /                → Chat UI (HTML)
  GET  /api/status      → System status JSON
  GET  /api/greeting    → SUBPHONICS greeting
  POST /api/chat        → Send message, get response
  GET  /api/session     → Current session history
  GET  /api/modules     → List all modules
  POST /api/render      → Render a named module
  GET  /static/<file>   → Static assets

Launch: python -m engine.subphonics_server [--port 8433]
"""

import json
import mimetypes
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

# Ensure engine is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.subphonics import MODULE_MAP, PHI, SubphonicsEngine, get_engine

PORT = 8433  # phi-adjacent: 8 + 433 ≈ 432 + 1
STATIC_DIR = Path(__file__).parent / "static"


class SubphonicsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for SUBPHONICS chatbot server."""

    engine: SubphonicsEngine | None = None  # set at server startup

    def log_message(self, format, *args):
        """Override to prefix with SUBPHONICS branding."""
        print(f"[SUBPHONICS] {args[0]}")

    # ─── GET routes ───────────────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        routes = {
            "/": self._serve_chat_ui,
            "/api/status": self._api_status,
            "/api/greeting": self._api_greeting,
            "/api/session": self._api_session,
            "/api/modules": self._api_modules,
        }

        if path in routes:
            routes[path]()
        elif path.startswith("/static/"):
            self._serve_static(path)
        else:
            self._json_response({"error": "not found"}, 404)

    # ─── POST routes ──────────────────────────────────────────────────

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/chat":
            self._api_chat()
        elif path == "/api/render":
            self._api_render()
        else:
            self._json_response({"error": "not found"}, 404)

    # ─── API handlers ────────────────────────────────────────────────

    def _serve_chat_ui(self):
        """Serve the main chat HTML page."""
        html_path = STATIC_DIR / "subphonics.html"
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8")
            self._html_response(content)
        else:
            self._html_response(
                "<h1>SUBPHONICS</h1><p>Chat UI not found. "
                "Place subphonics.html in engine/static/</p>", 500)

    def _api_status(self):
        """System status endpoint."""
        eng = self.engine or get_engine()
        uptime = round(time.time() - eng._boot_time, 1)
        eng_dir = Path(__file__).parent
        engine_files = len(list(eng_dir.glob("*.py"))) - 1

        data = {
            "name": "SUBPHONICS",
            "version": eng.identity["version"],
            "phi": PHI,
            "base_frequency_hz": 432,
            "engine_modules": engine_files,
            "commandable_modules": len(eng.module_map),
            "uptime_seconds": uptime,
            "session_messages": len(eng.session.messages),
            "status": "ONLINE",
        }
        self._json_response(data)

    def _api_greeting(self):
        """Get SUBPHONICS greeting."""
        eng = self.engine or get_engine()
        self._json_response({"greeting": eng.get_greeting()})

    def _api_session(self):
        """Get current session history."""
        eng = self.engine or get_engine()
        self._json_response(eng.session.to_dict())

    def _api_modules(self):
        """List all modules."""
        modules = []
        for name, info in sorted(MODULE_MAP.items()):
            modules.append({
                "name": name,
                "category": info["category"],
                "description": info["desc"],
            })
        self._json_response({"modules": modules, "total": len(modules)})

    def _api_chat(self):
        """Process a chat message."""
        body = self._read_body()
        if not body:
            self._json_response({"error": "empty body"}, 400)
            return

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json_response({"error": "invalid JSON"}, 400)
            return

        message = data.get("message", "").strip()
        if not message:
            self._json_response({"error": "no message"}, 400)
            return

        eng = self.engine or get_engine()
        response_msg = eng.process_message(message)

        self._json_response({
            "role": response_msg.role,
            "content": response_msg.content,
            "timestamp": response_msg.timestamp,
            "metadata": response_msg.metadata,
        })

    def _api_render(self):
        """Render a specific module."""
        body = self._read_body()
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            self._json_response({"error": "invalid JSON"}, 400)
            return

        module = data.get("module", "")
        if not module:
            self._json_response({"error": "no module specified"}, 400)
            return

        eng = self.engine or get_engine()
        result = eng._cmd_render_module(module)
        self._json_response({
            "module": module,
            "response": result.get("text", ""),
            "metadata": result.get("meta", {}),
        })

    # ─── Static file serving ─────────────────────────────────────────

    def _serve_static(self, path: str):
        """Serve static files from engine/static/."""
        rel = path.lstrip("/static/")
        file_path = STATIC_DIR / rel
        if not file_path.exists() or not file_path.is_file():
            self._json_response({"error": "file not found"}, 404)
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"

        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    # ─── CORS ─────────────────────────────────────────────────────────

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ─── Response helpers ─────────────────────────────────────────────

    def _json_response(self, data: dict, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html_response(self, html: str, status: int = 200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return b""
        return self.rfile.read(length)


def start_server(port: int = PORT, engine: SubphonicsEngine | None = None):
    """Start the SUBPHONICS web server."""
    eng = engine or get_engine()
    SubphonicsHandler.engine = eng

    server = HTTPServer(("0.0.0.0", port), SubphonicsHandler)
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███████╗██╗   ██╗██████╗ ██████╗ ██╗  ██╗ ██████╗         ║
║   ██╔════╝██║   ██║██╔══██╗██╔══██╗██║  ██║██╔═══██╗        ║
║   ███████╗██║   ██║██████╔╝██████╔╝███████║██║   ██║        ║
║   ╚════██║██║   ██║██╔══██╗██╔═══╝ ██╔══██║██║   ██║        ║
║   ███████║╚██████╔╝██████╔╝██║     ██║  ██║╚██████╔╝        ║
║   ╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝ ╚═════╝        ║
║                   N I C S                                    ║
║                                                              ║
║   DUBFORGE Project Director — Online                         ║
║   Port: {port:<5}  |  PHI: 1.6180339887  |  432 Hz          ║
║                                                              ║
║   Open browser → http://localhost:{port}                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SUBPHONICS] Shutting down. The bass never truly stops.")
        server.server_close()


def main() -> None:
    """Entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="SUBPHONICS Chat Server")
    parser.add_argument("--port", type=int, default=PORT,
                        help=f"Server port (default: {PORT})")
    args = parser.parse_args()
    start_server(port=args.port)


if __name__ == "__main__":
    main()
