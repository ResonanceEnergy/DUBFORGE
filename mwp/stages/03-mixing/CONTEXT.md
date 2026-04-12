# Stage 03 — MIXING: Stage Contract
> Layer 2: What do I do? Read after `../../CLAUDE.md` + `../../CONTEXT.md`.

---

## Inputs

| Source | File/Location | Scope | Why |
|--------|---------------|-------|-----|
| Arranged track | `../02-arrangement/output/arranged_track.json` | Full | Kick positions, section map, WAV path |
| Stems manifest | `../02-arrangement/output/stems_manifest.json` | Full | Per-stem WAV paths for bus loading |
| Song mandate | `../01-generation/output/song_mandate.json` | `name`, `bpm`, `total_bars` | Naming + loop length |
| Ableton rules | `../../_config/ableton_rules.md` | OSC commands + export trigger | How to control Ableton |
| Voice rules | `../../_config/voice.md` | Tonal targets + freq map | EQ targets per stem |

---

## Process

1. Connect to Ableton Live via `AbletonBridge`
2. Load available stems: check stems manifest for valid WAV paths
3. Create bus tracks: DRUMS, BASS, MELODIC, FX (return tracks)
4. Per stem:
   - Create audio track
   - Load WAV clip
   - Set gain from `_GAIN_TABLE` (kick=0.85, sub=0.82, etc.)
   - Set pan from `_PAN_TABLE` (kick=0.0, hats=0.3, etc.)
   - Route to correct bus via `_BUS_MAP`
5. Try sidechain: kick→sub compressor (wrapped in try/except; print manual note if fails)
6. Set master volume = 0.85, master pan = 0.0
7. Set loop length from arrangement WAV duration
8. Bounce mixed stereo WAV via osascript Cmd+Shift+R (timeout: 180s)
9. Write `output/mixed_track.json`

---

## Human Gate (After This Stage)

1. Open the mix session in Ableton
2. Pre-load EQ Eight + Compressor on DRUMS and BASS bus tracks (required for OSC device control)
3. Set up kick→sub sidechain compressor if Phase 2 didn't set it
4. A/B test against reference track — adjust faders if needed
5. When mix is balanced: proceed to Stage 04

---

## Outputs

| Artifact | Location | Format | Consumed By |
|----------|----------|--------|-------------|
| Mixed track info | `output/mixed_track.json` | JSON | Stage 04 |
| Stage summary | `output/stage_summary.md` | Markdown | Human review |

---

## Output Schema

### `mixed_track.json`
```json
{
  "kick_positions": [0, 4, 8, 12],
  "section_map": {"intro": 0, "drop1": 24},
  "total_bars": 112,
  "wav_path": "/path/to/mixed_bounce.wav",
  "mix_analysis": {
    "status": "complete",
    "stems_loaded": 8,
    "buses": ["DRUMS", "BASS", "MELODIC", "FX"]
  },
  "elapsed_s": 8.2
}
```

---

## Gain Staging Reference

| Stem | Gain | Pan | Bus |
|------|------|-----|-----|
| kick | 0.85 | 0.0 | DRUMS |
| sub_bass | 0.82 | 0.0 | BASS |
| snare | 0.80 | 0.0 | DRUMS |
| mid_bass | 0.78 | 0.0 | BASS |
| hats | 0.60 | +0.3 | DRUMS |
| lead | 0.72 | +0.1 | MELODIC |
| pad | 0.55 | 0.0 | MELODIC |
| fx | 0.65 | 0.0 | FX |

---

## References

- Full mandate: `../../phase_03_mixing/mandate/MANDATE.md`
- Entry module: `engine/phase_three.py::run_phase_three()`
