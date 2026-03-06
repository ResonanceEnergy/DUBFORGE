# INSTRUCTIONS — Chat Export + VS Code One-Drop

## Purpose

This one-drop provides a minimal, repo-friendly way to export chat transcripts into a plain text file.

## Files

- `export_chat.py` — main exporter.
- `chat_transcript.txt` — current session transcript (optional / may be empty).
- `run.ps1` — Windows runner.
- `run.sh` — macOS/Linux runner.

## Usage (recommended)

### Step 1 — Paste messages

Open `export_chat.py` and paste the messages into the `messages` list.

Example:

```python
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"},
]
```

### Step 2 — Run

#### Windows

```powershell
python .\export_chat.py
```

#### macOS/Linux

```bash
python3 ./export_chat.py
```

### Step 3 — Grab output

The exporter writes:

- `./out/chat_transcript.txt`

## Conventions

- Roles are **USER** / **ASSISTANT** in the output file.
- Each message is separated by a blank line.

## Tips

- If you want a single continuous file without role headers, edit the `render()` function.
- If you want Markdown output, change the formatting inside `render()`.

## Troubleshooting

- **Python not found**: install Python 3.10+ and ensure it's on PATH.
- **Permission denied (run.sh)**: run `chmod +x run.sh` then `./run.sh`.

## Security

Do not paste passwords, API keys, or private tokens into the transcript.
