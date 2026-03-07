"""
DUBFORGE Engine — __init__

All engine modules accessible from `from engine import *`
"""

from engine.ableton_live import (
    LOM_REFERENCE,
    build_arrangement_template,
    build_dubstep_session_template,
    generate_m4l_control_script,
    psbs_device_chain,
)
from engine.ableton_live import (
    SESSION_PRESETS as ABLETON_PRESETS,
)
from engine.als_generator import (
    ALL_ALS_TEMPLATES,
    ALSProject,
    ALSScene,
    ALSTrack,
    build_als_xml,
    dubstep_weapon_session,
    emotive_melodic_session,
    hybrid_fractal_session,
    write_als,
    write_als_json,
)
from engine.chord_progression import (
    ALL_PRESETS as CHORD_PRESETS,
)
from engine.chord_progression import (
    build_chord,
    build_progression,
)
from engine.config_loader import (
    get_config_value,
    list_configs,
    load_config,
    validate_all_configs,
    validate_config,
)
from engine.dojo import (
    ARTIST_PROFILE,
    BELT_SYSTEM,
    DOJO_PLATFORM,
    DOJO_TECHNIQUES,
    THE_APPROACH,
    ApproachPhase,
    ApproachStep,
    BeltLevel,
    BeltRank,
    DojoTechnique,
    RackCategory,
    RackZone,
    TechniqueType,
    build_128_rack,
    build_dojo_session_template,
    phi_approach_timing,
    phi_belt_progression,
    phi_mudpie_recipe,
)
from engine.drum_generator import (
    ALL_DRUM_PATTERNS,
    DrumHit,
    DrumPattern,
    generate_breakbeat,
    generate_dubstep_build,
    generate_dubstep_drop,
    generate_fibonacci_fill,
    generate_halftime_groove,
    generate_intro_minimal,
    pattern_to_midi_track,
    write_drum_midi,
    write_full_drum_arrangement,
)
from engine.fxp_writer import (
    ALL_PRESETS as FXP_PRESETS,
)
from engine.fxp_writer import (
    FXPBank,
    FXPPreset,
    VSTParam,
    dubstep_growl_preset,
    dubstep_lead_preset,
    dubstep_pad_preset,
    dubstep_sub_preset,
    read_fxp,
    write_fxb,
    write_fxp,
)
from engine.growl_resampler import (
    bit_reduce,
    comb_filter,
    formant_filter,
    frequency_shift,
    generate_fm_source,
    generate_saw_source,
    growl_resample_pipeline,
    pitch_shift,
    waveshape_distortion,
)
from engine.log import get_logger
from engine.mastering_chain import (
    MasterReport,
    MasterSettings,
    apply_eq,
    compress,
    dubstep_master_settings,
    estimate_lufs,
    limit,
    loudness_normalize,
    master,
    master_file,
    stereo_widen,
    streaming_master_settings,
)
from engine.memory import (
    MemoryEngine,
    get_memory,
    phi_recency_score,
    phi_relevance,
)
from engine.midi_export import (
    NoteEvent,
    arp_pattern_to_events,
    events_to_track,
    export_arp_midi,
    export_clip_midi,
    export_full_arrangement,
    export_progression_midi,
    midi_clip_to_events,
    progression_to_events,
    write_midi_file,
    write_single_track_midi,
)
from engine.phi_core import (
    FIBONACCI,
    PHI,
    fibonacci_harmonic_series,
    freq_to_midi,
    generate_phi_core_v1,
    generate_phi_core_v2_wook,
    midi_to_freq,
    phi_harmonic_series,
    write_wav,
)
from engine.psbs import (
    BassLayer,
    PSBSPreset,
    calculate_phase_coherence,
    default_psbs,
    phi_crossovers,
    render_psbs_cycle,
    weapon_psbs,
    wook_psbs,
)
from engine.psbs import (
    export_preset as export_psbs_preset,
)
from engine.psbs import (
    export_wavetable as export_psbs_wavetable,
)
from engine.rco import (
    RCOProfile,
    Section,
    exponential_curve,
    fibonacci_step_curve,
    generate_energy_curve,
    linear_curve,
    phi_curve,
    plot_curve,
    subtronics_emotive_preset,
    subtronics_hybrid_preset,
    subtronics_weapon_preset,
)
from engine.sample_slicer import (
    SlicePoint,
    SliceResult,
    SliceSegment,
    detect_onsets,
    fibonacci_slice_points,
    read_audio,
    slice_audio,
    slice_file,
    snap_to_grid,
    write_audio,
)
from engine.sb_analyzer import (
    Album,
    SignatureVector,
    analyze_corpus,
    build_corpus,
    build_signature_vector,
    load_corpus,
    vip_delta_analysis,
)
from engine.sb_analyzer import (
    Track as SBTrack,
)
from engine.serum2 import (
    SERUM2_ARCHITECTURE,
    Serum2Patch,
    phi_envelope,
    phi_filter_cutoff,
    phi_fm_ratio,
    phi_unison_detune,
)
from engine.serum2 import (
    build_dubstep_patches as serum2_dubstep_patches,
)
from engine.serum2 import (
    build_init_template as serum2_init_template,
)
from engine.trance_arp import (
    ArpNote,
    ArpPattern,
    fibonacci_rise_pattern,
    golden_gate_pattern,
    pattern_to_midi_data,
    phi_spiral_pattern,
)
from engine.trance_arp import (
    export_pattern as export_arp_pattern,
)

