#!/bin/zsh
# ═══════════════════════════════════════════════════════════════════
# DUBFORGE NIGHTLY — Automated AI Health & Build Tasks
# Resonance Energy Studio · M4 Pro 64GB
# Runs via launchd (see companion .plist)
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────
DUBFORGE_DIR="$HOME/Documents/GitHub/DUBFORGE"
REPORT_DIR="$DUBFORGE_DIR/reports/nightly"
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
REPORT_FILE="$REPORT_DIR/nightly_${TIMESTAMP}.md"
LOG_FILE="$REPORT_DIR/nightly_${TIMESTAMP}.log"
PYTHON="$DUBFORGE_DIR/.venv/bin/python3"
OLLAMA_MODEL="${DUBFORGE_NIGHTLY_MODEL:-qwen3:8b}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
CORES=$(sysctl -n hw.perflevel0.logicalcpu 2>/dev/null || echo 10)

# ── Setup ──────────────────────────────────────────────────────────
mkdir -p "$REPORT_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "═══ DUBFORGE NIGHTLY — $TIMESTAMP ═══"
echo "Cores: $CORES | Model: $OLLAMA_MODEL | Python: $PYTHON"
echo ""

cd "$DUBFORGE_DIR"

# ── Helper: Section Timer ──────────────────────────────────────────
section_start() {
    SECTION_NAME="$1"
    SECTION_T0=$(date +%s)
    echo "──── $SECTION_NAME ────"
}
section_end() {
    local elapsed=$(( $(date +%s) - SECTION_T0 ))
    echo "  ✓ $SECTION_NAME completed in ${elapsed}s"
    echo ""
}

# ── Helper: Ollama Query ──────────────────────────────────────────
ollama_query() {
    local prompt="$1"
    local max_tokens="${2:-2048}"
    curl -s "$OLLAMA_HOST/api/generate" \
        -d "{\"model\": \"$OLLAMA_MODEL\", \"prompt\": \"$prompt\", \"stream\": false, \"options\": {\"num_predict\": $max_tokens}}" \
        2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','[no response]'))" 2>/dev/null || echo "[ollama unavailable]"
}

# ═══════════════════════════════════════════════════════════════════
# TASK 1: GIT STATUS & CHANGES
# ═══════════════════════════════════════════════════════════════════
section_start "Git Status"

GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
GIT_DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
GIT_LAST_COMMIT=$(git log -1 --format="%h %s (%ar)" 2>/dev/null || echo "no commits")
GIT_CHANGED_FILES=$(git diff --name-only HEAD~1 2>/dev/null | head -20 || echo "n/a")

cat >> "$REPORT_FILE" <<EOF
# DUBFORGE Nightly Report — $TIMESTAMP

