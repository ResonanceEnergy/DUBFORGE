"""Extract all crash events from Ableton Log.txt in crash report ZIPs."""
import zipfile
import os
import glob

reports_dir = r"C:\Users\gripa\AppData\Roaming\Ableton\Live Reports"

# Process ALL ZIPs
zips = sorted(glob.glob(os.path.join(reports_dir, "*.zip")))
print(f"Found {len(zips)} crash report ZIPs\n")

for z in zips:
    print(f"=== {os.path.basename(z)} ===")
    with zipfile.ZipFile(z) as zf:
        content = zf.read("Preferences/Log.txt").decode("utf-8", errors="replace")
        lines = content.strip().split("\n")

        crashes = []
        for i, line in enumerate(lines):
            if "EXCEPTION_ACCESS_VIOLATION" in line:
                doc = "unknown"
                for j in range(i - 1, max(0, i - 10), -1):
                    if "Loading document" in lines[j]:
                        doc = lines[j].split('Loading document')[1].strip().strip('"')
                        break
                crashes.append((line[:26], os.path.basename(doc)))

        if crashes:
            for ts, doc in crashes:
                print(f"  {ts}  ->  {doc}")
        else:
            print("  No ACCESS_VIOLATION crashes")
    print()

# Also read the most recent .crashlog files (Apr 3)
print("=" * 60)
print("RECENT CRASHLOGS (Apr 3):")
print("=" * 60)
usage_dir = os.path.join(reports_dir, "Usage")
crashlogs = sorted(glob.glob(os.path.join(usage_dir, "*.crashlog")))
for cl in crashlogs:
    basename = os.path.basename(cl)
    if "20260403" in basename:
        size = os.path.getsize(cl)
        print(f"\n  {basename} ({size:,} bytes)")

# Also count .dmp files by date
print("\n" + "=" * 60)
print("CRASH DUMPS BY DATE:")
print("=" * 60)
temp_dir = os.path.join(reports_dir, "Temp")
dmps = sorted(glob.glob(os.path.join(temp_dir, "*.dmp")))
from collections import Counter
dates = Counter()
for d in dmps:
    basename = os.path.basename(d)
    # Extract date: ..._2026_03_28__22_34_55.dmp
    parts = basename.split("_")
    # Find year-month-day
    for idx, p in enumerate(parts):
        if p == "2026" and idx + 2 < len(parts):
            date_str = f"{p}-{parts[idx+1]}-{parts[idx+2]}"
            dates[date_str] += 1
            break

for date, count in sorted(dates.items()):
    print(f"  {date}: {count} crash dumps")

# Read the Ableton Log.txt directly (current one, not from ZIP)
print("\n" + "=" * 60)
print("CURRENT LOG.TXT - LAST 3 SESSIONS:")
print("=" * 60)
log_path = r"C:\Users\gripa\AppData\Roaming\Ableton\Live 12.3.6\Preferences\Log.txt"
if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        log_content = f.read()
    log_lines = log_content.strip().split("\n")

    # Split into sessions
    sessions = []
    current = []
    for line in log_lines:
        if "# Opening Log:" in line:
            if current:
                sessions.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sessions.append(current)

    # Print last 3 sessions
    for i, session in enumerate(sessions[-3:]):
        idx = len(sessions) - 3 + i
        # Find key events in session
        has_crash = any("EXCEPTION_ACCESS_VIOLATION" in l for l in session)
        loading = [l for l in session if "Loading document" in l]
        loaded_files = [l.split('Loading document')[1].strip().strip('"') for l in loading]

        print(f"\nSession {idx+1}/{len(sessions)} ({session[0].strip()}):")
        if loaded_files:
            for lf in loaded_files:
                print(f"  Loaded: {os.path.basename(lf)}")
        if has_crash:
            print(f"  ** CRASHED **")
        else:
            # Find if it ended normally
            last_lines = [l for l in session[-5:] if l.strip()]
            if last_lines:
                print(f"  Last: {last_lines[-1][:100]}")
else:
    print("  Log.txt not found")
