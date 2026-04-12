# DUBFORGE — Master Workflow Playbook (MWP v6.0.0)
**AbletonOSC-Native 4-Phase Production Pipeline**
**Last Updated: 2026-04-10**

---

## 0. PREREQUISITES

```
Hardware:  Mac Mini M4 Pro, 64 GB, macOS 15 Sequoia
DAW:       Ableton Live 12 Suite (running + AbletonOSC active)
Python:    3.12+, venv at /DUBFORGE/.venv
OSC:       AbletonOSC port 11000 (send) / 11001 (recv)
Perms:     macOS Accessibility → Terminal ✓  (for osascript Cmd+Shift+R)
```

Pre-flight checklist:
- [ ] Ableton Live 12 Suite **open**
- [ ] AbletonOSC loaded (Tools → AbletonOSC or M4L device)
- [ ] No other project open (blank session or previous project closed)
- [ ] Accessibility permission granted for Terminal / VS Code

---

## 1. LAUNCH THE FORGE UI

```bash
cd /Users/natrix/Documents/GitHub/DUBFORGE
source .venv/bin/activate
python forge.py --launch --ui-only
# → http://localhost:7861
```

Fill in:
| Field | Example | Notes |
|-------|---------|-------|
| Song Name | `CYCLOPS FURY` | Semantic name drives SongDNA |
| Style | `dubstep` | |
| Mood | `aggressive` | Maps to parameter curve |
| Key | `A` | Leave blank for auto |
| Scale | `minor` | Leave blank for auto |
| BPM | `140` | 0 = DNA-derived |
| Arrangement | `WEAPON` | WEAPON / EMOTIVE / HYBRID / blank |

Click **FORGE IT**. The 13-step progress bar drives all 4 phases.

---

## 2. PHASE 1 — GENERATION (Steps 1–9)

**Entry point**: `engine/phase_one.py :: run_phase_one(blueprint) → SongMandate`

### What happens automatically
1. **SongBlueprint → SongDNA** via `variation_engine.forge_dna()`
   - 153-field spec: DrumDNA, BassDNA, LeadDNA, AtmosphereDNA, FxDNA, MixDNA, SongDNA
2. **MIDI sequences** generated for all stems (kick, snare, hats, sub_bass, mid_bass, lead, pad, arp, fx)
3. **Serum 2 presets** (.fxp) generated per stem via `serum2_controller.py`
4. **Wavetables** built via `phi_core.py` (PHI_CORE, GROWL_SAW, GROWL_FM)
5. **Drum samples** selected from GALATCIA, 128 Rack ADG generated
6. **Render ALS** built by `als_generator.py` (MIDI tracks + drum rack + returns)
7. **SongMandate** returned — all assets catalogued

### Output
```
SongMandate
├── render_als_path          # .als for Ableton (open and configure manually)
├── audio_manifest.files[]   # List of stem WAVs expected
├── midi_sequences{}         # Per-stem MIDI note sequences
├── stem_configs{}           # Per-stem volume/pan/FX parameters
├── serum2_presets[]         # .fxp file paths
├── wavetables               # Wavetable pack paths
├── rack_128                 # 128 Rack zone map
└── sections{}               # Bar map: INTRO/BUILD/DROP/BREAK/OUTRO
```

### Manual step required (Serum 2 loading)
- Open `output/ableton/*_render.als` in Ableton
- On each MIDI track: load Serum 2 VST3 manually
- Load matching .fxp from `output/presets/<stem>.fxp`
- *This is the only manual step in the pipeline*

---

## 3. PHASE 2 — ARRANGEMENT (Step 10)

**Entry point**: `engine/phase_two.py :: run_phase_two(mandate) → ArrangedTrack`

