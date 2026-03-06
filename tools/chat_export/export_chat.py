'''export_chat.py

Drop your chat messages into the `messages` list and run:

    python export_chat.py

It will write ./out/chat_transcript.txt

Messages format:
    {"role": "user"|"assistant", "content": "..."}
'''

from pathlib import Path

messages = [
    # Paste your messages here.
    # {"role": "user", "content": "Hello"},
    # {"role": "assistant", "content": "Hi!"},
]


def render(messages):
    lines = []
    for m in messages:
        role = m.get('role', '').upper()
        content = (m.get('content') or '').strip()
        lines.append(f"[{role}]\n{content}\n")
    return "\n".join(lines)


def main():
    out_dir = Path('out')
    out_dir.mkdir(exist_ok=True)
    text = render(messages)
    (out_dir / 'chat_transcript.txt').write_text(text, encoding='utf-8')
    print('Wrote', out_dir / 'chat_transcript.txt')


if __name__ == '__main__':
    main()
