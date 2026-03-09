"""Tests for engine.preset_browser — Session 152."""
import pytest
from engine.preset_browser import PresetBrowser, Preset


class TestPresetBrowser:
    def test_init(self):
        b = PresetBrowser()
        assert b.count() > 0  # has builtin presets

    def test_search(self):
        b = PresetBrowser()
        results = b.search("bass")
        assert isinstance(results, list)

    def test_categories(self):
        b = PresetBrowser()
        cats = b.categories()
        assert isinstance(cats, list)

    def test_add_preset(self):
        b = PresetBrowser()
        p = Preset(name="test", module="sub_bass", category="bass")
        b.add(p)
        found = b.search("test")
        assert len(found) > 0

    def test_remove(self):
        b = PresetBrowser()
        p = Preset(name="removeme", module="test")
        b.add(p)
        assert b.remove(p.uid) is True

    def test_by_module(self):
        b = PresetBrowser()
        results = b.by_module("sub_bass")
        assert isinstance(results, list)

    def test_summary(self):
        b = PresetBrowser()
        s = b.summary_text()
        assert isinstance(s, str)
