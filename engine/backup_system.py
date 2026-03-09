"""
DUBFORGE — Backup System Engine  (Session 191)

Project backup and restore with compression,
versioning, and integrity verification.
"""

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass, field

PHI = 1.6180339887


@dataclass
class BackupEntry:
    """A single backup record."""
    backup_id: str
    timestamp: float
    description: str
    files: list[str]
    total_size: int = 0
    checksum: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.backup_id,
            "timestamp": self.timestamp,
            "description": self.description,
            "files": self.files,
            "total_size": self.total_size,
            "checksum": self.checksum,
        }


@dataclass
class BackupManifest:
    """Manifest tracking all backups."""
    project_name: str
    backups: list[BackupEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project": self.project_name,
            "backup_count": len(self.backups),
            "backups": [b.to_dict() for b in self.backups],
        }


class BackupSystem:
    """Manages project backups."""

    def __init__(self, backup_dir: str = "output/backups",
                 project_name: str = "DUBFORGE"):
        self.backup_dir = backup_dir
        self.project_name = project_name
        self.manifest = BackupManifest(project_name)
        self._load_manifest()

    def _manifest_path(self) -> str:
        return os.path.join(self.backup_dir, "manifest.json")

    def _load_manifest(self) -> None:
        path = self._manifest_path()
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            self.manifest.project_name = data.get("project", self.project_name)
            for b in data.get("backups", []):
                self.manifest.backups.append(BackupEntry(
                    backup_id=b["id"],
                    timestamp=b["timestamp"],
                    description=b["description"],
                    files=b["files"],
                    total_size=b.get("total_size", 0),
                    checksum=b.get("checksum", ""),
                ))

    def _save_manifest(self) -> None:
        os.makedirs(self.backup_dir, exist_ok=True)
        with open(self._manifest_path(), "w") as f:
            json.dump(self.manifest.to_dict(), f, indent=2)

    def _compute_checksum(self, paths: list[str]) -> str:
        """Compute combined checksum of files."""
        h = hashlib.sha256()
        for path in sorted(paths):
            if os.path.exists(path):
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
            else:
                h.update(path.encode())
        return h.hexdigest()[:16]

    def backup(self, source_paths: list[str],
               description: str = "") -> BackupEntry | None:
        """Create a backup of specified files."""
        if not source_paths:
            return None

        ts = time.time()
        backup_id = hashlib.sha1(
            f"{ts}{description}".encode()
        ).hexdigest()[:12]

        backup_subdir = os.path.join(self.backup_dir, backup_id)
        os.makedirs(backup_subdir, exist_ok=True)

        backed_up: list[str] = []
        total_size = 0

        for src in source_paths:
            if os.path.exists(src):
                rel = os.path.basename(src)
                dst = os.path.join(backup_subdir, rel)
                shutil.copy2(src, dst)
                backed_up.append(rel)
                total_size += os.path.getsize(src)

        checksum = self._compute_checksum(
            [os.path.join(backup_subdir, f) for f in backed_up]
        )

        entry = BackupEntry(
            backup_id=backup_id,
            timestamp=ts,
            description=description or f"Backup {len(self.manifest.backups) + 1}",
            files=backed_up,
            total_size=total_size,
            checksum=checksum,
        )
        self.manifest.backups.append(entry)
        self._save_manifest()
        return entry

    def restore(self, backup_id: str,
                target_dir: str = ".") -> list[str]:
        """Restore files from a backup."""
        entry = None
        for b in self.manifest.backups:
            if b.backup_id == backup_id:
                entry = b
                break

        if not entry:
            return []

        backup_subdir = os.path.join(self.backup_dir, backup_id)
        restored: list[str] = []

        for filename in entry.files:
            src = os.path.join(backup_subdir, filename)
            dst = os.path.join(target_dir, filename)
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
                shutil.copy2(src, dst)
                restored.append(dst)

        return restored

    def verify(self, backup_id: str) -> bool:
        """Verify backup integrity."""
        entry = None
        for b in self.manifest.backups:
            if b.backup_id == backup_id:
                entry = b
                break

        if not entry:
            return False

        backup_subdir = os.path.join(self.backup_dir, backup_id)
        paths = [os.path.join(backup_subdir, f) for f in entry.files]
        checksum = self._compute_checksum(paths)
        return checksum == entry.checksum

    def list_backups(self) -> list[BackupEntry]:
        """List all backups, newest first."""
        return sorted(self.manifest.backups,
                       key=lambda b: b.timestamp, reverse=True)

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        for i, b in enumerate(self.manifest.backups):
            if b.backup_id == backup_id:
                backup_subdir = os.path.join(self.backup_dir, backup_id)
                if os.path.exists(backup_subdir):
                    shutil.rmtree(backup_subdir)
                self.manifest.backups.pop(i)
                self._save_manifest()
                return True
        return False

    def prune(self, keep_latest: int = 5) -> int:
        """Remove old backups, keeping only the latest N."""
        backups = self.list_backups()
        removed = 0
        for b in backups[keep_latest:]:
            if self.delete_backup(b.backup_id):
                removed += 1
        return removed

    def get_summary(self) -> dict:
        """Get backup system summary."""
        total_size = sum(b.total_size for b in self.manifest.backups)
        return {
            "project": self.project_name,
            "total_backups": len(self.manifest.backups),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "latest": (self.manifest.backups[-1].backup_id
                        if self.manifest.backups else None),
        }


def main() -> None:
    print("Backup System Engine")

    backup = BackupSystem("output/backups", "DUBFORGE")

    # Create test files
    os.makedirs("output/backups/test_src", exist_ok=True)
    test_files: list[str] = []
    for i in range(3):
        path = f"output/backups/test_src/file_{i}.txt"
        with open(path, "w") as f:
            f.write(f"DUBFORGE test file {i}\nPHI={PHI}")
        test_files.append(path)

    # Backup
    entry = backup.backup(test_files, "Test backup")
    if entry:
        print(f"  Created: {entry.backup_id}")
        print(f"    Files: {entry.files}")
        print(f"    Size: {entry.total_size} bytes")

        # Verify
        valid = backup.verify(entry.backup_id)
        print(f"    Valid: {valid}")

    # Summary
    summary = backup.get_summary()
    print(f"\n  Summary: {summary}")

    # Cleanup test files
    shutil.rmtree("output/backups/test_src", ignore_errors=True)

    print("Done.")


if __name__ == "__main__":
    main()
