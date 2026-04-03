"""Shared test fixtures and automatic markers for DUBFORGE test suite.

Test tiers (use ``pytest -m <marker>`` to select):
    fast   — structure, data-model, config, metadata tests  (~88 files)
    slow   — DSP / audio-processing tests that render signals (~40 files)

Quick CI gate:   pytest -m fast          (should finish in <30 s)
Full suite:      pytest                  (runs everything)
Parallel:        pytest -n auto          (needs pytest-xdist)
"""
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

# Files whose engine imports touch DSP / audio rendering modules.
# Everything NOT in this set is auto-marked ``fast``.
_SLOW_FILES: frozenset[str] = frozenset({
    "test_ambient_texture.py",
    "test_arp_synth.py",
    "test_bass_oneshot.py",
    "test_batch_renderer.py",
    "test_chord_pad.py",
    "test_cli.py",
    "test_convolution.py",
    "test_drone_synth.py",
    "test_drum_generator.py",
    "test_error_handling.py",
    "test_formant_synth.py",
    "test_fx_generator.py",
    "test_glitch_engine.py",
    "test_granular_synth.py",
    "test_harmonic_analysis.py",
    "test_impact_hit.py",
    "test_integration.py",
    "test_lead_synth.py",
    "test_lfo_matrix.py",
    "test_mastering_chain.py",
    "test_multiband_distortion.py",
    "test_noise_generator.py",
    "test_pad_synth.py",
    "test_perc_synth.py",
    "test_phi_core.py",
    "test_pluck_synth.py",
    "test_reverb_delay.py",
    "test_riddim_engine.py",
    "test_riser_synth.py",
    "test_sample_slicer.py",
    "test_sidechain.py",
    "test_spectral_resynthesis.py",
    "test_stereo_imager.py",
    "test_sub_bass.py",
    "test_transition_fx.py",
    "test_turboquant_integration.py",
    "test_vocal_chop.py",
    "test_vocal_processor.py",
    "test_wavetable_morph.py",
    "test_wobble_bass.py",
})


def pytest_collection_modifyitems(config, items):
    """Auto-apply ``fast`` or ``slow`` markers based on filename."""
    mark_slow = pytest.mark.slow
    mark_fast = pytest.mark.fast
    for item in items:
        fname = Path(item.fspath).name
        if fname in _SLOW_FILES:
            item.add_marker(mark_slow)
        else:
            item.add_marker(mark_fast)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Provide a temporary output directory for tests that write files."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def configs_dir() -> Path:
    """Path to the project configs directory."""
    return Path(__file__).parent.parent / "configs"
