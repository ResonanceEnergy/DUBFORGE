"""Tests for engine.tag_system — Session 199."""
import pytest
from engine.tag_system import TagSystem


class TestTagSystem:
    def test_create(self, tmp_path):
        ts = TagSystem(data_dir=str(tmp_path / "tags"))
        assert isinstance(ts, TagSystem)

    def test_add_item_with_tags(self, tmp_path):
        ts = TagSystem(data_dir=str(tmp_path / "tags"))
        item = ts.add_item("sample1", "bass_hit", tags=["bass", "heavy"])
        assert "bass" in item.tags
        assert "heavy" in item.tags
