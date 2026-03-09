"""
DUBFORGE — Mix Assistant Engine  (Session 153)

AI-powered mixing suggestions for SUBPHONICS: gain staging,
frequency balance, stereo width, and conflict detection.
"""

from dataclasses import dataclass, field

PHI = 1.6180339887
A4_432 = 432.0
SAMPLE_RATE = 44100

# Frequency bands (Hz)
BANDS = {
    "sub": (20, 60),
    "bass": (60, 250),
    "low_mid": (250, 500),
    "mid": (500, 2000),
    "upper_mid": (2000, 4000),
    "presence": (4000, 8000),
    "air": (8000, 20000),
}

# Ideal RMS levels per element type (dBFS)
IDEAL_LEVELS = {
    "kick": -8.0,
    "snare": -10.0,
    "hihat": -16.0,
    "sub_bass": -10.0,
    "bass": -12.0,
    "lead": -14.0,
    "pad": -20.0,
    "vocal": -12.0,
    "fx": -18.0,
    "riser": -16.0,
    "master": -6.0,
}

# Frequency ranges per element (Hz)
ELEMENT_RANGES = {
    "kick": (30, 200),
    "snare": (150, 5000),
    "hihat": (5000, 18000),
    "sub_bass": (20, 80),
    "bass": (60, 300),
    "lead": (300, 6000),
    "pad": (200, 8000),
    "vocal": (200, 4000),
    "fx": (500, 16000),
}


@dataclass
class MixElement:
    """A single element in the mix."""
    name: str
    element_type: str = "unknown"
    rms_db: float = -20.0
    peak_db: float = -6.0
    freq_range: tuple[float, float] = (20.0, 20000.0)
    stereo_width: float = 0.5  # 0=mono, 1=wide
    pan: float = 0.0  # -1=L, 0=C, 1=R


@dataclass
class MixSuggestion:
    """A mixing suggestion."""
    element: str
    category: str  # level, eq, stereo, conflict, general
    severity: str  # info, warning, critical
    message: str
    action: str = ""


@dataclass
class MixAnalysis:
    """Complete mix analysis result."""
    elements: list[MixElement] = field(default_factory=list)
    suggestions: list[MixSuggestion] = field(default_factory=list)
    headroom_db: float = 0.0
    overall_score: float = 0.0  # 0-100

    def to_dict(self) -> dict:
        return {
            "elements": [
                {
                    "name": e.name,
                    "type": e.element_type,
                    "rms_db": e.rms_db,
                    "peak_db": e.peak_db,
                    "stereo_width": e.stereo_width,
                    "pan": e.pan,
                }
                for e in self.elements
            ],
            "suggestions": [
                {
                    "element": s.element,
                    "category": s.category,
                    "severity": s.severity,
                    "message": s.message,
                    "action": s.action,
                }
                for s in self.suggestions
            ],
            "headroom_db": self.headroom_db,
            "overall_score": self.overall_score,
        }


def analyze_levels(elements: list[MixElement]) -> list[MixSuggestion]:
    """Check gain staging."""
    suggestions = []
    for e in elements:
        ideal = IDEAL_LEVELS.get(e.element_type, -14.0)
        diff = e.rms_db - ideal

        if diff > 6:
            suggestions.append(MixSuggestion(
                element=e.name,
                category="level",
                severity="critical",
                message=f"{e.name} is {diff:.1f}dB too hot "
                        f"(RMS {e.rms_db:.1f} vs ideal {ideal:.1f})",
                action=f"Reduce gain by {diff:.1f}dB",
            ))
        elif diff > 3:
            suggestions.append(MixSuggestion(
                element=e.name,
                category="level",
                severity="warning",
                message=f"{e.name} is {diff:.1f}dB above ideal level",
                action=f"Consider reducing gain by {diff:.1f}dB",
            ))
        elif diff < -6:
            suggestions.append(MixSuggestion(
                element=e.name,
                category="level",
                severity="warning",
                message=f"{e.name} is {abs(diff):.1f}dB too quiet",
                action=f"Boost gain by {abs(diff):.1f}dB",
            ))

        # Check for clipping
        if e.peak_db > -0.3:
            suggestions.append(MixSuggestion(
                element=e.name,
                category="level",
                severity="critical",
                message=f"{e.name} is clipping! Peak at {e.peak_db:.1f}dBFS",
                action="Reduce gain or add limiter",
            ))
    return suggestions


def detect_conflicts(elements: list[MixElement]) -> list[MixSuggestion]:
    """Detect frequency masking conflicts."""
    suggestions = []
    for i, a in enumerate(elements):
        ra = ELEMENT_RANGES.get(a.element_type, a.freq_range)
        for b in elements[i + 1:]:
            rb = ELEMENT_RANGES.get(b.element_type, b.freq_range)
            # Check overlap
            overlap_lo = max(ra[0], rb[0])
            overlap_hi = min(ra[1], rb[1])
            if overlap_lo < overlap_hi:
                overlap_range = overlap_hi - overlap_lo
                total_range = max(ra[1], rb[1]) - min(ra[0], rb[0])
                overlap_pct = overlap_range / total_range * 100

                if overlap_pct > 50:
                    suggestions.append(MixSuggestion(
                        element=f"{a.name} vs {b.name}",
                        category="conflict",
                        severity="warning",
                        message=f"Frequency conflict between {a.name} and "
                                f"{b.name} ({overlap_pct:.0f}% overlap, "
                                f"{overlap_lo:.0f}-{overlap_hi:.0f}Hz)",
                        action=f"Use EQ to separate — cut {a.name} above "
                               f"{overlap_lo + (overlap_hi - overlap_lo) / 2:.0f}Hz "
                               f"or sidechain {b.name} to {a.name}",
                    ))
    return suggestions