### What happens automatically
1. **AbletonBridge.connect()** — OSC handshake (port 11000)
2. `set_tempo(dna.bpm)`, `set_time_signature(4,4)`, `set_metronome(False)`
3. Open Phase 1 render ALS via osascript `open POSIX file`
4. Per stem in `mandate.audio_manifest`:
   - `create_audio_track(-1, stem_name)` → track_idx
   - `set_track_volume(track_idx, 0.85 * level)`
   - `set_track_pan(track_idx, pan_value)`
   - `create_arrangement_audio_clip(track_idx, wav_path, 0.0)`
5. `_write_section_automation()` — OSC volume rides per section per stem
6. `_setup_return_tracks()` — creates REV/DLY returns, sets per-stem sends
7. `set_loop(True, 0.0, total_beats)`
8. `_trigger_export_and_wait(output_path)` — osascript Cmd+Shift+R + poll (180s)

### Output: ArrangedTrack dataclass
```python
@dataclass
class ArrangedTrack:
    kick_positions: list[int]    # Sample positions of kick hits
    section_map: dict[str, int]  # Section name → bar count
    total_bars: int
    total_samples: int
    dna: Any                     # SongDNA
    stem_paths: dict[str, str]   # stem_name → WAV path
    wav_path: str                # Bounced arrangement WAV
    track_indices: dict[str, int] # stem → Ableton track index
    elapsed_s: float
```

### Graceful fallback
If Ableton is unreachable: Phase 1 stem paths forwarded directly (wav_path from audio_manifest).

---

## 4. PHASE 3 — MIXING (Step 11)

**Entry point**: `engine/phase_three.py :: run_phase_three(arranged, mandate) → MixedTrack`

### What happens automatically
1. **AbletonBridge.connect()** — fresh session
2. Create bus group tracks: DRUMS, BASS, MELODIC, FX
3. Per stem from `arranged.stem_paths`:
   - `create_audio_track(-1, stem_name)` → track_idx
   - `set_track_volume(track_idx, _GAIN_TABLE[stem])` — gain staging
   - `set_track_pan(track_idx, _PAN_TABLE[stem])` — spatial placement
   - `create_arrangement_audio_clip(track_idx, wav_path, 0.0)`
4. Sidechain try: `bridge.set_sidechain(bass_track, kick_track)` — AbletonOSC limitation, configure manually
5. `set_master_volume(0.85)`, `set_master_pan(0.0)`
6. `set_loop(True, 0.0, total_beats)`
7. `_trigger_export_and_wait(output_path)` — osascript Cmd+Shift+R + poll (180s)

### Gain staging tables (from `_GAIN_TABLE`)
| Stem | Gain | Pan |
|------|------|-----|
| kick | 0.85 | 0.0 |
| sub_bass | 0.82 | 0.0 |
| snare | 0.80 | 0.0 |
| mid_bass | 0.78 | 0.05 |
| hats | 0.60 | 0.3 |
| lead | 0.72 | 0.1 |
| pad | 0.55 | 0.0 |
| arp | 0.65 | -0.15 |
| fx | 0.50 | 0.0 |

### Manual step: sidechain
- In Ableton: on BASS track, add Compressor with sidechain input = kick track
- AbletonOSC cannot configure sidechain routing programmatically

### Output: MixedTrack dataclass
```python
@dataclass
class MixedTrack:
    kick_positions: list[int]
    section_map: dict[str, int]
    total_bars: int
    dna: Any
    wav_path: str          # Mixed stereo WAV path
    mix_analysis: dict     # peak, rms, rms_db
    elapsed_s: float
    stereo: Any = None     # compat field, always None
```

---

## 5. PHASE 4 — MASTERING (Step 12)

**Entry point**: `engine/phase_four.py :: run_phase_four(mixed, mandate, output_dir) → str`

### What happens automatically

#### Part A: AbletonOSC mastering
1. **AbletonBridge.connect()** — fresh mastering session
2. `create_audio_track(0, "MASTER_IN")` → load `mixed.wav_path`
3. `set_master_volume(0.9)`, `set_master_pan(0.0)`
4. Try to set Ceiling device param (pre-load Limiter first)
5. Read mix WAV duration → compute total_beats
6. `set_loop(True, 0.0, total_beats)`
7. `_trigger_export_and_wait(ableton_master_wav, timeout_s=300)` — poll

