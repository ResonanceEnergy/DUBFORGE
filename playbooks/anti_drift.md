# DUBFORGE Anti-Drift Playbook

**Prevent scope creep, finish tracks, and ship.**

Synthesized from: Ayesha (aye5ha.substack.com), Music Scientists (musicscientists.substack.com), ill.Gates / Producer Dojo methodology, and DUBFORGE production experience.

---

## The Core Problem

> "Discovery velocity outpaces production output velocity." — Music Scientists

DUBFORGE has **168 engine modules**, **20 song templates**, and an infinite parameter space (phi ratios, Fibonacci structures, Serum 2 presets). That's power — and it's a drift trap. Every new module, every wavetable variant, every "what if I phi-ratio this too" is a context switch away from a finished track.

---

## 1. THE SINGLE-TRACK RULE

> "Narrowing the unit of expression shortens the distance between intention and completion." — Ayesha

- Work on **one track at a time**. Not a pack, not an EP — one track.
- Describe the track's vibe in **one sentence** before starting. If you can't, you're not ready.
- Write the sentence at the top of your `make_*.py` script as a comment.

```python
# VIBE: "Relentless industrial acid that builds tension for 7 minutes without adding elements."
```

---

## 2. THE 3-SESSION WALL

> "Max 3 sessions. If a track demands more, table it." — Ayesha

| Session | Purpose | Deliverable |
|---------|---------|-------------|
| **1** | Generation (Phase 1) — sounds, SongDNA, palette | Sound palette + MIDI |
| **2** | Arrangement + rough mix (Phase 2–3) | Full `.als` session |
| **3** | Mix polish + master (Phase 3–4) | Final WAV |

If it needs a 4th session, one of two things is true:
1. The idea isn't clear enough — rewrite the vibe sentence and start fresh.
2. You're polishing, not creating — export and move on.

---

## 3. SESSION EXIT QUESTIONS

Ask after **every** production session (stolen from Ayesha, adapted for DUBFORGE):

1. **Am I still excited about this track?** If no → table it. No guilt.
2. **Does the SongDNA still match the vibe sentence?** If it drifted → revert or restart.
3. **Did this session make the track better or worse?** A/B the bounces.
4. **Could I release this version right now?** If yes → you're done. Stop.

---

## 4. THE DECISIONS-PER-HOUR METRIC

> "The person who makes 50 edits in an hour will always beat the person who makes 5, even with a 'smarter' tool." — Music Scientists

Drift disguises itself as productivity. Signs you're drifting:

| Drift Signal | What's Actually Happening |
|---|---|
| Tweaking phi ratios for >15 min | Procrastinating on arrangement |
| Generating 10+ pattern variants | Avoiding commitment (Infinite Sketch Syndrome) |
| Adding a new engine module mid-track | Scope creep |
| Browsing presets/samples for >10 min | The Plugin Feed problem |
| Switching between `make_wild_ones` and `make_apology` | Context thrashing |

**The fix**: Generate → Edit (max 2 changes) → Commit (freeze/flatten to audio) → Move On.

---

## 5. THE CONTEXT SWITCH TAX

> "Momentum is the only metric that finishes tracks." — Music Scientists

Every time you leave the DAW or switch tasks, you pay:
- **Loss of momentum** — the "soul" of the session evaporates
- **Loss of recall** — which version? which parameter? which rationale?
- **Loss of automation** — you lose real-time tweaking flow

**DUBFORGE-specific rules:**
- Don't modify `engine/` modules during a track session. Engine work is a separate concern.
- Don't open the Gradio UIs (studio/analyzer/launchpad) while in a deep production session — analysis is revision, not creation.
- Don't `git commit` mid-session. Batch it at session end.
- Use `make track` (quick WAV) to hear results fast. Don't reach for `make song` (full pipeline) until Session 3.

---

## 6. THE FREEZE PROTOCOL

