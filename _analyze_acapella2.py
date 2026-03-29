"""Full vocal activity map of the Wild Ones acapella."""
import librosa
import numpy as np

fpath = r"C:\dev\DUBFORGE GALATCIA\Flo-Rida-ft-Sia-Wild-Ones-Studio-Acapella.mp3"
y, sr = librosa.load(fpath, sr=44100, mono=True)
dur = len(y) / sr
print(f"Duration: {dur:.2f}s  SR: {sr}  Samples: {len(y)}")

# BPM = 127 (known). Calculate bar/beat grid
BPM = 127.0
beat_dur = 60.0 / BPM  # seconds per beat
bar_dur = beat_dur * 4  # seconds per bar
total_bars = dur / bar_dur
print(f"Beat duration: {beat_dur:.4f}s")
print(f"Bar duration: {bar_dur:.4f}s")
print(f"Total bars (at 127 BPM): {total_bars:.1f}")

# RMS energy per beat (fine-grained vocal map)
hop = int(sr * beat_dur / 4)  # 1/4 beat resolution
rms = librosa.feature.rms(y=y, frame_length=hop*2, hop_length=hop)[0]
rms_times = np.arange(len(rms)) * hop / sr

# Group into bars
print(f"\n{'Bar':>4} | {'Time':>7} | {'RMS':>8} | {'Activity'}")
print("-" * 50)
for bar in range(int(total_bars) + 1):
    t_start = bar * bar_dur
    t_end = (bar + 1) * bar_dur
    # Get RMS frames in this bar
    mask = (rms_times >= t_start) & (rms_times < t_end)
    if np.any(mask):
        bar_rms = np.mean(rms[mask])
        peak_rms = np.max(rms[mask])
    else:
        bar_rms = 0.0
        peak_rms = 0.0
    
    # Classify
    if peak_rms > 0.15:
        activity = "LOUD VOCAL"
    elif peak_rms > 0.05:
        activity = "vocal"
    elif peak_rms > 0.01:
        activity = "quiet"
    else:
        activity = "silence"
    
    print(f"{bar:4d} | {t_start:6.1f}s | {bar_rms:.5f} | {activity}")

# Also detect the song structure by looking at energy envelope
print("\n\nCOARSE SECTION MAP (8-bar blocks):")
print(f"{'Section':>3} | {'Bars':>8} | {'Time':>12} | {'Avg RMS':>8} | {'Type'}")
print("-" * 60)
for section in range(int(total_bars) // 8 + 1):
    bar_start = section * 8
    bar_end = min(bar_start + 8, int(total_bars) + 1)
    t_start = bar_start * bar_dur
    t_end = bar_end * bar_dur
    mask = (rms_times >= t_start) & (rms_times < t_end)
    if np.any(mask):
        sec_rms = np.mean(rms[mask])
        sec_peak = np.max(rms[mask])
    else:
        sec_rms = 0.0
        sec_peak = 0.0
    
    if sec_peak > 0.15:
        stype = "CHORUS/HOOK"
    elif sec_peak > 0.08:
        stype = "VERSE"
    elif sec_peak > 0.02:
        stype = "BRIDGE/BREAK"
    else:
        stype = "SILENCE"
    
    print(f"{section:3d} | {bar_start:3d}-{bar_end-1:3d} | {t_start:5.1f}s-{t_end:5.1f}s | {sec_rms:.5f} | {stype}")