#### Part B: Python post-processing
8. `_read_stereo_wav(master_wav)` — reads back Ableton export
9. `validate_output()`, `apply_auto_master()`, `get_reference_insights()`
10. `normalize_phi_master()`, `analyze_phi_coherence()`
11. `apply_final_dither()`, `embed_audio_watermark()`
12. `_write_stereo_wav(out_path)` — final 24-bit WAV

#### Part C: RELEASE exports
13. `run_audio_analysis()`, `validate_key_consistency()`, `compare_to_reference()`
14. `export_midi_file()`, `write_audio_metadata()`, `export_bounce_stems()`
15. `generate_artwork()`, `export_serum2_preset()`, `build_ep_metadata()`
16. `export_ableton_rack()`, `tag_output_file()`
17. `build_grandmaster_report_hook()`, `get_ascension_manifest()`

#### Part D: REFLECT
18. `generate_report_card()` — grades the track 0–100
19. `assess_belt_promotion()` — belt system advancement
20. `record_render_lessons()`, `log_milestone()`

### Output
```
output/<track_name>/
├── <track_name>.wav              # Final 24-bit master WAV ← THE BANGER
├── <track_name>_ableton_master.wav  # Raw Ableton export (pre-Python processing)
├── midi/<track_name>.mid         # Full MIDI export
└── ...                           # Artwork, presets, metadata
```

---

## 6. DATA FLOW SUMMARY

```
SongBlueprint (name, mood, key, bpm, style)
        │
        ▼  run_phase_one()
SongMandate (render_als_path, audio_manifest, midi_sequences, stem_configs, ...)
        │
        │  [Manual: open ALS in Ableton, load Serum 2 + .fxp presets]
        │
        ▼  run_phase_two()
ArrangedTrack (wav_path, stem_paths, section_map, kick_positions, track_indices)
        │
        │  [Manual: configure sidechain in Ableton if desired]
        │
        ▼  run_phase_three()
MixedTrack (wav_path, section_map, total_bars, dna, mix_analysis)
        │
        ▼  run_phase_four()
str  ←  output/<name>/<name>.wav   ← THE DANCEFLOOR BANGER
```

---

## 7. AbletonOSC API CHEATSHEET

All calls go through `engine/ableton_bridge.py :: AbletonBridge`.

```python
from engine.ableton_bridge import AbletonBridge

bridge = AbletonBridge()  # host=127.0.0.1, send=11000, recv=11001
bridge.connect()

# Transport
bridge.set_tempo(140.0)
bridge.set_time_signature(4, 4)
bridge.set_loop(True, 0.0, 256.0)   # enable, start_beats, length_beats
bridge.play()
bridge.stop()

# Tracks
t = bridge.create_audio_track(-1, "KICK")
bridge.set_track_volume(t, 0.85)     # 0.0–1.0
bridge.set_track_pan(t, 0.0)         # -1.0–1.0
bridge.set_track_mute(t, False)

# Clips (Arrangement view)
bridge.create_arrangement_audio_clip(t, "/path/to/file.wav", 0.0)

# Devices
params = bridge.get_device_parameters(t, 0)
bridge.set_device_parameter_by_name(t, 0, "Ceiling", -0.3)

# Returns
r = bridge.create_return_track("REVERB")
bridge.set_track_send(t, 0, 0.3)    # track, send_index, amount

# Master
bridge.set_master_volume(0.9)
bridge.set_master_pan(0.0)

# Export  ← CANNOT DO via OSC
# Use osascript:  key code 15 using {command down, shift down}

bridge.disconnect()
```

---

## 8. EXPORT TRIGGER (osascript)

Used in all 3 bouncing phases. Located in each phase module as `_trigger_export_and_wait()`.

