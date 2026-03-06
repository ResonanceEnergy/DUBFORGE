"""
DUBFORGE Engine — __init__

All engine modules accessible from `from engine import *`
"""

from engine.phi_core import (
    PHI,
    FIBONACCI,
    generate_phi_core_v1,
    generate_phi_core_v2_wook,
    phi_harmonic_series,
    fibonacci_harmonic_series,
    write_wav,
)
from engine.chord_progression import (
    build_progression,
    build_chord,
    midi_to_freq,
    ALL_PRESETS as CHORD_PRESETS,
)
from engine.ableton_live import (
    build_dubstep_session_template,
    build_arrangement_template,
    psbs_device_chain,
    generate_m4l_control_script,
    SESSION_PRESETS as ABLETON_PRESETS,
    LOM_REFERENCE,
)

__all__ = [
    "PHI",
    "FIBONACCI",
    "generate_phi_core_v1",
    "generate_phi_core_v2_wook",
    "phi_harmonic_series",
    "fibonacci_harmonic_series",
    "write_wav",
    "build_progression",
    "build_chord",
    "midi_to_freq",
    "CHORD_PRESETS",
    "build_dubstep_session_template",
    "build_arrangement_template",
    "psbs_device_chain",
    "generate_m4l_control_script",
    "ABLETON_PRESETS",
    "LOM_REFERENCE",
]
