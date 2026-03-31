"""Inspect Ableton databases and search for device presets."""
import sqlite3
import os

# Check the files database — look for device info
db_path = r"C:\Users\gripa\AppData\Local\Ableton\Live Database\Live-files-12300.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name, type FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", [t[0] for t in tables])

# Check devices table
try:
    cursor.execute('PRAGMA table_info("devices")')
    print("\nDevices table columns:")
    for c in cursor.fetchall():
        print(f"  {c[1]} ({c[2]})")
    
    # Search for Serum in devices
    cursor.execute("SELECT * FROM devices WHERE name LIKE '%erum%' LIMIT 10")
    rows = cursor.fetchall()
    print(f"\nSerum devices found: {len(rows)}")
    for r in rows:
        print(f"  ROW: {str(r)[:300]}")
except Exception as e:
    print(f"  Error: {e}")

# Check files for device_id containing Serum
try:
    cursor.execute("SELECT file_id, name, device_id, device_type FROM files WHERE device_id LIKE '%erum%' OR name LIKE '%erum%' LIMIT 10")
    rows = cursor.fetchall()
    print(f"\nSerum files found: {len(rows)}")
    for r in rows:
        print(f"  ROW: {r}")
except Exception as e:
    print(f"  Error: {e}")

conn.close()

# Search for ADV/ADG files
print("\n\n=== Searching for Serum ADV/ADG files ===")
search_paths = [
    os.path.expandvars(r"%APPDATA%\Ableton"),
    os.path.expandvars(r"%LOCALAPPDATA%\Ableton"),
    r"C:\ProgramData\Ableton",
    os.path.expanduser(r"~\Documents\Ableton"),
]
for sp in search_paths:
    if os.path.isdir(sp):
        for root, dirs, files in os.walk(sp):
            for f in files:
                fl = f.lower()
                if "serum" in fl or fl.endswith((".adv", ".adg")):
                    full = os.path.join(root, f)
                    print(f"  {full} ({os.path.getsize(full)} bytes)")

