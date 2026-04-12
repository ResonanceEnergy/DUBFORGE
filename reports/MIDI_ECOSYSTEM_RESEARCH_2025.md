# MIDI Detection, Pattern Generation & Dubstep Production Research
## Deep Dive — July 2025

---

## 1. AUDIO-TO-MIDI DETECTION (Automatic Music Transcription)

### Tier 1: Production-Ready Tools

| Tool | Stars | What It Does | Best For DUBFORGE |
|------|-------|-------------|-------------------|
| **Spotify Basic Pitch** | 4.9k | Lightweight neural AMT, polyphonic, instrument-agnostic. Generates MIDI with pitch bends. Supports TF/CoreML/TFLite/ONNX. Has VST version (NeuralNote). `pip install basic-pitch` | **HIGH** — drop-in reference audio→MIDI. Could replace/augment our `reference_intake.py` melody extraction |
| **Demucs v4** (Meta) | 10k | Hybrid Transformer source separation. Separates drums, bass, vocals, other (+ experimental guitar/piano). SDR 9.0 dB on MUSDB HQ. `pip install demucs` | **HIGH** — pre-process reference tracks into stems before MIDI extraction. Bass stem → basic-pitch = clean bass MIDI |
| **CREPE** | 1.4k | Monophonic pitch tracker via deep CNN on raw waveform. Outputs (time, frequency, confidence). Viterbi smoothing. Multiple model sizes. | **MEDIUM** — great for isolated monophonic lines (sub-bass, lead melodies) after Demucs separation |
| **madmom** | 1.6k | Audio signal processing for MIR. Beat tracking (DBNBeatTracker), onset detection, tempo estimation, chord recognition, key detection. Pre-trained neural models. | **HIGH** — beat/downbeat tracking, onset detection, tempo estimation. Complements our librosa-based analysis |

### Tier 2: Research/Heavy Models

| Tool | Stars | What It Does | DUBFORGE Relevance |
|------|-------|-------------|-------------------|
| **ByteDance Piano Transcription** | 2k (archived) | High-res piano transcription with pedals. PyTorch CRNN. Built GiantMIDI-Piano dataset. | LOW — piano-specific |
| **Melodia** (Salamon) | 404'd | Was the classic melody extraction algorithm. Concepts live on in librosa's `pyin` | Already using pyin via librosa |

### Detection Pipeline for DUBFORGE (Recommended)
```
Reference Audio
    ├── Demucs → separate into drums, bass, vocals, other
    │   ├── bass stem → Basic Pitch → sub-bass MIDI
    │   ├── other stem → Basic Pitch → melody/chords MIDI
    │   └── drums stem → madmom onset detection → drum pattern
    ├── madmom → tempo, beats, downbeats, key
    └── librosa → spectral features, chroma, MFCCs (already in use)
```

---

## 2. MIDI UTILITY LIBRARIES

| Library | Stars | Purpose | Integration |
|---------|-------|---------|-------------|
| **pretty-midi** | 1k | MIDI read/write/manipulate. Estimate tempo, get chroma, shift notes, synthesize. `pip install pretty_midi` | Already usable — complement mido for analysis |
| **magenta/note-seq** | 237 | Google's NoteSequence format. Create from MIDI/abc/MusicXML. Extract melodies, drum tracks, chords. Convert to training tensors. | Research reference |
| **MusPy** | 509 | Toolkit for symbolic music generation. Dataset management, I/O (MIDI/MusicXML/ABC), common representations (pitch-based, event-based, piano-roll, note-based), evaluation metrics. | Good for benchmarking generated output quality |
| **Symusic** | — | Fast MIDI I/O in Rust with Python bindings. Used by MidiTok. | Consider for performance if mido is bottleneck |

---

## 3. MIDI TOKENIZATION & REPRESENTATIONS

### MidiTok (858 stars, actively maintained)
**The** standard for converting MIDI to token sequences for deep learning. Implements 10 tokenization schemes:

