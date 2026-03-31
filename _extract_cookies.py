"""Extract SoundCloud cookies from Edge into Netscape cookies.txt format.

Uses Playwright + CDP to launch Edge with the real user profile,
which handles App-Bound Encryption (Chrome v127+) transparently.
"""
import sys
import os

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: pip install playwright && python -m playwright install")
    sys.exit(1)

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(edge_path):
    edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(edge_path):
    print("ERROR: Cannot find msedge.exe")
    sys.exit(1)

user_data = os.path.join(
    os.environ["LOCALAPPDATA"], "Microsoft", "Edge", "User Data"
)

print("Launching Edge to extract cookies (this opens a window briefly)...")

with sync_playwright() as p:
    # Launch Edge using the real user profile (already logged into SoundCloud)
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        executable_path=edge_path,
        channel="msedge",
        headless=False,
        args=["--no-first-run", "--no-default-browser-check"],
    )

    # Get cookies for soundcloud.com
    cookies = ctx.cookies(["https://soundcloud.com", "https://api-v2.soundcloud.com"])

    if not cookies:
        print("No SoundCloud cookies found. Are you logged in?")
        ctx.close()
        sys.exit(1)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# Extracted from Microsoft Edge via Playwright CDP\n")
        for c in cookies:
            domain = c.get("domain", "")
            httponly = "TRUE" if domain.startswith(".") else "FALSE"
            sec = "TRUE" if c.get("secure", False) else "FALSE"
            exp = int(c.get("expires", 0))
            name = c.get("name", "")
            value = c.get("value", "")
            path = c.get("path", "/")
            f.write(f"{domain}\t{httponly}\t{path}\t{sec}\t{exp}\t{name}\t{value}\n")

    ctx.close()

print(f"Exported {len(cookies)} decrypted SoundCloud cookies to {out_path}")
