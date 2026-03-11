"""
DUBFORGE — Session Logger  (Session 230)

Production session logging — track decisions, A/B results,
render history, module usage, phi metrics.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from engine.config_loader import PHI
@dataclass
class LogEntry:
    """A session log entry."""
    timestamp: float
    category: str
    message: str
    data: dict = field(default_factory=dict)
    level: str = "info"  # info, warn, error, debug, milestone

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "time_str": time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(self.timestamp),
            ),
            "category": self.category,
            "level": self.level,
            "message": self.message,
            "data": self.data,
        }


@dataclass
class SessionStats:
    """Session statistics."""
    total_entries: int = 0
    renders: int = 0
    errors: int = 0
    modules_used: list[str] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_entries": self.total_entries,
            "renders": self.renders,
            "errors": self.errors,
            "modules_used": len(self.modules_used),
            "milestones": self.milestones,
            "duration_s": round(self.duration_s, 1),
        }


class SessionLogger:
    """Log production session activity."""

    def __init__(self, session_name: str = "session"):
        self.session_name = session_name
        self.entries: list[LogEntry] = []
        self.start_time = time.time()
        self._module_usage: dict[str, int] = {}

    def log(self, category: str, message: str,
            level: str = "info", **data) -> LogEntry:
        """Add a log entry."""
        entry = LogEntry(
            timestamp=time.time(),
            category=category,
            message=message,
            level=level,
            data=data,
        )
        self.entries.append(entry)
        return entry

    def info(self, message: str, **data) -> LogEntry:
        return self.log("general", message, "info", **data)

    def warn(self, message: str, **data) -> LogEntry:
        return self.log("general", message, "warn", **data)

    def error(self, message: str, **data) -> LogEntry:
        return self.log("general", message, "error", **data)

    def milestone(self, message: str, **data) -> LogEntry:
        return self.log("milestone", message, "milestone", **data)

    def log_render(self, module: str, output: str,
                   duration_s: float = 0, **data) -> LogEntry:
        """Log a render operation."""
        self._module_usage[module] = self._module_usage.get(module, 0) + 1
        return self.log("render", f"Rendered {module} -> {output}",
                        "info", module=module, output=output,
                        duration_s=duration_s, **data)

    def log_module(self, module: str, action: str = "used",
                   **data) -> LogEntry:
        """Log module usage."""
        self._module_usage[module] = self._module_usage.get(module, 0) + 1
        return self.log("module", f"{module}: {action}",
                        "info", module=module, **data)

    def log_ab_test(self, name: str, choice: str,
                    **data) -> LogEntry:
        """Log an A/B test decision."""
        return self.log("ab_test", f"A/B: {name} -> {choice}",
                        "info", test_name=name, choice=choice, **data)

    def get_stats(self) -> SessionStats:
        """Get session statistics."""
        renders = [e for e in self.entries if e.category == "render"]
        errors = [e for e in self.entries if e.level == "error"]
        milestones = [e.message for e in self.entries
                      if e.level == "milestone"]

        return SessionStats(
            total_entries=len(self.entries),
            renders=len(renders),
            errors=len(errors),
            modules_used=list(self._module_usage.keys()),
            milestones=milestones,
            duration_s=time.time() - self.start_time,
        )

    def get_recent(self, count: int = 10) -> list[dict]:
        """Get recent log entries."""
        return [e.to_dict() for e in self.entries[-count:]]

    def search(self, query: str,
               category: str | None = None,
               level: str | None = None) -> list[LogEntry]:
        """Search log entries."""
        results: list[LogEntry] = []
        q = query.lower()

        for e in self.entries:
            if category and e.category != category:
                continue
            if level and e.level != level:
                continue
            if q in e.message.lower():
                results.append(e)

        return results

    def module_rankings(self) -> list[tuple[str, int]]:
        """Get modules ranked by usage."""
        return sorted(
            self._module_usage.items(),
            key=lambda x: x[1],
            reverse=True,
        )

    def save(self, path: str) -> None:
        """Save session log."""
        data = {
            "session_name": self.session_name,
            "start_time": self.start_time,
            "stats": self.get_stats().to_dict(),
            "entries": [e.to_dict() for e in self.entries],
            "module_usage": self._module_usage,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        """Load session log."""
        with open(path) as f:
            data = json.load(f)

        self.session_name = data.get("session_name", "loaded")
        self.start_time = data.get("start_time", time.time())
        self._module_usage = data.get("module_usage", {})

        self.entries = []
        for ed in data.get("entries", []):
            self.entries.append(LogEntry(
                timestamp=ed["timestamp"],
                category=ed["category"],
                message=ed["message"],
                level=ed["level"],
                data=ed.get("data", {}),
            ))

    def phi_summary(self) -> dict:
        """PHI-themed session summary."""
        stats = self.get_stats()
        return {
            "session": self.session_name,
            "phi_ratio": round(
                stats.renders / max(1, stats.errors) / PHI, 3
            ),
            "golden_score": round(
                len(self._module_usage) / PHI, 1
            ),
            "total_actions": stats.total_entries,
            "milestones": stats.milestones,
        }


def main() -> None:
    print("Session Logger")
    logger = SessionLogger("test_session")

    # Simulate session
    logger.info("Session started")
    logger.log_module("sub_bass", "generated 40Hz sub")
    logger.log_render("drum_generator", "output/drums/kick.wav", 0.5)
    logger.log_render("wobble_bass", "output/bass/wobble.wav", 1.2)
    logger.log_ab_test("reverb_type", "plate", reason="warmer tail")
    logger.milestone("First drop section complete")
    logger.log_module("mastering_chain", "applied to master")
    logger.warn("Peak at -0.1dB, close to ceiling")

    # Stats
    stats = logger.get_stats()
    d = stats.to_dict()
    print(f"  Entries: {d['total_entries']}")
    print(f"  Renders: {d['renders']}")
    print(f"  Modules: {d['modules_used']}")
    print(f"  Milestones: {d['milestones']}")

    # Rankings
    rankings = logger.module_rankings()
    for mod, count in rankings:
        print(f"    {mod}: {count}x")

    # PHI summary
    phi = logger.phi_summary()
    print(f"\n  PHI score: {phi['golden_score']}")

    print("Done.")


if __name__ == "__main__":
    main()
