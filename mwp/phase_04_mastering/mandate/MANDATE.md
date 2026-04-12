# Phase 4: MASTERING — Mission Mandate

> v6.0.0 — AbletonOSC mastering. Mastering chain via Ableton devices.
> No numpy DSP mastering. The DAW IS the mastering engine.

> **Brain:** CRITIC — metering, loudness targets, final quality
> **Dojo Phase:** MASTER (Sprint 5) + RELEASE + REFLECT
> **Entry:** `phase_four.py` → `run_phase_four(mixed_audio)`
> **Input:** Mixed stereo WAV (from Phase 3 AbletonOSC bounce)
> **Output:** Final WAV (24-bit, 48kHz) + master report + QA validation

## SOT Architecture

- Canonical runtime entrypoint: `forge.py`
- Canonical orchestrator: `tools/forge_runner.py`
- Stage 4 execution path: `forge.py` → `tools/forge_runner.py` → `engine/phase_four.py::run_phase_four()`

---

## Mission Statement

Load Phase 3's mixed stereo into a **mastering session in Ableton Live** and
apply the mastering chain through AbletonOSC-controlled Ableton devices:
EQ Eight, Multiband Dynamics, Glue Compressor, Utility, and Limiter.

Then validate against quality gates, verify LUFS/true peak targets,
apply phi normalization, dither, watermark, and export the final 24-bit WAV.

**Ableton Live IS the mastering engine.** DUBFORGE controls it via AbletonOSC.

> "Mastering is the last creative decision and the first technical guarantee."

---

## Mastering Chain (Ableton Master Track Devices)

Devices inserted on Ableton's master track, controlled via AbletonOSC:

| Step | Ableton Device | Purpose | Key Parameters |
|------|----------------|---------|----------------|
| 1 | **EQ Eight** | Shape frequency balance | HPF@45Hz, low shelf, high shelf, parametric mid |
| 2 | **Multiband Dynamics** | Per-band dynamics control | 3-band: 120Hz / 4kHz crossovers, per-band ratio/threshold |
| 3 | **Glue Compressor** | Stereo bus glue | Gentle envelope, attack/release tuned per DNA |
| 4 | **Utility** | Stereo width + mono check | Mid/side processing, width from DNA |
| 5 | **Limiter** | Final ceiling enforcement | Ceiling -0.3 dBTP, LUFS targeting (-10 dubstep) |

---

## Dubstep Master Settings

Target settings (controlled via AbletonOSC device params):

| Parameter | Value | Notes |
|-----------|-------|-------|
| target_lufs | -10 | Competitive dubstep loudness |
| ceiling_db | -0.3 | Headroom for codec encoding |
| EQ | All bands 0.0 | V4b: no mastering EQ boosts (Phase 3 handled it) |
| Multiband ratio | ~3.5 | Targeting DR ≈ 18dB |
| Stereo width | 0.5 | Narrowed from 1.0 (reference analysis) |

---

## AbletonOSC Commands Used

| Command | Purpose | Step |
|---------|---------|------|
| `bridge.connect()` | Establish OSC connection | Setup |
| `bridge.create_audio_track("master_input")` | Import mixed stereo | Setup |
| `bridge.import_audio(track, wav_path)` | Load Phase 3 mix | Setup |
| `bridge.load_device("master", "EQ Eight")` | Insert mastering EQ | 1 |
| `bridge.load_device("master", "Multiband Dynamics")` | Insert multiband | 2 |
| `bridge.load_device("master", "Glue Compressor")` | Insert bus comp | 3 |
| `bridge.load_device("master", "Utility")` | Insert stereo control | 4 |
| `bridge.load_device("master", "Limiter")` | Insert limiter | 5 |
| `bridge.set_device_param(...)` | Configure all device params | 1-5 |
| `bridge.export_audio(path)` | Bounce final master | Export |
| `bridge.save_project(path)` | Save mastering session | Export |

---

## Post-Master Processing (Python Analysis)

After Ableton bounces the master, Python handles validation and metadata:

| Step | Function | Purpose |
|------|----------|---------|
| 1 | `qa_validator.validate_output()` | 6 QA gates |
| 2 | Measure LUFS / true peak | Dojo quality gate verification |
| 3 | `normalize_phi_master()` | Phi-weighted normalization (optional post-adjustment) |
| 4 | `analyze_phi_coherence()` | Phi alignment score |
| 5 | `apply_final_dither()` | Dither for bit-depth reduction |
| 6 | `embed_audio_watermark()` | Imperceptible watermark |
| 7 | Write final 24-bit WAV | Export |
| 8 | Write master_report.json | Audit |

---

## QA Validator — 6 Gates

`qa_validator.validate_render(left, right, sr, has_vocals)`:

| Gate | Condition | Threshold |
|------|-----------|-----------|
| **Peak level** | Must be < 1.0 (0 dBFS) | Prevents clipping |
| **DC offset** | Must be < 0.01 | No DC bias |
| **Silence ratio** | Must be < 50% | Not mostly silence |
| **Stereo correlation** | Must be > -0.5 | Not phase-inverted |
| **Crest factor** | Must be > 3 dB | Not over-compressed |
| **Noise floor** | Must be < -40 dB | Clean noise floor |

---

## Dojo Quality Gates

| Metric | Min | Max |
|--------|-----|-----|
| LUFS | -12 | -6 |
| True Peak | -1.5 dBTP | -0.1 dBTP |

---

## Module Dependencies

### AbletonOSC (primary)

| Module | Purpose |
|--------|---------|
| `ableton_bridge.py` | ALL device insertion, parameter control, export |

### Post-master analysis (Python)

| Module | Purpose |
|--------|---------|
| `qa_validator.py` | 6-gate quality validation |
| `normalizer.py` | Phi-weighted normalization |
| `phi_analyzer.py` | Phi coherence scoring |
| `dither.py` | Noise-shaped 24-bit dither |
| `watermark.py` | Imperceptible audio watermark |

### NOT called (replaced by Ableton devices)

| Module | Status |
|--------|--------|
| `mastering_chain.py` | Replaced by Ableton EQ Eight + Multiband Dynamics + Limiter |
| `dsp_core.py` | No numpy DSP — Ableton handles multiband, soft clip, limiting |
| `turboquant.py` | Not needed — Ableton handles compression |
| `auto_master.py` | Supplementary analysis only, not applied |
| `stage_integrations.py` | Mastering wrappers not needed — direct Ableton control |

---

## Output Contract

| Artifact | Location |
|----------|----------|
| Final WAV | `output/{song_name}_master.wav` (24-bit, 48kHz) |
| Mastering session | `output/{song_name}_master.als` (Ableton project, saved for recall) |
| Master report | `audit/08_MASTER/master_report.json` |
| QA validation | `audit/08_MASTER/qa_report.json` |
| Phi coherence | `audit/08_MASTER/phi_score.json` |
