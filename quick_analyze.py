#!/usr/bin/env python3
"""Quick analysis of rendered track quality."""
import sys, wave, struct, numpy as np
from numpy.fft import rfft, rfftfreq

f = sys.argv[1] if len(sys.argv) > 1 else "output/skull_crusher.wav"
w = wave.open(f, "rb")
sr = w.getframerate()
ch = w.getnchannels()
sw = w.getsampwidth()
n = w.getnframes()
raw = w.readframes(n)
w.close()

print(f"Sample rate: {sr} Hz")
print(f"Channels: {ch}")
print(f"Bit depth: {sw * 8}-bit")
print(f"Duration: {n/sr:.1f}s ({int(n/sr//60)}:{int(n/sr%60):02d})")

# Decode (fast vectorized)
if sw == 3:
    # Fast 24-bit decode: pad each 3-byte sample to 4 bytes, interpret as int32
    raw_bytes = np.frombuffer(raw, dtype=np.uint8)
    n_samples = len(raw_bytes) // 3
    raw_bytes = raw_bytes[:n_samples * 3].reshape(-1, 3)
    # Pad to 4 bytes (little-endian: add zero MSB, then shift for sign)
    padded = np.zeros((n_samples, 4), dtype=np.uint8)
    padded[:, 0] = raw_bytes[:, 0]
    padded[:, 1] = raw_bytes[:, 1]
    padded[:, 2] = raw_bytes[:, 2]
    # Convert to int32, then shift left 8 and right 8 for sign extension
    int_vals = padded.view(np.int32).flatten()
    int_vals = (int_vals << 8) >> 8  # sign extend 24-bit to 32-bit
    samples = int_vals.astype(np.float64) / 8388607.0
elif sw == 2:
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
else:
    raise ValueError(f"Unsupported sample width: {sw}")

L = samples[0::2]
R = samples[1::2]
mono = (L + R) / 2.0

# Peak / RMS
peak = np.max(np.abs(samples))
rms = np.sqrt(np.mean(mono**2))
print(f"Peak: {20*np.log10(max(peak, 1e-10)):.1f} dB")
print(f"RMS:  {20*np.log10(max(rms, 1e-10)):.1f} dB")
print(f"Est LUFS: {20*np.log10(max(rms, 1e-10)) - 0.7:.1f}")

# Spectrum in drop section (30-50% of track)
drop_start = int(len(mono) * 0.3)
drop_end = int(len(mono) * 0.5)
seg = mono[drop_start:drop_end]
fft_data = np.abs(rfft(seg))
freqs = rfftfreq(len(seg), 1.0 / sr)

# A-weighting for perceived loudness analysis
def a_weight(f):
    """A-weighting filter magnitude at frequency f."""
    f = np.maximum(f, 1e-10)
    f2 = f * f
    num = 12194.0**2 * f2**2
    den = (f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194.0**2)
    return num / np.maximum(den, 1e-10)

aw = a_weight(freqs)
aw = aw / np.max(aw)  # normalize so 1kHz = 1.0
fft_weighted = fft_data * aw

sub_e = np.mean(fft_data[(freqs >= 20) & (freqs < 80)])
low_e = np.mean(fft_data[(freqs >= 80) & (freqs < 300)])
mid_e = np.mean(fft_data[(freqs >= 300) & (freqs < 3000)])
high_e = np.mean(fft_data[(freqs >= 3000) & (freqs < 10000)])
air_e = np.mean(fft_data[(freqs >= 10000)])
total_e = sub_e + low_e + mid_e + high_e + air_e

sub_aw = np.mean(fft_weighted[(freqs >= 20) & (freqs < 80)])
low_aw = np.mean(fft_weighted[(freqs >= 80) & (freqs < 300)])
mid_aw = np.mean(fft_weighted[(freqs >= 300) & (freqs < 3000)])
high_aw = np.mean(fft_weighted[(freqs >= 3000) & (freqs < 10000)])
air_aw = np.mean(fft_weighted[(freqs >= 10000)])
total_aw = sub_aw + low_aw + mid_aw + high_aw + air_aw

