# Stage 04 — MASTERING: Stage Contract
> Layer 2: What do I do? Read after `../../CLAUDE.md` + `../../CONTEXT.md`.

---

## Inputs

| Source | File/Location | Scope | Why |
|--------|---------------|-------|-----|
| Mixed track | `../03-mixing/output/mixed_track.json` | Full | WAV path, kick positions, section map |
| Song mandate | `../01-generation/output/song_mandate.json` | `name`, `bpm`, `key` | Output naming + metadata |
| Phi constants | `../../_config/phi_constants.md` | Core constants | Phi normalization target |
| Ableton rules | `../../_config/ableton_rules.md` | Export trigger | osascript for master bounce |
| Voice rules | `../../_config/voice.md` | Tonal targets | LUFS targets, EQ targets |

---

## Process

### Part A — Ableton Mastering Session
1. Connect to Ableton Live via `AbletonBridge`
2. Create MASTER_IN audio track
3. Load `mixed_track.wav_path` as audio clip
4. Pre-loaded master chain (human sets up before this stage): EQ Eight → Glue Compressor → Limiter
5. Set loop length = full track duration
6. Bounce master WAV via osascript Cmd+Shift+R (timeout: 300s)
7. Poll until `ableton_master.wav` file stabilises

### Part B — Python QA
1. Read bounced master WAV `_read_stereo_wav()`
2. Validate loudness: check LUFS target (–7 to –9 LUFS club, –14 LUFS streaming)
3. Phi normalization: normalize peak to `PHI_INV = 0.618` (62% of full scale)
4. Dither: add TPDF dither before 16-bit export
5. Watermark: write metadata tags
6. Write final WAV to `output/master.wav`

### Part C — Release
7. `run_audio_analysis(dna, L, R, SR)` → mix report
8. `export_midi_file(dna, mandate)` → MIDI stems
9. `write_audio_metadata(dna, out_path)` → ID3 tags
10. `generate_artwork(dna)` → cover art
11. `build_ep_metadata(mandate)` → EP sheet

### Part D — Reflect
12. `generate_report_card(dna, out_path, L, R, SR)` → grade
13. `assess_belt_promotion(mem_engine, …)` → belt status
14. `record_render_lessons(dna)` → lesson log

---

## Human Gate (Before This Stage)

1. Open a fresh Ableton session
2. Create audio track named "MASTER_IN"
3. Pre-load on Master track: **EQ Eight** → **Glue Compressor** → **Limiter**
4. Set Limiter ceiling to –0.3 dBFS
5. Save session as `{track_name}_master.als`
6. Activate AbletonOSC M4L device

---

## Outputs

| Artifact | Location | Format | Final Product? |
|----------|----------|--------|----------------|
| Master WAV | `output/master.wav` | 24-bit WAV stereo | YES — delivery file |
| Master info | `output/master_info.json` | JSON | Handoff reference |
| Report card | `output/report_card.md` | Markdown | Human review |
| Stage summary | `output/stage_summary.md` | Markdown | Human review |

---

## Output Schema

### `master_info.json`
```json
{
  "track_name": "apology",
  "final_wav": "/path/to/master.wav",
  "lufs_integrated": -8.4,
  "peak_dbfs": -0.3,
  "phi_normalized": true,
  "belt": "yellow",
  "grade": "B",
  "overall_score": 74,
  "promoted": false,
  "elapsed_s": 45.2
}
```

---

## LUFS Targets

| Delivery | Target LUFS | Headroom |
|----------|------------|---------|
| Club/DJ | –7 to –9 | –0.3 dBFS ceiling |
| Streaming | –14 | –1.0 dBFS ceiling |
| Mastered for iTunes | –16 | –1.0 dBFS ceiling |

---

## References

- Full mandate: `../../phase_04_mastering/mandate/MANDATE.md`
- Entry module: `engine/phase_four.py::run_phase_four()`
