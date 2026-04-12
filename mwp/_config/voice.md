# DUBFORGE — Voice & Aesthetic Rules
> Layer 3 stable config. Defines the aesthetic targets for every production decision.

---

## The Two Masters

### ill.Gates / Producer Dojo
- **Volume is the teacher** — use automation and volume rides over heavy compression
- **Mudpies** — every element must have a function. No decorative sounds.
- **The 14-Minute Hit** — drop should hit in first 32 bars. Energy curve is everything.
- **128 Drum Rack discipline** — all drums in one rack, zones mapped, no free clips
- **Separate creation from revision** — never mix while creating
- **Belt system** — White → Yellow → Orange → Green → Blue → Purple → Brown → Red
- **Stock devices first** — use Ableton built-ins before reaching for VSTs

### Subtronics
- **Insane but clean** — the wobble sits in the mix, never fights the kick
- **Double drops** — build 1 → drop 1 → break → build 2 → DROP 2 (harder/dirtier)
- **Frequency sculpting** — kick owns 50–80Hz, sub owns 40–60Hz, they take turns
- **Crowd excitement** — track must be playable to 1000+ people. Test on big imaginary speakers.
- **VIP energy** — evolution, not repetition. Each section must differ from the last.

---

## Tonal Targets

| Element | Target | Notes |
|---------|--------|-------|
| Sub bass | 40–60 Hz fundamental | 1 note at a time with kick |
| Kick | 50–80 Hz punch | Side-chain sub to kick |
| Mid bass / wobble | 80–300 Hz | Serum 2 Filter + LFO |
| Lead / screech | 1–4 kHz | Short attack, fast envelope |
| Pads | 200–800 Hz | Low cut at 200 Hz |
| Hats | 8–16 kHz | High shelf boost for air |
| Master LUFS | –7 to –9 LUFS | Streaming: –14 LUFS |

---

## Arrangement Archetypes

Use one per track. Defined in `phase_01_generation/` MANDATE.

| Archetype | Sections | Energy Shape |
|-----------|---------|-------------|
| `double_drop` | I–B1–D1–BR–B2–D2–O | 3/10 → 8/10 → 4/10 → 10/10 |
| `single_massive` | I–B1–B2–D–BR–D2–O | 2/10 → 6/10 → 10/10 flat |
| `halftime_crawl` | I–B–D–BR–D2–O | 1/10 → 9/10 step |
| `festival_banger` | I–B1–D1–BR–D2–O | 4/10 → 10/10 → 8/10 |
| `underground_dark` | I–B–D–BR–D–O | 5/10 plateau |

---

## Energy Curve Rules

1. Intro: 20–40% of full energy
2. Build: ramp +2% per bar minimum
3. Drop: 100% — every element on
4. Breakdown: 10–30% — space and silence
5. Build 2: faster ramp than Build 1
6. Drop 2: 100% + 10% extra (add a new element)
7. Outro: 40% → 0% over 16 bars

---

## Sound Design Targets (Serum 2)

| Stem | Wavetable Type | Filter | LFO |
|------|---------------|--------|-----|
| sub_bass | Sine + slight noise | Low pass, Cutoff=80% | Off |
| fm_growl | FM operator stack | Band pass, Q=0.7 | Rate synced, Depth=80% |
| wobble | Wavetable morph | Low pass, Res=60% | 1/2 bar |
| screech | Super saw + detune | High pass + phaser | Fast, 8th note |
| chord_f | Pad atk=80ms | Low pass + reverb | Slow, 4 bar |
| atmos | Granular texture | Band pass wide | Very slow, 8 bar |
