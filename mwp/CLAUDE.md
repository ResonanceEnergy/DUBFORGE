# DUBFORGE — Layer 0 Identity & Routing
> Read this first. Always. Then read `CONTEXT.md` for stage routing.

---

## Identity

**DUBFORGE** is an AbletonOSC-native 4-phase production pipeline that takes a song
idea and produces a mastered dubstep track. Ableton Live IS the engine — all
arrangement, mixing, and mastering flows through AbletonOSC. No numpy DSP fallback.

**Aesthetic Authority:**
- **ill.Gates / Producer Dojo** — methodology, belt system, 128 Rack, The Approach
- **Subtronics** — sound design, drops, crowd energy, arrangement drama
- **Dan Winter** — phi ratio (φ=1.618...), fractal timing, Planck×phi mathematics

**Constraints:**
- Python 3.12+, macOS 15 Sequoia, M4 Pro (Metal/MPS — not CUDA)
- Ableton Live 12 Suite required to be OPEN before phases 2–4
- AbletonOSC M4L device must be active on Master track (send:11000, recv:11001)
- osascript used for export trigger (Cmd+Shift+R) — AbletonOSC cannot trigger export
- Time signature: 4/4 ALWAYS. BEATS_PER_BAR = 4.

**Entrypoint:**
- Canonical project entrypoint is `forge.py`
- Launch/UI: `python forge.py --launch --ui-only`
- Full run from CLI: `python forge.py --song "TRACK NAME"`

---

## Where To Go Next

| Task | Go to |
|------|-------|
| Run the pipeline | `CONTEXT.md` → stage index |
| Understand phase rules | `_config/ableton_rules.md` |
| Check aesthetic targets | `_config/voice.md` |
| See phi/timing constants | `_config/phi_constants.md` |
| Naming + file conventions | `_config/conventions.md` |
| Cross-stage samples | `shared/sample_pack_index.md` |
| Stage 1 contract | `stages/01-generation/CONTEXT.md` |
| Stage 2 contract | `stages/02-arrangement/CONTEXT.md` |
| Stage 3 contract | `stages/03-mixing/CONTEXT.md` |
| Stage 4 contract | `stages/04-mastering/CONTEXT.md` |
| Phase reference docs | `phase_01_generation/`, `phase_02_arrangement/`, etc. |

---

## Context Budget

| Layer | File | Token Budget | When to Load |
|-------|------|-------------|--------------|
| 0 | `CLAUDE.md` (this file) | ~400 | Always |
| 1 | `CONTEXT.md` | ~300 | Always |
| 2 | `stages/XX/CONTEXT.md` | ~400 | Active stage only |
| 3 | `_config/*.md` | ~200 each | When referenced by stage |
| 4 | `stages/XX/output/*.json` | varies | Active stage handoff only |

**Total per-stage budget: ~1,500–3,000 tokens max.**
Do not load phase_XX_*/mandate/ or phase_XX_*/playbook/ unless debugging.