> "You cannot leave these patches live in a heavy project. Generate the texture, bounce it to audio, and move on." — Music Scientists

Once a sound or section works:
1. **Bounce** it to WAV inside the Ableton session.
2. **Freeze** the track — don't leave it as live DSP.
3. **Delete** the source chain if you're tempted to keep tweaking.

In DUBFORGE terms: once `forge.py` or `make_track.py` outputs a WAV — **listen to it, don't re-run it**. If the impulse is to change one parameter and regenerate, ask: "Am I making it better, or am I avoiding the next step?"

---

## 7. THE PLUGIN/MODULE AUDIT

> "Plugin hoarding is a workflow bug." — Music Scientists

**Weekly audit** (add to `make nightly` or run manually):
1. Which of the 168 engine modules did you actually use in the last track? Probably ~20.
2. Are you reaching for modules you haven't used before? That's exploration, not production.
3. **Module freeze**: For a given track, lock your module set after Session 1. No new modules in Sessions 2–3.

---

## 8. STOP AT COHERENCE

> "The track doesn't need further reinforcement. Adding or removing another element will clearly weaken the idea." — Ayesha

A track is done when:
- [x] You'd play it at peak-time without flinching
- [x] The vibe sentence still describes it accurately
- [x] You've lived with the mix for ≥24 hours
- [x] Every sonic element has a clear creative purpose
- [x] It sounds great with the limiter off (A/B test)
- [x] It felt "finished" at least one session ago

If you check 5 of 6 → **export final WAV and ship it**.

---

## 9. DUBFORGE-SPECIFIC ANTI-DRIFT GUARDS

### In Code
- Every `make_*.py` script starts with a `# VIBE:` one-liner and a `# SESSIONS: 1/3` counter.
- `forge.py` logs a session timestamp. If >3 sessions detected on same SongDNA, warn.
- `make track` (quick WAV) is the default. `make song` (full pipeline) is Session 3 only.

### In Workflow
- **Engine Fridays**: All module development, refactoring, new DSP work happens on Fridays only. Mon–Thu = production.
- **One active `make_*.py`**: Only one track script should be "in progress" at a time.
- **Version ceiling**: No more than 3 versions of a track script (v1, v2, v3). If you need v4, the idea needs to change, not the tweaks.

### In Git
- Feature branches for engine work. `main` stays production-ready.
- Track scripts get committed once at session end, not mid-session.
- If a PR touches >5 engine modules, it's probably drift. Split it.

---

## 10. THE ANTI-DRIFT CHECKLIST (Print This)

Before starting a session:
```
□ What track am I working on? (one name)
□ What's the vibe sentence?
□ What session number is this? (1, 2, or 3)
□ What is the ONE deliverable for this session?
```

Before ending a session:
```
□ Did I produce the deliverable?
□ Is the track better than when I started?
□ Am I done? (check the 6 coherence tests)
□ Bounce/export the current state
□ Commit and log
```

---

## Sources

- **Ayesha** — [The Discomfort of Finishing Music](https://aye5ha.substack.com/p/the-discomfort-of-finishing-music) (Jan 2026)
- **Ayesha** — [Narrowing the Unit of Expression](https://aye5ha.substack.com/p/narrowing-the-unit-of-expression) (Feb 2026)
- **Music Scientists** — [The Plugin Feed Is Loud](https://musicscientists.substack.com/p/the-plugin-feed-is-loud-heres-what) (Feb 2026)
- **Music Scientists** — [The Death of the $200 Preset Pack](https://musicscientists.substack.com/p/the-death-of-the-200-preset-pack) (Feb 2026)
- **Music Scientists** — [Live 12 Isn't ChatGPT-for-Beats](https://musicscientists.substack.com/p/live-12-isnt-chatgpt-for-beats-its) (Feb 2026)
- **ill.Gates / Producer Dojo** — The Approach, 14-Minute Hit, Belt System (codified in `engine/dojo.py`)
