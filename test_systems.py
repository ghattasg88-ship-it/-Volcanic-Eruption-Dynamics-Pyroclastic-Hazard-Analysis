"""
test_systems.py
==============
Headless integration tests for the simulation subsystems. Panda3D is run
with `window-type none` so these execute in CI without a display.

Run:  python -m pytest tests/test_systems.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="module")
def base():
    """A headless Panda3D ShowBase shared across tests."""
    from panda3d.core import loadPrcFileData
    loadPrcFileData("", "window-type none")
    loadPrcFileData("", "audio-library-name null")
    from direct.showbase.ShowBase import ShowBase
    b = ShowBase()
    yield b
    b.destroy()


@pytest.fixture(scope="module")
def terrain(base):
    from src.terrain import VolcanoTerrain
    return VolcanoTerrain(base.render, size=20000, resolution=60,
                          summit_height=2800)


# ----------------------------------------------------------------------
def test_terrain_sampler_within_bounds(terrain):
    z_centre = terrain.sample(0, 0)
    z_edge = terrain.sample(9000, 9000)
    # Centre (cone, minus crater) should be far higher than the edge
    assert z_centre > z_edge
    assert -200 < z_edge < 500


def test_terrain_summit_height(terrain):
    # Max of the field should approach the configured summit height
    assert terrain.heights.max() > 2500


def test_eruption_column_emits_and_rises(base, terrain):
    from src.eruption_column import EruptionColumn
    vent = (0, 0, float(terrain.summit_pos().z))
    col = EruptionColumn(base.render, vent, 25.0)
    col.emit_step(0.2)
    z0 = col.pos[col.alive].mean(axis=0)[2]
    for _ in range(20):
        col.update(0.1)
    assert col.num_alive > 0
    z1 = col.pos[col.alive].mean(axis=0)[2]
    assert z1 > z0  # column rises


def test_pyroclastic_flow_runout(base, terrain):
    from src.pyroclastic_flow import PyroclasticFlow
    vent = (0, 0, float(terrain.summit_pos().z))
    pdc = PyroclasticFlow(base.render, vent, terrain.sample,
                          heim_coefficient=0.24, collapse_height=2200)
    pdc.trigger_collapse(400)
    assert pdc.num_alive > 0
    # Max runout matches energy-cone expectation (~9 km)
    assert 8000 < pdc.max_runout < 10000


def test_ballistics_impact(base, terrain):
    from src.ballistics import BallisticEjecta
    vent = (0, 0, float(terrain.summit_pos().z))
    ball = BallisticEjecta(base.render, vent, terrain.sample)
    ball.launch(60, 320)
    for _ in range(400):       # 40 s of flight
        ball.update(0.1)
    assert len(ball.impacts) > 0  # blocks land and are recorded


def test_ashfall_deposits(base, terrain):
    from src.ashfall import AshFall
    ash = AshFall(base.render, terrain.sample, wind=(12, 3, 0))
    ash.seed_from_umbrella((0, 0), 7500, 4000, n=200)
    for _ in range(600):       # 300 s
        ash.update(0.5)
    assert ash.loading.max() > 0  # tephra accumulates on the ground grid


def test_hazard_zones_toggle(base, terrain):
    from src.hazard_zones import HazardZones
    hz = HazardZones(base.render, terrain, 9000.0)
    assert not hz.visible
    hz.toggle()
    assert hz.visible
    hz.toggle()
    assert not hz.visible
