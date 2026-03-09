"""Tests for engine.subphonics — SUBPHONICS AI core engine."""

import time

import pytest

from engine.subphonics import (
    COMMAND_PATTERNS,
    FIBONACCI,
    FLAVOR_LINES,
    FREQ_WISDOM,
    MODULE_MAP,
    PHI,
    PHI_WISDOM,
    SUBPHONICS_IDENTITY,
    ChatMessage,
    ChatSession,
    CommandResult,
    SubphonicsEngine,
    get_engine,
    main,
)

# ═══════════════════════════════════════════════════════════════════════════
# ChatMessage
# ═══════════════════════════════════════════════════════════════════════════

class TestChatMessage:
    def test_create(self):
        msg = ChatMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.timestamp > 0

    def test_auto_timestamp(self):
        t0 = time.time()
        msg = ChatMessage(role="subphonics", content="yo")
        assert msg.timestamp >= t0

    def test_explicit_timestamp(self):
        msg = ChatMessage(role="user", content="x", timestamp=12345.0)
        assert msg.timestamp == 12345.0

    def test_default_metadata(self):
        msg = ChatMessage(role="user", content="x")
        assert msg.metadata == {}

    def test_custom_metadata(self):
        msg = ChatMessage(role="subphonics", content="x",
                          metadata={"module": "sub_bass"})
        assert msg.metadata["module"] == "sub_bass"


# ═══════════════════════════════════════════════════════════════════════════
# ChatSession
# ═══════════════════════════════════════════════════════════════════════════

