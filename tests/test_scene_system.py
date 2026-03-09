"""Tests for engine.scene_system — Session 176."""
import pytest
from engine.scene_system import (
    SceneManager, Scene, ParamSnapshot, create_dubstep_scenes,
)


class TestSceneSystem:
    def test_create(self):
        sm = SceneManager()
        assert isinstance(sm, SceneManager)

    def test_add_scene(self):
        sm = SceneManager()
        s = Scene(name="intro", params=[
            ParamSnapshot(module="sub_bass", param="volume", value=0.8),
        ], bpm=140)
        sm.add_scene(s)

    def test_activate(self):
        sm = SceneManager()
        s = Scene(name="intro", params=[], bpm=140)
        sm.add_scene(s)
        assert sm.activate("intro") is True

    def test_dubstep_scenes(self):
        scenes = create_dubstep_scenes()
        assert len(scenes) > 0
