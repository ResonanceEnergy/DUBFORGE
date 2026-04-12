# Phase 2: ARRANGEMENT — Playbook

> v7.0.0 — Template-first architecture. Session template → stem mapping → AbletonOSC.
> Phase 2 Setup builds structured SessionArrangement before section placement.
> ALL phases AbletonOSC. No numpy DSP.

Step-by-step recipes for the template-routed arrangement and stem bounce pipeline.

**Input:** Phase 1 deliverables = (1) pre-loaded ALS template, (2) audio files,
(3) arrangement data/mapping, (4) modulation/automation data for FX chains.

**New in v7:** Phase 2 Setup (engine/phase_two_setup.py) runs FIRST to:
- Build the canonical track layout from session_template.py
- Map every SongMandate stem to a specific template track
- Apply per-track processing (HPF/LPF, mono, gain staging)
- Route through buses (DRUMS/BASS/MELODICS/FX)
- Configure sidechain pairs and return sends
- Build energy curve from section intensities

---

## Recipe 0: Phase 2 Setup — Template → Session (NEW)

**Goal:** Build the structured SessionArrangement from SongMandate + session template.

```python
from engine.phase_two_setup import setup_phase_two

session = setup_phase_two(mandate)
# session.buses: {drums: BusArrangement, bass: ..., melodics: ..., fx: ...}
# session.returns: {reverb: ..., delay: ..., parallel: ...}
# session.section_map: {INTRO: 0, BUILD 1: 8, DROP 1: 24, ...}
# session.energy_curve: np.ndarray (per-sample energy)
# session.kick_positions: [int] (for sidechain triggers)
```

**Template lookup:** engine/session_template.py defines the canonical layout:
- 19 audio/MIDI tracks across 4 bus groups
- 3 return tracks (Reverb, Delay, Parallel Comp)
- 9 scenes (INTRO → OUTRO, ~112–144 bars)
- DBS_GAINS, RETURN_GAINS, DEFAULT_SENDS for gain staging

**Stem mapping:** `MANDATE_TO_TRACK` maps every SongMandate field to a track:
- `drums.kick` → "Kick", `bass.sub` → "Sub", `leads.screech` → "Lead"
- `fx.riser` → "Risers", `atmosphere.dark_pad` → "Pad"
- See session_template.py MANDATE_TO_TRACK for the full mapping.

**Backflow:** Stage 1I injects template requirements into `mandate.design_intent["session_template"]`
so all Phase 1 stages know what content to generate.

---

## Recipe 1: Connect to Ableton Live

**Goal:** Establish AbletonOSC connection (ports 11000/11001).

```python
from engine.ableton_bridge import AbletonBridge

bridge = AbletonBridge()
bridge.connect()  # Test OSC roundtrip
bridge.set_tempo(mandate.dna.bpm)
```

**Precondition:** Ableton Live running with AbletonOSC remote script installed.
**Failure:** Raises RuntimeError — Phase 2 cannot proceed without Ableton.

---

## Recipe 2: Load / Build ALS Project

**Goal:** Load the Phase 1 pre-built ALS project into Ableton, or build from mandate.

```python
# Option A: Load pre-built ALS from Phase 1 Stage 4I/5G
if mandate.production_als_path and mandate.production_als_path.exists():
    bridge.open_project(mandate.production_als_path)

# Option B: Build live from mandate data
else:
    # Create tracks from stem_configs
    for stem_name, config in mandate.stem_configs.items():
        track_idx = bridge.create_midi_track(name=stem_name)
        # Load Serum 2 with preset state
        if stem_name in mandate.serum2_state_map:
            state, ctrl = mandate.serum2_state_map[stem_name]
            bridge.load_device(track_idx, "Serum 2", preset_state=state)
        # Configure FX chain
        if stem_name in mandate.fx_chains:
            for fx_config in mandate.fx_chains[stem_name]:
                bridge.load_device(track_idx, fx_config.device_name)
                for param, value in fx_config.parameters.items():
                    bridge.set_device_param(track_idx, fx_config.device_name, param, value)
```

---

## Recipe 3: Place WAV Stems in Arrangement

**Goal:** Place all Phase 1 rendered audio in arrangement view per section map.

```python
# Place Serum 2 bounced stems (Stage 4J)
for stem_name, wav_path in mandate.audio_clips.items():
    track_idx = bridge.find_track(stem_name)
    # Place at arrangement position per section
    for section in mandate.arrangement_template.sections:
        start_beat = section_to_beat(section, mandate.dna.bpm)
        length_beats = section.bars * 4
        bridge.insert_audio_clip(track_idx, wav_path, start_beat, length_beats)

# Place drum pattern renders (Stage 5G)
for section_name, renders in mandate.stage5_renders.items():
    for zone_group, wav_path in renders.items():
        track_idx = bridge.find_track(zone_group)
        start_beat = section_name_to_beat(section_name, mandate)
        bridge.insert_audio_clip(track_idx, wav_path, start_beat)

# Place MIDI clips from mandate.midi_sequences
for stem_name, clips in mandate.midi_sequences.items():
    track_idx = bridge.find_track(stem_name)
    for clip in clips:
        bridge.create_clip(track_idx, clip.start_beat, clip.length_beats)
        bridge.add_notes(track_idx, clip.notes)
```

