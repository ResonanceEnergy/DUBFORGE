"""
DUBFORGE — Preset Version Control Engine  (Session 185)

Git-like versioning for presets: commits, branches,
diffs, and rollback for sound design iterations.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field

PHI = 1.6180339887


@dataclass
class PresetCommit:
    """A versioned preset snapshot."""
    commit_id: str
    parent_id: str | None
    timestamp: float
    message: str
    params: dict
    author: str = "DUBFORGE"

    def to_dict(self) -> dict:
        return {
            "id": self.commit_id,
            "parent": self.parent_id,
            "timestamp": self.timestamp,
            "message": self.message,
            "params": self.params,
            "author": self.author,
        }


@dataclass
class PresetDiff:
    """Difference between two preset versions."""
    added: dict = field(default_factory=dict)
    removed: list[str] = field(default_factory=list)
    changed: dict = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.added and not self.removed and not self.changed

    def to_dict(self) -> dict:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": {k: {"old": v[0], "new": v[1]}
                        for k, v in self.changed.items()},
        }


@dataclass
class PresetBranch:
    """A branch of preset development."""
    name: str
    head_id: str | None = None
    created_at: float = 0.0


class PresetVCS:
    """Version control system for presets."""

    def __init__(self, name: str = "Untitled Preset"):
        self.name = name
        self.commits: dict[str, PresetCommit] = {}
        self.branches: dict[str, PresetBranch] = {}
        self.current_branch: str = "main"
        self.branches["main"] = PresetBranch("main", created_at=time.time())

    def _hash_params(self, params: dict, parent_id: str | None,
                      timestamp: float) -> str:
        """Generate commit ID from content."""
        content = json.dumps(params, sort_keys=True)
        content += f"|{parent_id}|{timestamp}"
        return hashlib.sha1(content.encode()).hexdigest()[:12]

    def commit(self, params: dict, message: str = "",
               author: str = "DUBFORGE") -> PresetCommit:
        """Commit a new preset version."""
        branch = self.branches[self.current_branch]
        parent = branch.head_id
        ts = time.time()

        commit_id = self._hash_params(params, parent, ts)
        commit = PresetCommit(
            commit_id=commit_id,
            parent_id=parent,
            timestamp=ts,
            message=message or f"Update {self.name}",
            params=dict(params),
            author=author,
        )

        self.commits[commit_id] = commit
        branch.head_id = commit_id
        return commit

    def get_head(self) -> PresetCommit | None:
        """Get current HEAD commit."""
        branch = self.branches.get(self.current_branch)
        if branch and branch.head_id:
            return self.commits.get(branch.head_id)
        return None

    def diff(self, id_a: str, id_b: str) -> PresetDiff:
        """Compute diff between two commits."""
        a = self.commits.get(id_a)
        b = self.commits.get(id_b)
        if not a or not b:
            return PresetDiff()

        result = PresetDiff()

        # Added params
        for k, v in b.params.items():
            if k not in a.params:
                result.added[k] = v

        # Removed params
        for k in a.params:
            if k not in b.params:
                result.removed.append(k)

        # Changed params
        for k in a.params:
            if k in b.params and a.params[k] != b.params[k]:
                result.changed[k] = (a.params[k], b.params[k])

        return result

    def log(self, max_entries: int = 20) -> list[PresetCommit]:
        """Get commit history for current branch."""
        branch = self.branches.get(self.current_branch)
        if not branch or not branch.head_id:
            return []

        history: list[PresetCommit] = []
        current = branch.head_id

        while current and len(history) < max_entries:
            commit = self.commits.get(current)
            if not commit:
                break
            history.append(commit)
            current = commit.parent_id

        return history

    def checkout(self, commit_id: str) -> dict | None:
        """Checkout a specific commit's params."""
        commit = self.commits.get(commit_id)
        return dict(commit.params) if commit else None

    def rollback(self, steps: int = 1) -> PresetCommit | None:
        """Roll back N commits."""
        branch = self.branches.get(self.current_branch)
        if not branch or not branch.head_id:
            return None

        current = branch.head_id
        for _ in range(steps):
            commit = self.commits.get(current)
            if not commit or not commit.parent_id:
                break
            current = commit.parent_id

        branch.head_id = current
        return self.commits.get(current)

    def create_branch(self, name: str) -> PresetBranch:
        """Create a new branch from current HEAD."""
        head = self.branches[self.current_branch].head_id
        branch = PresetBranch(name, head, time.time())
        self.branches[name] = branch
        return branch

    def switch_branch(self, name: str) -> bool:
        """Switch to a different branch."""
        if name in self.branches:
            self.current_branch = name
            return True
        return False

    def merge(self, source_branch: str) -> PresetCommit | None:
        """Merge source branch into current branch."""
        source = self.branches.get(source_branch)
        if not source or not source.head_id:
            return None

        source_commit = self.commits.get(source.head_id)
        if not source_commit:
            return None

        head = self.get_head()
        if head:
            # Simple merge: overlay source params
            merged = dict(head.params)
            merged.update(source_commit.params)
        else:
            merged = dict(source_commit.params)

        return self.commit(merged, f"Merge {source_branch} → {self.current_branch}")

    def save(self, path: str) -> str:
        """Save VCS state to file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = {
            "name": self.name,
            "current_branch": self.current_branch,
            "branches": {
                name: {"head": b.head_id, "created": b.created_at}
                for name, b in self.branches.items()
            },
            "commits": {
                cid: c.to_dict() for cid, c in self.commits.items()
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path

    def load(self, path: str) -> bool:
        """Load VCS state from file."""
        if not os.path.exists(path):
            return False

        with open(path) as f:
            data = json.load(f)

        self.name = data.get("name", "Untitled")
        self.current_branch = data.get("current_branch", "main")

        self.branches = {}
        for name, b in data.get("branches", {}).items():
            self.branches[name] = PresetBranch(name, b.get("head"), b.get("created", 0))

        self.commits = {}
        for cid, c in data.get("commits", {}).items():
            self.commits[cid] = PresetCommit(
                commit_id=c["id"],
                parent_id=c.get("parent"),
                timestamp=c.get("timestamp", 0),
                message=c.get("message", ""),
                params=c.get("params", {}),
                author=c.get("author", "DUBFORGE"),
            )

        return True

    def get_summary(self) -> dict:
        return {
            "name": self.name,
            "branch": self.current_branch,
            "branches": list(self.branches.keys()),
            "total_commits": len(self.commits),
            "head": self.branches[self.current_branch].head_id,
        }


def main() -> None:
    print("Preset Version Control Engine")

    vcs = PresetVCS("Brutal Bass")

    # Initial commit
    c1 = vcs.commit({"freq": 55, "drive": 0.3, "cutoff": 800},
                      "Initial bass patch")
    print(f"  Commit 1: {c1.commit_id}")

    # Iterate
    c2 = vcs.commit({"freq": 55, "drive": 0.6, "cutoff": 500, "resonance": 0.5},
                      "More aggressive")
    print(f"  Commit 2: {c2.commit_id}")

    c3 = vcs.commit({"freq": 40, "drive": 0.8, "cutoff": 400, "resonance": 0.7},
                      "Filthy settings")
    print(f"  Commit 3: {c3.commit_id}")

    # Diff
    diff = vcs.diff(c1.commit_id, c3.commit_id)
    print(f"\n  Diff c1→c3: {diff.to_dict()}")

    # History
    log = vcs.log()
    print("\n  History:")
    for c in log:
        print(f"    {c.commit_id}: {c.message}")

    # Branch
    vcs.create_branch("experiment")
    vcs.switch_branch("experiment")
    c4 = vcs.commit({"freq": 80, "drive": 0.2, "cutoff": 2000},
                      "Experimental clean bass")
    print(f"\n  Experiment: {c4.commit_id}")

    # Merge back
    vcs.switch_branch("main")
    merged = vcs.merge("experiment")
    print(f"  Merged: {merged.commit_id if merged else 'None'}")

    # Summary
    print(f"\n  Summary: {vcs.get_summary()}")

    # Save
    path = vcs.save("output/presets/brutal_bass_vcs.json")
    print(f"  Saved: {path}")

    print("Done.")


if __name__ == "__main__":
    main()
