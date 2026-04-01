#!/usr/bin/env zsh
# ═══════════════════════════════════════════════════════════════════════════
# DUBFORGE v4.1 — Mac Mini Setup (Apple Silicon Optimized)
# ═══════════════════════════════════════════════════════════════════════════
#
# Usage:
#   chmod +x setup.sh && ./setup.sh         # Core deps only
#   ./setup.sh --full                       # All deps (audio, plot, UI)
#
# Prerequisites: Homebrew, uv
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

PYTHON_VERSION="3.14"
VENV_DIR=".venv"

echo "═══════════════════════════════════════════"
echo "  DUBFORGE — Mac Mini Bootstrap"
echo "═══════════════════════════════════════════"
echo ""

# ── Check prerequisites ──────────────────────────────────────────────────

if ! command -v brew &>/dev/null; then
    echo "✗ Homebrew not found. Install: https://brew.sh"
    exit 1
fi

if ! command -v uv &>/dev/null; then
    echo "→ Installing uv..."
    brew install uv
fi

# ── Ensure Python is available ───────────────────────────────────────────

if ! uv python find "$PYTHON_VERSION" &>/dev/null; then
    echo "→ Installing Python ${PYTHON_VERSION} via uv..."
    uv python install "$PYTHON_VERSION"
fi

PYTHON_PATH=$(uv python find "$PYTHON_VERSION")
echo "✓ Python: $PYTHON_PATH"
$PYTHON_PATH --version

# ── Create venv ──────────────────────────────────────────────────────────

if [[ -d "$VENV_DIR" ]]; then
    echo "→ Removing existing venv..."
    rm -rf "$VENV_DIR"
fi

echo "→ Creating venv with Python ${PYTHON_VERSION}..."
uv venv --python "$PYTHON_VERSION" "$VENV_DIR"

# ── Install deps ─────────────────────────────────────────────────────────

source "$VENV_DIR/bin/activate"

if [[ "${1:-}" == "--full" ]]; then
    echo "→ Installing ALL dependencies (core + audio + plot + UI + dev)..."
    uv pip install -e ".[full,dev]"
else
    echo "→ Installing core + dev dependencies..."
    uv pip install -e ".[dev]"
fi

# ── Verify Apple Silicon NumPy ───────────────────────────────────────────

echo ""
echo "── NumPy Configuration ──"
python3 -c "
import numpy as np
print(f'  NumPy version: {np.__version__}')
import platform
print(f'  Architecture:  {platform.machine()}')
print(f'  Python:        {platform.python_version()}')
# Check if Accelerate is linked
config = np.__config__
if hasattr(config, 'show'):
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        np.show_config()
    cfg_text = buf.getvalue()
    if 'accelerate' in cfg_text.lower() or 'veclib' in cfg_text.lower():
        print('  BLAS/LAPACK:   Apple Accelerate ✓ (native ARM NEON)')
    elif 'openblas' in cfg_text.lower():
        print('  BLAS/LAPACK:   OpenBLAS (good, but Accelerate is faster on Apple Silicon)')
    else:
        print('  BLAS/LAPACK:   unknown — check with: python3 -c \"import numpy; numpy.show_config()\"')
"

# ── System summary ───────────────────────────────────────────────────────

echo ""
echo "── System ──"
PCORES=$(sysctl -n hw.perflevel0.logicalcpu 2>/dev/null || sysctl -n hw.performancecores 2>/dev/null || echo "?")
ECORES=$(sysctl -n hw.perflevel1.logicalcpu 2>/dev/null || sysctl -n hw.efficiencycores 2>/dev/null || echo "?")
TOTAL_MEM=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1073741824}' || echo "?")
CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Apple Silicon")
echo "  Chip:         $CHIP"
echo "  P-cores:      $PCORES"
echo "  E-cores:      $ECORES"
echo "  RAM:          ${TOTAL_MEM}GB"
echo "  Workers:      $PCORES (parallel build default)"

echo ""
echo "═══════════════════════════════════════════"
echo "  ✓ DUBFORGE ready"
echo ""
echo "  Activate:     source .venv/bin/activate"
echo "  Build:        make build"
echo "  Parallel:     make parallel"
echo "  Test:         make test"
echo "  Benchmark:    make bench"
echo "  System info:  make sysinfo"
echo "═══════════════════════════════════════════"
