"""Tests for engine.metadata — Session 189."""
import pytest
from engine.metadata import MetadataManager, AudioMetadata


class TestMetadata:
    def test_create(self):
        mm = MetadataManager()
        assert isinstance(mm, MetadataManager)

    def test_create_metadata(self):
        mm = MetadataManager()
        meta = mm.create("test.wav", title="Test Track", bpm=140)
        assert isinstance(meta, AudioMetadata)
        assert meta.title == "Test Track"

    def test_metadata_to_dict(self):
        mm = MetadataManager()
        meta = mm.create("test.wav", bpm=140)
        d = meta.to_dict()
        assert isinstance(d, dict)
