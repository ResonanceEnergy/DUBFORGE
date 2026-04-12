"""Tests for engine.plugin_scaffold — plugin registry, discovery, templates."""

from pathlib import Path

import pytest

from engine.plugin_scaffold import (
    PluginEntry,
    PluginMeta,
    PluginRegistry,
    create_plugin_template,
    discover_plugins,
    get_registry,
    main,
)

# ── PluginMeta ───────────────────────────────────────────────────────────

class TestPluginMeta:
    def test_creation(self):
        m = PluginMeta("synth1", "1.0.0", "author", "synth", "A synth")
        assert m.name == "synth1"
        assert m.version == "1.0.0"
        assert m.author == "author"
        assert m.category == "synth"
        assert m.description == "A synth"

    def test_default_description(self):
        m = PluginMeta("x", "0.1", "a", "fx")
        assert m.description == ""


# ── PluginRegistry ───────────────────────────────────────────────────────

class TestPluginRegistry:
    def test_register_and_get(self):
        reg = PluginRegistry()
        reg.register("test_plug", lambda: "result")
        entry = reg.get("test_plug")
        assert entry is not None
        assert entry.name == "test_plug"

    def test_register_with_meta(self):
        reg = PluginRegistry()
        meta = PluginMeta("p", "2.0", "me", "fx", "My FX")
        reg.register("p", lambda: None, meta)
        entry = reg.get("p")
        assert entry is not None
        assert entry.meta.version == "2.0"

    def test_register_with_presets(self):
        reg = PluginRegistry()
        presets = {"warm": {"cutoff": 500}}
        reg.register("p", lambda: None, presets=presets)
        entry = reg.get("p")
        assert entry is not None
        assert entry.presets == presets

    def test_unregister_existing(self):
        reg = PluginRegistry()
        reg.register("p", lambda: None)
        assert reg.unregister("p") is True
        assert reg.get("p") is None

    def test_unregister_nonexistent(self):
        reg = PluginRegistry()
        assert reg.unregister("nope") is False

    def test_list_plugins_sorted(self):
        reg = PluginRegistry()
        reg.register("zebra", lambda: None)
        reg.register("alpha", lambda: None)
        assert reg.list_plugins() == ["alpha", "zebra"]

    def test_list_plugins_empty(self):
        reg = PluginRegistry()
        assert reg.list_plugins() == []

    def test_list_by_category(self):
        reg = PluginRegistry()
        reg.register("s1", lambda: None, PluginMeta("s1", "1", "a", "synth"))
        reg.register("f1", lambda: None, PluginMeta("f1", "1", "a", "fx"))
        reg.register("s2", lambda: None, PluginMeta("s2", "1", "a", "synth"))
        synths = reg.list_by_category("synth")
        assert synths == ["s1", "s2"]

    def test_list_by_category_empty(self):
        reg = PluginRegistry()
        assert reg.list_by_category("analysis") == []

    def test_run_success(self):
        reg = PluginRegistry()
        reg.register("adder", lambda x=0, y=0: x + y)
        result = reg.run("adder", x=3, y=4)
        assert result == 7

    def test_run_not_found_raises(self):
        reg = PluginRegistry()
        with pytest.raises(KeyError, match="Plugin not found"):
            reg.run("missing")

    def test_get_nonexistent_returns_none(self):
        reg = PluginRegistry()
        assert reg.get("nonexistent") is None

    def test_register_overwrites(self):
        reg = PluginRegistry()
        reg.register("p", lambda: "v1")
        reg.register("p", lambda: "v2")
        assert reg.run("p") == "v2"


# ── PluginEntry ──────────────────────────────────────────────────────────

class TestPluginEntry:
    def test_entry_fields(self):
        meta = PluginMeta("e", "1", "a", "fx")
        entry = PluginEntry("e", lambda: None, meta)
        assert entry.name == "e"
        assert entry.meta.category == "fx"
        assert entry.presets == {}


# ── discover_plugins ─────────────────────────────────────────────────────

class TestDiscoverPlugins:
    def test_nonexistent_dir_returns_empty(self):
        result = discover_plugins("/tmp/nonexistent_dir_xyz_dubforge")
        assert result == []

    def test_discover_in_dir_with_py_files(self, tmp_path):
        (tmp_path / "my_synth.py").write_text("# plugin")
        (tmp_path / "my_fx.py").write_text("# plugin")
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "_private.py").write_text("")
        result = discover_plugins(str(tmp_path))
        assert "my_synth" in result
        assert "my_fx" in result
        assert "__init__" not in result
        assert "_private" not in result


# ── create_plugin_template ───────────────────────────────────────────────

class TestCreatePluginTemplate:
    def test_creates_file(self, tmp_path):
        path = create_plugin_template("my_plug", "fx", str(tmp_path))
        assert Path(path).exists()

    def test_file_contains_name(self, tmp_path):
        path = create_plugin_template("cool_synth", "synth", str(tmp_path))
        content = Path(path).read_text()
        assert "cool_synth" in content

    def test_file_contains_category(self, tmp_path):
        path = create_plugin_template("bass", "synth", str(tmp_path))
        content = Path(path).read_text()
        assert "synth" in content


# ── get_registry ─────────────────────────────────────────────────────────

class TestGetRegistry:
    def test_returns_registry(self):
        reg = get_registry()
        assert isinstance(reg, PluginRegistry)

    def test_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2


# ── main ─────────────────────────────────────────────────────────────────

class TestMain:
    def test_main_runs(self, capsys):
        main()
        captured = capsys.readouterr()
        assert "Plugin Scaffold" in captured.out
