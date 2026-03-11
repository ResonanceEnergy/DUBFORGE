"""
DUBFORGE — Final Audit  (Session 143)

Comprehensive technical audit of the entire codebase.
Counts modules, tests, presets, exports, lines of code,
and produces a structured audit report.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.config_loader import PHI
@dataclass
class AuditReport:
    """Comprehensive audit report."""
    engine_modules: int = 0
    test_files: int = 0
    config_files: int = 0
    total_python_loc: int = 0
    total_test_loc: int = 0
    modules_with_main: int = 0
    modules_with_banks: int = 0
    export_functions: int = 0
    phi_references: int = 0
    fibonacci_references: int = 0
    wav_writers: int = 0
    version: str = ""
    issues: list[str] = field(default_factory=list)

    @property
    def health_score(self) -> float:
        """Overall health score 0.0-1.0."""
        checks = [
            self.engine_modules >= 50,
            self.test_files >= 40,
            self.modules_with_main >= 40,
            self.total_python_loc >= 10000,
            self.total_test_loc >= 5000,
            self.export_functions >= 20,
            self.phi_references >= 30,
            self.wav_writers >= 10,
            len(self.issues) < 5,
        ]
        return sum(checks) / len(checks)


def count_lines(filepath: str) -> int:
    """Count non-empty lines in a file."""
    try:
        with open(filepath) as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def count_pattern(filepath: str, pattern: str) -> int:
    """Count occurrences of a pattern in a file."""
    try:
        with open(filepath) as f:
            content = f.read()
        return content.lower().count(pattern.lower())
    except Exception:
        return 0


def audit_engine_dir(engine_dir: str = "engine") -> dict[str, Any]:
    """Audit the engine directory."""
    p = Path(engine_dir)
    if not p.is_dir():
        return {"error": "engine directory not found"}

    modules = []
    for f in sorted(p.glob("*.py")):
        if f.name == "__init__.py":
            continue
        info = {
            "name": f.stem,
            "loc": count_lines(str(f)),
            "has_main": count_pattern(str(f), "def main()") > 0,
            "has_banks": count_pattern(str(f), "ALL_") > 0,
            "has_export": count_pattern(str(f), "def export_") > 0,
            "has_write_wav": count_pattern(str(f), "_write_wav") > 0,
            "phi_refs": count_pattern(str(f), "PHI"),
            "fib_refs": count_pattern(str(f), "fibonacci") + count_pattern(str(f), "FIBONACCI"),
        }
        modules.append(info)

    return {
        "module_count": len(modules),
        "total_loc": sum(m["loc"] for m in modules),
        "with_main": sum(1 for m in modules if m["has_main"]),
        "with_banks": sum(1 for m in modules if m["has_banks"]),
        "with_export": sum(1 for m in modules if m["has_export"]),
        "with_write_wav": sum(1 for m in modules if m["has_write_wav"]),
        "total_phi_refs": sum(m["phi_refs"] for m in modules),
        "total_fib_refs": sum(m["fib_refs"] for m in modules),
        "modules": modules,
    }


def audit_tests_dir(tests_dir: str = "tests") -> dict[str, Any]:
    """Audit the tests directory."""
    p = Path(tests_dir)
    if not p.is_dir():
        return {"error": "tests directory not found"}

    test_files = list(p.glob("test_*.py"))
    return {
        "test_file_count": len(test_files),
        "total_loc": sum(count_lines(str(f)) for f in test_files),
        "files": [f.name for f in sorted(test_files)],
    }


def audit_configs(config_dir: str = "configs") -> dict[str, Any]:
    """Audit configuration files."""
    p = Path(config_dir)
    if not p.is_dir():
        return {"error": "configs directory not found"}

    configs = list(p.glob("*.yaml")) + list(p.glob("*.yml"))
    return {
        "config_count": len(configs),
        "files": [f.name for f in sorted(configs)],
    }


def read_version() -> str:
    """Read version from pyproject.toml."""
    try:
        with open("pyproject.toml") as f:
            for line in f:
                if line.strip().startswith("version"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"


def run_full_audit() -> AuditReport:
    """Run a complete audit of the DUBFORGE project."""
    report = AuditReport()
    report.version = read_version()

    # Engine audit
    eng = audit_engine_dir()
    report.engine_modules = eng.get("module_count", 0)
    report.total_python_loc = eng.get("total_loc", 0)
    report.modules_with_main = eng.get("with_main", 0)
    report.modules_with_banks = eng.get("with_banks", 0)
    report.export_functions = eng.get("with_export", 0)
    report.wav_writers = eng.get("with_write_wav", 0)
    report.phi_references = eng.get("total_phi_refs", 0)
    report.fibonacci_references = eng.get("total_fib_refs", 0)

    # Tests audit
    tst = audit_tests_dir()
    report.test_files = tst.get("test_file_count", 0)
    report.total_test_loc = tst.get("total_loc", 0)

    # Config audit
    audit_configs()

    # Issue detection
    if report.engine_modules < 50:
        report.issues.append(f"Low module count: {report.engine_modules}")
    if report.test_files < report.engine_modules * 0.7:
        report.issues.append(f"Test coverage gap: {report.test_files} test files for {report.engine_modules} modules")
    if report.phi_references < 30:
        report.issues.append(f"Low phi integration: {report.phi_references} references")

    return report


def export_audit_report(report: AuditReport,
                        output_dir: str = "output/analysis") -> str:
    """Export audit report as JSON."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = str(Path(output_dir) / "audit_report.json")

    data = {
        "version": report.version,
        "engine_modules": report.engine_modules,
        "test_files": report.test_files,
        "total_python_loc": report.total_python_loc,
        "total_test_loc": report.total_test_loc,
        "modules_with_main": report.modules_with_main,
        "modules_with_banks": report.modules_with_banks,
        "export_functions": report.export_functions,
        "phi_references": report.phi_references,
        "fibonacci_references": report.fibonacci_references,
        "wav_writers": report.wav_writers,
        "health_score": round(report.health_score, 4),
        "issues": report.issues,
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def main() -> None:
    report = run_full_audit()
    print(f"Final Audit — DUBFORGE v{report.version}")
    print(f"  Engine modules:  {report.engine_modules}")
    print(f"  Test files:      {report.test_files}")
    print(f"  Python LOC:      {report.total_python_loc}")
    print(f"  Test LOC:        {report.total_test_loc}")
    print(f"  Modules w/main:  {report.modules_with_main}")
    print(f"  Export functions: {report.export_functions}")
    print(f"  WAV writers:     {report.wav_writers}")
    print(f"  Phi references:  {report.phi_references}")
    print(f"  Health score:    {report.health_score:.1%}")
    if report.issues:
        print(f"  Issues ({len(report.issues)}):")
        for issue in report.issues:
            print(f"    - {issue}")
    else:
        print("  No issues detected")
    export_audit_report(report)


if __name__ == "__main__":
    main()
