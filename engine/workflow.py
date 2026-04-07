"""MWP Workflow — 10-Phase Production Pipeline Orchestrator.

Implements the ill.GATES Producer Dojo methodology as a sequential pipeline:

  ORACLE → COLLECT → RECIPES → SKETCH → ARRANGE → DESIGN →
  MIX → MASTER → RELEASE → REFLECT

Each phase:
  1. Runs pre-hooks (user-registered callbacks)
  2. Executes the phase function from forge.py
  3. Runs post-hooks
  4. Advances the DojoSession governor

Usage:
    from engine.workflow import MWPWorkflow
    path = MWPWorkflow(dna).run()

    # With hooks:
    wf = MWPWorkflow(dna)
    wf.register_hook("post_sketch", my_custom_processor)
    path = wf.run()
"""

import types


# ═══════════════════════════════════════════════════════════════
#  PRODUCTION CONTEXT
# ═══════════════════════════════════════════════════════════════

class ProductionContext:
    """Shared state container passed between MWP phases.

    Each phase reads what it needs from ctx and writes its outputs.
    This replaces the 100+ local variables in the old monolith.

    Core attributes set by oracle phase:
        dna         — SongDNA specification
        BEAT, BAR   — Timing constants (seconds)
        samples()   — Convert beats to sample count
        n()         — Scale degree to Hz
        FREQ        — Frequency lookup table
        dd,bd,ld,ad,fd,md — DNA sub-spec aliases

    Sound elements set by sketch phase:
        kick, snare, hat_c, hat_o, clap — Drum sounds
        sub, fm_growl, growl_wt, ... — Bass variants
        lead_notes, chord_notes_l/r  — Melodic content
        dark_pad, lush, drone, ...   — Atmospherics
        riser, boom, hit, ...        — Transition FX
        vocal_chops                  — Vocal elements

    Buffers set by arrange phase:
        L, R            — Stereo output buffers
        kick_positions  — Sample offsets of kick hits

    Output set by master phase:
        output_path     — Path to rendered WAV file
    """

    def __init__(self, dna=None):
        self.dna = dna
        self.output_path = None


# ═══════════════════════════════════════════════════════════════
#  MWP WORKFLOW
# ═══════════════════════════════════════════════════════════════

class MWPWorkflow:
    """10-Phase Minimum Workable Pipeline for dubstep production.

    Orchestrates the full render through 10 sequential phases,
    each governed by the DojoSession (phase timing, brain modes,
    quality gates, belt enforcement).

    Phases:
        1. ORACLE   — DNA setup, reference analysis, goal setting
        2. COLLECT  — Gather samples, presets, session state
        3. RECIPES  — Templates, blueprints, variation planning
        4. SKETCH   — Raw sound design (synths, drums, bass, FX)
        5. ARRANGE  — Place sounds in time (Fat Loop subtractive)
        6. DESIGN   — Effects, automation, spatial processing
        7. MIX      — Bus routing, frequency balance, levels
        8. MASTER   — Final processing, LUFS targeting, limiting
        9. RELEASE  — Export WAV, MIDI, artwork, presets, ALS
       10. REFLECT  — Belt assessment, report card, session review
    """

    PHASES = [
        "oracle", "collect", "recipes", "sketch", "arrange",
        "design", "mix", "master", "release", "reflect",
    ]

    def __init__(self, dna=None):
        self.dna = dna
        self._hooks = {}
        self.ctx = ProductionContext(dna)

    def register_hook(self, point: str, fn):
        """Register a callback at a hook point.

        Hook points follow the pattern: pre_<phase> or post_<phase>
        Example: wf.register_hook("post_sketch", add_vocoder_layer)

        The callback receives the ProductionContext as its only argument.
        """
        self._hooks.setdefault(point, []).append(fn)

    def _run_hooks(self, point: str, ctx=None):
        """Execute all hooks registered at the given point."""
        target = ctx if ctx is not None else self.ctx
        for fn in self._hooks.get(point, []):
            fn(target)

    def run(self):
        """Execute the full 10-phase MWP pipeline.

        Calls forge.render_full_track with this workflow instance,
        which fires pre/post hooks at each phase boundary.

        Returns:
            str: Path to the rendered output WAV file.
        """
        # Lazy import to avoid circular dependency
        from forge import render_full_track

        result = render_full_track(self.dna, workflow=self)
        return result


# ═══════════════════════════════════════════════════════════════
#  CONVENIENCE
# ═══════════════════════════════════════════════════════════════

def render_via_workflow(dna=None, hooks=None):
    """One-liner to render a track through the MWP pipeline.

    Args:
        dna: SongDNA specification (None for V5 defaults).
        hooks: dict of {hook_point: callable} to register.

    Returns:
        str: Path to rendered WAV.
    """
    wf = MWPWorkflow(dna)
    if hooks:
        for point, fn in hooks.items():
            wf.register_hook(point, fn)
    return wf.run()