```python
def _trigger_export_and_wait(output_path, timeout_s=180.0, total_beats=256.0):
    script = (
        'tell application "Ableton Live 12 Suite" to activate\n'
        'delay 0.5\n'
        'tell application "System Events"\n'
        '    key code 15 using {command down, shift down}\n'
        '    delay 2.0\n'
        '    key code 36\n'    # Enter to confirm dialog
        'end tell\n'
    )
    subprocess.run(["osascript", "-e", script], capture_output=True)
    # Poll every 2s until file exists and size stabilises
    deadline = time.time() + timeout_s
    last_size = -1
    while time.time() < deadline:
        p = Path(output_path)
        if p.exists():
            size = p.stat().st_size
            if size > 0 and size == last_size:
                return output_path
            last_size = size
        time.sleep(2.0)
    return output_path
```

---

## 9. KNOWN LIMITATIONS

| Limitation | Workaround |
|-----------|-----------|
| AbletonOSC cannot trigger export | osascript Cmd+Shift+R + poll |
| AbletonOSC cannot configure sidechain routing | Configure manually in Ableton before Phase 3 |
| AbletonOSC cannot load VST instruments | Load Serum 2 + .fxp presets manually after Phase 1 |
| Device loading via OSC is unreliable | Pre-load devices in Ableton template; use `set_device_parameter_by_name()` |
| Accessibility permissions required | System Settings → Privacy → Accessibility → Terminal ✓ |

---

## 10. TROUBLESHOOTING

### "AbletonBridge.connect() failed"
- Ableton is not running, or AbletonOSC M4L device is not loaded
- Check: Tools → AbletonOSC, or drag M4L device onto Master track

### "Export timed out" (phase WAV not created)
- Ableton's Export dialog may be hidden or have an error
- Check Ableton window manually; dismiss any blocking dialog
- Re-run the phase individually from Python

### "Phase 3 sidechain config: set up manually"
- Expected — AbletonOSC cannot configure sidechain input
- Action: in Ableton, on the sub_bass/mid_bass audio track, add Compressor, set Sidechain = Audio From = kick track

### osascript permission denied
- Grant macOS Accessibility for your terminal emulator
- System Settings → Privacy & Security → Accessibility → add Terminal / VS Code

### Phase 4 fallback: "Using mixed WAV as master"
- Ableton export timed out or Ableton was not reachable
- The Python QA/release pipeline still runs on the mixed WAV
- For proper mastering, open Ableton, load the mixed WAV, apply master chain, export manually

---

## 11. ABLETON MASTER CHAIN SETUP (for Phase 4)

Pre-load these devices on the **Master** track before running Phase 4:

1. **EQ Eight** — low shelf +1.5 dB at 80 Hz, high shelf +1.0 dB at 16 kHz  
2. **Glue Compressor** — ratio 2:1, attack 10ms, release Auto, threshold -18 dB  
3. **OTT** (Multiband Dynamics) — depth 0.3, upward comp enabled, phi crossovers: 89/233/610 Hz  
4. **Limiter** — ceiling -0.3 dB, lookahead 3ms  

These are the reference settings. Phase 4 will attempt to set `Ceiling = md.ceiling_db` via OSC.

---

## 12. BELT PROGRESSION (ill.Gates Dojo)

Phase 4 automatically calls `assess_belt_promotion()` and `generate_report_card()`.

| Belt | Tracks Required | Score Threshold |
|------|----------------|----------------|
| White | 0 | — |
| Yellow | 3 | 60+ |
| Orange | 8 | 65+ |
| Green | 13 | 70+ |
| Blue | 21 | 75+ |
| Purple | 34 | 80+ |
| Brown | 55 | 85+ |
| Red | 89 | 88+ |
| Black | 144 | 91+ |
| Grandmaster | 144+ | 95+ |

*(Thresholds are Fibonacci-approximate. Exact values in `engine/dojo.py`.)*

---

*See also: CONTEXT.md (full pipeline reference), DOCTRINE.md (cardinal rules + module tables), playbooks/anti_drift.md (finish-track discipline)*
