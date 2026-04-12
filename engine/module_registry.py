"""MWP Module Registry — Single source of truth for all DubForge engine modules.

Maps every engine module to its MWP (Minimum Workable Pipeline) phase,
current wiring status, and capability description.

Phases follow the ill.GATES Producer Dojo 10-phase methodology:
  ORACLE → COLLECT → RECIPES → SKETCH → ARRANGE → DESIGN →
  MIX → MASTER → RELEASE → REFLECT

Status:
  "wired"     — Actively called in forge.py or stage_integrations.py
  "available" — Module exists with public API but not yet wired into pipeline
  "infra"     — Infrastructure/acceleration layer used by other modules
"""

# ═══════════════════════════════════════════════════════════════
#  PHASE → MODULE MAP
# ═══════════════════════════════════════════════════════════════

REGISTRY = {
    # ─── PHASE 1: ORACLE ──────────────────────────────────────
    # Reference analysis, DNA introspection, goal setting.
    # Brain: ARCHITECT — understand what you're building before touching anything.
    "oracle": {
        "audio_analyzer":       {"status": "wired",     "provides": "Spectral analysis, peak detection, loudness measurement"},
        "dubstep_taste_analyzer": {"status": "wired",   "provides": "Reference track DNA extraction, style fingerprinting"},
        "reference_analyzer":   {"status": "wired",     "provides": "A/B comparison against reference tracks"},
        "reference_library":    {"status": "wired",     "provides": "Curated reference track database with golden ratios"},
        "sb_analyzer":          {"status": "wired",     "provides": "Subtronics/bass music style analysis"},
        "frequency_analyzer":   {"status": "wired",     "provides": "FFT-based frequency content analysis"},
        "harmonic_analysis":    {"status": "wired",     "provides": "Harmonic series detection, overtone mapping"},
        "key_detector":         {"status": "wired",     "provides": "Musical key detection from audio"},
        "tempo_detector":       {"status": "wired",     "provides": "BPM detection from audio reference"},
        "phi_analyzer":         {"status": "wired",     "provides": "Golden ratio analysis of structure and spectrum"},
        "emulator":             {"status": "available",  "provides": "Emulate characteristics of reference tracks"},
        "style_transfer":       {"status": "available",  "provides": "Transfer sonic style from reference to new material"},
    },

    # ─── PHASE 2: COLLECT ─────────────────────────────────────
    # Gather sounds, samples, presets, session state.
    # Brain: CHILD — explore freely, no judgment.
    "collect": {
        "sample_library":       {"status": "wired",     "provides": "Sample library indexing and search"},
        "galatcia":             {"status": "wired",     "provides": "GALATCIA sample catalog with metadata"},
        "sound_palette":        {"status": "wired",     "provides": "Curated sound palette from DNA + samples"},
        "wav_pool":             {"status": "wired",     "provides": "WAV file pool with lazy loading"},
        "preset_browser":       {"status": "wired",     "provides": "Browse and filter preset library"},
        "sample_slicer":        {"status": "wired",     "provides": "Slice loops into one-shots"},
        "config_loader":        {"status": "wired",     "provides": "YAML config loading, WORKERS_COMPUTE"},
        "song_templates":       {"status": "wired",     "provides": "Pre-built song structure templates"},
        "mood_engine":          {"status": "wired",     "provides": "Mood-to-parameter mapping"},
        "rco":                  {"status": "wired",     "provides": "RCO energy mapping for sections"},
        "psbs":                 {"status": "wired",     "provides": "PSBS system integration"},
        "lessons_learned":      {"status": "wired",     "provides": "Cross-session learning adjustments"},
        "evolution_engine":     {"status": "wired",     "provides": "Evolutionary preset generation"},
        "memory":               {"status": "wired",     "provides": "Session memory persistence"},
        "session_logger":       {"status": "wired",     "provides": "Milestone logging during render"},
        "markov_melody":        {"status": "wired",     "provides": "Markov chain melody generation"},
        "trance_arp":           {"status": "wired",     "provides": "Trance-style arpeggiator layers"},
        "tuning_system":        {"status": "wired",     "provides": "432Hz tuning validation"},
        "backup_system":        {"status": "available",  "provides": "Project state backup and restore"},
        "session_persistence":  {"status": "available",  "provides": "Save/resume render sessions"},
        "project_manager":      {"status": "available",  "provides": "Multi-project organisation and state"},
        "preset_vcs":           {"status": "available",  "provides": "Version control for presets"},
    },

    # ─── PHASE 3: RECIPES ─────────────────────────────────────
    # Templates, blueprints, variation planning, arrangement skeletons.
    # Brain: ARCHITECT — plan the structure before building.
    "recipes": {
        "recipe_book":          {"status": "wired",     "provides": "Recipe selection + quality gate checks"},
        "template_generator":   {"status": "wired",     "provides": "Arrangement template generation from DNA"},
        "macro_controller":     {"status": "wired",     "provides": "Macro parameter presets for quick tweaks"},
        "preset_mutator":       {"status": "wired",     "provides": "Genetic mutation of synth presets"},
        "serum_blueprint":      {"status": "wired",     "provides": "Serum 2 wavetable blueprint generation"},
        "variation_engine":     {"status": "wired",     "provides": "Controlled variation of parameters"},
        "genetic_evolver":      {"status": "wired",     "provides": "Genetic algorithm preset evolution"},
        "fibonacci_feedback":   {"status": "wired",     "provides": "Phi-ratio feedback loop engine"},
        "vip_pack":             {"status": "wired",     "provides": "VIP bass mutation presets"},
        "chord_progression":    {"status": "wired",     "provides": "Chord progression generation from key/scale"},
        "randomizer":           {"status": "available",  "provides": "Constrained random parameter generation"},
    },

    # ─── PHASE 4: SKETCH ─────────────────────────────────────
    # Raw sound design — synths, drums, bass, leads, pads, FX.
    # Brain: CHILD — first instincts, no judgment, just CREATE.
    "sketch": {
        # Drums
        "perc_synth":           {"status": "wired",     "provides": "Kick, snare, hat, clap synthesis"},
        "drum_generator":       {"status": "wired",     "provides": "Full drum kit generation"},
        "drum_pipeline":        {"status": "wired",     "provides": "Drum processing pipeline checks"},
        # Bass
        "bass_oneshot":         {"status": "wired",     "provides": "Bass one-shot synthesis (sub, wobble, growl, neuro)"},
        "fm_synth":             {"status": "wired",     "provides": "FM synthesis with operator stacks"},
        "formant_synth":        {"status": "wired",     "provides": "Formant-based vocal bass synthesis"},
        "growl_resampler":      {"status": "wired",     "provides": "Growl resampling pipeline (saw/FM → wavetable)"},
        "sub_bass":             {"status": "wired",     "provides": "Sub bass with harmonic enhancement"},
        "wobble_bass":          {"status": "wired",     "provides": "LFO-driven wobble bass"},
        "riddim_engine":        {"status": "wired",     "provides": "Riddim bass variants"},
        "midbass_pipeline":     {"status": "wired",     "provides": "Mid-bass processing chain checks"},
        "wave_folder":          {"status": "wired",     "provides": "Wave folding distortion for bass"},
        "ring_mod":             {"status": "wired",     "provides": "Ring modulation for metallic textures"},
        # Leads + Melodic
        "lead_synth":           {"status": "wired",     "provides": "Screech lead synthesis"},
        "additive_synth":       {"status": "wired",     "provides": "Additive synthesis with partial control"},
        "lead_pipeline":        {"status": "wired",     "provides": "Lead processing chain"},
        "arp_synth":            {"status": "wired",     "provides": "Arpeggiator synthesis"},
        "chord_pad":            {"status": "wired",     "provides": "Chord pad voicing"},
        "pluck_synth":          {"status": "wired",     "provides": "Karplus-Strong pluck synthesis"},
        # Pads + Atmosphere
        "pad_synth":            {"status": "wired",     "provides": "Dark pad, lush pad synthesis"},
        "drone_synth":          {"status": "wired",     "provides": "Multi-voice drone generation"},
        "granular_synth":       {"status": "wired",     "provides": "Granular cloud synthesis"},
        "ambient_texture":      {"status": "wired",     "provides": "Ambient texture layers"},
        "supersaw":             {"status": "wired",     "provides": "Supersaw unison with stereo spread"},
        "karplus_strong":       {"status": "wired",     "provides": "Physical modelling string synthesis"},
        # Noise + FX
        "noise_generator":      {"status": "wired",     "provides": "White/pink/brown noise generation"},
        "vocal_chop":           {"status": "wired",     "provides": "Vocal chop synthesis with formants"},
        "vocal_processor":      {"status": "wired",     "provides": "Vocal processing chain"},
        "glitch_engine":        {"status": "wired",     "provides": "Glitch/stutter effects"},
        "beat_repeat":          {"status": "wired",     "provides": "Beat repeat/stutter patterns"},
        "impact_hit":           {"status": "wired",     "provides": "Sub boom + cinematic hit synthesis"},
        "riser_synth":          {"status": "wired",     "provides": "Noise-sweep riser generation"},
        "transition_fx":        {"status": "wired",     "provides": "Tape stop, pitch dive, reverse crash, gate chop"},
        "harmonic_gen":         {"status": "wired",     "provides": "Harmonic enrichment layers"},
        # Available — not yet wired
        "phase_distortion":     {"status": "available",  "provides": "Phase distortion synthesis (Casio CZ-style)"},
        "vector_synth":         {"status": "available",  "provides": "Vector synthesis with morph paths"},
        "vocoder":              {"status": "available",  "provides": "Channel vocoder for robotic textures"},
        "vocal_tts":            {"status": "available",  "provides": "Text-to-speech vocal generation"},
        "spectral_morph":       {"status": "available",  "provides": "Spectral bin morphing between sources"},
        "spectral_resynthesis": {"status": "available",  "provides": "FFT analysis → resynthesis with modification"},
        "wavetable_morph":      {"status": "available",  "provides": "Smooth morphing between wavetable frames"},
        "envelope_generator":   {"status": "available",  "provides": "Complex ADSR/MSEG envelope generation"},
        # Session 13 gap modules
        "resample_feedback":    {"status": "wired",     "provides": "Live resampling feedback loop (bass_mangle, whirlpool, stutter_stack, spectral_freeze)"},
        "wavetable_export":     {"status": "wired",     "provides": "Custom wavetable export to Serum 2 (clm format, harmonic/FM/fractal/formant/resample)"},
        "granular_depth":       {"status": "wired",     "provides": "Deep granular processing (time_stretch, pitch_grain, cloud, freeze, morph)"},
        "guitar_synth":         {"status": "wired",     "provides": "Guitar-synth hybrid layer (Karplus-Strong + supersaw/FM/pad)"},
        "vocal_mangle":         {"status": "wired",     "provides": "Creative vocal mangling (glitch_slice, granular, formant_morph, reverse_build, stutter_gate)"},
        "serum_lfo_shapes":     {"status": "wired",     "provides": "Serum 2 LFO shape generation (phi_step, fibonacci, fractal, euclidean, harmonic)"},
    },

    # ─── PHASE 5: ARRANGE ─────────────────────────────────────
    # Place sounds in time — sections, transitions, energy flow.
    # Brain: ARCHITECT — structure and subtract (Fat Loop method).
    "arrange": {
        "arrangement_sequencer": {"status": "wired",    "provides": "Section sequencing and bar placement"},
        "auto_arranger":        {"status": "wired",     "provides": "Auto-arrangement from templates"},
        "clip_manager":         {"status": "wired",     "provides": "Audio clip management and scheduling"},
        "crossfade":            {"status": "wired",     "provides": "Section crossfade generation"},
        "audio_stitcher":       {"status": "wired",     "provides": "Stitch audio segments seamlessly"},
        "audio_splitter":       {"status": "wired",     "provides": "Split audio at markers"},
        "cue_points":           {"status": "wired",     "provides": "Cue point placement for DJ software"},
        "groove":               {"status": "wired",     "provides": "Groove templates and swing"},
        "rhythm_engine":        {"status": "wired",     "provides": "Pattern-driven drum/perc placement"},
        "clip_launcher":        {"status": "available",  "provides": "Scene/clip triggering for live arrangement"},
        "automation_recorder":  {"status": "available",  "provides": "Record parameter automation curves"},
        "tempo_sync":           {"status": "available",  "provides": "Tempo-synced modulation and delay"},
    },

    # ─── PHASE 6: DESIGN ──────────────────────────────────────
    # Post-arrangement sound sculpting, FX chains, spatial design.
    # Brain: CHILD — creative effect application, automation.
    "design": {
        "reverb_delay":         {"status": "wired",     "provides": "Algorithmic reverb + delay sends"},
        "dynamics":             {"status": "wired",     "provides": "Compression, expansion, gating"},
        "saturation":           {"status": "wired",     "provides": "Tube/tape/foldback saturation engine"},
        "intelligent_eq":       {"status": "wired",     "provides": "Adaptive EQ with resonance detection"},
        "stereo_imager":        {"status": "wired",     "provides": "Mid/side processing, stereo width"},
        "multiband_distortion": {"status": "wired",     "provides": "3-band distortion (tube/tape/aggressive)"},
        "lfo_matrix":           {"status": "wired",     "provides": "Multi-target LFO modulation"},
        "panning":              {"status": "wired",     "provides": "Pan law + auto-pan engine"},
        "pitch_automation":     {"status": "wired",     "provides": "Pitch bend, dive, rise automation"},
        "spectral_gate":        {"status": "wired",     "provides": "Frequency-selective noise gate"},
        "convolution":          {"status": "wired",     "provides": "Convolution reverb with IR loading"},
        "dynamics_processor":   {"status": "wired",     "provides": "Advanced dynamics (parallel, upward comp)"},
        "resonance":            {"status": "wired",     "provides": "Resonant filter sweeps"},
        "sidechain":            {"status": "wired",     "provides": "Sidechain compression from kick trigger"},
        "signal_chain":         {"status": "wired",     "provides": "Signal chain routing and ordering"},
        "fx_pipeline":          {"status": "wired",     "provides": "Effect pipeline builder"},
        "fx_generator":         {"status": "wired",     "provides": "Auto-generate effect chains from DNA"},
        "fx_rack":              {"status": "available",  "provides": "Rack-style parallel effect routing"},
        "live_fx":              {"status": "available",  "provides": "Real-time effect processing"},
        "atmos_pipeline":       {"status": "available",  "provides": "Atmospheric processing pipeline"},
        "sub_pipeline":         {"status": "available",  "provides": "Sub-bass processing pipeline"},
        # Session 13 gap modules
        "ab_workflow":          {"status": "wired",     "provides": "A/B sound design comparison workflow (bracket, round_robin, elimination, golden_split, blind_vote)"},
    },

    # ─── PHASE 7: MIX ────────────────────────────────────────
    # Bus routing, stem mixing, frequency collision management.
    # Brain: CRITIC — technical precision, no creativity.
    "mix": {
        "mix_assistant":        {"status": "wired",     "provides": "Mix guidance and frequency collision detection"},
        "mix_bus":              {"status": "wired",     "provides": "Mix bus summing and routing"},
        "bus_router":           {"status": "wired",     "provides": "Bus routing topology"},
        "auto_mixer":           {"status": "wired",     "provides": "Auto-gain staging and balance"},
        "stem_mixer":           {"status": "wired",     "provides": "Multi-stem mixing with level control"},
        "dc_remover":           {"status": "wired",     "provides": "DC offset removal filter"},
        "normalizer":           {"status": "wired",     "provides": "Peak and loudness normalisation"},
        "realtime_monitor":     {"status": "wired",     "provides": "Real-time level and spectrum monitoring"},
        "production_pipeline":  {"status": "wired",     "provides": "Production pipeline checks"},
        "stem_separator":       {"status": "available",  "provides": "AI-based stem separation (vocals/drums/bass/other)"},
        "multitrack_renderer":  {"status": "available",  "provides": "Render individual stems to separate files"},
        "audio_buffer":         {"status": "available",  "provides": "Ring buffer for streaming audio"},
        "audio_math":           {"status": "available",  "provides": "Audio math utilities (dBFS, RMS, crest factor)"},
        "render_pipeline":      {"status": "available",  "provides": "Configurable render pipeline with stages"},
    },

    # ─── PHASE 8: MASTER ──────────────────────────────────────
    # Mastering chain, final processing, quality assurance.
    # Brain: CRITIC — precision metering, target LUFS.
    "master": {
        "mastering_chain":      {"status": "wired",     "provides": "Full mastering chain (EQ, comp, limiter, stereo)"},
        "auto_master":          {"status": "wired",     "provides": "Auto-mastering with DNA-driven targets"},
        "qa_validator":         {"status": "wired",     "provides": "Quality assurance validation (LUFS, peak, key)"},
        "phi_core":             {"status": "wired",     "provides": "Golden ratio normalisation and coherence"},
        "dither":               {"status": "wired",     "provides": "Dithering for bit-depth reduction"},
        "watermark":            {"status": "wired",     "provides": "Audio watermarking (inaudible fingerprint)"},
        "turboquant":           {"status": "wired",     "provides": "TurboQuant wavetable micro-tuner"},
        "pattern_recognizer":   {"status": "wired",     "provides": "Pattern detection for structural analysis"},
    },

    # ─── PHASE 9: RELEASE ─────────────────────────────────────
    # Export, metadata, distribution, artwork.
    # Brain: ARCHITECT — package everything for delivery.
    "release": {
        "als_generator":        {"status": "wired",     "provides": "Ableton Live .als project file generation"},
        "fxp_writer":           {"status": "wired",     "provides": ".fxp VST2 preset file writer"},
        "midi_export":          {"status": "wired",     "provides": "MIDI file export from note data"},
        "metadata":             {"status": "wired",     "provides": "Audio file metadata embedding"},
        "marketplace_metadata": {"status": "wired",     "provides": "Marketplace-ready metadata format"},
        "artwork_generator":    {"status": "wired",     "provides": "Album artwork generation"},
        "bounce":               {"status": "wired",     "provides": "Stem bounce to individual WAVs"},
        "tag_system":           {"status": "wired",     "provides": "Audio file tagging (genre, mood, key)"},
        "ep_builder":           {"status": "wired",     "provides": "EP/album builder with track ordering"},
        "wavetable_pack":       {"status": "wired",     "provides": "Wavetable pack packaging"},
        "serum2":               {"status": "wired",     "provides": "Serum 2 wavetable format writer"},
        "serum2_preset":        {"status": "wired",     "provides": "Serum 2 preset (.fxp) generation"},
        "genre_detector":       {"status": "wired",     "provides": "Genre classification from audio features"},
        "soundcloud_pipeline":  {"status": "wired",     "provides": "SoundCloud upload preparation"},
        "ableton_rack_builder": {"status": "wired",     "provides": "Ableton Rack (.adg) generation"},
        "ableton_live":         {"status": "wired",     "provides": "Ableton Live integration (track/scene creation)"},
        "sample_pack_builder":  {"status": "available",  "provides": "Build distributable sample packs"},
        "preset_pack_builder":  {"status": "available",  "provides": "Build distributable preset packs"},
        "sample_pack_exporter": {"status": "available",  "provides": "Export sample packs in standard formats"},
        "batch_renderer":       {"status": "available",  "provides": "Batch render multiple tracks/variants"},
        "batch_processor":      {"status": "available",  "provides": "Batch process audio files with effects"},
        "format_converter":     {"status": "available",  "provides": "Convert between audio formats (WAV/FLAC/MP3)"},
        "midi_processor":       {"status": "available",  "provides": "MIDI file processing and manipulation"},
        # Session 13 gap modules
        "vip_generator":        {"status": "wired",     "provides": "VIP generation mode (Fractals → Antifractals workflow with A/B selection)"},
    },

    # ─── PHASE 10: REFLECT ────────────────────────────────────
    # Session review, learning, belt progression, reporting.
    # Brain: ARCHITECT — honest assessment, no ego.
    "reflect": {
        "dojo":                 {"status": "wired",     "provides": "Dojo session governor (phases, brains, belts, gates)"},
        "openclaw_agent":       {"status": "wired",     "provides": "OpenClaw AI agent for production guidance"},
        "ascension":            {"status": "wired",     "provides": "Ascension system for progression tracking"},
        "grandmaster":          {"status": "wired",     "provides": "Grandmaster report generation"},
        "autonomous":           {"status": "wired",     "provides": "Autonomous director for self-directed sessions"},
        "final_audit":          {"status": "available",  "provides": "Comprehensive final audit of render quality"},
        "full_integration":     {"status": "available",  "provides": "Full integration test suite runner"},
    },

    # ─── INFRASTRUCTURE (cross-phase) ─────────────────────────
    # Acceleration, DSP core, stage wiring, logging.
    "infrastructure": {
        "accel":                {"status": "infra",     "provides": "Hardware acceleration dispatch (GPU/VDSP/CPU)"},
        "accelerate_gpu":       {"status": "available",  "provides": "GPU-accelerated DSP via Metal/CUDA"},
        "accelerate_vdsp":      {"status": "available",  "provides": "Apple vDSP-accelerated DSP"},
        "dsp_core":             {"status": "infra",     "provides": "Core DSP: SVF filters, saturation, oversampling"},
        "log":                  {"status": "infra",     "provides": "Centralised logging"},
        "error_handling":       {"status": "available",  "provides": "Error handling and recovery"},
        "stage_integrations":   {"status": "infra",     "provides": "Fail-safe wrappers for all phase hooks (114 functions)"},
        "audio_mmap":           {"status": "available",  "provides": "Memory-mapped audio file I/O"},
        "_captured_serum2_state": {"status": "available", "provides": "Captured Serum 2 controller state"},
    },

    # ─── DAW / LIVE PERFORMANCE ───────────────────────────────
    # Real-time integration with Ableton, Serum 2, Link.
    "daw_live": {
        "scene_system":         {"status": "wired",     "provides": "Scene management for live performance"},
        "looper":               {"status": "wired",     "provides": "Loop recording and playback"},
        "performance_recorder": {"status": "wired",     "provides": "Record performance for later analysis"},
        "ableton_bridge":       {"status": "available",  "provides": "Bidirectional Ableton Live communication"},
        "serum2_controller":    {"status": "available",  "provides": "Real-time Serum 2 parameter control via OSC"},
        "link_sync":            {"status": "available",  "provides": "Ableton Link tempo synchronisation"},
        "osc_controller":       {"status": "available",  "provides": "Generic OSC message sending/receiving"},
    },

    # ─── TOOLS / UI / DEV ─────────────────────────────────────
    # CLI, preview, profiling, collaboration.
    "tools": {
        "cli":                  {"status": "available",  "provides": "Command-line interface for DubForge"},
        "web_preview":          {"status": "available",  "provides": "Web-based audio preview server"},
        "audio_preview":        {"status": "available",  "provides": "Quick audio preview playback"},
        "waveform_display":     {"status": "available",  "provides": "Terminal waveform visualisation"},
        "spectrogram_chat":     {"status": "available",  "provides": "Interactive spectrogram analysis"},
        "perf_monitor":         {"status": "available",  "provides": "Performance monitoring (CPU, memory, time)"},
        "profiler":             {"status": "available",  "provides": "Module-level profiling and timing"},
        "tutorials":            {"status": "available",  "provides": "Interactive production tutorials"},
        "chain_commands":       {"status": "available",  "provides": "Chain multiple commands into a batch"},
        "param_control":        {"status": "available",  "provides": "Parameter control surface mapping"},
        "collaboration":        {"status": "available",  "provides": "Multi-user collaboration features"},
        "plugin_host":          {"status": "available",  "provides": "VST plugin hosting"},
        "plugin_scaffold":      {"status": "available",  "provides": "VST plugin project scaffolding"},
        "subphonics_server":    {"status": "available",  "provides": "Subphonics server for external communication"},
        "render_queue":         {"status": "available",  "provides": "Queue multiple renders for batch processing"},
        "snapshot_manager":     {"status": "available",  "provides": "Save/restore project snapshots"},
    },
}