| Tokenization | Paper | Key Idea |
|-------------|-------|----------|
| **REMI** | ACM MM 2020 | Position + Duration + Pitch + Velocity tokens. Beat-based. Most popular for pop/EDM. |
| **REMI+** | ICLR 2022 | Extended REMI with better time handling |
| **MIDI-Like** | 2018 | Note-on/off events (closest to raw MIDI) |
| **TSD** (TimeShift-Duration) | 2023 | Time shifts between events + explicit durations |
| **Structured** | 2021 | Family/Type/Value token triples |
| **CPWord** (Compound Word) | AAAI 2021 | Multiple attributes per time step in one token |
| **Octuple** | ACL 2021 | 8 attributes per token (used by MusicBERT) |
| **MuMIDI** | ACM MM 2020 | Multi-track approach |
| **MMM** | 2020 | Multi-track measure concatenation |
| **PerTok** | 2024 | Performance-oriented tokenization |

**Key insight for DUBFORGE**: Our `midi_pattern_db.py` uses `(scale_degree, beat_position, duration, velocity)` tuples — this is essentially a simplified version of the note-based representation. MidiTok's REMI tokenization could be used to train a dubstep-specific generative model on curated MIDI data.

### Usage:
```python
from miditok import REMI, TokenizerConfig
config = TokenizerConfig(num_velocities=16, use_chords=True, use_programs=True)
tokenizer = REMI(config)
tokens = tokenizer(midi)  # Score object
```

---

## 4. MIDI GENERATION MODELS

### Transformer-Based (Most Relevant)

| Model | Stars | Architecture | Notes |
|-------|-------|-------------|-------|
| **SkyTNT/midi-model** | 356 | MIDI event transformer | Trained on Los Angeles MIDI Dataset. Has Gradio demo + Windows app. Good for symbolic generation. |
| **Music Transformer** | (Google) | Relative attention Transformer | Minute-long compositions with structure. Accompaniment generation. State of the art on piano. |
| **MuseNet** | (OpenAI, 2019) | Large Transformer | Multi-instrument, 4-minute compositions. Not open source. |
| **MusicBERT** | (Microsoft) | BERT pre-training | OctupleMIDI encoding. 1M+ song corpus. Melody completion, accompaniment suggestion, genre/style classification. |
| **MidiBERT-Piano** | 2021 | BERT for MIDI | Melody extraction, velocity prediction, composer/emotion classification from 4,166 pieces. |

### Diffusion-Based

| Model | Architecture | Notes |
|-------|-------------|-------|
| **MuseDiffusion** | Seq2seq diffusion | Music generation & modification from MIDI sequences |
| **Symbolic Music Diffusion** (2021) | VAE + diffusion | Non-autoregressive, parallel generation. Latent space of pre-trained VAE. |

### GAN-Based

| Model | Notes |
|-------|-------|
| **MuseGAN** (509 stars) | Multi-track music generation with GANs |
| **MidiNet** | CNN-based, conditional on chords or previous bars |
| **C-RNN-GAN** | Continuous RNN with adversarial training |

### LLM-Based (Newest)

| Model | Notes |
|-------|-------|
| **LLMidi** | VST3 plugin powered by local/online LLMs for MIDI generation — JUCE-based, supports GGUF models |
| **YuE** | Open full-song music generation (like Suno but open). LLaMA-based. |

### Other Notable

| Tool | Stars | Notes |
|------|-------|-------|
| **Amphion** (open-mmlab) | Large | Toolkit for Audio/Music/Speech generation. Reproducible research. |
| **FunMusic** (Alibaba) | — | Fundamental toolkit for music/song/audio generation |
| **ACE-Step UI** | — | Open-source Suno alternative, local generation |
| **soundgrep** | — | Multi-agent AI music production orchestrator. Semantic sample search, voice-to-MIDI, Ableton control, stem separation, MIDI generation, MCP server. **Very relevant architecture pattern.** |
| **TuneFlow** | — | AI-enhanced DAW with plugin system for custom music algorithms |

---

## 5. MIDI DATASETS

### Large-Scale

| Dataset | Size | Content |
|---------|------|---------|
| **Lakh MIDI** | 176,581 MIDIs | 45,129 matched to Million Song Dataset. The standard for MIR research. |
| **MetaMIDI Dataset (MMD)** | 436,631 MIDIs | With artist, title, genre metadata |
| **Los Angeles MIDI Dataset** | Large | Used by midi-model. On HuggingFace. |
| **XMIDI** | 108,023 MIDIs | Annotated with emotion + genre labels |
| **GiantMIDI-Piano** | 10,855 MIDIs | Classical piano, 2,786 composers. Transcribed from recordings. |