__all__ = [
    # phi_core
    "PHI",
    "FIBONACCI",
    "generate_phi_core_v1",
    "generate_phi_core_v2_wook",
    "phi_harmonic_series",
    "fibonacci_harmonic_series",
    "write_wav",
    "midi_to_freq",
    "freq_to_midi",
    # rco
    "Section",
    "RCOProfile",
    "phi_curve",
    "fibonacci_step_curve",
    "linear_curve",
    "exponential_curve",
    "generate_energy_curve",
    "subtronics_weapon_preset",
    "subtronics_emotive_preset",
    "subtronics_hybrid_preset",
    "plot_curve",
    # psbs
    "BassLayer",
    "PSBSPreset",
    "phi_crossovers",
    "default_psbs",
    "weapon_psbs",
    "wook_psbs",
    "calculate_phase_coherence",
    "render_psbs_cycle",
    "export_psbs_preset",
    "export_psbs_wavetable",
    # sb_analyzer
    "SBTrack",
    "Album",
    "SignatureVector",
    "build_corpus",
    "load_corpus",
    "analyze_corpus",
    "build_signature_vector",
    "vip_delta_analysis",
    # trance_arp
    "ArpNote",
    "ArpPattern",
    "fibonacci_rise_pattern",
    "phi_spiral_pattern",
    "golden_gate_pattern",
    "pattern_to_midi_data",
    "export_arp_pattern",
    # growl_resampler
    "pitch_shift",
    "waveshape_distortion",
    "frequency_shift",
    "comb_filter",
    "bit_reduce",
    "formant_filter",
    "growl_resample_pipeline",
    "generate_saw_source",
    "generate_fm_source",
    # chord_progression
    "build_progression",
    "build_chord",
    "CHORD_PRESETS",
    # ableton_live
    "build_dubstep_session_template",
    "build_arrangement_template",
    "psbs_device_chain",
    "generate_m4l_control_script",
    "ABLETON_PRESETS",
    "LOM_REFERENCE",
    # serum2
    "Serum2Patch",
    "serum2_dubstep_patches",
    "serum2_init_template",
    "SERUM2_ARCHITECTURE",
    "phi_unison_detune",
    "phi_envelope",
    "phi_filter_cutoff",
    "phi_fm_ratio",
    # dojo
    "BeltRank",
    "BeltLevel",
    "ApproachPhase",
    "ApproachStep",
    "TechniqueType",
    "DojoTechnique",
    "RackZone",
    "RackCategory",
    "BELT_SYSTEM",
    "THE_APPROACH",
    "DOJO_TECHNIQUES",
    "ARTIST_PROFILE",
    "DOJO_PLATFORM",
    "build_128_rack",
    "build_dojo_session_template",
    "phi_belt_progression",
    "phi_approach_timing",
    "phi_mudpie_recipe",
    # memory
    "MemoryEngine",
    "get_memory",
    "phi_recency_score",
    "phi_relevance",
    # log
    "get_logger",
    # midi_export
    "NoteEvent",
    "progression_to_events",
    "arp_pattern_to_events",
    "midi_clip_to_events",
    "events_to_track",
    "write_midi_file",
    "write_single_track_midi",
    "export_progression_midi",
    "export_arp_midi",
    "export_clip_midi",
    "export_full_arrangement",
    # drum_generator
    "DrumHit",
    "DrumPattern",
    "ALL_DRUM_PATTERNS",
    "generate_dubstep_drop",
    "generate_dubstep_build",
    "generate_halftime_groove",
    "generate_fibonacci_fill",
    "generate_breakbeat",
    "generate_intro_minimal",
    "pattern_to_midi_track",
    "write_drum_midi",
    "write_full_drum_arrangement",
    # sample_slicer
    "SlicePoint",
    "SliceSegment",
    "SliceResult",
    "detect_onsets",
    "snap_to_grid",
    "fibonacci_slice_points",
    "slice_audio",
    "slice_file",
    "read_audio",
    "write_audio",
    # mastering_chain
    "MasterSettings",
    "MasterReport",
    "master",
    "master_file",
    "loudness_normalize",
    "compress",
    "limit",
    "apply_eq",
    "stereo_widen",
    "estimate_lufs",
    "dubstep_master_settings",
    "streaming_master_settings",
    # als_generator
    "ALSTrack",
    "ALSScene",
    "ALSProject",
    "ALL_ALS_TEMPLATES",
    "build_als_xml",
    "write_als",
    "write_als_json",
    "dubstep_weapon_session",
    "emotive_melodic_session",
    "hybrid_fractal_session",
    # fxp_writer
    "VSTParam",
    "FXPPreset",
    "FXPBank",
    "FXP_PRESETS",
    "write_fxp",
    "read_fxp",
    "write_fxb",
    "dubstep_sub_preset",
    "dubstep_growl_preset",
    "dubstep_lead_preset",
    "dubstep_pad_preset",
    # config_loader
    "load_config",
    "get_config_value",
    "list_configs",
    "validate_config",
    "validate_all_configs",
]
