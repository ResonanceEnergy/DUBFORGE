"""Consolidated smoke tests for engine modules.

Merged from 42 individual stub files — each had 1-2 tests verifying
basic instantiation and one representative operation per module.
"""
import math
import os

import pytest

SR = 44100


# ── Pure isinstance stubs (no behaviour beyond construction) ────────────


class TestBatchProcessor:
    def test_create(self):
        from engine.batch_processor import BatchProcessor
        assert isinstance(BatchProcessor(), BatchProcessor)


class TestCollaboration:
    def test_create(self):
        from engine.collaboration import CollaborationEngine
        assert isinstance(CollaborationEngine(), CollaborationEngine)


class TestEPBuilder:
    def test_create(self):
        from engine.ep_builder import EPBuilder
        assert isinstance(EPBuilder(), EPBuilder)


class TestFormatConverter:
    def test_create(self):
        from engine.format_converter import FormatConverter
        assert isinstance(FormatConverter(), FormatConverter)


class TestMultiTrackRenderer:
    def test_create(self):
        from engine.multitrack_renderer import MultiTrackRenderer
        assert isinstance(MultiTrackRenderer(), MultiTrackRenderer)


class TestSamplePackExporter:
    def test_create(self):
        from engine.sample_pack_exporter import SamplePackExporter
        assert isinstance(SamplePackExporter(), SamplePackExporter)


class TestWavPool:
    def test_create(self):
        from engine.wav_pool import WavPool
        assert isinstance(WavPool(), WavPool)


class TestBackupSystem:
    def test_create(self, tmp_path):
        from engine.backup_system import BackupSystem
        assert isinstance(BackupSystem(str(tmp_path / "backups")), BackupSystem)


# ── Audio analysis / detection ──────────────────────────────────────────


class TestAudioAnalyzer:
    def test_create(self):
        from engine.audio_analyzer import AudioAnalyzer
        assert isinstance(AudioAnalyzer(), AudioAnalyzer)

    def test_analyze(self):
        from engine.audio_analyzer import AudioAnalyzer, AnalysisReport
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = AudioAnalyzer().analyze(signal)
        assert isinstance(result, AnalysisReport)


class TestKeyDetector:
    def test_create(self):
        from engine.key_detector import KeyDetector
        assert isinstance(KeyDetector(), KeyDetector)

    def test_detect_key(self):
        from engine.key_detector import KeyDetector, KeyResult
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = KeyDetector().detect_key(signal)
        assert isinstance(result, KeyResult)


class TestTempoDetector:
    def test_create(self):
        from engine.tempo_detector import TempoDetector
        assert isinstance(TempoDetector(), TempoDetector)

    def test_detect(self):
        from engine.tempo_detector import TempoDetector
        beat_dur = int(60.0 / 140 * SR)
        signal = [0.0] * (beat_dur * 8)
        for beat in range(8):
            pos = beat * beat_dur
            for j in range(200):
                if pos + j < len(signal):
                    signal[pos + j] = 0.9 * math.exp(-j / 50.0)
        result = TempoDetector().detect(signal)
        assert isinstance(result.bpm, float)
        assert result.bpm > 0


# ── Audio processing ────────────────────────────────────────────────────


class TestAudioSplitter:
    def test_create(self):
        from engine.audio_splitter import AudioSplitter
        assert isinstance(AudioSplitter(), AudioSplitter)

    def test_split_by_duration(self):
        from engine.audio_splitter import AudioSplitter, AudioSegment
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR * 2)]
        chunks = AudioSplitter().split_by_duration(signal, duration_ms=1000.0)
        assert len(chunks) >= 2
        assert isinstance(chunks[0], AudioSegment)


class TestAudioStitcher:
    def test_create(self):
        from engine.audio_stitcher import AudioStitcher
        assert isinstance(AudioStitcher(), AudioStitcher)

    def test_stitch_sequential(self):
        from engine.audio_stitcher import AudioStitcher, StitchSegment
        segments = [
            StitchSegment(samples=[0.5] * 1000),
            StitchSegment(samples=[0.3] * 1000),
        ]
        result = AudioStitcher().stitch_sequential(segments)
        assert len(result) == 2000


class TestDCRemover:
    def test_create(self):
        from engine.dc_remover import DCRemover
        assert isinstance(DCRemover(), DCRemover)

    def test_remove_mean(self):
        from engine.dc_remover import DCRemover
        signal = [0.5 + 0.3 * i / 100 for i in range(100)]
        result = DCRemover().remove_mean(signal)
        mean = sum(result) / len(result)
        assert abs(mean) < 0.01