### Specialized

| Dataset | Content |
|---------|---------|
| **CHORDONOMICON** | 666,000 songs' chord progressions with genre/sub-genre/structure metadata. **Very relevant for DUBFORGE chord analysis.** |
| **POP909** | 909 pop songs: vocal melody + lead melody + piano accompaniment + tempo/beat/key/chord annotations |
| **DadaGP** | 26,181 GuitarPro songs in 739 genres, tokenized for Transformer training |
| **MAESTRO** | 200 hours of piano with fine-aligned MIDI + audio (3ms accuracy) |
| **Nottingham** | 1,200 British/American folk tunes |
| **JSB Chorales** | Bach chorales — the "MNIST of music generation" |

---

## 6. DUBSTEP / BASS MUSIC PRODUCTION TECHNIQUES

### Dubstep Structure (140 BPM, UK/140 style)
- **8-bar increments**: intro → build → drop 1A → 1B → 1C → breakdown → build 2 → drop 2A → 2B → outro
- Two-step kick pattern (kick on 1, ghost/skip on 2, kick on 3)
- Clap/rimshot on beat 3 (not heavy snares like riddim/brostep)
- Shuffle/groove on hi-hats and shakers (2-step shuffled 16ths)
- E minor or F minor most common keys for deep bass

### Bass Design in Serum (Production Workflow)

#### Sub-Bass Foundation
1. Start with basic wavetable (square variation)
2. Apply MG Low 24 filter
3. LFO 1 (Dome shape) → Filter A cutoff, rate 1/8 dotted
4. FM modulation: OSC B (+2 oct, level 0) → FM FROM B on OSC A
5. Effects chain: Hyper Dimension → Distortion → Comb Filter

#### Bass Modulation (Key Technique)
- **Macro 1**: Filter A cutoff
- **Macro 2**: FM FROM B amount
- **Macro 3**: Distortion drive + inverse mix (volume compensation)
- Automate macros across the arrangement for movement

#### Mid-Bass / Fills Technique
1. Duplicate sub-bass, freeze & flatten to audio
2. Heavy post-processing: distortion (Rift/Trash), filtering, OTT
3. Chop into fills at phrase endings
4. Fade in/out sections — don't play continuously

#### Bass Processing Chain
- EQ: cut 100-300 Hz (clash zone with kick), boost 1-3 kHz (presence)
- Multiband compression
- Sidechain compression to kick
- Saturation for harmonics

### Riddim / Heavy Dubstep Specifics (Subtronics Style)
- **Resampling workflow**: Render bass → re-process → render again → layer
- **Wavetable manipulation**: Custom wavetables from resampled audio
- **LFO modulation**: Multiple LFOs at different rates on different params
- **Formant shifting**: Vowel-like sounds ("yoi", "wub") via formant filters
- **FM synthesis**: Heavy use of FM for metallic/aggressive textures
- **Bitcrushing + downsampling**: For gritty digital textures
- **Comb filtering**: For resonant, metallic overtones
- **Granular processing**: Time-stretch artifacts as design elements
- **Sound layering**: Sub layer + mid layer + top layer, each processed separately

### Dubstep MIDI Pattern Conventions
- Sub-bass: follows root notes of chord progression, often simple (whole/half notes)
- Mid-bass: syncopated 8th/16th note patterns, often call-and-response with drum hits
- Neuro bass: rapid 16th/32nd note bursts, pitch modulation, glide between notes
- Riddim: repetitive 8th note patterns with heavy processing doing the heavy lifting
- Lead: sparse, atmospheric, pentatonic/minor scale, reverb-drenched
- Arps: 16th note runs, often following chord tones, gated/stuttered

---

## 7. RESEARCH PAPERS TIMELINE (Music Generation)

Key papers relevant to DUBFORGE:

