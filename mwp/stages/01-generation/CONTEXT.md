# Stage 01 — GENERATION: Stage Contract
> Layer 2: What do I do? Read after `../../CLAUDE.md` + `../../CONTEXT.md`.

---

## Inputs

| Source | File/Location | Scope | Why |
|--------|---------------|-------|-----|
| Song blueprint | `../../../configs/base_template.yaml` or UI params | Full | name, mood, key, BPM, style |
| Phi constants | `../../_config/phi_constants.md` | Full | Frequency table, envelope timing |
| Voice rules | `../../_config/voice.md` | Aesthetic targets section | Sound design targets |
| Genre palette | `../../shared/genre_palette.md` | Sub-genre table + freq map | Genre constraints |
| Sub-genre corpus | `../../../configs/sb_corpus_v1.yaml` | Full | Subtronics DNA reference |
| Serum presets | `../../../configs/serum2_module_pack_v1.yaml` | Full | Stem preset mapping |

---

## Process

1. Parse song blueprint → **SongDNA** (153 fields, 7 sub-DNAs via `VariationEngine`)
2. Resolve chord progression + frequency table (phi-tuned, A4=432 Hz)
3. Generate MIDI sequences for all 10 stems (S1-S10: kick, sub, growl, wobble…)
4. Stage 4 — Synth Factory: wavetables → Serum 2 presets → load in ALS → bounce 10 WAV stems
5. Stage 5 — Drum Factory: 128 Rack build → patterns → bounce per-section drum WAVs
6. Write ALS template with all tracks + FX chains pre-loaded
7. Serialize **SongMandate** (42 fields) to `output/song_mandate.json`
8. Write **audio manifest** to `output/audio_manifest.json`

---

## Human Gate (After This Stage)

1. Open the ALS template in Ableton Live
2. Load Serum 2 `.fxp` preset files onto each MIDI track manually
3. Verify each stem sounds correct — adjust if needed
4. Bounce any pending stems listed in `output/audio_manifest.json` → `pending`
5. Update `output/audio_manifest.json` with actual WAV paths for pending items
6. When all stems are bounced: proceed to Stage 02

---

## Outputs

| Artifact | Location | Format | Consumed By |
|----------|----------|--------|-------------|
| Song mandate | `output/song_mandate.json` | JSON | Stage 02 direct read |
| Audio manifest | `output/audio_manifest.json` | JSON path list | Stage 02 stem loading |
| ALS template path | `output/als_path.txt` | Plain text path | Stage 02 Ableton open |
| Stage summary | `output/stage_summary.md` | Markdown | Human review |

---

## Output Schema

### `song_mandate.json`
```json
{
  "name": "apology",
  "style": "riddim",
  "key": "F",
  "scale": "minor",
  "bpm": 140,
  "root_freq": 43.65,
  "total_bars": 112,
  "sections": {"intro": 8, "build": 16, "drop1": 32, "break": 8, "build2": 8, "drop2": 32, "outro": 8},
  "groove_template": "dubstep_halftime",
  "als_path": "/path/to/apology_template.als",
  "stems": {
    "kick": "/path/to/renders/kick.wav",
    "sub_bass": "/path/to/renders/sub_bass.wav"
  },
  "arrange_tasks": ["Place kick on grid", "Load sub bass on track 2"],
  "phase_log": []
}
```

### `audio_manifest.json`
```json
{
  "total": 24,
  "delivered": 10,
  "stems": {"kick": "/path.wav", "sub_bass": "/path.wav"},
  "pending": ["bass_loop_drop.wav"]
}
```

---

## References

- Full Stage 4 recipe: `../../phase_01_generation/playbook/PLAYBOOK.md`
- Full mandate: `../../phase_01_generation/mandate/MANDATE.md`
- Entry module: `engine/phase_one.py::run_phase_one()`
