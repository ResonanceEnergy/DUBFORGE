# COPILOT PROMPT LIBRARY — DUBFORGE × M4 Pro 64GB
**Resonance Energy Studio · NATRIX**
**Last Updated: 2026-04-02**

---

## How to Use

Paste these prompts into **Copilot Chat** (`Ctrl+L` / `Cmd+L`) or **Copilot Edits**.
Prefix with `@workspace` when you need full repo context.
Prefix with `@file` or `#file:filename` to scope to a specific file.

---

## 1. ARCHITECTURE & ANALYSIS

### Full Repo Audit
```
@workspace Analyze the entire DUBFORGE repository architecture:
1. Map all module dependencies in engine/
2. Identify circular imports or dead code
3. Flag CPU-bound bottlenecks that could benefit from multiprocessing
4. Identify I/O-bound code that should be async
5. Report memory-intensive operations that could exceed reasonable bounds
Return a prioritized list of improvements.
```

### Module Dependency Map
```
@workspace Trace the import chain for engine/ modules.
Build a dependency graph showing:
- Which modules import what
- Entry points (called from run_all.py, make_*.py)
- Isolated modules with no dependents
- Circular dependency chains
Format as a Mermaid diagram.
```

### Performance Hotspot Scan
```
@workspace Identify the top 10 performance hotspots in engine/:
- numpy operations that could use vectorization
- Loops that should be replaced with array ops
- File I/O that blocks the main thread
- Memory allocations in hot paths
For each, suggest a concrete fix with code.
```

---

## 2. APPLE SILICON OPTIMIZATION

### Metal/MPS Acceleration Check
```
@workspace Audit all numerical computation in engine/ for Apple Silicon optimization:
- numpy ops that could use Accelerate framework
- Any torch usage → ensure MPS backend
- DSP operations that could use vDSP
- Matrix ops that could use BLAS/LAPACK via vecLib
Suggest concrete changes for M4 Pro with 16-core GPU.
```

### Parallel Execution Audit
```
@workspace This runs on M4 Pro (12 perf + 4 efficiency cores, 64GB unified memory).
Analyze engine/ for parallelization opportunities:
- Which modules can run concurrently with multiprocessing.Pool?
- Which operations are embarrassingly parallel?
- Where would concurrent.futures.ProcessPoolExecutor help?
- What's the optimal worker count for this chip?
Show before/after code for the top 3 wins.
```

### Memory Optimization (64GB Unified)
```
@workspace With 64GB unified memory available:
- Which engine modules could benefit from larger in-memory caches?
- Where are we doing unnecessary disk I/O that could be RAM-cached?
- Are there numpy arrays being copied when views would suffice?
- Could we memory-map any large audio files?
Suggest changes that trade memory for speed.
```

---

## 3. DUBSTEP ENGINE / DSP

### Sound Design Parameter Review
```
@workspace Review all phi/Fibonacci-based parameter calculations in engine/.
For each module that uses PHI or FIBONACCI constants:
1. Verify the math is correct
2. Check parameter ranges are musically valid (Hz, dB, ms units)
3. Flag any values outside safe ranges for Serum 2
4. Suggest improvements for 150 BPM dubstep context
```

### TurboQuant Integration Check
```
@workspace Audit engine/turboquant.py integration:
1. Which modules call turboquant functions?
2. Are all 10 psychoacoustic bands being used correctly?
3. Is quantization applied before or after phi scaling?
4. Are there modules that SHOULD use TurboQuant but don't?
5. Verify the arXiv:2504.19874 implementation matches the paper
```

### Arrangement Structure Audit
```
@workspace Analyze the arrangement/structure generation in engine/:
- Verify INTRO → BUILD → DROP → BREAK → BUILD2 → DROP2 → OUTRO flow
- Check bar counts follow Fibonacci sequences
- Validate energy curves match dubstep conventions
- Ensure double-drop sections are properly handled
- Flag any arrangement that would sound unnatural at 150 BPM
```

### Mix & Master Chain Review
```
@workspace Review the mixing and mastering chain in engine/:
1. EQ curves — are frequency bands correct for dubstep (sub, bass, mid, high)?
2. Compression ratios — appropriate for each stem group?
3. Stereo imaging — mono below 200Hz enforced?
4. Limiter settings — LUFS target reasonable for streaming?
5. Are ill.Gates Dojo rules being followed (separate creation from revision)?
```

---

## 4. TESTING & QUALITY

### Test Coverage Expansion
```
@workspace Analyze test coverage gaps in tests/:
1. Which engine modules lack tests?
2. Which functions have 0% branch coverage?
3. Suggest 5 critical test cases that are missing
4. Generate pytest fixtures for common test data
5. Prioritize by risk (modules that affect audio output first)
```

### Generate Edge Case Tests
```
#file:engine/{module}.py
Generate pytest test cases for edge conditions:
- Zero/empty inputs
- Extreme values (very high BPM, very low frequency)
- Boundary conditions (exactly on Fibonacci thresholds)
- Type mismatches
- NaN/Inf in numpy arrays
Use parametrize for combinatorial coverage.
```