# ═══════════════════════════════════════════════════════════════
#  QUERY HELPERS
# ═══════════════════════════════════════════════════════════════

def get_phase_modules(phase: str) -> dict:
    """Get all modules for a given MWP phase."""
    return REGISTRY.get(phase, {})


def get_wired_modules(phase: str = "") -> dict:
    """Get modules with status 'wired', optionally filtered by phase."""
    result = {}
    phases = [phase] if phase else REGISTRY.keys()
    for p in phases:
        for mod, info in REGISTRY.get(p, {}).items():
            if info["status"] == "wired":
                result[mod] = {"phase": p, **info}
    return result


def get_available_modules(phase: str = "") -> dict:
    """Get modules with status 'available' — ready to wire in."""
    result = {}
    phases = [phase] if phase else REGISTRY.keys()
    for p in phases:
        for mod, info in REGISTRY.get(p, {}).items():
            if info["status"] == "available":
                result[mod] = {"phase": p, **info}
    return result


def get_module_phase(module_name: str) -> str:
    """Look up which phase a module belongs to."""
    for phase, modules in REGISTRY.items():
        if module_name in modules:
            return phase
    return "unknown"


def print_registry_summary():
    """Print a compact summary of the module registry."""
    total = 0
    wired = 0
    available = 0
    for phase, modules in REGISTRY.items():
        phase_total = len(modules)
        phase_wired = sum(1 for m in modules.values() if m["status"] == "wired")
        phase_avail = sum(1 for m in modules.values() if m["status"] == "available")
        phase_infra = sum(1 for m in modules.values() if m["status"] == "infra")
        total += phase_total
        wired += phase_wired + phase_infra
        available += phase_avail
        status = f"{phase_wired}W + {phase_avail}A"
        if phase_infra:
            status += f" + {phase_infra}I"
        print(f"  {phase:20s} │ {phase_total:3d} modules │ {status}")
    print(f"  {'─' * 20}─┼─{'─' * 12}─┼─{'─' * 20}")
    print(f"  {'TOTAL':20s} │ {total:3d} modules │ {wired}W + {available}A")


# ═══════════════════════════════════════════════════════════════
#  MWP PHASE ORDER (canonical)
# ═══════════════════════════════════════════════════════════════

PHASE_ORDER = [
    "oracle",       # 1. Understand what you're building
    "collect",      # 2. Gather sounds and materials
    "recipes",      # 3. Plan structure and templates
    "sketch",       # 4. Design sounds — first instincts
    "arrange",      # 5. Place in time — subtractive arrangement
    "design",       # 6. Sculpt effects and automation
    "mix",          # 7. Balance frequencies and levels
    "master",       # 8. Final processing and loudness
    "release",      # 9. Export and package
    "reflect",      # 10. Review, learn, level up
]

PHASE_BRAIN = {
    "oracle":   "ARCHITECT",
    "collect":  "CHILD",
    "recipes":  "ARCHITECT",
    "sketch":   "CHILD",
    "arrange":  "ARCHITECT",
    "design":   "CHILD",
    "mix":      "CRITIC",
    "master":   "CRITIC",
    "release":  "ARCHITECT",
    "reflect":  "ARCHITECT",
}
