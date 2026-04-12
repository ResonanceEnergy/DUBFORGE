# DUBFORGE — Sample Pack Index
> Layer 3 shared resource. Cross-stage reference for all sample sources.

---

## Sample Architecture

All sample packs are resolved by `engine/config_loader.py` at import.
Sample paths live in the system sample pack directories or project `configs/`.
This file is the human-readable index — update it when packs change.

---

## Active Sample Packs

| Pack | Type | Contents | Used In |
|------|------|---------|---------|
| `configs/sb_corpus_v1.yaml` | Corpus | Subtronics discography analysis, VIP deltas | Phase 1: DNA |
| `configs/serum2_module_pack_v1.yaml` | Synth presets | 10 stem presets for Serum 2 | Phase 1: Stage 4 |
| `configs/fibonacci_blueprint_pack_v1.yaml` | Blueprint | Phi-based arrangement templates | Phase 1: Stage 2 |
| `configs/memory_v1.yaml` | Memory | Belt tracking, render history | Phase 4: REFLECT |
| `configs/crystal_theorem.yaml` | Extended | Crystal Theorem VIP delta | Phase 1: DNA override |
| `configs/void_protocol.yaml` | Extended | Void Protocol dark pack | Phase 1: DNA override |
| `configs/rco_psbs_vip_delta_v1.1.yaml` | VIP delta | RCO PSBS VIP energy corrections | Phase 1: DNA |

---

## Drum Sample Sources

| Source | Zone Range | Content |
|--------|-----------|---------|
| Galactia FX pack | Zones 48–79 | Uplifters, sweeps, impacts, crashes |
| Bass one-shots | Zones 0–15 | Sub hits, punches, slam bass |
| Drum kit | Zones 16–47 | Kick, snare, hats, clap, tom |
| Lead one-shots | Zones 80–111 | Stabs, chords, melody hits |
| FX/misc | Zones 112–127 | Misc FX, noise, texture |

See `engine/drum_generator.py` → `_ZONE_RANGES` for exact zone boundaries.

---

## Audio Manifest Format

Phase 1 writes `stages/01-generation/output/audio_manifest.json`:

```json
{
  "total": 24,
  "delivered": 10,
  "stems": {
    "kick": "output/renders/kick_stem.wav",
    "sub_bass": "output/renders/sub_bass_stem.wav",
    "fm_growl": "output/renders/fm_growl_stem.wav",
    "wobble": "output/renders/wobble_stem.wav",
    "screech": "output/renders/screech_stem.wav",
    "chord_f_l": "output/renders/chord_f_l_stem.wav",
    "chord_f_r": "output/renders/chord_f_r_stem.wav",
    "dark_pad": "output/renders/dark_pad_stem.wav",
    "drone": "output/renders/drone_stem.wav",
    "atmos": "output/renders/atmos_stem.wav"
  },
  "drum_loops": {},
  "pending": ["bass_loop_drop.wav", "kick_pattern_build.wav"]
}
```

---

## Cross-Stage Sample Rules

1. **Phase 1 → Phase 2**: Stem WAV paths in `output/audio_manifest.json`
2. **Phase 2 → Phase 3**: Individual stem paths in `output/stems_manifest.json`
3. **Phase 3 → Phase 4**: Mixed stereo path in `output/mixed_track.json`
4. **Phase 4 output**: Master WAV path in `output/master_info.json`

Never pass raw numpy arrays between phases. Paths only.

---

## Missing Sample Protocol

If a sample is missing at stage boundary:
1. Check `output/audio_manifest.json` pending list
2. Open the relevant ALS in Ableton
3. Bounce the missing stems manually
4. Update the manifest JSON with the new paths
5. Re-run the next stage
