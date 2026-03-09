"""Tests for engine.subphonics_server — SUBPHONICS web server."""

import json
import threading
import time
from http.server import HTTPServer

import pytest

from engine.subphonics import SubphonicsEngine
from engine.subphonics_server import (
    PORT,
    STATIC_DIR,
    SubphonicsHandler,
    start_server,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    return SubphonicsEngine()


@pytest.fixture
def test_server(engine):
    """Start a test server on a random port."""
    import socket
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        port = s.getsockname()[1]

    SubphonicsHandler.engine = engine
    server = HTTPServer(("127.0.0.1", port), SubphonicsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)  # let server start
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_port(self):
        assert PORT == 8433

    def test_static_dir(self):
        assert STATIC_DIR.name == "static"

    def test_static_dir_exists(self):
        assert STATIC_DIR.exists()


# ═══════════════════════════════════════════════════════════════════════════
# SubphonicsHandler (unit tests without HTTP)
# ═══════════════════════════════════════════════════════════════════════════

class TestHandlerConfig:
    def test_handler_has_engine_attr(self):
        assert hasattr(SubphonicsHandler, 'engine')


# ═══════════════════════════════════════════════════════════════════════════
# Integration tests with real HTTP
# ═══════════════════════════════════════════════════════════════════════════

class TestAPIStatus:
    def test_status(self, test_server):
        import urllib.request
        resp = urllib.request.urlopen(f"{test_server}/api/status")
        data = json.loads(resp.read())
        assert data["name"] == "SUBPHONICS"
        assert data["status"] == "ONLINE"
        assert data["phi"] > 1.6
        assert data["base_frequency_hz"] == 432
        assert data["commandable_modules"] >= 40

    def test_status_has_version(self, test_server):
        import urllib.request
        resp = urllib.request.urlopen(f"{test_server}/api/status")
        data = json.loads(resp.read())
        assert "version" in data


class TestAPIGreeting:
    def test_greeting(self, test_server):
        import urllib.request
        resp = urllib.request.urlopen(f"{test_server}/api/greeting")
        data = json.loads(resp.read())
        assert "greeting" in data
        assert "SUBPHONICS" in data["greeting"]
        assert len(data["greeting"]) > 30


class TestAPIModules:
    def test_modules_list(self, test_server):
        import urllib.request
        resp = urllib.request.urlopen(f"{test_server}/api/modules")
        data = json.loads(resp.read())
        assert "modules" in data
        assert data["total"] >= 40
        assert len(data["modules"]) == data["total"]

    def test_module_structure(self, test_server):
        import urllib.request
        resp = urllib.request.urlopen(f"{test_server}/api/modules")
        data = json.loads(resp.read())
        m = data["modules"][0]
        assert "name" in m
        assert "category" in m
        assert "description" in m


class TestAPIChat:
    def test_chat_basic(self, test_server):
        import urllib.request
        body = json.dumps({"message": "hello"}).encode()
        req = urllib.request.Request(
            f"{test_server}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        assert data["role"] == "subphonics"
        assert len(data["content"]) > 10
        assert "timestamp" in data

    def test_chat_help(self, test_server):
        import urllib.request
        body = json.dumps({"message": "help"}).encode()
        req = urllib.request.Request(
            f"{test_server}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        assert "render" in data["content"].lower() or "command" in data["content"].lower()

    def test_chat_status(self, test_server):
        import urllib.request
        body = json.dumps({"message": "status"}).encode()
        req = urllib.request.Request(
            f"{test_server}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        assert "module" in data["content"].lower() or "status" in data["content"].lower()

    def test_chat_empty_message(self, test_server):
        import urllib.request
        body = json.dumps({"message": ""}).encode()
        req = urllib.request.Request(
            f"{test_server}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())
            assert "error" in data
        except urllib.error.HTTPError as e:
            assert e.code == 400

    def test_chat_invalid_json(self, test_server):
        import urllib.request
        req = urllib.request.Request(
            f"{test_server}/api/chat",
            data=b"not json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            assert e.code == 400


class TestAPISession:
    def test_session(self, test_server):
        import urllib.request
        # Send a message first
        body = json.dumps({"message": "yo"}).encode()
        req = urllib.request.Request(
            f"{test_server}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req)

        # Check session
        resp = urllib.request.urlopen(f"{test_server}/api/session")
        data = json.loads(resp.read())
        assert "session_id" in data
        assert "messages" in data
        assert len(data["messages"]) >= 2


class TestAPIRender:
    def test_render_endpoint(self, test_server):
        import urllib.request
        body = json.dumps({"module": "phi_analyzer"}).encode()
        req = urllib.request.Request(
            f"{test_server}/api/render",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        assert "module" in data
        assert "response" in data

    def test_render_no_module(self, test_server):
        import urllib.request
        body = json.dumps({}).encode()
        req = urllib.request.Request(
            f"{test_server}/api/render",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            assert e.code == 400


class TestStaticServing:
    def test_serve_html(self, test_server):
        import urllib.request
        resp = urllib.request.urlopen(f"{test_server}/")
        html = resp.read().decode()
        assert "SUBPHONICS" in html
        assert "<!DOCTYPE html>" in html

    def test_404(self, test_server):
        import urllib.request
        try:
            urllib.request.urlopen(f"{test_server}/nonexistent")
        except urllib.error.HTTPError as e:
            assert e.code == 404


class TestCORS:
    def test_options(self, test_server):
        import urllib.request
        req = urllib.request.Request(
            f"{test_server}/api/chat",
            method="OPTIONS",
        )
        resp = urllib.request.urlopen(req)
        assert resp.status == 204


# ═══════════════════════════════════════════════════════════════════════════
# start_server (just verify it's callable, don't actually block)
# ═══════════════════════════════════════════════════════════════════════════

class TestStartServer:
    def test_start_server_callable(self):
        assert callable(start_server)
