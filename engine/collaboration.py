"""
DUBFORGE — Collaboration Engine  (Session 196)

Multi-user collaboration: project sharing, change tracking,
merge conflicts, real-time sync protocol.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from engine.config_loader import PHI
@dataclass
class Change:
    """A single tracked change."""
    change_id: str
    user: str
    timestamp: float
    change_type: str  # "add", "modify", "delete"
    target: str  # what was changed
    data: dict = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.change_id,
            "user": self.user,
            "timestamp": self.timestamp,
            "type": self.change_type,
            "target": self.target,
            "data": self.data,
            "description": self.description,
        }


@dataclass
class CollabUser:
    """A collaborator."""
    username: str
    role: str = "editor"  # owner, editor, viewer
    joined: float = 0.0
    last_active: float = 0.0
    changes_count: int = 0

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "role": self.role,
            "changes": self.changes_count,
        }


@dataclass
class CollabProject:
    """A collaborative project."""
    project_id: str
    name: str
    owner: str
    users: list[CollabUser] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    state: dict = field(default_factory=dict)
    created: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.project_id,
            "name": self.name,
            "owner": self.owner,
            "users": [u.to_dict() for u in self.users],
            "changes": len(self.changes),
            "state_keys": list(self.state.keys()),
        }


class MergeConflict:
    """Represents a merge conflict."""

    def __init__(self, target: str, local_value: Any,
                 remote_value: Any, user_a: str, user_b: str):
        self.target = target
        self.local_value = local_value
        self.remote_value = remote_value
        self.user_a = user_a
        self.user_b = user_b
        self.resolved = False
        self.resolution: Any = None

    def resolve_local(self) -> None:
        """Keep local value."""
        self.resolution = self.local_value
        self.resolved = True

    def resolve_remote(self) -> None:
        """Keep remote value."""
        self.resolution = self.remote_value
        self.resolved = True

    def resolve_phi_blend(self) -> None:
        """PHI-weighted blend (if numeric)."""
        try:
            a = float(self.local_value)
            b = float(self.remote_value)
            self.resolution = a / PHI + b * (1 - 1 / PHI)
            self.resolved = True
        except (TypeError, ValueError):
            self.resolve_local()

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "local": self.local_value,
            "remote": self.remote_value,
            "user_a": self.user_a,
            "user_b": self.user_b,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }


class CollaborationEngine:
    """Engine for multi-user collaboration."""

    def __init__(self, data_dir: str = "output/collab"):
        self.data_dir = data_dir
        self.projects: dict[str, CollabProject] = {}
        os.makedirs(data_dir, exist_ok=True)

    def create_project(self, name: str, owner: str) -> CollabProject:
        """Create a new collaborative project."""
        pid = hashlib.sha1(
            f"{name}{owner}{time.time()}".encode()
        ).hexdigest()[:12]

        user = CollabUser(
            username=owner, role="owner",
            joined=time.time(), last_active=time.time(),
        )

        project = CollabProject(
            project_id=pid,
            name=name,
            owner=owner,
            users=[user],
            created=time.time(),
        )
        self.projects[pid] = project
        self._save_project(project)
        return project

    def join_project(self, project_id: str, username: str,
                     role: str = "editor") -> bool:
        """Add user to project."""
        project = self.projects.get(project_id)
        if not project:
            return False

        for u in project.users:
            if u.username == username:
                return True  # already joined

        user = CollabUser(
            username=username, role=role,
            joined=time.time(), last_active=time.time(),
        )
        project.users.append(user)
        self._save_project(project)
        return True

    def make_change(self, project_id: str, user: str,
                    change_type: str, target: str,
                    data: dict | None = None, description: str = "") -> Change | None:
        """Record a change."""
        project = self.projects.get(project_id)
        if not project:
            return None

        # Verify user
        found = False
        for u in project.users:
            if u.username == user:
                if u.role == "viewer":
                    return None
                u.last_active = time.time()
                u.changes_count += 1
                found = True
                break

        if not found:
            return None

        cid = hashlib.sha1(
            f"{user}{target}{time.time()}".encode()
        ).hexdigest()[:10]

        change = Change(
            change_id=cid,
            user=user,
            timestamp=time.time(),
            change_type=change_type,
            target=target,
            data=data or {},
            description=description,
        )

        # Apply to state
        if change_type == "add" or change_type == "modify":
            project.state[target] = data or {}
        elif change_type == "delete":
            project.state.pop(target, None)

        project.changes.append(change)
        self._save_project(project)
        return change

    def detect_conflicts(self, project_id: str,
                         window_seconds: float = 60.0) -> list[MergeConflict]:
        """Detect conflicts from overlapping changes."""
        project = self.projects.get(project_id)
        if not project:
            return []

        now = time.time()
        recent = [c for c in project.changes
                  if now - c.timestamp < window_seconds]

        # Group by target
        by_target: dict[str, list[Change]] = {}
        for c in recent:
            if c.target not in by_target:
                by_target[c.target] = []
            by_target[c.target].append(c)

        conflicts: list[MergeConflict] = []
        for target, changes in by_target.items():
            if len(changes) < 2:
                continue

            # Different users editing same target
            users_seen: dict[str, Change] = {}
            for c in changes:
                if c.user in users_seen:
                    continue
                for other_user, other_change in users_seen.items():
                    if c.user != other_user:
                        conflict = MergeConflict(
                            target=target,
                            local_value=other_change.data,
                            remote_value=c.data,
                            user_a=other_user,
                            user_b=c.user,
                        )
                        conflicts.append(conflict)
                users_seen[c.user] = c

        return conflicts

    def get_history(self, project_id: str,
                    limit: int = 50) -> list[dict]:
        """Get change history."""
        project = self.projects.get(project_id)
        if not project:
            return []

        history = sorted(project.changes,
                          key=lambda c: c.timestamp, reverse=True)
        return [c.to_dict() for c in history[:limit]]

    def get_user_changes(self, project_id: str,
                         username: str) -> list[dict]:
        """Get changes by a specific user."""
        project = self.projects.get(project_id)
        if not project:
            return []
        return [c.to_dict() for c in project.changes
                if c.user == username]

    def export_state(self, project_id: str) -> dict:
        """Export current project state."""
        project = self.projects.get(project_id)
        if not project:
            return {}
        return {
            "project": project.to_dict(),
            "state": project.state,
            "exported": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _save_project(self, project: CollabProject) -> None:
        """Persist project to disk."""
        path = os.path.join(self.data_dir,
                             f"{project.project_id}.json")
        data = {
            **project.to_dict(),
            "state": project.state,
            "change_log": [c.to_dict() for c in project.changes[-100:]],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def list_projects(self) -> list[dict]:
        """List all projects."""
        return [p.to_dict() for p in self.projects.values()]

    def get_summary(self) -> dict:
        """Get collaboration summary."""
        total_users = set()
        total_changes = 0
        for p in self.projects.values():
            for u in p.users:
                total_users.add(u.username)
            total_changes += len(p.changes)

        return {
            "projects": len(self.projects),
            "users": len(total_users),
            "total_changes": total_changes,
        }


def main() -> None:
    print("Collaboration Engine")

    collab = CollaborationEngine()

    # Create project
    project = collab.create_project("PHI Sessions", "producer_1")
    print(f"  Project: {project.name} [{project.project_id}]")

    # Add collaborator
    collab.join_project(project.project_id, "producer_2")
    print(f"  Users: {[u.username for u in project.users]}")

    # Make changes
    c1 = collab.make_change(
        project.project_id, "producer_1",
        "add", "track_1/bass",
        {"type": "wobble", "freq": 80, "phi_ratio": PHI},
        "Added wobble bass"
    )
    c2 = collab.make_change(
        project.project_id, "producer_2",
        "modify", "track_1/bass",
        {"type": "growl", "freq": 90, "phi_ratio": PHI},
        "Changed bass to growl"
    )

    if c1 and c2:
        print(f"  Changes: {c1.change_id}, {c2.change_id}")

    # Check conflicts
    conflicts = collab.detect_conflicts(project.project_id, window_seconds=300)
    print(f"  Conflicts: {len(conflicts)}")
    for conf in conflicts:
        conf.resolve_phi_blend()
        print(f"    {conf.target}: resolved={conf.resolved}")

    # Summary
    summary = collab.get_summary()
    print(f"\n  Summary: {summary}")
    print("Done.")


if __name__ == "__main__":
    main()
