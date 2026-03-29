"""Quick V3 output verification."""
import os, json

wt = sorted(f for f in os.listdir("output/wavetables") if f.startswith("APOLOGY_V3_"))
pr = sorted(f for f in os.listdir("output/presets") if f.endswith((".fxp", ".fxb")))
st = sorted(f for f in os.listdir("output/stems") if f.startswith("apology_v3_"))

print("=== V3 OUTPUT VERIFICATION ===")
print(f"Wavetables: {len(wt)}")
for f in wt:
    print(f"  {f} ({os.path.getsize(os.path.join('output/wavetables', f)):,} bytes)")
print(f"Presets: {len(pr)}")
for f in pr:
    print(f"  {f} ({os.path.getsize(os.path.join('output/presets', f)):,} bytes)")
print(f"Stems: {len(st)}")
print(f"Mixdown: {os.path.exists('output/apology_never_came_v3.wav')}")
print(f"MIDI: {os.path.exists('output/midi/apology_never_came_v3.mid')}")
print(f"ALS: {os.path.exists('output/ableton/Apology_Never_Came_V3.als')}")
ok = len(wt) == 6 and len(pr) >= 9 and len(st) == 14
print(f"\n{'ALL PASS' if ok else 'ISSUES DETECTED'}")
