"""
DUBFORGE — Chain Commands Engine  (Session 148)

Multi-step command chains for SUBPHONICS: parse "make sub bass then
sidechain then master" into sequential module executions.
"""

import re
import time
from dataclasses import dataclass, field

PHI = 1.6180339887


@dataclass
class ChainStep:
    """A single step in a command chain."""
    command: str
    status: str = "pending"  # pending, running, done, error
    result_text: str = ""
    elapsed_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class ChainResult:
    """Result of executing a command chain."""
    steps: list[ChainStep]
    total_elapsed_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0

    @property
    def all_success(self) -> bool:
        return self.error_count == 0


# Delimiters that separate chained commands
CHAIN_DELIMITERS = re.compile(
    r'\b(?:then|and then|after that|next|also|plus|&&|->|→)\b',
    re.IGNORECASE,
)


def parse_chain(text: str) -> list[str]:
    """Split a compound command into individual steps."""
    # Split on delimiters
    parts = CHAIN_DELIMITERS.split(text)
    # Clean up
    steps = [p.strip() for p in parts if p.strip()]
    return steps if steps else [text.strip()]


def is_chain(text: str) -> bool:
    """Check if text contains chain delimiters."""
    return bool(CHAIN_DELIMITERS.search(text))


def execute_chain(text: str, engine) -> ChainResult:
    """Parse and execute a chained command sequence.

    Args:
        text: User input with chain delimiters.
        engine: SubphonicsEngine instance.

    Returns:
        ChainResult with all step results.
    """
    commands = parse_chain(text)
    steps: list[ChainStep] = []
    t0 = time.time()
    success = 0
    errors = 0

    for cmd in commands:
        step = ChainStep(command=cmd)
        step.status = "running"
        step_t0 = time.time()

        try:
            msg = engine.process_message(cmd)
            step.result_text = msg.content
            step.metadata = msg.metadata
            step.status = "done"
            success += 1
        except Exception as e:
            step.result_text = f"Error: {e}"
            step.status = "error"
            errors += 1

        step.elapsed_ms = round((time.time() - step_t0) * 1000, 1)
        steps.append(step)

    total = round((time.time() - t0) * 1000, 1)
    return ChainResult(
        steps=steps,
        total_elapsed_ms=total,
        success_count=success,
        error_count=errors,
    )


def chain_result_to_text(result: ChainResult) -> str:
    """Format a chain result as human-readable text."""
    lines = [f"**Command Chain** — {len(result.steps)} steps, "
             f"{result.total_elapsed_ms}ms total\n"]

    for i, step in enumerate(result.steps, 1):
        icon = "✓" if step.status == "done" else "✗"
        lines.append(f"**Step {i}** [{icon}] `{step.command}` "
                      f"({step.elapsed_ms}ms)")
        # Truncate long results
        text = step.result_text
        if len(text) > 200:
            text = text[:200] + "…"
        lines.append(f"  {text}\n")

    status = "All steps completed" if result.all_success else \
             f"{result.error_count} step(s) failed"
    lines.append(f"**Result:** {status}")
    return "\n".join(lines)


def chain_result_to_dict(result: ChainResult) -> dict:
    """Convert chain result to JSON-serializable dict."""
    return {
        "steps": [
            {
                "command": s.command,
                "status": s.status,
                "result_text": s.result_text,
                "elapsed_ms": s.elapsed_ms,
                "metadata": s.metadata,
            }
            for s in result.steps
        ],
        "total_elapsed_ms": result.total_elapsed_ms,
        "success_count": result.success_count,
        "error_count": result.error_count,
        "all_success": result.all_success,
    }


def main() -> None:
    print("Chain Commands Engine")
    tests = [
        "make sub bass then sidechain then master",
        "render drums and then add reverb",
        "analyze phi -> export midi",
        "build wobble bass plus render lead",
    ]
    for t in tests:
        steps = parse_chain(t)
        print(f"  '{t}' → {len(steps)} steps: {steps}")
    print("Done.")


if __name__ == "__main__":
    main()
