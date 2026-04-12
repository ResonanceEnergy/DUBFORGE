# Stage 02 — ARRANGEMENT: Stage Contract
> Layer 2: What do I do? Read after `../../CLAUDE.md` + `../../CONTEXT.md`.

---

## Inputs

| Source | File/Location | Scope | Why |
|--------|---------------|-------|-----|
| Song mandate | `../01-generation/output/song_mandate.json` | Full | BPM, sections, stem paths, ALS path |
| Audio manifest | `../01-generation/output/audio_manifest.json` | stems dict | Which WAV files to load into Ableton |
| ALS path | `../01-generation/output/als_path.txt` | Full | Which template to open in Ableton |
| Ableton rules | `../../_config/ableton_rules.md` | OSC commands + export trigger | How to control Ableton |
| Voice rules | `../../_config/voice.md` | Arrangement archetypes | Section energy targets |

---

## Process

1. Connect to Ableton Live via `AbletonBridge` (port 11000/11001)
2. Open ALS template via osascript: `open -a "Ableton Live 12 Suite" {als_path}`
3. Set tempo from mandate BPM
4. Create audio tracks (one per stem) — set names, volume, pan
5. Load each stem WAV into Ableton audio clips per section map
6. Write section-level automation (volume rides, filter sweeps, FX sends)
7. Set sidechain routing → kick→sub compressor (manual if OSC unavailable)
8. Apply subtractive map: mute elements per section per energy curve
9. Bounce arrangement to stereo WAV via osascript Cmd+Shift+R (timeout: 180s)
10. Write `output/arranged_track.json` + `output/stems_manifest.json`

---

## Human Gate (After This Stage)

1. Open the arrangement session in Ableton
2. Set up kick→sub_bass sidechain compressor manually (OSC limitation)
3. Review automation in arrangement view — adjust levels and filter sweeps
4. When satisfied with arrangement: proceed to Stage 03

---

## Outputs

| Artifact | Location | Format | Consumed By |
|----------|----------|--------|-------------|
| Arranged track summary | `output/arranged_track.json` | JSON | Stage 03 stem loading |
| Stems manifest | `output/stems_manifest.json` | JSON path dict | Stage 03 |
| Bounce path | `output/arrangement_bounce.wav` or in JSON | .wav path string | Stage 03 |
| Stage summary | `output/stage_summary.md` | Markdown | Human review |

---

## Output Schema

### `arranged_track.json`
```json
{
  "kick_positions": [0, 4, 8, 12],
  "section_map": {
    "intro": 0, "build": 8, "drop1": 24, "break": 56,
    "build2": 64, "drop2": 72, "outro": 104
  },
  "total_bars": 112,
  "wav_path": "/path/to/arrangement_bounce.wav",
  "elapsed_s": 12.4
}
```

### `stems_manifest.json`
```json
{
  "kick": "/path/kick_stem.wav",
  "sub_bass": "/path/sub_bass_stem.wav",
  "fm_growl": "/path/fm_growl_stem.wav",
  "wobble": "/path/wobble_stem.wav"
}
```

---

## References

- Full architecture: `../../phase_02_arrangement/mandate/MANDATE.md`
- Step-by-step: `../../phase_02_arrangement/playbook/PLAYBOOK.md`
- Entry module: `engine/phase_two.py::run_phase_two()`
