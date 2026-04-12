# Phase 4: MASTERING — Workflow

> v6.0.0 — AbletonOSC mastering. Mastering chain via Ableton devices.
> **Time signature: 4/4 always** — `BEATS_PER_BAR = 4`. No odd meters.

Execution order for every render pass through the mastering phase.

**Entry:** `phase_four.py` → `run_phase_four(mixed_audio)` → Final WAV

## SOT Architecture

- Canonical runtime entrypoint: `forge.py`
- Canonical orchestrator: `tools/forge_runner.py`
- Stage workflow path: `forge.py` → `tools/forge_runner.py` → `engine/phase_four.py::run_phase_four()`

---

## Execution Order

```
Phase 4: MASTERING (AbletonOSC)
│
├── Setup
│   ├── 1. Connect to Ableton Live (OSC ports 11000/11001)
│   │       └── bridge.connect()
│   ├── 2. Create mastering session
│   │       └── Import Phase 3 mixed stereo WAV as audio track
│   └── 3. Set tempo (match original BPM)
│
├── Mastering Chain (Ableton master track devices)
│   ├── 4. EQ Eight → HPF@45Hz, shelf, parametric (all 0.0 in V4b)
│   ├── 5. Multiband Dynamics → 3-band (120Hz / 4kHz)
│   ├── 6. Glue Compressor → bus glue
│   ├── 7. Utility → stereo width (0.5)
│   └── 8. Limiter → ceiling -0.3 dBTP, target LUFS -10
│
├── Bounce
│   ├── 9. Export mastered stereo WAV (24-bit, 48kHz)
│   │       └── bridge.export_audio()
│   └── 10. Save mastering session .als
│           └── bridge.save_project()
│
├── Quality Gates (Python analysis on bounced WAV)
│   ├── 11. QA validator: 6 gates (peak, DC, silence, correlation, crest, noise)
│   └── 12. Dojo gate: LUFS [-12, -6], True Peak [-1.5, -0.1] dBTP
│
├── Phi Processing
│   ├── 13. normalize_phi_master() → phi-weighted normalization
│   └── 14. analyze_phi_coherence() → phi alignment score
│
└── Final Export
    ├── 15. apply_final_dither() → 24-bit dither
    ├── 16. embed_audio_watermark() → imperceptible watermark
    ├── 17. Write final 24-bit stereo WAV at 48kHz
    └── 18. Write master_report.json
```

---

## Dependency Graph

```
Phase 3 Output
    └── Mixed stereo WAV ──────────→ [2] Import into Ableton
                                     │
                              [4-8] Mastering chain
                              (EQ → Multiband → Glue → Width → Limiter)
                                     │
                              [9-10] Bounce + save session
                                     │
                              [11-12] Quality gates
                                     │
                              [13-14] Phi normalization + coherence
                                     │
                              [15-18] Dither → watermark → export
                                     │
                                     ▼
                              Final WAV (24-bit, 48kHz)
                              + master_report.json
                              + mastering session .als
```
