# DUBFORGE Vocal Research Report
## Ableton, Producer Dojo, Subtronics — Vocal Workflows, Sound Design, Effects Chains, Mixing & Mastering
## + Text-to-Singing App Survey

*Generated 2026-08-22 for DUBFORGE integration planning*

---

## Table of Contents
1. [Ableton Live — Vocal Handling & Effects](#1-ableton-live--vocal-handling--effects)
2. [Producer Dojo — Vocal Production Philosophy](#2-producer-dojo--vocal-production-philosophy)
3. [Subtronics — Vocal Processing & Sound Design](#3-subtronics--vocal-processing--sound-design)
4. [Text-to-Singing Apps & AI Vocal Synthesis](#4-text-to-singing-apps--ai-vocal-synthesis)
5. [Comparative Effects Chain Reference](#5-comparative-effects-chain-reference)
6. [Integration Recommendations for DUBFORGE](#6-integration-recommendations-for-dubforge)

---

## 1. Ableton Live — Vocal Handling & Effects

### 1.1 Native Vocal Tools

**Auto Shift** (Live 12+) — Real-time pitch correction built into Ableton:
- **Quantizer Mode**: Snaps pitch to nearest note in selected scale. Correction amount 0-100%. Faster correction = more robotic/T-Pain effect; slower = natural.
- **MIDI Input Mode**: Pitch locks to notes from external MIDI source — enables creative vocoding-style harmony.
- **Formant Shift**: Adjusts formant independently of pitch (-24 to +24 semitones). Shift up = chipmunk; shift down = deep/demonic. Critical for dubstep vocal design.
- **Vibrato Controls**: Rate, amount, and onset delay for natural vibrato simulation.
- **LFO Section**: Modulates pitch for wobble/warble effects.

**Vocoder** (instrument rack):
- Carrier + modulator architecture.
- Use synth pad as carrier, vocal as modulator = classic robot vocal.
- Band count affects intelligibility (more bands = clearer speech).
- Essential for dubstep "robot voice" textures.

### 1.2 Vocal Effects Chain (Ableton Native)

**Standard Vocal Chain (Clean):**
```
1. EQ Eight (HPF at 80Hz, cut mud 200-400Hz, presence boost 3-5kHz, air 10-12kHz)
2. Compressor (ratio 3:1, threshold -18dB, attack 10ms, release 100ms)
3. Auto Shift (subtle pitch correction, scale-locked)
4. Saturator (warm drive, soft clip mode, low amount)
5. Delay (ping-pong, 1/8 note, low feedback, filtered)
6. Reverb (plate, short decay 1.2s, pre-delay 30ms)
```

**Dubstep Vocal Chain (Aggressive):**
```
1. EQ Eight (aggressive HPF at 120Hz, narrow cuts for resonance)
2. Compressor (ratio 8:1, fast attack 1ms, hard knee — heavy squash)
3. Auto Shift (full correction, chromatic, fast speed — robotic)
4. Auto Filter (Vowel mode — sweeps through vowel-like formants)
5. Saturator (hard curve, high drive for grit)
6. Corpus (metallic resonance body, adds alien/mechanical texture)
7. Beat Repeat (glitch repeats on vocals, mixed probability)
8. Echo (dotted 1/8, high feedback with filter, stereo width)
9. Utility (mono below 200Hz, width control)
```

### 1.3 Key Ableton Vocal Techniques

| Technique | Ableton Tool | Use Case |
|-----------|-------------|----------|
| Pitch correction | Auto Shift | Tuning, robotic vocal |
| Formant shifting | Auto Shift (Formant knob) | Gender/character change |
| Vocal chops | Simpler (Slice mode) | Rhythmic vocal hits |
| Sidechain ducking | Compressor (sidechain input) | Make vocals cut through bass |
| Vowel filtering | Auto Filter (Vowel type) | EDM vocal sweeps |
| Glitch repeats | Beat Repeat | Stuttering vocal effects |
| Harmonic stacking | MIDI effect rack + pitch | Vocal harmonies from one take |
| Granular stretch | Texture mode in Simpler | Ambient vocal pads |
| Frequency splitting | Audio Effect Rack (3-band) | Process lows/mids/highs independently |

### 1.4 Mixing Vocals in Ableton

- **Gain Staging**: Clip gain to normalize before effects. Target -18dBFS average levels into plugins.
- **De-essing**: Use EQ Eight with dynamic band on 5-8kHz range, or Multiband Dynamics targeting sibilance.
- **Parallel Compression**: Audio Effect Rack with dry + heavily compressed wet path. Blend with chain volume.
- **Bus Processing**: Group all vocal tracks, apply glue compressor on bus, then send to master.
- **Sidechain Pattern**: Route kick/snare to compressor sidechain on vocal bus for rhythmic pumping.
- **Automation**: Automate Utility volume for phrase-level dynamics rather than clip gain.

### 1.5 Mastering Considerations for Vocals

- **EQ Eight** final stage: gentle shelf boost at 10kHz+ for air, HPF at 30Hz.
- **Multiband Dynamics**: Tame 2-4kHz harshness band, compress lows separately.
- **Limiter**: Ceiling at -1.0dBTP, target -14 LUFS for streaming.
- **Glue Compressor**: On master bus, ratio 2:1, slow attack, auto release — cohesion.

---

## 2. Producer Dojo — Vocal Production Philosophy

### 2.1 Overview

Producer Dojo (founded by **ill.Gates** / Dylan Forbes) is a music production education platform built around a martial-arts-inspired "belt system" progression. Their approach to vocals in electronic/bass music emphasizes:

- **Modular thinking**: Vocals treated as one layer in a modular production framework
- **The Grid System**: Arranging vocal chops on a rhythmic grid for maximum impact
- **Sound Design First**: Transform vocals into unrecognizable sound design elements before mixing

### 2.2 Producer Dojo Vocal Workflow

**Phase 1 — Source Collection:**
- Record raw vocals (even phone recordings work)
- Harvest acapellas from stems/sample packs
- Use text-to-speech/singing as starting material
- Layer multiple vocal takes for texture

**Phase 2 — Sound Design Processing:**
- **Granular synthesis** on vocals: load into Granulator II (Max for Live) or Ableton Simpler Texture mode
- **Formant shifting** extreme ranges: +12 to -12 semitones for alien textures
- **Spectral processing**: Freeze and stretch using Paulstretch-type algorithms
- **Resampling chain**: Process → bounce → process again → bounce. Each pass adds character.
- **Vocoder layers**: Use vocal as modulator against bass synths for "talking bass"

**Phase 3 — Arrangement (The ill.Gates Method):**
- **Call and Response**: Vocal phrase answered by bass hit or synth stab
- **The "Money Shot"**: Key vocal hook placed at drop for maximum impact
- **Tension Building**: Vocal chops pitched up during risers, reversed in breakdowns
- **Sparse Drops**: Let 1-2 word vocal chops hit hard in gaps between bass

**Phase 4 — Mixing (Producer Dojo Standards):**
- Vocals sit ON TOP of the mix, never buried
- Heavy sidechain compression from kick to ALL elements (including vocals) for pumping
- Parallel distortion for vocal presence: Trash 2 or Ableton Saturator on send
- High-pass everything below 100Hz on vocal tracks
- Automate volume per phrase, not per word

### 2.3 Key Producer Dojo Principles for Vocal Production

1. **"If it sounds cool, it IS cool"** — No rules about vocal processing purity
2. **Resampling is king** — Process vocals, bounce, process again
3. **Less is more in the drop** — 1-2 word chops > full vocal phrases
4. **Layer for width** — Duplicate vocal, detune ±5 cents, pan L/R
5. **Contrast is everything** — Clean vocal in breakdown, destroyed vocal in drop
6. **The "20% rule"** — Vocals should occupy ~20% of the frequency real estate

---

## 3. Subtronics — Vocal Processing & Sound Design

### 3.1 Artist Profile

**Subtronics** (Jesse Kardon) is a leading figure in riddim/dubstep known for mechanical, processed vocal textures. His production style features:
- Heavy vocal manipulation into bass design elements
- Robotic/mechanical vocal chops
- Formant-shifted one-shots as rhythmic elements
- "Cyclops Army" signature aggressive riddim sound

### 3.2 Subtronics Vocal Processing Chain (Reconstructed)

Based on production breakdowns, livestreams, and community analysis:

**Signal Flow:**
```
Raw Vocal Recording / Sample
    ↓
[1] Pitch Correction (Melodyne or Auto-Tune, hard correction)
    ↓
[2] Formant Shift (-5 to -12 semitones for deep/robotic character)
    ↓
[3] Vocoder (synth carrier = detuned saw waves, 20+ bands)
    ↓
[4] Distortion/Saturation (Trash 2 or SoundToys Decapitator, heavy drive)
    ↓
[5] Ring Modulation (metallic overtones, tuned to track key)
    ↓
[6] Multiband Compression (OTT or similar, extreme settings)
    ↓
[7] Chorus/Flanger (subtle width, stereo image)
    ↓
[8] EQ (surgical cuts, presence boost 2-5kHz)
    ↓
[9] Limiter (brick-wall, loud and proud)
```

### 3.3 Signature Subtronics Vocal Techniques

**1. "Robot Voice" Method:**
- Record speech → Auto-Tune chromatic hard correction → Vocoder with saw carrier → OTT multiband compression → Heavy saturation
- Result: Mechanical, artificial voice that sits in the bass/midrange

**2. "Vocal Bass" Technique:**
- Import vocal into Serum 2 as wavetable (drag audio into oscillator)
- Apply FM synthesis on top of the vocal wavetable
- LFO modulate wavetable position for evolving vocal-bass hybrid
- Add formant filter manipulation in Serum's filter section

**3. Vocal Chops as Percussion:**
- Slice vocals in DAW → Pick single phonemes ("ah", "eh", "oh")
- Layer with transient shaper (attack boost)
- Process through bit crusher (8-12 bit reduction)
- Trigger on snare hits or as fills between bass notes

**4. The "Cyclops" Vocal Stack:**
- 3 layers: Original (center), pitched +5st (left), pitched -5st (right)
- All three through same distortion chain
- Sum to mono below 200Hz
- Result: Wide, aggressive, alien vocal texture

### 3.4 Subtronics Mixing Approach for Vocals

- **Vocals rarely clean** — always at least distortion + compression
- **Frequency carving**: Automate EQ to make space for bass during drops, full-range in breakdowns
- **Dynamic sidechain**: Vocals duck to bass/sub, but NOT to kick (unusual approach)
- **Parallel processing**: Always has a "dry" blend path, even if only 5-10% — retains intelligibility
- **Bus saturation**: All vocal elements hit a single bus with Decapitator or similar analog emulation
- **Reference against bass**: Checks vocal presence against bass elements, not against silence

---

## 4. Text-to-Singing Apps & AI Vocal Synthesis

### 4.1 Technology Overview

Singing voice synthesis has evolved from concatenative synthesis (splicing recorded phonemes) to AI/deep-learning models that generate natural-sounding vocals from text and melody input.

**Key Technologies:**
- **Concatenative synthesis**: Splices recorded vocal fragments (diphones/polyphones). Used in VOCALOID 1-5. Requires large sample libraries per voice.
- **Parametric synthesis**: Models vocal tract mathematically. Less natural but more flexible.
- **Neural/AI synthesis**: Deep learning models trained on singing data. Produces the most natural results. Used in VOCALOID:AI (V6), Synthesizer V, ACE Studio, Diff-SVC, SO-VITS-SVC.

### 4.2 Commercial Text-to-Singing Applications

| App | Technology | Price | Languages | DAW Integration | Quality |
|-----|-----------|-------|-----------|----------------|---------|
| **VOCALOID 6** | Concatenative + AI (Vocaloid:AI) | $225+ | JA, EN, ZH, KO, ES, CA | VST/AU | Professional |
| **Synthesizer V** (Dreamtonics) | AI/DNN | $89 (editor) + voice DBs | JA, EN, ZH, ES, FR | VST/AU, standalone | Excellent |
| **ACE Studio** | AI neural | Free tier / $10-20/mo | EN, ZH, JA | Standalone (audio export) | Very good |
| **CeVIO AI** | AI/HMM hybrid | $80+ | JA, EN | Standalone (ReWire) | Very good |
| **Piapro Studio** (Crypton) | Proprietary AI | Bundled with voices | JA, EN | VST | Good |
| **UTAU / OpenUTAU** | Concatenative (free) | Free / Open source | Any (user-created) | Standalone | Variable |
| **Diff-SVC** | Diffusion model | Free / Open source | Any | CLI/API | Excellent |
| **SO-VITS-SVC** | VITS + SoftVC | Free / Open source | Any | CLI/API | Excellent |
| **Suno AI** | Generative AI (full song) | Free tier / $10-30/mo | EN + others | Web only | Good |
| **Udio** | Generative AI (full song) | Free tier / $10-30/mo | EN + others | Web only | Good |

### 4.3 Detailed App Profiles

#### VOCALOID 6 (Yamaha)
- **Architecture**: Score editor (piano roll) → singer library (sampled phonemes at multiple pitches) → synthesis engine (frequency-domain concatenation with pitch/timbre transforms, inverse FFT)
- **How it works**: User enters notes + lyrics in piano roll. System converts lyrics to phonemes via pronunciation dictionary. Engine selects samples, adjusts pitch, aligns timing (vowel onset = note-on position), interpolates spectral envelopes for sustained vowels, applies vibrato and articulation.
- **Japanese**: 500 diphones per pitch range. **English**: 2,500 diphones per pitch range (more closed syllables).
- **Vocaloid:AI** (V6 feature): Can import user singing audio and recreate it with AI voices.
- **DAW workflow**: Runs as VSTi, sends Vocaloid MIDI directly to synthesis engine bypassing score editor.
- **Limitations**: Can't replicate hoarse/shouted vocals. Best for clean singing.

#### Synthesizer V (Dreamtonics)
- **Engine**: Deep neural network (DNN) based synthesis.
- **Key features**: Cross-language voice synthesis (Japanese voice can sing English), vocal modes (power, soft, belt), AI retakes (generates variations automatically), tone shift, breath control.
- **VST3/AU plugin**: Works directly in Ableton, FL Studio, Logic, etc.
- **Voice quality**: Often cited as the most natural-sounding commercial singing synthesizer.
- **Voice databases**: ~$80-90 each. Popular: Eleanor Forte (EN), Solaria (EN), Mai (JA), Kevin (EN male).
- **Tempo/key sync**: Follows DAW tempo and can output MIDI for further processing.

#### ACE Studio
- **AI-powered**: Neural synthesis, no concatenation.
- **Free tier**: Limited renders per day.
- **Strengths**: Very natural vibrato, breath sounds, vocal fry. Emotional expression controls.
- **Export**: Renders audio files (WAV/FLAC) for import into DAW.

#### UTAU / OpenUTAU
- **Free and open-source** concatenative singing synthesizer.
- **User-created voicebanks**: Anyone can record and package a voice.
- **OpenUTAU**: Modern rewrite with better UI, plugin support, NNSVS/ENUNU neural rendering.
- **Community**: Tens of thousands of free voicebanks available.
- **Best for**: Experimental/lo-fi vocal textures, custom character voices.

#### Diff-SVC / SO-VITS-SVC (Open Source AI Voice Cloning)
- **Diff-SVC**: Diffusion-based singing voice conversion. Train on ~30 min of target singer's audio.
- **SO-VITS-SVC**: SoftVC content encoder + VITS decoder. Similar training requirements.
- **Workflow**: Record yourself singing → model converts to target voice in real-time or offline.
- **Quality**: Can produce near-indistinguishable vocals from the training source.
- **Legal/ethical note**: Only use on voices you have rights to. Do not clone without consent.
- **Dubstep use case**: Train on your own robotic vocal processing → create an "instrument" from your voice.

#### Suno AI / Udio (Generative)
- **Full song generation**: Enter text prompt + optional lyrics → generates complete song with vocals.
- **Not fine-grained**: Limited control over individual notes/timing.
- **Best for**: Quick reference tracks, inspiration, scratch vocals.
- **Dubstep-relevant**: Can generate vocal hooks/phrases to then resample and process.

### 4.4 AI Vocal Synthesis Workflow for DUBFORGE

**Recommended Pipeline:**
```
Text/Lyrics Input
    ↓
Synthesizer V (VST3 in Ableton) — Generate singing vocal
    ↓
Export stems (dry vocal)
    ↓
DUBFORGE effects chain (per-channel FX from _ROLE_FX_CHAIN)
    ↓
Optional: SO-VITS-SVC voice conversion for character matching
    ↓
Final vocal sits in Ableton project alongside generated tracks
```

---

## 5. Comparative Effects Chain Reference

### 5.1 Vocal Effects Chains Side-by-Side

| Stage | Ableton (Clean) | Producer Dojo (Bass Music) | Subtronics (Riddim) |
|-------|-----------------|---------------------------|---------------------|
| **1. Prep** | Gain staging | Gain staging + noise gate | Gain staging |
| **2. Pitch** | Auto Shift (subtle) | Melodyne (creative) | Auto-Tune (hard) |
| **3. EQ** | Surgical cleanup | Aggressive HPF + cuts | Surgical + presence |
| **4. Compression** | 3:1 gentle | 6:1 + parallel smash | 8:1+ OTT multiband |
| **5. Character** | Light Saturator | Granular + Vocoder layers | Formant shift + vocoder |
| **6. Distortion** | Warm drive (optional) | Trash 2 (heavy) | Decapitator (extreme) |
| **7. Modulation** | Chorus-Ensemble | Flanger + phaser | Ring mod + flanger |
| **8. Space** | Plate reverb + delay | Short room + filtered delay | Minimal (dry in drops) |
| **9. Bus** | Glue compressor | Sidechain + bus sat | Bus sat + limiter |
| **10. Master** | Multiband + limiter | Clip + limiter (loud!) | OTT + clip + limiter |

### 5.2 Common Plugins Across All Three

| Category | Common Choices |
|----------|---------------|
| **Pitch** | Auto-Tune Pro, Melodyne, Ableton Auto Shift |
| **Compression** | OTT (Xfer), Pro-C2 (FabFilter), Ableton Compressor |
| **Saturation** | Decapitator (SoundToys), Trash 2 (iZotope), Ableton Saturator |
| **EQ** | Pro-Q3 (FabFilter), Ableton EQ Eight |
| **Vocoder** | TAL-Vocoder, Ableton Vocoder, iZotope VocalSynth |
| **Multiband** | OTT, Ableton Multiband Dynamics, Pro-MB |
| **Reverb** | Valhalla VintageVerb, Ableton Reverb, FabFilter Pro-R |
| **Delay** | Valhalla Delay, EchoBoy (SoundToys), Ableton Echo |
| **Formant** | Soundtoys Little AlterBoy, MeldaProduction MAutoPitch |

---

## 6. Integration Recommendations for DUBFORGE

### 6.1 Immediate Implementation (make_template.py)

1. **Add vocal channel type** to `_ROLE_FX_CHAIN`:
   ```python
   "vocal_lead": ["EQ Eight", "Compressor", "Auto Filter", "Saturator", "Utility"],
   "vocal_chop": ["EQ Eight", "Compressor", "Saturator", "Beat Repeat", "Utility"],
   "vocal_fx": ["Auto Filter", "Corpus", "Saturator", "Echo", "Utility"],
   ```

2. **Add vocal preset recipes** to `_ROLE_PRESET_MAP` in serum2_preset.py:
   - `vocal_formant`: Serum 2 with wavetable loaded from vocal sample
   - `vocal_pad`: Granular-style sustained vocal texture
   - `talking_bass`: Vocoder-processed bass with formant filter

3. **Add vocal bus** to als_generator.py:
   - Dedicated return track with sidechain from kick
   - Parallel compression send
   - Bus saturation

### 6.2 Future Integration — AI Vocals

1. **Synthesizer V VST3 integration**: Add to `_VST3_REGISTRY` in als_generator.py
2. **Text-to-singing pipeline**: Config YAML field `vocal_lyrics` → generate via API
3. **Voice model training**: SO-VITS-SVC pipeline for custom DUBFORGE voice character
4. **Preset per aesthetic**: Robotic, clean, ethereal, aggressive vocal processing types

### 6.3 Vocal Production Workflow for DUBFORGE Tracks

```
DUBFORGE Track Generation Workflow (with vocals):

1. Generate track YAML config (key, BPM, structure)
2. Add vocal_lyrics field to config
3. Generate ALS project (make_template.py)
4. AI generates vocal audio (Synthesizer V or Suno)
5. Vocal audio imported to vocal_lead/vocal_chop channels
6. Per-channel FX chains auto-applied from _ROLE_FX_CHAIN
7. Sidechain routing auto-configured
8. Export stems → master
```

---

## Sources & Notes

- **Ableton Audio Effects Reference** (Ch. 28, Live 12 Manual): Auto Shift, Auto Filter (Vowel mode), Compressor sidechain, Corpus, Beat Repeat, Echo, Saturator
- **Wikipedia — Vocaloid**: System architecture, concatenative synthesis engine, singer library (diphone counts), pitch conversion, timing adjustment, spectral envelope interpolation, Vocaloid 6 AI features
- **Wikipedia — Music Technology (Singing Voice Synthesis)**: VODER/VOCODER history, Bell Labs singing computer (1962), CHANT at IRCAM, concatenation via MIDI, post-2010 AI synthesis advances
- **Producer Dojo (ill.Gates)**: Belt system curriculum, resampling philosophy, modular production framework
- **Subtronics production analysis**: Community breakdowns, livestream observations, riddim/neuro production conventions
- **Text-to-singing landscape**: VOCALOID, Synthesizer V, ACE Studio, CeVIO, UTAU/OpenUTAU, Diff-SVC, SO-VITS-SVC, Suno, Udio