def check_stereo(elements: list[MixElement]) -> list[MixSuggestion]:
    """Check stereo balance and width."""
    suggestions = []
    for e in elements:
        # Low frequencies should be mono
        if e.element_type in ("kick", "sub_bass") and e.stereo_width > 0.3:
            suggestions.append(MixSuggestion(
                element=e.name,
                category="stereo",
                severity="warning",
                message=f"{e.name} has too much stereo width "
                        f"({e.stereo_width:.1f}) — low end should be mono",
                action="Narrow stereo width below 100Hz",
            ))

        # Check pan balance
        if abs(e.pan) > 0.8 and e.element_type in ("kick", "snare", "bass",
                                                      "sub_bass", "vocal"):
            suggestions.append(MixSuggestion(
                element=e.name,
                category="stereo",
                severity="warning",
                message=f"{e.name} is panned too far "
                        f"({'L' if e.pan < 0 else 'R'} {abs(e.pan):.1f})",
                action="Center important elements",
            ))
    return suggestions


def phi_suggestions(elements: list[MixElement]) -> list[MixSuggestion]:
    """PHI-based mixing recommendations."""
    suggestions = []
    if len(elements) >= 2:
        # Suggest golden ratio level relationships
        suggestions.append(MixSuggestion(
            element="master",
            category="general",
            severity="info",
            message=f"PHI tip: Set lead/bass ratio at 1:{PHI:.2f} "
                    f"for golden balance (~3.5dB difference)",
            action="Adjust lead ~3.5dB below bass for PHI balance",
        ))

    suggestions.append(MixSuggestion(
        element="master",
        category="general",
        severity="info",
        message=f"PHI reverb: Pre-delay at {int(1000 / PHI / 8)}ms, "
                f"decay at {PHI:.2f}s for natural spatial feel",
        action="Apply golden ratio reverb timings",
    ))
    return suggestions


def analyze_mix(elements: list[MixElement]) -> MixAnalysis:
    """Full mix analysis."""
    suggestions: list[MixSuggestion] = []
    suggestions.extend(analyze_levels(elements))
    suggestions.extend(detect_conflicts(elements))
    suggestions.extend(check_stereo(elements))
    suggestions.extend(phi_suggestions(elements))

    # Calculate headroom
    if elements:
        peak = max(e.peak_db for e in elements)
        headroom = -peak
    else:
        headroom = float("inf")

    # Calculate score
    critical = sum(1 for s in suggestions if s.severity == "critical")
    warnings = sum(1 for s in suggestions if s.severity == "warning")
    score = max(0.0, 100.0 - critical * 20 - warnings * 5)

    return MixAnalysis(
        elements=elements,
        suggestions=suggestions,
        headroom_db=round(headroom, 1),
        overall_score=round(score, 1),
    )


def mix_analysis_text(analysis: MixAnalysis) -> str:
    """Format analysis as readable text."""
    lines = [
        f"**Mix Analysis** — Score: {analysis.overall_score}/100 | "
        f"Headroom: {analysis.headroom_db}dB",
        "",
    ]

    if analysis.elements:
        lines.append("**Elements:**")
        for e in analysis.elements:
            lines.append(f"  {e.name} ({e.element_type}): "
                          f"RMS {e.rms_db:.1f}dB, Peak {e.peak_db:.1f}dB")
        lines.append("")

    for severity in ("critical", "warning", "info"):
        items = [s for s in analysis.suggestions if s.severity == severity]
        if items:
            icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}[severity]
            lines.append(f"**{severity.upper()}:**")
            for s in items:
                lines.append(f"  {icon} [{s.category}] {s.message}")
                if s.action:
                    lines.append(f"     → {s.action}")
            lines.append("")

    return "\n".join(lines)


def quick_mix_check(*elements_data: tuple) -> str:
    """Quick mix check from (name, type, rms, peak) tuples."""
    elements = []
    for data in elements_data:
        if len(data) >= 4:
            elements.append(MixElement(
                name=data[0],
                element_type=data[1],
                rms_db=data[2],
                peak_db=data[3],
            ))
    analysis = analyze_mix(elements)
    return mix_analysis_text(analysis)


def main() -> None:
    print("Mix Assistant Engine")
    elements = [
        MixElement("Kick", "kick", -7.0, -2.0),
        MixElement("Sub", "sub_bass", -9.0, -4.0, stereo_width=0.5),
        MixElement("Lead", "lead", -12.0, -6.0),
        MixElement("Pad", "pad", -18.0, -10.0, stereo_width=0.8),
        MixElement("Snare", "snare", -9.0, -3.0),
    ]
    analysis = analyze_mix(elements)
    print(mix_analysis_text(analysis))
    print("Done.")


if __name__ == "__main__":
    main()
