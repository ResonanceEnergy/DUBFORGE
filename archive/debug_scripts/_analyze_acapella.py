"""Analyze the Wild Ones acapella file."""
import librosa
import numpy as np

fpath = r"C:\dev\DUBFORGE GALATCIA\Flo-Rida-ft-Sia-Wild-Ones-Studio-Acapella.mp3"
y, sr = librosa.load(fpath, sr=None, mono=False)
print(f"Sample rate: {sr} Hz")
print(f"Shape: {y.shape}")
if y.ndim == 1:
    print("Channels: 1 (mono)")
    dur = len(y) / sr
else:
    print(f"Channels: {y.shape[0]}")
    dur = y.shape[1] / sr
print(f"Duration: {dur:.2f}s ({dur/60:.1f} min)")
print(f"Peak: {np.max(np.abs(y)):.4f}")
print(f"RMS: {np.sqrt(np.mean(y**2)):.4f}")

# Estimate BPM
y_mono = librosa.to_mono(y) if y.ndim > 1 else y
tempo, beats = librosa.beat.beat_track(y=y_mono, sr=sr)
if hasattr(tempo, "__len__"):
    tempo = tempo[0]
print(f"Estimated BPM: {tempo:.1f}")

# Key detection
chroma = librosa.feature.chroma_cqt(y=y_mono, sr=sr)
chroma_avg = np.mean(chroma, axis=1)
keys = ["C","C#","D","D#","E","F","F#","G","G#/Ab","A","A#/Bb","B"]
dominant = keys[np.argmax(chroma_avg)]
print(f"Dominant pitch class: {dominant}")
for k, v in zip(keys, chroma_avg):
    print(f"  {k:5s}: {v:.4f}")

# Beat positions for later sync
beat_times = librosa.frames_to_time(beats, sr=sr)
print(f"\nFirst 16 beat times: {beat_times[:16]}")
print(f"Total beats detected: {len(beat_times)}")

# Find onset times to understand vocal structure
onsets = librosa.onset.onset_detect(y=y_mono, sr=sr, units="time")
print(f"Total onsets: {len(onsets)}")
print(f"First 20 onset times: {onsets[:20]}")

# RMS energy over time to find silent/loud sections
rms = librosa.feature.rms(y=y_mono, frame_length=2048, hop_length=512)[0]
rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
# Find sections where vocal is active (above threshold)
threshold = np.max(rms) * 0.05
active = rms > threshold
# Find start/end of vocal sections
changes = np.diff(active.astype(int))
starts = np.where(changes == 1)[0]
ends = np.where(changes == -1)[0]
print(f"\nVocal activity sections (start_time - end_time):")
for i in range(min(len(starts), len(ends), 20)):
    s = rms_times[starts[i]]
    e = rms_times[ends[i]]
    if e - s > 0.5:  # Only show sections > 0.5s
        print(f"  {s:.1f}s - {e:.1f}s  (dur: {e-s:.1f}s)")