---

## Recipe 4: Write Automation

**Goal:** Write section-level automation for filter sweeps, volume rides, send levels.

```python
from engine.automation_recorder import AutomationLane
from engine.als_generator import (
    make_lp_sweep_automation,
    make_ramp_automation,
    make_section_send_automation,
)

# Filter sweep automation (builds: LP closed → open)
for section in mandate.arrangement_template.sections:
    if section.name.startswith("build"):
        bridge.write_automation(
            track_idx=bass_track,
            parameter="Filter Cutoff",
            points=make_lp_sweep_automation(
                start_beat=section_start_beat,
                length_beats=section.bars * 4,
                start_val=0.2, end_val=0.9,
            )
        )

# Volume rides from subtractive map
for section_name, mute_map in subtract_map.items():
    for stem_name, attenuation in mute_map.items():
        if attenuation < 1.0:
            bridge.write_automation(
                track_idx=bridge.find_track(stem_name),
                parameter="Volume",
                points=[(section_start, attenuation)]
            )

# Send levels (reverb/delay bus) per section
for stem_name, route in mandate.modulation_routes.items():
    bridge.write_automation(
        track_idx=bridge.find_track(stem_name),
        parameter=f"Send {route.send_idx}",
        points=make_section_send_automation(route, mandate.arrangement_template)
    )
```

---

## Recipe 5: Configure Sidechain Routing

**Goal:** Set up ghost kick → sidechain compressor routing in Ableton.

```python
# Ghost kick track (already in ALS from Phase 1 Stage 4I)
ghost_kick_track = bridge.find_track("GHOST_KICK")

# Enable sidechain on all bass/pad tracks
for stem_name in ["sub_bass", "mid_bass", "neuro", "wobble", "riddim", "pad"]:
    track_idx = bridge.find_track(stem_name)
    # Compressor with sidechain from ghost kick
    bridge.set_device_param(
        track_idx, "Compressor",
        "Sidechain Source", ghost_kick_track
    )
```

---

## Recipe 6: Apply Subtractive Map

**Goal:** Compute and apply per-section mutes/attenuations.

```python
from engine.stage_integrations import (
    compute_subtractive_map,
    compute_arrangement_energy_curve,
)

# Compute what to remove per section
subtract_map = compute_subtractive_map(
    mandate.audio_clips, mandate.dna, energy_curve
)

# Apply via track mute automation
for section_name, removals in subtract_map.items():
    section_start = section_beat_map[section_name]
    for stem_name, action in removals.items():
        track_idx = bridge.find_track(stem_name)
        if action == "mute":
            bridge.write_automation(
                track_idx, "Track Activator",
                [(section_start, 0.0), (section_end, 1.0)]
            )
        elif isinstance(action, float):  # attenuation
            bridge.write_automation(
                track_idx, "Volume",
                [(section_start, action)]
            )
```

---

## Recipe 7: Bounce Stems

**Goal:** Solo each track and export to individual WAV files.

```python
import numpy as np

stems: dict[str, np.ndarray] = {}
stem_metadata: dict[str, dict] = {}

# Set loop/render range to full arrangement
total_beats = mandate.total_bars * 4
bridge.set_loop(0, total_beats)

# Bounce each track
for track_idx, track_name in enumerate(bridge.list_tracks()):
    if track_name == "GHOST_KICK":
        continue  # Skip ghost kick (utility only)

    wav_path = output_dir / f"{track_name}.wav"
    bridge.bounce_track(track_idx, wav_path, solo=True)

    # Load bounced WAV
    audio = load_wav(wav_path)
    stems[track_name] = audio
    stem_metadata[track_name] = {
        "gain": bridge.get_volume(track_idx),
        "pan": bridge.get_pan(track_idx),
        "source": "ableton_bounce",
    }
```

---

## Recipe 8: Detect Kick Positions

**Goal:** Extract kick onset positions from bounced kick stem.

```python
from engine.stage_integrations import detect_kick_positions

kick_stem = stems.get("kick") or stems.get("KICKS")
kick_positions = detect_kick_positions(kick_stem, sr=48000, bpm=mandate.dna.bpm)
```

---

## Recipe 9: Assemble StemPack

**Goal:** Build final Phase 2 output.

```python
from engine.phase_two import StemPack

stem_pack = StemPack(
    stems=stems,
    section_map=section_beat_to_sample_map(mandate),
    kick_positions=kick_positions,
    total_bars=mandate.total_bars,
    total_samples=total_samples,
    dna=mandate.dna,
    stem_metadata=stem_metadata,
)
```

---

## Recipe 10: Quality Gate

```python
# Verify stem count
assert len(stem_pack.stems) >= 10, f"Only {len(stem_pack.stems)} stems bounced"

# Verify no silent stems
for name, audio in stem_pack.stems.items():
    rms = np.sqrt(np.mean(audio ** 2))
    assert rms > 1e-6, f"Stem {name} is silent"

# Verify kick positions
assert len(stem_pack.kick_positions) > 0, "No kick positions detected"

# Verify duration
total_s = len(next(iter(stem_pack.stems.values()))) / 48000
assert 120 <= total_s <= 360, f"Duration {total_s}s outside range"
```