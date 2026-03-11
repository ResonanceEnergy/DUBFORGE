"""
DUBFORGE — Snapshot Manager  (Session 206)

Save and recall complete engine state snapshots:
parameter values, chain configs, mixer settings.
Compare snapshots and morph between them.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field

from engine.config_loader import PHI
@dataclass
class Snapshot:
    """A complete state snapshot."""
    snapshot_id: str
    name: str
    timestamp: float
    state: dict = field(default_factory=dict)
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.snapshot_id,
            "name": self.name,
            "timestamp": self.timestamp,
            "description": self.description,
            "tags": self.tags,
            "state_keys": list(self.state.keys()),
            "state": self.state,
        }


class SnapshotManager:
    """Manage engine state snapshots."""

    def __init__(self, data_dir: str = "output/snapshots"):
        self.data_dir = data_dir
        self.snapshots: dict[str, Snapshot] = {}
        self.current_state: dict = {}
        os.makedirs(data_dir, exist_ok=True)
        self._load_all()

    def capture(self, name: str, state: dict,
                description: str = "",
                tags: list[str] = None) -> Snapshot:
        """Capture a state snapshot."""
        sid = hashlib.sha1(
            f"{name}{time.time()}".encode()
        ).hexdigest()[:10]

        snapshot = Snapshot(
            snapshot_id=sid,
            name=name,
            timestamp=time.time(),
            state=dict(state),
            description=description,
            tags=tags or [],
        )
        self.snapshots[sid] = snapshot
        self._save(snapshot)
        return snapshot

    def recall(self, snapshot_id: str) -> dict:
        """Recall a snapshot's state."""
        snapshot = self.snapshots.get(snapshot_id)
        if not snapshot:
            return {}
        self.current_state = dict(snapshot.state)
        return self.current_state

    def recall_by_name(self, name: str) -> dict:
        """Recall by snapshot name (latest if multiple)."""
        matches = [s for s in self.snapshots.values()
                   if s.name == name]
        if not matches:
            return {}
        latest = max(matches, key=lambda s: s.timestamp)
        return self.recall(latest.snapshot_id)

    def diff(self, id_a: str, id_b: str) -> dict:
        """Compare two snapshots."""
        snap_a = self.snapshots.get(id_a)
        snap_b = self.snapshots.get(id_b)
        if not snap_a or not snap_b:
            return {}

        changes: dict = {
            "added": {},
            "removed": {},
            "modified": {},
        }

        all_keys = set(snap_a.state.keys()) | set(snap_b.state.keys())
        for key in all_keys:
            in_a = key in snap_a.state
            in_b = key in snap_b.state

            if in_a and not in_b:
                changes["removed"][key] = snap_a.state[key]
            elif in_b and not in_a:
                changes["added"][key] = snap_b.state[key]
            elif snap_a.state[key] != snap_b.state[key]:
                changes["modified"][key] = {
                    "from": snap_a.state[key],
                    "to": snap_b.state[key],
                }

        return changes

    def morph(self, id_a: str, id_b: str,
              blend: float = 0.5) -> dict:
        """Morph between two snapshots (numeric values only)."""
        snap_a = self.snapshots.get(id_a)
        snap_b = self.snapshots.get(id_b)
        if not snap_a or not snap_b:
            return {}

        result: dict = {}
        all_keys = set(snap_a.state.keys()) | set(snap_b.state.keys())

        for key in all_keys:
            val_a = snap_a.state.get(key)
            val_b = snap_b.state.get(key)

            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                result[key] = val_a * (1 - blend) + val_b * blend
            elif val_a is not None:
                result[key] = val_a if blend < 0.5 else val_b
            else:
                result[key] = val_b

        return result

    def phi_morph(self, id_a: str, id_b: str) -> dict:
        """Morph at PHI blend point."""
        return self.morph(id_a, id_b, 1.0 / PHI)

    def search(self, query: str = "",
               tags: list[str] = None) -> list[Snapshot]:
        """Search snapshots."""
        results: list[Snapshot] = []
        for snap in self.snapshots.values():
            if query and query.lower() not in snap.name.lower():
                if not any(query.lower() in t for t in snap.tags):
                    continue
            if tags:
                if not any(t in snap.tags for t in tags):
                    continue
            results.append(snap)

        return sorted(results, key=lambda s: s.timestamp, reverse=True)

    def delete(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        if snapshot_id not in self.snapshots:
            return False
        del self.snapshots[snapshot_id]
        path = os.path.join(self.data_dir, f"{snapshot_id}.json")
        if os.path.exists(path):
            os.remove(path)
        return True

    def list_snapshots(self) -> list[dict]:
        """List all snapshots."""
        return [
            {
                "id": s.snapshot_id,
                "name": s.name,
                "description": s.description,
                "tags": s.tags,
                "keys": len(s.state),
            }
            for s in sorted(self.snapshots.values(),
                              key=lambda s: s.timestamp, reverse=True)
        ]

    def export_snapshot(self, snapshot_id: str) -> dict | None:
        """Export snapshot as dict."""
        snap = self.snapshots.get(snapshot_id)
        if not snap:
            return None
        return snap.to_dict()

    def import_snapshot(self, data: dict) -> Snapshot | None:
        """Import snapshot from dict."""
        try:
            snap = Snapshot(
                snapshot_id=data.get("id", hashlib.sha1(
                    str(time.time()).encode()
                ).hexdigest()[:10]),
                name=data["name"],
                timestamp=data.get("timestamp", time.time()),
                state=data.get("state", {}),
                description=data.get("description", ""),
                tags=data.get("tags", []),
            )
            self.snapshots[snap.snapshot_id] = snap
            self._save(snap)
            return snap
        except (KeyError, TypeError):
            return None

    def _save(self, snapshot: Snapshot) -> None:
        """Persist snapshot."""
        path = os.path.join(self.data_dir,
                             f"{snapshot.snapshot_id}.json")
        with open(path, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    def _load_all(self) -> None:
        """Load all snapshots from disk."""
        if not os.path.exists(self.data_dir):
            return
        for fname in os.listdir(self.data_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.data_dir, fname)
            try:
                with open(path) as f:
                    data = json.load(f)
                snap = Snapshot(
                    snapshot_id=data["id"],
                    name=data["name"],
                    timestamp=data.get("timestamp", 0),
                    state=data.get("state", {}),
                    description=data.get("description", ""),
                    tags=data.get("tags", []),
                )
                self.snapshots[snap.snapshot_id] = snap
            except (json.JSONDecodeError, KeyError):
                pass

    def get_summary(self) -> dict:
        return {
            "total_snapshots": len(self.snapshots),
            "snapshots": self.list_snapshots()[:5],
        }


def main() -> None:
    print("Snapshot Manager")

    mgr = SnapshotManager()

    # Capture snapshots
    state_a = {
        "bass_freq": 80.0,
        "bass_drive": 0.3,
        "reverb_mix": 0.2,
        "tempo": 140.0,
        "style": "dubstep",
    }
    snap_a = mgr.capture("Chill Drop", state_a,
                          "Relaxed dubstep drop", ["dubstep", "chill"])

    state_b = {
        "bass_freq": 40.0,
        "bass_drive": 0.9,
        "reverb_mix": 0.05,
        "tempo": 150.0,
        "style": "tearout",
    }
    snap_b = mgr.capture("Heavy Drop", state_b,
                          "Heavy tearout drop", ["tearout", "heavy"])

    print(f"  Snap A: {snap_a.snapshot_id}")
    print(f"  Snap B: {snap_b.snapshot_id}")

    # Diff
    diff = mgr.diff(snap_a.snapshot_id, snap_b.snapshot_id)
    print(f"\n  Diff: {diff}")

    # PHI morph
    morphed = mgr.phi_morph(snap_a.snapshot_id, snap_b.snapshot_id)
    print(f"\n  PHI morph: {morphed}")

    # Summary
    print(f"\n  Summary: {mgr.get_summary()}")
    print("Done.")


if __name__ == "__main__":
    main()