| Year | Paper | Relevance |
|------|-------|-----------|
| 2018 | **Music Transformer** (Google) | Relative attention for long-term structure in music |
| 2020 | **REMI** (Pop Music Transformer) | Beat-based tokenization — most popular for EDM |
| 2020 | **MMM** (Multi-Track Music Machine) | Track-level and bar-level inpainting, note density control |
| 2020 | **Jukebox** (OpenAI) | Raw audio generation with VQ-VAE + Transformers |
| 2020 | **Chord-Texture Disentanglement** | Separate chord from texture for controllable generation |
| 2021 | **Theme Transformer** | Theme-conditioned generation with contrastive learning |
| 2021 | **MusicVAE** (Google) | Latent space of multitrack measures, chord conditioning |
| 2021 | **RAVE** | Real-time audio VAE, 48kHz, 20x faster than real-time |
| 2022 | **AudioLM** (Google) | Language modeling for audio, coherent piano continuations |
| 2023 | **MusicLM** (Google) | Text-to-music, 24kHz, consistent over minutes |
| 2023 | **Hybrid Transformer Demucs** | State-of-the-art source separation |
| 2024 | **midi-model v1.3** | MIDI event transformer, quality-filtered dataset |

---

## 8. WHAT PEOPLE ARE ACTUALLY USING (Production Community)

### For MIDI Pattern Creation
- **Manual programming** in DAW piano roll (still dominant)
- **MIDI packs** from Splice, Loopmasters, etc.
- **Arpeggiators** built into DAWs/synths
- **Cthulhu** (Xfer Records) — chord/arp MIDI effect
- **Scaler 2** — chord progression generator + MIDI output
- **Captain Plugins** — melody, chords, bass, drums MIDI generators
- **Ableton Live 12 Generative MIDI Tools** (new in 2024) — 5 built-in MIDI generators
- **Manifest Audio Polyfold** — Max for Live sequencer with 1000+ steps, multidimensional

### For Reference Analysis
- **Demucs** for stem separation (most popular)
- **Basic Pitch** for audio-to-MIDI (growing fast)
- **Mixed In Key** for key/energy detection
- **Fadr** for AI stem separation + MIDI extraction
- **RipX** for advanced audio separation

### For Sound Design
- **Serum / Serum 2** (dominant in dubstep, ~90% of producers)
- **Vital** (free alternative, growing)
- **Phase Plant** (advanced modular)
- **Massive X** (legacy, still used)

---

## 9. ACTIONABLE RECOMMENDATIONS FOR DUBFORGE

### Quick Wins (integrate now)
1. **Add Basic Pitch** to reference intake pipeline — `pip install basic-pitch` — for polyphonic audio→MIDI, replacing/augmenting librosa pyin
2. **Add Demucs** pre-processing — separate reference into stems before analysis for much cleaner MIDI extraction
3. **Use CHORDONOMICON** — 666k chord progressions with genre tags — filter for dubstep/electronic and feed into pattern DB

### Medium-Term
4. **Integrate MidiTok REMI tokenization** — standardize our pattern representation for potential model training
5. **Add madmom beat/downbeat tracking** — more accurate than librosa's beat_track for complex rhythms
6. **Expand pattern DB with Lakh MIDI** — filter for electronic/bass music, extract patterns algorithmically

### Long-Term Vision
7. **Train a dubstep-specific MIDI Transformer** — fine-tune midi-model or Music Transformer on curated dubstep MIDI corpus
8. **Build a Serum preset↔MIDI coupling system** — link sound design parameters to MIDI pattern selection
9. **Implement the soundgrep multi-agent pattern** — orchestrate analysis, generation, and DAW control through agents

---

## 10. KEY TOOLS SUMMARY

```
DETECTION          GENERATION           DATASETS              PRODUCTION
─────────         ──────────           ────────              ──────────
Basic Pitch        midi-model           Lakh MIDI (177k)      Serum 2
Demucs             Music Transformer    MetaMIDI (437k)       Ableton Live 12
CREPE              LLMidi (VST3)        CHORDONOMICON (666k)  Cthulhu
madmom             MidiTok + HF models  XMIDI (108k)          Scaler 2
librosa            MuseDiffusion        POP909                OTT
pretty-midi        MuseGAN              DadaGP                Rift/Trash
                   YuE                  Los Angeles MIDI      Multiband Comp
```

---

*Research compiled for DUBFORGE MIDI pipeline enhancement — July 2025*
*Sources: GitHub, academic papers (ISMIR, ICASSP, ACM MM), edmprod.com, community forums*
