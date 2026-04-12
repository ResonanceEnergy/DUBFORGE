"""
DUBFORGE Engine — Config Loader

Centralized YAML config reader so engine modules can load their
configs at runtime instead of hardcoding values.

Also provides the canonical PHI/FIBONACCI constants that all
modules should import from here (or from phi_core).

Usage:
    from engine.config_loader import load_config, PHI, FIBONACCI

    cfg = load_config("rco_psbs_vip_delta_v1.1")
    rco_profiles = cfg["rco"]["profiles"]
"""

from pathlib import Path
from typing import Any, Optional
import os
import platform

from engine.log import get_logger

_log = get_logger("dubforge.config")

# ═══════════════════════════════════════════════════════════════════════════
# CANONICAL CONSTANTS — single source of truth
# ═══════════════════════════════════════════════════════════════════════════

PHI = 1.6180339887498948482
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
A4_432 = 432.0
A4_440 = 440.0

# ═══════════════════════════════════════════════════════════════════════════
# PLATFORM DETECTION — Apple Silicon optimization
# ═══════════════════════════════════════════════════════════════════════════

IS_ARM64 = platform.machine() == "arm64"
IS_MACOS = platform.system() == "Darwin"
IS_APPLE_SILICON = IS_ARM64 and IS_MACOS

def _detect_cpu_cores() -> dict[str, int]:
    """Detect CPU core topology. On Apple Silicon, distinguishes P/E cores."""
    info: dict[str, int] = {"total": os.cpu_count() or 4, "performance": 0, "efficiency": 0}
    if IS_MACOS:
        try:
            import subprocess
            # Try perflevel keys first (works on all Apple Silicon)
            for key, sysctl_keys in [
                ("performance", ["hw.perflevel0.logicalcpu", "hw.performancecores"]),
                ("efficiency", ["hw.perflevel1.logicalcpu", "hw.efficiencycores"]),
            ]:
                for sk in sysctl_keys:
                    r = subprocess.run(["sysctl", "-n", sk], capture_output=True, text=True, timeout=2)
                    if r.returncode == 0 and r.stdout.strip().isdigit():
                        info[key] = int(r.stdout.strip())
                        break
        except Exception:
            pass
    if info["performance"] == 0:
        info["performance"] = info["total"]
    return info

CPU_CORES = _detect_cpu_cores()

# Optimal worker counts for different workloads
WORKERS_COMPUTE = CPU_CORES["performance"]          # CPU-bound DSP
WORKERS_IO = CPU_CORES["total"]                     # I/O-bound file ops

# ═══════════════════════════════════════════════════════════════════════════
# ACCELERATION DETECTION — GPU (MLX), vDSP (Accelerate framework)
# ═══════════════════════════════════════════════════════════════════════════

HAS_MLX = False
HAS_VDSP = False

if IS_APPLE_SILICON:
    try:
        import mlx.core  # noqa: F401  # type: ignore[import-not-found]
        HAS_MLX = True
    except ImportError:
        pass

if IS_MACOS:
    import ctypes.util as _cu
    HAS_VDSP = _cu.find_library("Accelerate") is not None

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG DIRECTORY
# ═══════════════════════════════════════════════════════════════════════════

CONFIGS_DIR = Path(__file__).parent.parent / "configs"

# In-memory cache of loaded configs
_config_cache: dict[str, dict] = {}


def _find_yaml_parser():
    """Find available YAML parser. Tries PyYAML first, falls back to manual."""
    try:
        import yaml
        return yaml
    except ImportError:
        return None