### Regression Test Suite
```
@workspace Create a regression test that:
1. Runs the full pipeline (make_apology_v3.py equivalent)
2. Captures output checksums
3. Compares against known-good baseline
4. Reports any audio parameter drift
5. Runs in under 30 seconds on M4 Pro
```

---

## 5. REFACTORING

### Dead Code Elimination
```
@workspace Find and list all dead code in the repository:
- Functions never called from any entry point
- Variables assigned but never read
- Imports never used
- Files with no references from other modules
- Config keys that no code reads
Do NOT delete anything — just report with file:line references.
```

### Type Safety Pass
```
@workspace Add type hints to all public functions in engine/ that lack them.
Rules:
- Use Python 3.12+ syntax (X | Y, not Union[X, Y])
- numpy arrays: npt.NDArray[np.float64]
- Return types required for all public functions
- No changes to private/internal helpers
- No docstring additions — types only
```

### Extract Common Patterns
```
@workspace Identify repeated code patterns across engine/ modules:
- Duplicate phi calculations
- Repeated file I/O patterns
- Copy-pasted validation logic
- Similar numpy operations
For each pattern, suggest whether extraction is worth it
(only if used 3+ times and the abstraction is obvious).
```

---

## 6. ABLETON LIVE / ALS GENERATION

### ALS File Validation
```
@workspace Audit all ALS (Ableton Live Set) generation code:
1. Are XML structures valid for Ableton Live 12?
2. Are track IDs unique and non-colliding?
3. Are device chains properly nested?
4. Are automation envelopes correctly linked to parameters?
5. Will the generated .als open without errors in Live 12?
```

### Serum 2 Preset Generation
```
@workspace Review Serum 2 integration:
1. Are preset parameters within valid ranges?
2. Are wavetable references correct?
3. Do modulation routings conflict?
4. Are macro mappings within 0-127 range?
5. Will generated presets load in Serum 2 without errors?
```

---

## 7. CI/CD & AUTOMATION

### GitHub Actions Optimization
```
@workspace Review/create GitHub Actions workflow:
- Run tests on push to main and PRs
- Use Python matrix (3.12, 3.13, 3.14)
- Cache pip dependencies
- Run linting before tests (fail fast)
- Report coverage
- Total CI time target: under 3 minutes
```

### Pre-commit Hooks
```
@workspace Create .pre-commit-config.yaml for DUBFORGE:
- ruff check + format
- Type checking (mypy or pyright, strict on engine/)
- Test quick smoke (pytest -x --timeout=10)
- ALS validation (if .als files modified)
- No secrets in committed files
```

---

## 8. DOCUMENTATION & CONTEXT

### Generate ADR (Architecture Decision Record)
```
@workspace Create an ADR in adr/ for: [DECISION TOPIC]
Follow the template in adr/ADR-000-template.md.
Include:
- Context: why this decision matters for DUBFORGE
- Decision: what we chose
- Consequences: tradeoffs and risks
- Status: proposed/accepted/deprecated
```

### Module Documentation
```
#file:engine/{module}.py
Generate a concise module-level docstring explaining:
1. What this module does in the DUBFORGE pipeline
2. Which phase it belongs to (Generation/Arrangement/Mixing/Mastering)
3. Key functions and their roles
4. Dependencies on other engine modules
5. Phi/Fibonacci parameters used
Keep it under 20 lines.
```

---

## 9. DEBUGGING & DIAGNOSTICS

### Stack Trace Analysis
```
Analyze this error and provide:
1. Root cause (not just the symptom)
2. Which engine module is at fault
3. Whether this is a data issue or logic bug
4. Minimal fix (fewest lines changed)
5. Test case to prevent regression

Error:
[PASTE STACK TRACE]
```

### Audio Output Diagnosis
```
@workspace The rendered audio has [PROBLEM: e.g., clipping, silence, wrong tempo].
Trace the signal chain from input parameters to WAV output:
1. Which module generates the affected signal?
2. Where could the value go out of range?
3. What validation is missing?
4. Suggest a diagnostic print/log to isolate the issue
```

---

## 10. QUICK COMMANDS (Daily Use)

### Explain Any Module
```
#file:engine/{module}.py Explain this module in 3 sentences: what it does, how it fits the pipeline, and what it depends on.
```

### Quick Refactor
```
#file:engine/{module}.py Refactor for readability without changing behavior. Keep variable names domain-appropriate (dubstep/audio terms).
```

### Generate Config
```
@workspace Generate a new song config YAML for:
- Name: [TRACK NAME]
- BPM: 150
- Key: [KEY]
- Mood: [dark/aggressive/melodic/experimental]
- Energy: [1-10]
Follow the format in configs/production_queue.yaml
```

### Quick Benchmark
```
@workspace Write a quick benchmark script that times each engine module independently:
- Use time.perf_counter_ns()
- Run each module 100 times
- Report mean, p50, p99
- Sort by total time descending
- Target: identify modules taking >100ms
```