class TestNormalizer:
    def test_create(self):
        from engine.normalizer import AudioNormalizer
        assert isinstance(AudioNormalizer(), AudioNormalizer)

    def test_peak_normalize(self):
        from engine.normalizer import AudioNormalizer
        signal = [0.3 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        norm_result = AudioNormalizer().normalize_peak(signal, target_db=-0.3)
        peak = max(abs(s) for s in norm_result.samples)
        assert peak > 0.9


class TestDynamicsProcessor:
    def test_create(self):
        from engine.dynamics_processor import DynamicsProcessor
        assert isinstance(DynamicsProcessor(), DynamicsProcessor)

    def test_gate(self):
        from engine.dynamics_processor import DynamicsProcessor, GateConfig
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = DynamicsProcessor().gate(signal, GateConfig(threshold_db=-30.0))
        assert len(result) == len(signal)


class TestSpectralGate:
    def test_create(self):
        from engine.spectral_gate import SpectralGate
        assert isinstance(SpectralGate(), SpectralGate)

    def test_gate(self):
        from engine.spectral_gate import SpectralGate, BandGateConfig
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        config = BandGateConfig(low_freq=20.0, high_freq=20000.0, threshold_db=-40.0)
        result = SpectralGate().gate_band(signal, config)
        assert len(result) > 0


class TestSpectralMorph:
    def test_morph(self):
        from engine.spectral_morph import spectral_morph, MorphResult
        a = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        b = [0.5 * math.sin(2 * math.pi * 880 * i / SR) for i in range(SR)]
        result = spectral_morph(a, b, morph_factor=0.5)
        assert isinstance(result, MorphResult)
        assert len(result.signal) > 0

    def test_morph_result_to_dict(self):
        from engine.spectral_morph import spectral_morph
        a = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        b = [0.5 * math.sin(2 * math.pi * 880 * i / SR) for i in range(SR)]
        d = spectral_morph(a, b, morph_factor=0.5).to_dict()
        assert "morph_factor" in d


class TestStemSeparator:
    def test_separate(self):
        from engine.stem_separator import separate_stems, StemSet
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = separate_stems(signal)
        assert isinstance(result, StemSet)
        assert len(result.stems) > 0

    def test_stem_set_to_dict(self):
        from engine.stem_separator import separate_stems
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        d = separate_stems(signal).to_dict()
        assert "stems" in d


class TestStyleTransfer:
    def test_transfer(self):
        from engine.style_transfer import transfer_style, TransferResult
        source = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        target = [0.5 * math.sin(2 * math.pi * 880 * i / SR) for i in range(SR)]
        result = transfer_style(source, target)
        assert isinstance(result, TransferResult)
        assert len(result.signal) > 0

    def test_transfer_to_dict(self):
        from engine.style_transfer import transfer_style
        source = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        target = [0.5 * math.sin(2 * math.pi * 880 * i / SR) for i in range(SR)]
        d = transfer_style(source, target).to_dict()
        assert "transfer_amount" in d


# ── Synthesis / generation ──────────────────────────────────────────────


class TestEnvelopeGenerator:
    def test_create(self):
        from engine.envelope_generator import EnvelopeGenerator
        assert isinstance(EnvelopeGenerator(), EnvelopeGenerator)

    def test_adsr(self):
        from engine.envelope_generator import EnvelopeGenerator
        env = EnvelopeGenerator().adsr(0.01, 0.1, 0.7, 0.3, 1.0)
        assert len(env) > 0
        assert max(env) <= 1.01


class TestHarmonicGen:
    def test_create(self):
        from engine.harmonic_gen import HarmonicGenerator
        assert isinstance(HarmonicGenerator(), HarmonicGenerator)

    def test_render(self):
        from engine.harmonic_gen import HarmonicGenerator
        hg = HarmonicGenerator()
        spectrum = hg.harmonic_series(440.0)
        samples = hg.render(spectrum, duration_s=0.5)
        assert len(samples) > 0


class TestKarplusStrong:
    def test_render_default(self):
        from engine.karplus_strong import render_ks
        assert len(render_ks()) > 0

    def test_render_with_patch(self):
        from engine.karplus_strong import render_ks, KarplusStrongPatch
        patch = KarplusStrongPatch(frequency=440.0, duration=0.5)
        samples = render_ks(patch)
        assert len(samples) > 0
        assert len(samples) == int(0.5 * 44100)


class TestResonance:
    def test_create(self):
        from engine.resonance import ResonanceEngine
        assert isinstance(ResonanceEngine(), ResonanceEngine)

    def test_resonant_filter(self):
        from engine.resonance import ResonanceEngine
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = ResonanceEngine().resonant_filter(signal, 1000.0, 0.8)
        assert len(result) == len(signal)


class TestRingMod:
    def test_ring_modulate(self):
        from engine.ring_mod import ring_modulate, RingModPatch
        signal = [0.8 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        patch = RingModPatch(name="test", carrier_freq=200.0)
        result = ring_modulate(signal, patch)
        assert len(result) == len(signal)

    def test_phi_ring_mod(self):
        from engine.ring_mod import phi_ring_mod
        assert len(phi_ring_mod(440.0, 0.3)) > 0


class TestTuningSystem:
    def test_create(self):
        from engine.tuning_system import TuningSystem
        assert isinstance(TuningSystem(), TuningSystem)

    def test_equal_temperament_midi(self):
        from engine.tuning_system import TuningSystem
        freq = TuningSystem().equal_temperament_midi(69)  # A4
        assert abs(freq - 432.0) < 5


# ── Routing / arrangement / mastering ───────────────────────────────────


class TestAutoArranger:
    def test_generate_standard(self):
        from engine.auto_arranger import generate_arrangement, Arrangement
        arr = generate_arrangement(template="standard", bpm=140.0)
        assert isinstance(arr, Arrangement)
        assert arr.total_bars > 0

    def test_arrangement_to_dict(self):
        from engine.auto_arranger import generate_arrangement
        d = generate_arrangement(template="standard", bpm=140.0).to_dict()
        assert "sections" in d
        assert len(d["sections"]) > 0


class TestAutoMaster:
    def test_auto_master_default(self):
        from engine.auto_master import auto_master, MasterResult
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = auto_master(signal)
        assert isinstance(result, MasterResult)
        assert len(result.signal) > 0

    def test_auto_master_to_dict(self):
        from engine.auto_master import auto_master
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        d = auto_master(signal).to_dict()
        assert "stages" in d


class TestBusRouter:
    def test_create(self):
        from engine.bus_router import BusRouter
        assert isinstance(BusRouter(), BusRouter)

    def test_add_bus(self):
        from engine.bus_router import BusRouter
        br = BusRouter()
        br.add_bus("drums")
        assert "drums" in br.buses


class TestPanning:
    def test_create(self):
        from engine.panning import PanningEngine
        assert isinstance(PanningEngine(), PanningEngine)

    def test_pan(self):
        from engine.panning import PanningEngine
        result = PanningEngine().pan_constant_power([0.5] * 1000, 0.0)
        assert len(result.left) == 1000
        assert len(result.right) == 1000


class TestSignalChain:
    def test_create(self):
        from engine.signal_chain import SignalChainBuilder
        assert isinstance(SignalChainBuilder(), SignalChainBuilder)

    def test_create_and_process_chain(self):
        from engine.signal_chain import SignalChainBuilder
        chain = SignalChainBuilder().create_chain("test")
        chain.add("gain", params={"gain_db": -6})
        result = chain.process([0.8] * 1000)
        assert len(result) > 0


class TestBounce:
    def test_create(self):
        from engine.bounce import BounceEngine
        assert isinstance(BounceEngine(), BounceEngine)

    def test_bounce(self, output_dir):
        from engine.bounce import BounceEngine
        be = BounceEngine()
        path = str(output_dir / "test_bounce.wav")
        result = be.bounce([0.5] * 44100, path)
        assert os.path.exists(path)
        assert result.sample_count > 0


# ── Automation / control ────────────────────────────────────────────────


class TestAutomationRecorder:
    def test_create(self):
        from engine.automation_recorder import AutomationRecorder
        assert isinstance(AutomationRecorder(), AutomationRecorder)

    def test_record_point(self):
        from engine.automation_recorder import AutomationRecorder
        ar = AutomationRecorder()
        ar.create_lane("volume", target_module="mixer", target_param="vol")
        ar.add_point("volume", 0.0, 0.8)
        ar.add_point("volume", 1.0, 0.5)
        val = ar.get_value_at("volume", 0.5)
        assert isinstance(val, float)


class TestMacroController:
    def test_create(self):
        from engine.macro_controller import MacroController
        assert isinstance(MacroController(), MacroController)

    def test_set_and_get_value(self):
        from engine.macro_controller import MacroController
        mc = MacroController()
        mc.add_macro("volume", label="Volume")
        mc.set_value("volume", 0.5)
        assert abs(mc.get_value("volume") - 0.5) < 0.01


class TestRandomizer:
    def test_create(self):
        from engine.randomizer import RandomizerEngine
        assert isinstance(RandomizerEngine(seed=42), RandomizerEngine)

    def test_deterministic(self):
        from engine.randomizer import RandomizerEngine
        va = RandomizerEngine(seed=42).randomize("wobble_bass")
        vb = RandomizerEngine(seed=42).randomize("wobble_bass")
        assert va == vb


class TestCuePoints:
    def test_create(self):
        from engine.cue_points import CuePointManager
        assert isinstance(CuePointManager(), CuePointManager)

    def test_add_cue(self):
        from engine.cue_points import CuePointManager, CuePoint
        cm = CuePointManager()
        cm.create_map("test.wav", duration=120.0, bpm=140.0)
        cue = cm.add_cue("test.wav", position=30.0, label="drop")
        assert isinstance(cue, CuePoint)
        assert cue.position == 30.0


# ── Dataclass-only modules ──────────────────────────────────────────────


class TestAudioPreview:
    def test_dataclass(self):
        from engine.audio_preview import AudioPreview
        ap = AudioPreview(
            module_name="sub_bass", duration_s=1.0, sample_rate=44100,
            samples=44100, wav_base64="dGVzdA==", peak_db=-3.0,
            rms_db=-12.0, elapsed_ms=5.0,
        )
        assert ap.module_name == "sub_bass"
        assert ap.sample_rate == 44100

    def test_fields(self):
        from engine.audio_preview import AudioPreview
        ap = AudioPreview(
            module_name="lead_synth", duration_s=0.5, sample_rate=44100,
            samples=22050, wav_base64="YWJj", peak_db=-1.0,
            rms_db=-10.0, elapsed_ms=3.0,
        )
        assert ap.duration_s == 0.5
        assert ap.peak_db == -1.0


class TestSpectrogramResult:
    def test_dataclass(self):
        from engine.spectrogram_chat import SpectrogramResult
        r = SpectrogramResult(
            module_name="sub_bass", png_base64="abc",
            width=400, height=200, freq_range_hz=(20.0, 8000.0),
            time_range_s=(0.0, 1.0), peak_freq_hz=55.0, elapsed_ms=10.0,
        )
        assert r.module_name == "sub_bass"
        assert r.width == 400
        assert r.peak_freq_hz == 55.0


# ── Persistence / project management ───────────────────────────────────


class TestProjectManager:
    def test_create(self, tmp_path):
        from engine.project_manager import ProjectManager
        assert isinstance(ProjectManager(str(tmp_path)), ProjectManager)

    def test_create_project(self, tmp_path):
        from engine.project_manager import ProjectManager
        result = ProjectManager(str(tmp_path)).create_project("test_project")
        assert result is not None


class TestSnapshotManager:
    def test_create(self, tmp_path):
        from engine.snapshot_manager import SnapshotManager
        assert isinstance(
            SnapshotManager(data_dir=str(tmp_path / "snapshots")),
            SnapshotManager,
        )

    def test_capture_recall(self, tmp_path):
        from engine.snapshot_manager import SnapshotManager
        sm = SnapshotManager(data_dir=str(tmp_path / "snapshots"))
        snap = sm.capture("snap1", {"volume": 0.8, "freq": 440})
        recalled = sm.recall(snap.snapshot_id)
        assert recalled["volume"] == 0.8


class TestTagSystem:
    def test_create(self, tmp_path):
        from engine.tag_system import TagSystem
        assert isinstance(TagSystem(data_dir=str(tmp_path / "tags")), TagSystem)

    def test_add_item_with_tags(self, tmp_path):
        from engine.tag_system import TagSystem
        item = TagSystem(data_dir=str(tmp_path / "tags")).add_item(
            "sample1", "bass_hit", tags=["bass", "heavy"],
        )
        assert "bass" in item.tags
        assert "heavy" in item.tags


class TestSessionPersistence:
    def test_save_and_load(self, tmp_path):
        from engine.session_persistence import save_session, load_session
        from engine.subphonics import ChatSession, ChatMessage
        session = ChatSession()
        session.messages.append(ChatMessage(role="user", content="test"))
        save_session(session, output_dir=tmp_path)
        loaded = load_session(session.session_id, input_dir=tmp_path)
        assert loaded is not None
        assert len(loaded.messages) == 1

    def test_list_sessions_empty(self, tmp_path):
        from engine.session_persistence import list_sessions
        results = list_sessions(input_dir=tmp_path)
        assert isinstance(results, list)
        assert len(results) == 0