def _parse_yaml_minimal(text: str) -> dict:
    """
    Minimal YAML-subset parser for DUBFORGE configs.
    Handles: scalars, lists (- item), nested mappings (key: value),
    quoted strings, numbers, booleans. Enough for our config files.
    Does NOT handle anchors, flow collections, or multi-doc.
    """
    result: dict = {}
    stack: list[tuple[int, dict | list]] = [(-1, result)]
    current_list_key: Optional[str] = None

    for line in text.split("\n"):
        stripped = line.strip()

        # Skip blank lines, comments, and document markers
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue

        # Calculate indent level
        indent = len(line) - len(line.lstrip())

        # Pop stack to correct nesting level
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        _, container = stack[-1]

        # List item: "- value" or "- key: value"
        if stripped.startswith("- "):
            item_str = stripped[2:].strip()
            if isinstance(container, dict):
                # Need to find the list this belongs to
                if current_list_key and current_list_key in container:
                    target_list = container[current_list_key]
                    if isinstance(target_list, list):
                        parsed = _parse_value(item_str)
                        if ":" in item_str and not isinstance(parsed, str):
                            # "- key: value" as dict entry in list
                            k, v = item_str.split(":", 1)
                            entry = {k.strip(): _parse_value(v.strip())}
                            target_list.append(entry)
                        else:
                            target_list.append(parsed)
                        continue
                # Fallback: append to last list-type value
                for k in reversed(list(container.keys())):
                    if isinstance(container[k], list):
                        container[k].append(_parse_value(item_str))
                        break
            elif isinstance(container, list):
                container.append(_parse_value(item_str))
            continue

        # Key-value pair: "key: value" or "key:"
        if ":" in stripped:
            colon_pos = stripped.index(":")
            key = stripped[:colon_pos].strip()
            val_str = stripped[colon_pos + 1:].strip()

            # Remove inline comments
            if val_str and "#" in val_str:
                # Don't strip # inside quotes
                if not (val_str.startswith('"') or val_str.startswith("'")):
                    comment_pos = val_str.index("#")
                    val_str = val_str[:comment_pos].strip()

            if not val_str or val_str == ">":
                # Block scalar or nested mapping — start empty
                if isinstance(container, dict):
                    container[key] = {}
                    stack.append((indent, container[key]))
                    current_list_key = key
                continue

            parsed_val = _parse_value(val_str)

            if isinstance(container, dict):
                container[key] = parsed_val
                current_list_key = key

                # If value looks like it could be followed by list items
                if isinstance(parsed_val, (dict, list)):
                    stack.append((indent, container[key]))

    return result


def _parse_value(val: str) -> Any:
    """Parse a YAML scalar value."""
    if not val:
        return ""

    # Quoted string
    if (val.startswith('"') and val.endswith('"')) or \
       (val.startswith("'") and val.endswith("'")):
        return val[1:-1]

    # Boolean
    lower = val.lower()
    if lower in ("true", "yes", "on"):
        return True
    if lower in ("false", "no", "off"):
        return False
    if lower == "null" or lower == "~":
        return None

    # List inline: [a, b, c]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1]
        if not inner.strip():
            return []
        return [_parse_value(item.strip()) for item in inner.split(",")]

    # Number
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        pass

    return val


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def load_config(name: str, reload: bool = False) -> dict:
    """
    Load a YAML config by name (without extension).

    Examples:
        load_config("memory_v1")
        load_config("rco_psbs_vip_delta_v1.1")
        load_config("serum2_module_pack_v1")
        load_config("fibonacci_blueprint_pack_v1")

    Returns parsed dict. Caches results; use reload=True to force re-read.
    """
    if name in _config_cache and not reload:
        return _config_cache[name]

    # Try with .yaml extension
    path = CONFIGS_DIR / f"{name}.yaml"
    if not path.exists():
        path = CONFIGS_DIR / f"{name}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {name} (searched {CONFIGS_DIR})")

    text = path.read_text(encoding="utf-8")

    yaml_mod = _find_yaml_parser()
    if yaml_mod:
        data = yaml_mod.safe_load(text) or {}
    else:
        data = _parse_yaml_minimal(text)

    _config_cache[name] = data
    return data


def get_config_value(name: str, *keys: str, default: Any = None) -> Any:
    """
    Get a nested value from a config.

    Example:
        get_config_value("memory_v1", "recall", "recency_half_life_s", default=86400)
    """
    cfg = load_config(name)
    current = cfg
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def list_configs() -> list[str]:
    """List all available config names."""
    if not CONFIGS_DIR.exists():
        return []
    return [
        p.stem for p in CONFIGS_DIR.iterdir()
        if p.suffix in (".yaml", ".yml") and p.is_file()
    ]


