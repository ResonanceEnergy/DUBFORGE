"""Tests for engine.realtime_monitor — signal monitoring and phi coherence."""

import json
from pathlib import Path

import numpy as np

from engine.realtime_monitor import (
    MonitorSession,
    MonitorSnapshot,
    analyze_chunk,
    export_monitor_report,
    main,
    monitor_signal_stream,
)

SAMPLE_RATE = 44100


def _make_signal(freq: float = 432.0, dur: float = 1.0) -> np.ndarray:
    """Generate a sine signal for testing."""
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    return 0.5 * np.sin(2 * np.pi * freq * t)


# ── MonitorSnapshot ──────────────────────────────────────────────────────

class TestMonitorSnapshot:
    def test_creation(self):
        s = MonitorSnapshot(0.0, 0.35, 0.5, 432.0, 0.8, 1.43)
        assert s.timestamp == 0.0
        assert s.rms == 0.35
        assert s.peak == 0.5

    def test_fields(self):
        s = MonitorSnapshot(1.0, 0.1, 0.2, 100.0, 0.5, 2.0)
        assert s.spectral_centroid == 100.0
        assert s.phi_coherence == 0.5
        assert s.crest_factor == 2.0


# ── MonitorSession ───────────────────────────────────────────────────────

class TestMonitorSession:
    def test_empty_session(self):
        sess = MonitorSession()
        assert len(sess.snapshots) == 0

    def test_add_snapshot(self):
        sess = MonitorSession()
        snap = MonitorSnapshot(0.0, 0.1, 0.2, 100.0, 0.5, 2.0)
        sess.add(snap)
        assert len(sess.snapshots) == 1

    def test_latest_empty(self):
        sess = MonitorSession()
        assert sess.latest() is None

    def test_latest_returns_last(self):
        sess = MonitorSession()
        s1 = MonitorSnapshot(1.0, 0.1, 0.2, 100.0, 0.5, 2.0)
        s2 = MonitorSnapshot(2.0, 0.2, 0.3, 200.0, 0.6, 1.5)
        sess.add(s1)
        sess.add(s2)
        assert sess.latest().timestamp == 2.0

    def test_avg_phi_coherence_empty(self):
        sess = MonitorSession()
        assert sess.avg_phi_coherence() == 0.0

    def test_avg_phi_coherence(self):
        sess = MonitorSession()
        sess.add(MonitorSnapshot(0, 0.1, 0.2, 100, 0.4, 1.0))
        sess.add(MonitorSnapshot(0, 0.1, 0.2, 100, 0.6, 1.0))
        assert abs(sess.avg_phi_coherence() - 0.5) < 1e-6

    def test_peak_rms_empty(self):
        sess = MonitorSession()
        assert sess.peak_rms() == 0.0

    def test_peak_rms(self):
        sess = MonitorSession()
        sess.add(MonitorSnapshot(0, 0.1, 0.2, 100, 0.5, 1.0))
        sess.add(MonitorSnapshot(0, 0.3, 0.4, 100, 0.5, 1.0))
        assert sess.peak_rms() == 0.3

    def test_to_dict(self):
        sess = MonitorSession()
        sess.add(MonitorSnapshot(0, 0.1, 0.2, 100, 0.5, 2.0))
        d = sess.to_dict()
        assert d["n_snapshots"] == 1
        assert "avg_phi_coherence" in d
        assert "peak_rms" in d
        assert d["latest"] is not None

    def test_max_history_truncation(self):
        sess = MonitorSession(max_history=5)
        for i in range(10):
            sess.add(MonitorSnapshot(float(i), 0.1, 0.2, 100, 0.5, 2.0))
        assert len(sess.snapshots) == 5


# ── analyze_chunk ────────────────────────────────────────────────────────

class TestAnalyzeChunk:
    def test_returns_snapshot(self):
        sig = _make_signal()
        snap = analyze_chunk(sig)
        assert isinstance(snap, MonitorSnapshot)

    def test_rms_positive(self):
        sig = _make_signal()
        snap = analyze_chunk(sig)
        assert snap.rms > 0

    def test_peak_positive(self):
        sig = _make_signal()
        snap = analyze_chunk(sig)
        assert snap.peak > 0

    def test_spectral_centroid_positive(self):
        sig = _make_signal()
        snap = analyze_chunk(sig)
        assert snap.spectral_centroid > 0

    def test_empty_signal(self):
        sig = np.array([])
        snap = analyze_chunk(sig)
        assert snap.rms == 0.0
        assert snap.peak == 0.0


# ── monitor_signal_stream ───────────────────────────────────────────────

class TestMonitorSignalStream:
    def test_returns_session(self):
        chunks = [_make_signal(dur=0.5), _make_signal(dur=0.5)]
        sess = monitor_signal_stream(chunks)
        assert isinstance(sess, MonitorSession)

    def test_correct_snapshot_count(self):
        chunks = [_make_signal(dur=0.5) for _ in range(3)]
        sess = monitor_signal_stream(chunks)
        assert len(sess.snapshots) == 3


# ── export_monitor_report ────────────────────────────────────────────────

class TestExportMonitorReport:
    def test_creates_report(self, tmp_path):
        sess = MonitorSession()
        sess.add(MonitorSnapshot(0, 0.1, 0.2, 100, 0.5, 2.0))
        path = export_monitor_report(sess, str(tmp_path))
        assert Path(path).exists()

    def test_report_valid_json(self, tmp_path):
        sess = MonitorSession()
        sess.add(MonitorSnapshot(0, 0.1, 0.2, 100, 0.5, 2.0))
        path = export_monitor_report(sess, str(tmp_path))
        with open(path) as f:
            data = json.load(f)
        assert "n_snapshots" in data
        assert "snapshots" in data


# ── main ─────────────────────────────────────────────────────────────────

class TestMain:
    def test_main_runs(self, capsys):
        main()
        captured = capsys.readouterr()
        assert "Real-Time Monitor" in captured.out
