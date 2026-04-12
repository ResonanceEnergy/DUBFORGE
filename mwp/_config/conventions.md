# DUBFORGE — Workspace Conventions
> Layer 3 stable config. Edit to change the factory, not the product.

---

## The 15 ICM Conventions

| # | Convention | Rule |
|---|-----------|------|
| 1 | One stage, one job | Generation doesn't arrange. Arrangement doesn't mix. Mixing doesn't master. |
| 2 | Plain text interface | Markdown + JSON only. No binary pickles, no SQLite, no serialization. |
| 3 | Layered context loading | Load only CLAUDE.md + CONTEXT.md + active stage CONTEXT.md per run. |
| 4 | Every output is an edit surface | Human can edit any `output/*.json` before triggering next stage. |
| 5 | Configure the factory, not the product | Set preferences in `_config/`. Each run uses same config. |
| 6 | One-way references | stages/01 → _config → shared. Never reverse. No circular deps. |
| 7 | Canonical sources | Each fact lives in ONE file. Others reference it. |
| 8 | Specs are contracts | Stage CONTEXT.md defines WHAT and WHEN. Python defines HOW. |
| 9 | Docs over outputs | Stages learn from `references/` docs, not previous outputs. |
| 10 | Human gates are real gates | Do not skip the human review step between stages. |
| 11 | Ableton first | Every audio decision runs in Ableton. Python controls, Ableton renders. |
| 12 | One export mechanism | osascript Cmd+Shift+R. Never file>export manually. |
| 13 | Phi or fight | All timing parameters must reference phi/Fibonacci. Random = lazy. |
| 14 | 4/4 always | BEATS_PER_BAR = 4. No exceptions. Dubstep is 4/4. |
| 15 | Outputs survive restarts | stage `output/` files persist across code restarts. |

---

## File Naming

| Artifact | Pattern | Example |
|----------|---------|---------|
| Song manifests | `{stage}_summary.md` | `stage_summary.md` |
| Data snapshots | `{descriptor}.json` | `song_mandate.json` |
| Audio paths | `{descriptor}_manifest.json` | `audio_manifest.json` |
| ALS paths | `als_path.txt` | `als_path.txt` |
| Bounce path | `{stage}_bounce.wav` | note: WAV itself lives in `output/renders/` |

---

## Output Directory Rules

- `stages/XX/output/` is writable by Python (engine writes after each run)
- All files in `output/` are human-editable before next stage runs
- `output/README.md` documents expected artifacts for that stage
- Stale outputs (from old runs) are OVERWRITTEN by the next run
- Never commit large WAV files to git (covered by `.gitignore`)

---

## Python Interface

All workspace I/O goes through `engine/workspace_io.py`:
```python
from engine.workspace_io import write_stage_output, read_stage_output, write_summary

# Write a JSON artifact
write_stage_output("01-generation", "song_mandate.json", {"name": "apology", ...})

# Read previous stage output
data = read_stage_output("01-generation", "song_mandate.json")

# Write human-readable summary
write_summary("01-generation", ["✓ SongMandate complete", "✓ 10 stems bounced"])
```
