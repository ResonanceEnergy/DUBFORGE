#!/usr/bin/env python3
"""Run theme engine against 'Can You See The Apology That Never Came'."""

from engine.mood_engine import (
    resolve_mood, get_mood_suggestion, blend_moods, mood_suggestion_text
)

title = "Can You See The Apology That Never Came"
print("=" * 60)
print(f'  THEME ENGINE — "{title}"')
print("=" * 60)

vibes = ["melancholy", "dark", "epic", "emotional", "sad", "heavy", "dreamy"]
print()
print("── INDIVIDUAL MOOD READS ──")
for v in vibes:
    s = get_mood_suggestion(v)
    print(f"\n  [{v.upper()}]")
    print(f"    Resolves to: {s.mood}")
    print(f"    Key: {s.key} {s.scale} | BPM: {s.bpm} | Base: {s.base_freq}Hz")
    print(f"    Energy: {s.energy:.0%} | Darkness: {s.darkness:.0%}")
    print(f"    Reverb: {s.reverb:.0%} | Distortion: {s.distortion:.0%}")
    mods = ", ".join(s.modules[:5])
    tags = ", ".join(s.tags)
    print(f"    Modules: {mods}")
    print(f"    Tags: {tags}")

print()
print("── PRIMARY BLEND: MELANCHOLY × EPIC ──")
b1 = blend_moods("melancholy", "epic", 0.45)
print(mood_suggestion_text(b1))

print()
print("── SECONDARY BLEND: DARK × DREAMY ──")
b2 = blend_moods("dark", "dreamy", 0.35)
print(mood_suggestion_text(b2))

print()
print("── FINAL BLEND: MELANCHOLY × DARK ──")
b3 = blend_moods("melancholy", "dark", 0.4)
print(mood_suggestion_text(b3))

print()
print("── THEME SYNTHESIS ──")
print(f'  Title: "{title}"')
print("  Core Emotion: Grief that was never resolved. Yearning.")
print("  Sonic Identity: Dark melodic dubstep — haunting pads,")
print("    aching leads, thunderous drops that feel like rage")
print("    against silence.")
print('  Vocal Concept: Whispered/chopped vocal fragments —')
print('    "can you see" "apology" "never came" — processed,')
print("    never clean, because the apology was never clean.")
print()
print("  RECOMMENDED CONFIG:")
print("    Key: D minor (the saddest key)")
print("    BPM: 140 (heavy halftime)")
print("    Template: EMOTIVE arrangement")
print("    Mood Blend: melancholy 55% + epic 45%")
print("    Darkness: ~78% | Energy: ~55% | Reverb: ~75%")
print("    Distortion: 15% (clean-ish, pain not violence)")
print()
print("  SECTION ENERGY MAP:")
print("    Intro     — 10% — Drone + reversed pad + whisper")
print("    Verse 1   — 30% — Pluck arp + sub + chopped vocal")
print('    Build 1   — 55% — Riser + snare roll + "can you see"')
print("    Drop 1    — 90% — Full halftime + melodic bass + screech lead")
print('    Break     — 20% — Piano/pad + "apology that never came"')
print("    Build 2   — 65% — Darker riser + stutter vocal")
print("    Drop 2    —100% — Everything + distorted bass + impact")
print("    Outro     — 10% — Pad decay + final whisper")
print()
print("  MODULE SELECTION:")
modules = [
    "pad_synth (dark_pad, lush_pad)",
    "lead_synth (screech — the anguish, pluck — the memory)",
    "bass_oneshot (sub, reese, wobble, neuro)",
    "fm_synth (metallic impacts, the sharp edges of betrayal)",
    "impact_hit (sub_boom at drops, cinematic_hit, reverse_hit)",
    "noise_generator (white noise risers — the static of waiting)",
    "vocal_chop (formant fragments — the unspoken words)",
    "drone_synth (sustained tension underneath)",
    "supersaw (chord stabs — emotional release at drops)",
    "glitch_engine (stutter fills — time distorting with grief)",
    "riser_synth (build tension before each drop)",
]
for m in modules:
    print(f"    -> {m}")
print()
print("=" * 60)
print("  THEME ENGINE COMPLETE")
print("=" * 60)