# ═══════════════════════════════════════════════════════════════════════════
# HOT-RELOAD (Session 131) — watch configs for changes
# ═══════════════════════════════════════════════════════════════════════════

# Modification timestamps for change detection
_config_mtimes: dict[str, float] = {}


def _config_path(name: str) -> Optional[Path]:
    """Resolve a config name to its file path."""
    for ext in (".yaml", ".yml"):
        p = CONFIGS_DIR / f"{name}{ext}"
        if p.exists():
            return p
    return None


def reload_if_changed(name: str) -> bool:
    """Reload a config if its file has been modified since last load.

    Returns True if the config was reloaded.
    """
    path = _config_path(name)
    if path is None:
        return False

    current_mtime = path.stat().st_mtime
    prev_mtime = _config_mtimes.get(name, 0.0)

    if current_mtime > prev_mtime:
        load_config(name, reload=True)
        _config_mtimes[name] = current_mtime
        _log.info("Hot-reloaded config: %s (mtime %.0f → %.0f)", name, prev_mtime, current_mtime)
        return True
    return False


def reload_all_changed() -> list[str]:
    """Check all known configs for changes and reload any that were modified.

    Returns list of config names that were reloaded.
    """
    reloaded: list[str] = []
    for name in list_configs():
        if reload_if_changed(name):
            reloaded.append(name)
    return reloaded


def watch_configs_once() -> list[str]:
    """Single-pass config watcher.  Call periodically for hot-reload behavior.

    Returns list of reloaded config names.
    """
    return reload_all_changed()


# ═══════════════════════════════════════════════════════════════════════════
# Config Validation
# ═══════════════════════════════════════════════════════════════════════════

# Minimal schema: config_name → set of required top-level keys
_REQUIRED_KEYS: dict[str, set[str]] = {
    "fibonacci_blueprint_pack_v1": {"version", "pack"},
    "rco_psbs_vip_delta_v1.1":    {"rco_profiles", "psbs_presets"},
    "serum2_module_pack_v1":      {"version", "pack"},
    "memory_v1":                  {"meta", "storage"},
    "sb_corpus_v1":               {"albums"},
}


def validate_config(name: str) -> list[str]:
    """
    Validate a config file against the schema.
    Returns a list of error strings (empty = valid).
    """
    errors: list[str] = []
    try:
        data = load_config(name)
    except FileNotFoundError:
        return [f"{name}: file not found"]
    except Exception as e:
        return [f"{name}: parse error — {e}"]

    if not isinstance(data, dict):
        return [f"{name}: root is not a mapping (got {type(data).__name__})"]

    required = _REQUIRED_KEYS.get(name)
    if required:
        missing = required - set(data.keys())
        if missing:
            errors.append(f"{name}: missing required keys: {', '.join(sorted(missing))}")

    return errors


def validate_all_configs() -> dict[str, list[str]]:
    """Validate every config in configs/. Returns {name: [errors]}."""
    results: dict[str, list[str]] = {}
    for name in list_configs():
        errs = validate_config(name)
        if errs:
            results[name] = errs
    return results


def main() -> None:
    """Print all available configs and platform info."""
    print("[CONFIG LOADER] Platform:")
    print(f"  Apple Silicon: {'YES' if IS_APPLE_SILICON else 'no'}")
    print(f"  CPU cores:     {CPU_CORES['total']} total ({CPU_CORES['performance']}P + {CPU_CORES['efficiency']}E)")
    print(f"  Workers:       {WORKERS_COMPUTE} (compute) / {WORKERS_IO} (I/O)")
    print()
    print("[CONFIG LOADER] Available configs:")
    print("-" * 40)
    for name in sorted(list_configs()):
        try:
            cfg = load_config(name)
            keys = list(cfg.keys()) if isinstance(cfg, dict) else ["(not a dict)"]
            print(f"  {name}")
            for k in keys:
                print(f"    • {k}")
        except Exception as e:
            _log.warning("Failed to load config %s: %s", name, e)
    print()


if __name__ == "__main__":
    main()