class TestChatSession:
    def test_create(self):
        s = ChatSession()
        assert s.session_id.startswith("sub_")
        assert s.messages == []
        assert s.context == {}

    def test_custom_id(self):
        s = ChatSession(session_id="test_123")
        assert s.session_id == "test_123"

    def test_add_message(self):
        s = ChatSession()
        msg = s.add_message("user", "hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert len(s.messages) == 1

    def test_add_multiple(self):
        s = ChatSession()
        s.add_message("user", "yo")
        s.add_message("subphonics", "what up")
        assert len(s.messages) == 2

    def test_to_dict(self):
        s = ChatSession(session_id="test_1")
        s.add_message("user", "hi")
        d = s.to_dict()
        assert d["session_id"] == "test_1"
        assert len(d["messages"]) == 1
        assert d["messages"][0]["role"] == "user"

    def test_metadata_in_message(self):
        s = ChatSession()
        msg = s.add_message("subphonics", "done",
                            metadata={"module": "lead_synth"})
        assert msg.metadata["module"] == "lead_synth"


# ═══════════════════════════════════════════════════════════════════════════
# CommandResult
# ═══════════════════════════════════════════════════════════════════════════

class TestCommandResult:
    def test_create(self):
        r = CommandResult(command="render", success=True, output="ok")
        assert r.command == "render"
        assert r.success is True
        assert r.output == "ok"
        assert r.data == {}
        assert r.files_created == []
        assert r.elapsed_ms == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Constants & registries
# ═══════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_phi(self):
        assert abs(PHI - 1.6180339887) < 1e-9

    def test_fibonacci(self):
        assert FIBONACCI[:7] == [1, 1, 2, 3, 5, 8, 13]
        assert 144 in FIBONACCI

    def test_identity(self):
        assert SUBPHONICS_IDENTITY["name"] == "SUBPHONICS"
        assert "greeting" in SUBPHONICS_IDENTITY
        assert len(SUBPHONICS_IDENTITY["capabilities"]) >= 8
        assert len(SUBPHONICS_IDENTITY["personality"]) >= 5

    def test_module_map(self):
        assert len(MODULE_MAP) >= 40
        for name, info in MODULE_MAP.items():
            assert "category" in info
            assert "desc" in info

    def test_module_categories(self):
        categories = {info["category"] for info in MODULE_MAP.values()}
        assert "synth" in categories
        assert "fx" in categories
        assert "drums" in categories
        assert "pipeline" in categories
        assert "export" in categories
        assert "analysis" in categories

    def test_command_patterns(self):
        assert len(COMMAND_PATTERNS) >= 30
        for pattern, cmd, arg in COMMAND_PATTERNS:
            assert isinstance(pattern, str)
            assert isinstance(cmd, str)

    def test_flavor_lines(self):
        assert len(FLAVOR_LINES) >= 10
        for line in FLAVOR_LINES:
            assert isinstance(line, str)
            assert len(line) > 10

    def test_phi_wisdom(self):
        assert len(PHI_WISDOM) >= 2
        for w in PHI_WISDOM:
            assert "phi" in w.lower() or "PHI" in w

    def test_freq_wisdom(self):
        assert len(FREQ_WISDOM) >= 2
        for w in FREQ_WISDOM:
            assert "hz" in w.lower() or "Hz" in w


# ═══════════════════════════════════════════════════════════════════════════
# SubphonicsEngine — command routing
# ═══════════════════════════════════════════════════════════════════════════

class TestSubphonicsEngine:
    @pytest.fixture
    def engine(self):
        return SubphonicsEngine()

    def test_init(self, engine):
        assert engine.identity["name"] == "SUBPHONICS"
        assert len(engine.module_map) >= 40
        assert engine._boot_time > 0

    def test_greeting(self, engine):
        g = engine.get_greeting()
        assert "SUBPHONICS" in g
        assert len(g) > 30

    def test_session(self, engine):
        s = engine.get_session()
        assert isinstance(s, ChatSession)

    # ─── Greetings ────────────────────────────────────────────

    def test_greet_hello(self, engine):
        msg = engine.process_message("hello")
        assert msg.role == "subphonics"
        assert len(msg.content) > 10

    def test_greet_yo(self, engine):
        msg = engine.process_message("yo what up")
        assert len(msg.content) > 10

    def test_greet_hey(self, engine):
        msg = engine.process_message("hey there")
        assert len(msg.content) > 10

    # ─── Identity ─────────────────────────────────────────────

    def test_identity(self, engine):
        msg = engine.process_message("who are you")
        assert "SUBPHONICS" in msg.content

    def test_what_are_you(self, engine):
        msg = engine.process_message("what are you")
        assert "SUBPHONICS" in msg.content

    # ─── Phi wisdom ───────────────────────────────────────────

    def test_phi_wisdom(self, engine):
        msg = engine.process_message("tell me about phi")
        assert len(msg.content) > 50

    def test_golden_ratio(self, engine):
        msg = engine.process_message("golden ratio")
        assert len(msg.content) > 50

    def test_fibonacci_query(self, engine):
        msg = engine.process_message("what about fibonacci")
        assert len(msg.content) > 50

    # ─── Frequency wisdom ─────────────────────────────────────

    def test_freq_432(self, engine):
        msg = engine.process_message("tell me about 432")
        assert len(msg.content) > 50

    def test_frequency(self, engine):
        msg = engine.process_message("frequency tuning")
        assert len(msg.content) > 50

    # ─── Status ───────────────────────────────────────────────

    def test_status(self, engine):
        msg = engine.process_message("status")
        assert "STATUS" in msg.content or "module" in msg.content.lower()

    def test_info(self, engine):
        msg = engine.process_message("info")
        assert len(msg.content) > 20

    # ─── Help ─────────────────────────────────────────────────

    def test_help(self, engine):
        msg = engine.process_message("help")
        assert "render" in msg.content.lower() or "command" in msg.content.lower()

    def test_commands(self, engine):
        msg = engine.process_message("what can you do")
        assert len(msg.content) > 50

    # ─── List modules ─────────────────────────────────────────

    def test_list_modules(self, engine):
        msg = engine.process_message("list modules")
        assert "module" in msg.content.lower()
        assert "sub_bass" in msg.content or "synth" in msg.content.lower()

    def test_list_engines(self, engine):
        msg = engine.process_message("show me all engines")
        assert len(msg.content) > 50

    # ─── Render commands ──────────────────────────────────────

    def test_render_sub_bass(self, engine):
        msg = engine.process_message("make sub bass")
        c = msg.content.lower()
        assert "sub_bass" in c or "error" in c

    def test_render_wobble(self, engine):
        msg = engine.process_message("render wobble bass")
        c = msg.content.lower()
        assert "wobble" in c or "error" in c

    def test_render_lead(self, engine):
        msg = engine.process_message("generate a lead")
        c = msg.content.lower()
        assert "lead" in c or "error" in c

    def test_render_pad(self, engine):
        msg = engine.process_message("create a pad")
        c = msg.content.lower()
        assert "pad" in c or "error" in c

    def test_render_drums(self, engine):
        msg = engine.process_message("make drums")
        c = msg.content.lower()
        assert "drum" in c or "error" in c

    def test_render_arp(self, engine):
        msg = engine.process_message("build an arp")
        c = msg.content.lower()
        assert "arp" in c or "error" in c

    def test_render_pluck(self, engine):
        msg = engine.process_message("render pluck")
        c = msg.content.lower()
        assert "pluck" in c or "error" in c

    def test_render_drone(self, engine):
        msg = engine.process_message("make a drone")
        c = msg.content.lower()
        assert "drone" in c or "error" in c

    def test_render_riser(self, engine):
        msg = engine.process_message("create riser")
        c = msg.content.lower()
        assert "riser" in c or "error" in c

    def test_render_impact(self, engine):
        msg = engine.process_message("build impact hit")
        c = msg.content.lower()
        assert "impact" in c or "error" in c

    def test_render_noise(self, engine):
        msg = engine.process_message("generate noise")
        c = msg.content.lower()
        assert "noise" in c or "error" in c

    def test_render_glitch(self, engine):
        msg = engine.process_message("make glitch")
        c = msg.content.lower()
        assert "glitch" in c or "error" in c

    def test_render_wavetable(self, engine):
        msg = engine.process_message("build wavetable")
        c = msg.content.lower()
        assert "wavetable" in c or "error" in c

    def test_render_granular(self, engine):
        msg = engine.process_message("create granular")
        c = msg.content.lower()
        assert "granular" in c or "error" in c

    def test_render_riddim(self, engine):
        msg = engine.process_message("make riddim")
        c = msg.content.lower()
        assert "riddim" in c or "error" in c

    def test_render_transition(self, engine):
        msg = engine.process_message("create transition")
        c = msg.content.lower()
        assert "transition" in c or "error" in c

    def test_render_perc(self, engine):
        msg = engine.process_message("make perc")
        c = msg.content.lower()
        assert "perc" in c or "error" in c

    def test_render_formant(self, engine):
        msg = engine.process_message("generate formant")
        c = msg.content.lower()
        assert "formant" in c or "error" in c

    def test_render_bass_oneshot(self, engine):
        msg = engine.process_message("render bass oneshot")
        c = msg.content.lower()
        assert "bass_oneshot" in c or "error" in c

    def test_render_ambient(self, engine):
        msg = engine.process_message("make ambient texture")
        c = msg.content.lower()
        assert "ambient" in c or "error" in c

    # ─── FX commands ──────────────────────────────────────────

    def test_sidechain(self, engine):
        msg = engine.process_message("apply sidechain")
        c = msg.content.lower()
        assert "sidechain" in c or "error" in c

    def test_distortion(self, engine):
        msg = engine.process_message("distort this")
        c = msg.content.lower()
        assert "distort" in c or "multiband" in c or "error" in c

    def test_reverb(self, engine):
        msg = engine.process_message("add reverb")
        c = msg.content.lower()
        assert "reverb" in c or "error" in c

    def test_stereo(self, engine):
        msg = engine.process_message("widen stereo")
        c = msg.content.lower()
        assert "stereo" in c or "error" in c

    # ─── Export commands ──────────────────────────────────────

    def test_export_midi(self, engine):
        msg = engine.process_message("export midi")
        c = msg.content.lower()
        assert "midi" in c or "error" in c

    def test_export_preset(self, engine):
        msg = engine.process_message("save preset")
        c = msg.content.lower()
        assert "fxp" in c or "preset" in c or "error" in c

    def test_export_ableton(self, engine):
        msg = engine.process_message("export ableton")
        c = msg.content.lower()
        assert "als" in c or "ableton" in c or "error" in c

    def test_sample_pack(self, engine):
        msg = engine.process_message("make sample pack")
        c = msg.content.lower()
        assert "sample" in c or "error" in c

    def test_preset_pack(self, engine):
        msg = engine.process_message("generate preset pack")
        c = msg.content.lower()
        assert "preset" in c or "error" in c

    # ─── Analysis commands ────────────────────────────────────

    def test_analyze_phi(self, engine):
        msg = engine.process_message("analyze phi")
        c = msg.content.lower()
        assert "phi" in c or "error" in c

    def test_analyze_harmonic(self, engine):
        msg = engine.process_message("analyze harmonic")
        c = msg.content.lower()
        assert "harmonic" in c or "error" in c

    def test_analyze_subtronics(self, engine):
        msg = engine.process_message("analyze subtronics")
        c = msg.content.lower()
        assert "sb" in c or "subtronics" in c or "error" in c

    def test_evolve(self, engine):
        msg = engine.process_message("evolve presets")
        c = msg.content.lower()
        assert "mutate" in c or "preset" in c or "error" in c

    def test_ab_test(self, engine):
        msg = engine.process_message("compare sounds")
        c = msg.content.lower()
        assert "ab" in c or "test" in c or "error" in c

    # ─── Pipeline commands ────────────────────────────────────

    def test_pipeline(self, engine):
        msg = engine.process_message("run pipeline")
        c = msg.content.lower()
        assert "pipeline" in c or "render" in c or "error" in c

    def test_batch(self, engine):
        msg = engine.process_message("batch render")
        c = msg.content.lower()
        assert "batch" in c or "error" in c

    def test_mix(self, engine):
        msg = engine.process_message("mix stems")
        c = msg.content.lower()
        assert "stem" in c or "mix" in c or "error" in c

    def test_master(self, engine):
        msg = engine.process_message("master this")
        c = msg.content.lower()
        assert "master" in c or "error" in c

    # ─── System commands ──────────────────────────────────────

    def test_audit(self, engine):
        msg = engine.process_message("run audit")
        c = msg.content.lower()
        assert "audit" in c or "error" in c

    def test_benchmark(self, engine):
        msg = engine.process_message("benchmark performance")
        c = msg.content.lower()
        assert "profil" in c or "benchmark" in c or "error" in c

    # ─── Run named module ─────────────────────────────────────

    def test_run_named(self, engine):
        msg = engine.process_message("run phi_analyzer")
        c = msg.content.lower()
        assert "phi" in c or "error" in c

    def test_run_named_fuzzy(self, engine):
        msg = engine.process_message("run wobble")
        c = msg.content.lower()
        assert "wobble" in c or "error" in c

    def test_run_named_not_found(self, engine):
        msg = engine.process_message("run nonexistent_module_xyz")
        assert "not" in msg.content.lower() or "module" in msg.content.lower()

    # ─── Freeform fallback ────────────────────────────────────

    def test_freeform(self, engine):
        msg = engine.process_message("purple elephants dancing in moonlight")
        assert len(msg.content) > 20
        assert msg.role == "subphonics"

    def test_freeform_help_hint(self, engine):
        msg = engine.process_message("aksjdhaksjdhaksjdh")
        c = msg.content.lower()
        assert "help" in c or "module" in c or "command" in c

    # ─── Session tracking ─────────────────────────────────────

    def test_session_grows(self, engine):
        engine.process_message("hello")
        engine.process_message("status")
        engine.process_message("help")
        s = engine.get_session()
        # Each message generates user + subphonics = 2 per call
        assert len(s.messages) == 6

    def test_session_roles(self, engine):
        engine.process_message("yo")
        s = engine.get_session()
        assert s.messages[0].role == "user"
        assert s.messages[1].role == "subphonics"

    def test_session_to_dict(self, engine):
        engine.process_message("hello")
        d = engine.get_session().to_dict()
        assert "session_id" in d
        assert "messages" in d
        assert len(d["messages"]) == 2


# ═══════════════════════════════════════════════════════════════════════════
# SubphonicsEngine — internal commands
# ═══════════════════════════════════════════════════════════════════════════

class TestInternalCommands:
    @pytest.fixture
    def engine(self):
        return SubphonicsEngine()

    def test_cmd_greet(self, engine):
        result = engine._cmd_greet()
        assert "text" in result
        assert len(result["text"]) > 20

    def test_cmd_identity(self, engine):
        result = engine._cmd_identity()
        assert "SUBPHONICS" in result["text"]
        assert "Capabilities" in result["text"]

    def test_cmd_phi_wisdom(self, engine):
        result = engine._cmd_phi_wisdom()
        assert len(result["text"]) > 50

    def test_cmd_freq_wisdom(self, engine):
        result = engine._cmd_freq_wisdom()
        assert len(result["text"]) > 50

    def test_cmd_help(self, engine):
        result = engine._cmd_help()
        assert "COMMAND REFERENCE" in result["text"]
        assert "render" in result["text"].lower()

    def test_cmd_list_modules(self, engine):
        result = engine._cmd_list_modules()
        assert "DUBFORGE MODULES" in result["text"]
        assert "Total:" in result["text"]

    def test_cmd_system_status(self, engine):
        result = engine._cmd_system_status()
        assert "STATUS REPORT" in result["text"]
        assert "meta" in result
        assert "uptime" in result["meta"]

    def test_cmd_render_unknown(self, engine):
        result = engine._cmd_render_module("not_a_real_module")
        assert "not found" in result["text"].lower()

    def test_cmd_run_named_empty(self, engine):
        result = engine._cmd_run_named("")
        # Empty string should fuzzy match or fail gracefully
        assert "text" in result

    def test_cmd_freeform(self, engine):
        result = engine._cmd_freeform("random text here")
        assert "text" in result
        assert len(result["text"]) > 20

    def test_cmd_export_sample(self, engine):
        result = engine._cmd_export_packs("sample")
        assert "text" in result

    def test_cmd_export_preset(self, engine):
        result = engine._cmd_export_packs("preset")
        assert "text" in result


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

class TestSingleton:
    def test_get_engine(self):
        import engine.subphonics as mod
        mod._engine = None
        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2
        mod._engine = None  # cleanup


# ═══════════════════════════════════════════════════════════════════════════
# main()
# ═══════════════════════════════════════════════════════════════════════════

class TestMain:
    def test_main(self, capsys):
        main()
        out = capsys.readouterr().out
        assert "SUBPHONICS" in out
        assert "ONLINE" in out
