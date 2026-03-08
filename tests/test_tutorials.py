"""Tests for engine.tutorials — five tutorial scripts."""


from engine.tutorials import (
    ALL_TUTORIALS,
    main,
    run_all_tutorials,
    tutorial_arrangement,
    tutorial_export_workflow,
    tutorial_fx_processing,
    tutorial_phi_fundamentals,
    tutorial_sound_design,
)

# ── tutorial_phi_fundamentals ────────────────────────────────────────────

class TestPhiFundamentals:
    def test_returns_dict(self):
        result = tutorial_phi_fundamentals()
        assert isinstance(result, dict)

    def test_tutorial_key(self):
        result = tutorial_phi_fundamentals()
        assert result["tutorial"] == "phi_fundamentals"

    def test_base_freq(self):
        result = tutorial_phi_fundamentals()
        assert result["base_freq"] == 432.0

    def test_phi_freq_is_phi_multiple(self):
        result = tutorial_phi_fundamentals()
        assert abs(result["ratio"] - 1.6180339887) < 0.001

    def test_fibonacci_sequence(self):
        result = tutorial_phi_fundamentals()
        assert result["fib_sequence"] == [1, 1, 2, 3, 5, 8, 13, 21]

    def test_converges_to_phi(self):
        result = tutorial_phi_fundamentals()
        assert result["converges_to_phi"] is True


# ── tutorial_sound_design ────────────────────────────────────────────────

class TestSoundDesign:
    def test_returns_dict(self):
        assert isinstance(tutorial_sound_design(), dict)

    def test_tutorial_key(self):
        assert tutorial_sound_design()["tutorial"] == "sound_design"

    def test_waveforms(self):
        result = tutorial_sound_design()
        assert "sine" in result["waveforms"]
        assert "saw" in result["waveforms"]
        assert "square" in result["waveforms"]

    def test_peaks_positive(self):
        result = tutorial_sound_design()
        assert result["peak_sine"] > 0
        assert result["peak_saw"] > 0
        assert result["peak_square"] > 0


# ── tutorial_fx_processing ───────────────────────────────────────────────

class TestFxProcessing:
    def test_returns_dict(self):
        assert isinstance(tutorial_fx_processing(), dict)

    def test_tutorial_key(self):
        assert tutorial_fx_processing()["tutorial"] == "fx_processing"

    def test_effects_list(self):
        result = tutorial_fx_processing()
        assert "distortion" in result["effects"]
        assert "lowpass" in result["effects"]

    def test_rms_values(self):
        result = tutorial_fx_processing()
        assert result["rms_dry"] > 0
        assert result["rms_dist"] > 0


# ── tutorial_arrangement ─────────────────────────────────────────────────

class TestArrangement:
    def test_returns_dict(self):
        assert isinstance(tutorial_arrangement(), dict)

    def test_tutorial_key(self):
        assert tutorial_arrangement()["tutorial"] == "arrangement"

    def test_structure_has_sections(self):
        result = tutorial_arrangement()
        assert "intro" in result["structure"]
        assert "drop_1" in result["structure"]

    def test_total_bars_positive(self):
        result = tutorial_arrangement()
        assert result["total_bars"] > 0


# ── tutorial_export_workflow ─────────────────────────────────────────────

class TestExportWorkflow:
    def test_returns_dict(self):
        assert isinstance(tutorial_export_workflow(), dict)

    def test_tutorial_key(self):
        assert tutorial_export_workflow()["tutorial"] == "export_workflow"

    def test_status_complete(self):
        assert tutorial_export_workflow()["status"] == "complete"

    def test_pipeline_stages(self):
        result = tutorial_export_workflow()
        assert result["pipeline_stages"] == ["render", "analyze", "export"]


# ── ALL_TUTORIALS & run_all_tutorials ────────────────────────────────────

class TestAllTutorials:
    def test_all_tutorials_has_five(self):
        assert len(ALL_TUTORIALS) == 5

    def test_all_tutorials_keys(self):
        expected = {"phi_fundamentals", "sound_design", "fx_processing",
                    "arrangement", "export_workflow"}
        assert set(ALL_TUTORIALS.keys()) == expected

    def test_run_all_returns_five(self):
        results = run_all_tutorials()
        assert len(results) == 5

    def test_run_all_each_has_tutorial_key(self):
        results = run_all_tutorials()
        for name, r in results.items():
            assert "tutorial" in r


# ── main ─────────────────────────────────────────────────────────────────

class TestMain:
    def test_main_runs(self, capsys):
        main()
        captured = capsys.readouterr()
        assert "Tutorials" in captured.out