print(f"\nSpectrum (drop, raw FFT / A-weighted):")
print(f"  Sub  20-80Hz:   {sub_e/total_e*100:4.0f}% / {sub_aw/total_aw*100:4.0f}%  (target: 15-30%)")
print(f"  Low  80-300Hz:  {low_e/total_e*100:4.0f}% / {low_aw/total_aw*100:4.0f}%  (target: 15-25%)")
print(f"  Mid  300-3kHz:  {mid_e/total_e*100:4.0f}% / {mid_aw/total_aw*100:4.0f}%  (target: 25-40%)")
print(f"  High 3-10kHz:   {high_e/total_e*100:4.0f}% / {high_aw/total_aw*100:4.0f}%  (target: 10-20%)")
print(f"  Air  10kHz+:    {air_e/total_e*100:4.0f}% / {air_aw/total_aw*100:4.0f}%  (target: 3-10%)")

# Stereo width
mid_sig = (L + R) / 2
side_sig = (L - R) / 2
mid_rms = np.sqrt(np.mean(mid_sig**2))
side_rms = np.sqrt(np.mean(side_sig**2))
print(f"\nStereo width: {side_rms / max(mid_rms, 1e-10):.3f}  (target: 0.3-0.7)")

# Energy curve (10 segments)
seg_size = len(mono) // 10
ec = []
for i in range(10):
    s = mono[i * seg_size : (i + 1) * seg_size]
    s_rms = np.sqrt(np.mean(s**2))
    ec.append(20 * np.log10(max(s_rms, 1e-10)))

print(f"\nEnergy curve:")
for i, val in enumerate(ec):
    bar_len = max(0, int((val + 60) / 2))
    block = chr(9608)
    print(f"  {i*10:>3}-{(i+1)*10:>3}%: {val:6.1f} dB  {block * bar_len}")

# Section contrast
intro_e_db = ec[0]
drop_e_db = max(ec[2:5])
break_e_db = min(ec[4:7])
print(f"\nSection contrast:")
print(f"  Intro to Drop: {drop_e_db - intro_e_db:.1f} dB  (target: 6-12 dB)")
print(f"  Drop to Break: {drop_e_db - break_e_db:.1f} dB  (target: 3-8 dB)")

# Sidechain pump detection
print(f"\nSidechain pump detection:")
chunk_ms = 50
chunk_size = int(sr * chunk_ms / 1000)
drop_mono = mono[drop_start:drop_end]
n_chunks = len(drop_mono) // chunk_size
if n_chunks > 0:
    chunk_rms = []
    for i in range(n_chunks):
        c = drop_mono[i * chunk_size : (i + 1) * chunk_size]
        chunk_rms.append(np.sqrt(np.mean(c**2)))
    chunk_rms = np.array(chunk_rms)
    chunk_db = 20 * np.log10(np.maximum(chunk_rms, 1e-10))
    diffs = np.diff(chunk_db)
    dips = np.sum(diffs < -3)
    recoveries = np.sum(diffs > 3)
    print(f"  Dips (>3dB): {dips}")
    print(f"  Recoveries (>3dB): {recoveries}")
    if dips > 5 and recoveries > 5:
        print("  SIDECHAIN PUMPING DETECTED")
    else:
        print("  No significant pumping detected")

print("\n--- BEFORE vs AFTER ---")
print("Metric           | Before (avg)  | After")
print("Duration          | 96-110s       | {:.0f}s".format(n/sr))
print("LUFS              | -8 to -17     | {:.1f}".format(20*np.log10(max(rms, 1e-10)) - 0.7))
print("Sub %             | 60-83%        | {:.0f}%".format(sub_e/total_e*100))
print("Mid %             | 3-4%          | {:.0f}%".format(mid_e/total_e*100))
print("Stereo width      | 0.03-0.39     | {:.3f}".format(side_rms / max(mid_rms, 1e-10)))
print("Format            | 16-bit/44.1k  | {}-bit/{}k".format(sw*8, sr//1000))
