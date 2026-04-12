# DUBFORGE — Genre Palette
> Layer 3 shared resource. Cross-stage reference for genre decisions.

---

## Dubstep Sub-Genres DUBFORGE Produces

| Sub-Genre | BPM Range | Key Characteristics | Reference Tracks |
|-----------|-----------|--------------------|-----------------:|
| `riddim` | 140–150 | Minimal, repetitive, surgical bass | Subtronics, Kompany |
| `melodic_dubstep` | 140–145 | Emotional leads, clean drops | Rezz-adjacent |
| `brostep` | 140–150 | Massive wobble, festival energy | Early Skrillex |
| `dark_dubstep` | 138–145 | Distorted bass, industrial textures | Space Laces |
| `tearout` | 148–175 | Chaotic bass, high aggression | Marauda, Subfiltronik |
| `halftime` | 70–80 | Half-time groove, hip-hop influence | Eprom |
| `future_bass` | 130–145 | Vocal chops, lush pads, bright | Flume-adjacent |

---

## Drop Energy Checklist

Every drop must contain:
- [ ] Kick: 4-on-the-floor pattern, tuned to root note
- [ ] Sub bass: one note per kick, root frequency
- [ ] Mid bass / wobble: main melodic movement (1–2 octaves above sub)
- [ ] Snare: bar 2 and 4 (half-time) or every beat (brostep)
- [ ] Percussion: hi-hats, shakers, percussion loops
- [ ] Texture: atmospheric pad or drone (–20dB under the bass)
- [ ] FX: reverse crash, uplifter, or stutter on bar transitions

---

## Frequency Map (Dubstep Mix Convention)

```
20–60 Hz    Sub bass   → Kick punch + sub fundamental (MONO below 120 Hz)
60–120 Hz   Kick body  → Low mid kick attack
120–250 Hz  Warmth     → Mid bass body, no buildup here
250–500 Hz  Mud zone   → Cut from pads, bass, everything unless intentional
500Hz–2kHz  Presence   → Lead voice lives here, side chains to sub
2–8 kHz     Air / edge → Hi hat transients, screech attack, sibilance
8–16 kHz    Air        → Open hats, top end shimmer
```

---

## Key-Mood Mapping

| Key | Mood | Use Case |
|-----|------|---------|
| F minor | Dark, industrial | Default DUBFORGE root |
| A minor | Sad, emotional | Melodic dubstep |
| D minor | Tension, drama | Build sections |
| G minor | Heavy, grinding | Riddim |
| C minor | Aggressive | Tearout drops |
| E minor | Mysterious | Dark ambient intros |
| B minor | Cold, alien | Future bass |

---

## Reference Artists (Corpus)

Defined in `configs/sb_corpus_v1.yaml`:
- **Subtronics** — primary aesthetic authority
- **Space Laces** — dark industrial texture
- **Marauda** — tearout energy
- **ill.Gates** — production methodology
- **Virtual Riot** — tech complexity
- **Eprom** — halftime groove
- **Rezz** — minimalist hypnotic
