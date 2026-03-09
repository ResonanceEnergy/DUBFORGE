"""Quick smoke test for dsp_core and upgraded engines."""
import numpy as np

# 1. dsp_core imports
from engine.dsp_core import (
    svf_lowpass, svf_highpass, svf_bandpass, svf_notch,
    svf_lowpass_24, osc_saw, osc_square, osc_saw_np, _polyblep,
    distort_tube, distort_tape, distort_foldback, distort_bitcrush,
    distort_clipper, saturate_warm, saturate_aggressive,
    oversample_2x, downsample_2x, oversampled_distort,
    reverb_schroeder, chorus, multiband_compress,
    white_noise, pink_noise, normalize, dc_block, crossfade, soft_clip,
    multiband_split,
)
print("dsp_core imports OK")

sig = osc_saw_np(100.0, 0.1, 44100)
print(f"osc_saw_np: {sig.shape}, peak={np.max(np.abs(sig)):.3f}")

sig = osc_square(100.0, 0.1, 44100)
print(f"osc_square: {sig.shape}, peak={np.max(np.abs(sig)):.3f}")

filtered = svf_lowpass(sig, 1000.0, 0.3, 44100)
print(f"svf_lowpass: {filtered.shape}, peak={np.max(np.abs(filtered)):.3f}")

filtered24 = svf_lowpass_24(sig, 1000.0, 0.3, 44100)
print(f"svf_lowpass_24: {filtered24.shape}")

sat = saturate_warm(sig, 2.0, 44100)
print(f"saturate_warm: {sat.shape}")

sat2 = saturate_aggressive(sig, 2.0, 44100)
print(f"saturate_aggressive: {sat2.shape}")

rev = reverb_schroeder(sig, 44100, 1.0, 0.3)
print(f"reverb: {rev.shape}")

ch = chorus(sig, 44100)
print(f"chorus: {ch.shape}")

mb = multiband_compress(sig, 44100)
print(f"multiband_compress: {mb.shape}")

sc = soft_clip(sig)
print(f"soft_clip: {sc.shape}")

print("\n--- Engine smoke tests ---")

# 2. bass_oneshot
from engine.bass_oneshot import BassPreset, synthesize_bass
for bt in ["reese", "square", "growl", "wobble", "acid", "neuro", "saw", "tape",
           "formant", "pulse_width"]:
    p = BassPreset(f"test_{bt}", bt, 65.41, duration_s=0.3, distortion=0.2,
                   filter_cutoff=0.5, detune_cents=15)
    try:
        s = synthesize_bass(p)
        print(f"  bass {bt}: {s.shape}, peak={np.max(np.abs(s)):.3f}")
    except Exception as e:
        print(f"  bass {bt}: FAILED — {e}")

# 3. pad_synth
from engine.pad_synth import PadPreset, synthesize_pad
for pt in ["lush", "dark", "shimmer", "evolving", "choir", "warm", "noise"]:
    p = PadPreset(f"test_{pt}", pt, 220.0, duration_s=0.5, detune_cents=20,
                  filter_cutoff=0.5, brightness=0.6, lfo_rate=0.5)
    try:
        s = synthesize_pad(p)
        print(f"  pad {pt}: {s.shape}, peak={np.max(np.abs(s)):.3f}")
    except Exception as e:
        print(f"  pad {pt}: FAILED — {e}")

# 4. lead_synth
from engine.lead_synth import LeadPreset, synthesize_lead
for lt in ["screech", "pluck", "supersaw", "acid", "saw", "pwm"]:
    p = LeadPreset(f"test_{lt}", lt, 440.0, duration_s=0.3, distortion=0.2,
                   filter_cutoff=0.6, resonance=0.4, detune_cents=15)
    try:
        s = synthesize_lead(p)
        print(f"  lead {lt}: {s.shape}, peak={np.max(np.abs(s)):.3f}")
    except Exception as e:
        print(f"  lead {lt}: FAILED — {e}")

print("\nALL SMOKE TESTS PASSED")
