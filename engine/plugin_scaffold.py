"""
DUBFORGE — Plugin Scaffold  (Session 136)

Architecture for user-contributed modules.
Plugin interface, discovery, and registration.
"""

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from engine.config_loader import PHI
@dataclass
class PluginMeta:
    """Metadata for a registered plugin."""
    name: str
    version: str
    author: str
    category: str  # synth, fx, analysis, export
    description: str = ""


@dataclass
class PluginRegistry:
    """Central registry for DUBFORGE plugins."""
    plugins: dict[str, "PluginEntry"] = field(default_factory=dict)

    def register(
        self,
        name: str,
        main_fn: Callable,
        meta: Optional[PluginMeta] = None,
        presets: Optional[dict] = None,
    ) -> None:
        entry = PluginEntry(
            name=name,
            main_fn=main_fn,
            meta=meta or PluginMeta(name, "0.1.0", "unknown", "synth"),
            presets=presets or {},
        )
        self.plugins[name] = entry

    def unregister(self, name: str) -> bool:
        return self.plugins.pop(name, None) is not None

    def get(self, name: str) -> Optional["PluginEntry"]:
        return self.plugins.get(name)

    def list_plugins(self) -> list[str]:
        return sorted(self.plugins.keys())

    def list_by_category(self, category: str) -> list[str]:
        return sorted(
            n for n, e in self.plugins.items()
            if e.meta.category == category
        )

    def run(self, name: str, **kwargs: Any) -> Any:
        entry = self.get(name)
        if entry is None:
            raise KeyError(f"Plugin not found: {name}")
        return entry.main_fn(**kwargs)


@dataclass
class PluginEntry:
    """A registered plugin entry."""
    name: str
    main_fn: Callable
    meta: PluginMeta
    presets: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# PLUGIN DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════

def discover_plugins(plugin_dir: str = "plugins") -> list[str]:
    """Scan a directory for Python plugin modules."""
    p = Path(plugin_dir)
    if not p.is_dir():
        return []
    return sorted(
        f.stem for f in p.glob("*.py")
        if f.stem != "__init__" and not f.stem.startswith("_")
    )


def load_plugin(module_path: str, registry: PluginRegistry) -> bool:
    """Load a plugin module and register it."""
    try:
        mod = importlib.import_module(module_path)
        if hasattr(mod, "register_plugin"):
            mod.register_plugin(registry)
            return True
        elif hasattr(mod, "main"):
            meta = PluginMeta(
                name=module_path.split(".")[-1],
                version=getattr(mod, "__version__", "0.1.0"),
                author=getattr(mod, "__author__", "unknown"),
                category=getattr(mod, "__category__", "synth"),
                description=getattr(mod, "__doc__", ""),
            )
            registry.register(
                meta.name,
                mod.main,
                meta,
                getattr(mod, "ALL_PRESETS", {}),
            )
            return True
    except Exception:
        pass
    return False


def create_plugin_template(name: str, category: str = "synth",
                           output_dir: str = "plugins") -> str:
    """Generate a plugin template .py file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = os.path.join(output_dir, f"{name}.py")
    template = f'''"""
DUBFORGE Plugin — {name}
Category: {category}
"""

__version__ = "0.1.0"
__author__ = "DUBFORGE User"
__category__ = "{category}"

import numpy as np


def register_plugin(registry):
    """Register this plugin with DUBFORGE."""
    from engine.plugin_scaffold import PluginMeta
    meta = PluginMeta(
        name="{name}",
        version=__version__,
        author=__author__,
        category=__category__,
        description=__doc__,
    )
    registry.register("{name}", main, meta)


def main(**kwargs):
    """Plugin entry point."""
    print(f"{name} plugin running")
    return {{"status": "ok", "name": "{name}"}}
'''
    with open(path, "w") as f:
        f.write(template)
    return path


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

_global_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    return _global_registry


def main() -> None:
    reg = get_registry()
    # Self-register as an example
    reg.register(
        "scaffold_demo",
        lambda: {"status": "demo"},
        PluginMeta("scaffold_demo", "1.0.0", "DUBFORGE", "system",
                    "Plugin scaffold demo"),
    )
    print(f"Plugin Scaffold: {len(reg.list_plugins())} plugins registered")
    for name in reg.list_plugins():
        entry = reg.get(name)
        if entry:
            print(f"  [{entry.meta.category}] {name} v{entry.meta.version}")
    found = discover_plugins()
    print(f"  Discovered {len(found)} external plugins")


if __name__ == "__main__":
    main()
