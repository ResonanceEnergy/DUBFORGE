"""Tests for engine.sb_analyzer — Subtronics corpus analyzer."""
import pytest
from engine.sb_analyzer import (
    Track,
    Album,
    SignatureVector,
    build_corpus,
    load_corpus,
    analyze_corpus,
    build_signature_vector,
    vip_delta_analysis,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def corpus():
    return build_corpus()


@pytest.fixture
def tiny_corpus():
    """Minimal 1-album corpus for deterministic checks."""
    return [
        Album(
            title="Test EP",
            year=2025,
            tracks=[
                Track(title="Drop A", duration_s=200.0, bpm=150.0, is_vip=False),
                Track(title="Drop B", duration_s=240.0, bpm=148.0, is_vip=True),
                Track(title="Drop A VIP", duration_s=210.0, bpm=150.0, is_vip=True),
            ],
        )
    ]


# ── Track dataclass ──────────────────────────────────────────────

class TestTrack:
    def test_defaults(self):
        t = Track(title="X", duration_s=180.0)
        assert t.bpm == 150.0
        assert t.is_vip is False
        assert t.is_remix is False
        assert t.collab_artist == ""

    def test_custom_fields(self):
        t = Track(title="Y", duration_s=200.0, bpm=140.0, key="F", is_collab=True, collab_artist="Artist")
        assert t.bpm == 140.0
        assert t.is_collab is True
        assert t.collab_artist == "Artist"


# ── Album dataclass ──────────────────────────────────────────────

class TestAlbum:
    def test_properties(self):
        tracks = [
            Track(title="A", duration_s=200.0, bpm=150.0),
            Track(title="B", duration_s=300.0, bpm=140.0),
        ]
        album = Album(title="EP", year=2024, tracks=tracks)
        assert album.track_count == 2
        assert album.total_duration_s == 500.0
        assert album.avg_duration_s == 250.0
        assert album.avg_bpm == 145.0


# ── SignatureVector ──────────────────────────────────────────────

class TestSignatureVector:
    def test_defaults(self):
        sv = SignatureVector()
        assert sv.avg_bpm == 150.0
        assert sv.build_curve == "phi"
        assert sv.fractal_alignment_score == 0.0

    def test_compute_fractal_alignment(self):
        sv = SignatureVector()
        score = sv.compute_fractal_alignment(16)
        assert 0.0 <= score <= 1.0
        assert sv.fractal_alignment_score == score

    def test_fractal_alignment_non_fibonacci(self):
        sv = SignatureVector()
        score = sv.compute_fractal_alignment(7)  # not Fibonacci
        assert 0.0 <= score <= 1.0


# ── build_corpus ─────────────────────────────────────────────────

class TestBuildCorpus:
    def test_returns_list_of_albums(self, corpus):
        assert isinstance(corpus, list)
        assert len(corpus) >= 4
        assert all(isinstance(a, Album) for a in corpus)

    def test_total_tracks(self, corpus):
        total = sum(a.track_count for a in corpus)
        assert total >= 50  # ~74 in full corpus

    def test_albums_have_tracks(self, corpus):
        for a in corpus:
            assert a.track_count > 0
            assert a.year > 2000


# ── load_corpus ──────────────────────────────────────────────────

class TestLoadCorpus:
    def test_returns_albums(self):
        result = load_corpus()
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(a, Album) for a in result)


# ── analyze_corpus ───────────────────────────────────────────────

class TestAnalyzeCorpus:
    def test_structure(self, corpus):
        analysis = analyze_corpus(corpus)
        assert "total_albums" in analysis
        assert "total_tracks" in analysis
        assert "global_avg_bpm" in analysis
        assert "albums" in analysis
        assert analysis["total_albums"] == len(corpus)

    def test_durations(self, corpus):
        analysis = analyze_corpus(corpus)
        assert analysis["total_duration_s"] > 0
        assert analysis["global_avg_duration_s"] > 0

    def test_tiny_corpus(self, tiny_corpus):
        analysis = analyze_corpus(tiny_corpus)
        assert analysis["total_albums"] == 1
        assert analysis["total_tracks"] == 3


# ── build_signature_vector ───────────────────────────────────────

class TestBuildSignatureVector:
    def test_returns_signature_vector(self, corpus):
        sv = build_signature_vector(corpus)
        assert isinstance(sv, SignatureVector)
        assert sv.avg_bpm > 100

    def test_key_centers(self, corpus):
        sv = build_signature_vector(corpus)
        assert isinstance(sv.key_centers, list)


# ── vip_delta_analysis ───────────────────────────────────────────

class TestVipDeltaAnalysis:
    def test_returns_list(self, corpus):
        deltas = vip_delta_analysis(corpus)
        assert isinstance(deltas, list)

    def test_delta_structure(self, corpus):
        deltas = vip_delta_analysis(corpus)
        if deltas:
            d = deltas[0]
            assert "vip" in d or "remix" in d