## Git Status
- **Branch**: $GIT_BRANCH
- **Dirty files**: $GIT_DIRTY
- **Last commit**: $GIT_LAST_COMMIT
- **Changed since last commit**:
\`\`\`
$GIT_CHANGED_FILES
\`\`\`

EOF
section_end

# ═══════════════════════════════════════════════════════════════════
# TASK 2: LINT CHECK
# ═══════════════════════════════════════════════════════════════════
section_start "Lint Check"

LINT_OUTPUT=$($PYTHON -m ruff check engine/ --output-format text 2>&1 || true)
LINT_COUNT=$(echo "$LINT_OUTPUT" | grep -c ":" 2>/dev/null || echo "0")

cat >> "$REPORT_FILE" <<EOF
## Lint Results
- **Issues found**: $LINT_COUNT

<details>
<summary>Details</summary>

\`\`\`
$(echo "$LINT_OUTPUT" | head -50)
\`\`\`
</details>

EOF
section_end

# ═══════════════════════════════════════════════════════════════════
# TASK 3: TEST SUITE
# ═══════════════════════════════════════════════════════════════════
section_start "Test Suite"

TEST_OUTPUT=$($PYTHON -m pytest tests/ -v -n "$CORES" --timeout=120 --tb=short 2>&1 || true)
TEST_PASSED=$(echo "$TEST_OUTPUT" | grep -oP '\d+ passed' | head -1 || echo "0 passed")
TEST_FAILED=$(echo "$TEST_OUTPUT" | grep -oP '\d+ failed' | head -1 || echo "0 failed")
TEST_ERRORS=$(echo "$TEST_OUTPUT" | grep -oP '\d+ error' | head -1 || echo "0 errors")
TEST_DURATION=$(echo "$TEST_OUTPUT" | grep -oP '[\d.]+s' | tail -1 || echo "unknown")

cat >> "$REPORT_FILE" <<EOF
## Test Results
- **Passed**: $TEST_PASSED
- **Failed**: $TEST_FAILED
- **Errors**: $TEST_ERRORS
- **Duration**: $TEST_DURATION
- **Workers**: $CORES

<details>
<summary>Failures (if any)</summary>

\`\`\`
$(echo "$TEST_OUTPUT" | grep -A5 "FAILED\|ERROR" | head -60)
\`\`\`
</details>

EOF
section_end

# ═══════════════════════════════════════════════════════════════════
# TASK 4: ENGINE MODULE HEALTH
# ═══════════════════════════════════════════════════════════════════
section_start "Engine Module Health"

MODULE_COUNT=$(find engine/ -name "*.py" -not -name "__init__.py" | wc -l | tr -d ' ')
TEST_COUNT=$(find tests/ -name "test_*.py" | wc -l | tr -d ' ')
TOTAL_LOC=$(find engine/ -name "*.py" -exec cat {} + | wc -l | tr -d ' ')
IMPORT_ERRORS=$($PYTHON -c "
import importlib, pathlib, sys
sys.path.insert(0, '.')
errors = []
for f in sorted(pathlib.Path('engine').glob('*.py')):
    if f.name == '__init__.py': continue
    mod = f'engine.{f.stem}'
    try:
        importlib.import_module(mod)
    except Exception as e:
        errors.append(f'{mod}: {type(e).__name__}: {e}')
for e in errors[:20]:
    print(e)
if not errors:
    print('All modules import cleanly.')
" 2>&1 || echo "import check failed")

cat >> "$REPORT_FILE" <<EOF
## Engine Health
- **Modules**: $MODULE_COUNT
- **Test files**: $TEST_COUNT
- **Total LOC**: $TOTAL_LOC
- **Import check**:
\`\`\`
$IMPORT_ERRORS
\`\`\`

EOF
section_end

# ═══════════════════════════════════════════════════════════════════
# TASK 5: PERFORMANCE BENCHMARK
# ═══════════════════════════════════════════════════════════════════
section_start "Performance Benchmark"

BENCH_OUTPUT=$($PYTHON -c "
import time, importlib, pathlib, sys, statistics
sys.path.insert(0, '.')
results = []
for f in sorted(pathlib.Path('engine').glob('*.py'))[:30]:
    if f.name.startswith('__'): continue
    mod_name = f'engine.{f.stem}'
    times = []
    for _ in range(3):
        t0 = time.perf_counter_ns()
        try:
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
            else:
                importlib.import_module(mod_name)
            elapsed = (time.perf_counter_ns() - t0) / 1e6
            times.append(elapsed)
        except:
            break
    if times:
        avg = statistics.mean(times)
        results.append((avg, mod_name))
results.sort(reverse=True)
for avg, name in results[:15]:
    flag = ' ⚠️' if avg > 100 else ''
    print(f'  {avg:8.1f}ms  {name}{flag}')
" 2>&1 || echo "benchmark failed")

cat >> "$REPORT_FILE" <<EOF
## Import Benchmark (top 15 slowest modules)
\`\`\`
$BENCH_OUTPUT
\`\`\`

EOF
section_end

# ═══════════════════════════════════════════════════════════════════
# TASK 6: SYSTEM HEALTH
# ═══════════════════════════════════════════════════════════════════
section_start "System Health"

DISK_USAGE=$(df -h / | tail -1 | awk '{print $5 " used of " $2}')
MEMORY_PRESSURE=$(memory_pressure 2>/dev/null | head -1 || echo "unknown")
SWAP_USAGE=$(sysctl vm.swapusage 2>/dev/null | awk -F= '{print $2}' || echo "unknown")
UPTIME_INFO=$(uptime | sed 's/.*up /up /' | sed 's/,.*//')

cat >> "$REPORT_FILE" <<EOF
## System Health (M4 Pro · 64GB)
- **Disk**: $DISK_USAGE
- **Memory**: $MEMORY_PRESSURE
- **Swap**: $SWAP_USAGE
- **Uptime**: $UPTIME_INFO

EOF
section_end

# ═══════════════════════════════════════════════════════════════════
# TASK 7: AI ANALYSIS (Local LLM via Ollama)
# ═══════════════════════════════════════════════════════════════════
section_start "AI Analysis (Ollama: $OLLAMA_MODEL)"

# Only run if Ollama is available
if curl -s "$OLLAMA_HOST/api/tags" >/dev/null 2>&1; then
    # Summarize test failures for AI analysis
    FAILURE_SUMMARY=$(echo "$TEST_OUTPUT" | grep -A3 "FAILED" | head -30)

    if [ -n "$FAILURE_SUMMARY" ] && [ "$FAILURE_SUMMARY" != "" ]; then
        AI_DIAGNOSIS=$(ollama_query "You are a Python engineer. These pytest failures occurred in a dubstep music engine called DUBFORGE. Diagnose the root cause and suggest fixes. Be concise (under 200 words). Failures: $FAILURE_SUMMARY")
    else
        AI_DIAGNOSIS="All tests passed — no failures to analyze."
    fi

    # Code quality insight
    AI_QUALITY=$(ollama_query "You are a code quality expert. Given a Python project with $MODULE_COUNT modules, $TOTAL_LOC lines of code, $LINT_COUNT lint issues, and $TEST_PASSED / $TEST_FAILED test results: Give 3 actionable improvement suggestions in under 100 words.")

    cat >> "$REPORT_FILE" <<EOF
## AI Analysis
### Test Diagnosis
$AI_DIAGNOSIS

### Quality Suggestions
$AI_QUALITY

EOF
else
    cat >> "$REPORT_FILE" <<EOF
## AI Analysis
*Ollama not available at $OLLAMA_HOST — skipped AI analysis.*

EOF
fi

section_end

# ═══════════════════════════════════════════════════════════════════
# TASK 8: CLEANUP OLD REPORTS (keep last 30 days)
# ═══════════════════════════════════════════════════════════════════
section_start "Cleanup"
find "$REPORT_DIR" -name "nightly_*.md" -mtime +30 -delete 2>/dev/null || true
find "$REPORT_DIR" -name "nightly_*.log" -mtime +30 -delete 2>/dev/null || true
KEPT=$(ls "$REPORT_DIR"/nightly_*.md 2>/dev/null | wc -l | tr -d ' ')
echo "  Kept $KEPT reports (30-day retention)"
section_end

# ═══════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════
TOTAL_TIME=$SECONDS

cat >> "$REPORT_FILE" <<EOF
---
*Generated by DUBFORGE Nightly · $(date) · ${TOTAL_TIME:-0}s total*
EOF

echo "═══════════════════════════════════════════════"
echo "  NIGHTLY COMPLETE — ${TOTAL_TIME:-0}s"
echo "  Report: $REPORT_FILE"
echo "  Log:    $LOG_FILE"
echo "═══════════════════════════════════════════════"
