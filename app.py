"""
app.py
======
Main Panda3D application tying together terrain, eruption column,
pyroclastic flows, ballistics, ashfall, camera, HUD and hazard zones
into a staged eruption simulation.

Eruption phases (advance with SPACE):
    0  PRE-ERUPTION   - quiescent edifice
    1  VENT OPENING   - ballistic ejecta + initial gas-thrust jet
    2  PLINIAN COLUMN - sustained convective eruption column + ashfall
    3  COLUMN COLLAPSE- pyroclastic density currents sweep the flanks
    4  WANING         - emission tapers, deposits remain
"""

import json
import os

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, DirectionalLight, Fog, Vec3, Vec4, LColor,
    ClockObject, WindowProperties,
)

from .terrain import VolcanoTerrain
from .eruption_column import EruptionColumn
from .pyroclastic_flow import PyroclasticFlow
from .ballistics import BallisticEjecta
from .ashfall import AshFall
from .camera_controller import OrbitCamera
from .hud import HUD
from .hazard_zones import HazardZones
from .physics import VEI_TABLE, mass_eruption_rate_from_height

globalClock = ClockObject.getGlobalClock()

PHASE_NAMES = ["PRE-ERUPTION", "VENT OPENING", "PLINIAN COLUMN",
               "COLUMN COLLAPSE", "WANING"]


class VolcanoApp(ShowBase):
    def __init__(self, scenario_path=None):
        ShowBase.__init__(self)

        props = WindowProperties()
        props.setTitle("Volcanic Eruption Dynamics - Pyroclastic Hazard Analysis")
        props.setSize(1280, 720)
        self.win.requestProperties(props)

        self.scenario = self._load_scenario(scenario_path)
        self.vei = self.scenario["vei"]
        self.plume_km = self.scenario["plume_height_km"]

        self._setup_environment()
        self._setup_scene()
        self._setup_systems()

        self.hud = HUD(self)
        self.hud.set_phase(PHASE_NAMES[0])

        self.phase = 0
        self.sim_time = 0.0
        self.running = False

        self.accept("space", self.advance_phase)
        self.accept("r", self.reset)
        self.accept("h", self.hazard.toggle)
        self.accept("escape", self.userExit)

        self.taskMgr.add(self.update, "sim-update")

    # ------------------------------------------------------------------
    def _load_scenario(self, path):
        default = {
            "name": "Mount Generic - VEI 4 Plinian reference",
            "vei": 4,
            "plume_height_km": 25.0,
            "vent_velocity": 280.0,
            "vent_radius": 90.0,
            "heim_coefficient": 0.24,
            "collapse_height": 2200.0,
            "wind": [12.0, 3.0, 0.0],
        }
        if path and os.path.exists(path):
            with open(path) as f:
                default.update(json.load(f))
        return default

    # ------------------------------------------------------------------
    def _setup_environment(self):
        self.setBackgroundColor(0.45, 0.55, 0.68)   # hazy daylight sky

        amb = AmbientLight("amb")
        amb.setColor((0.40, 0.42, 0.48, 1))
        self.render.setLight(self.render.attachNewNode(amb))

        sun = DirectionalLight("sun")
        sun.setColor((0.95, 0.92, 0.85, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-50, -55, 0)
        self.render.setLight(sun_np)

        # Atmospheric depth fog
        fog = Fog("atmofog")
        fog.setColor(0.55, 0.60, 0.68)
        fog.setExpDensity(0.000035)
        self.render.setFog(fog)

    # ------------------------------------------------------------------
    def _setup_scene(self):
        self.terrain = VolcanoTerrain(
            self.render, size=20000.0, resolution=160,
            summit_height=2800.0, crater_radius=400.0)
        self.vent = self.terrain.summit_pos()
        self.camera_ctl = OrbitCamera(
            self, target=Vec3(0, 0, 1600), distance=14000.0)

    # ------------------------------------------------------------------
    def _setup_systems(self):
        sampler = self.terrain.sample
        vent = (self.vent.x, self.vent.y, self.vent.z)

        self.column = EruptionColumn(
            self.render, vent, self.plume_km,
            vent_velocity=self.scenario["vent_velocity"],
            vent_radius=self.scenario["vent_radius"])
        self.column.set_wind(self.scenario["wind"])

        self.pdc = PyroclasticFlow(
            self.render, vent, sampler,
            heim_coefficient=self.scenario["heim_coefficient"],
            collapse_height=self.scenario["collapse_height"])

        self.ballistics = BallisticEjecta(self.render, vent, sampler)
        self.ash = AshFall(self.render, sampler, wind=self.scenario["wind"])

        self.hazard = HazardZones(
            self.render, self.terrain, self.pdc.max_runout,
            vent_xy=(self.vent.x, self.vent.y))

        self._ash_seed_accum = 0.0

    # ------------------------------------------------------------------
    def advance_phase(self):
        if not self.running:
            self.running = True
        self.phase = min(self.phase + 1, len(PHASE_NAMES) - 1)
        self.hud.set_phase(PHASE_NAMES[self.phase])

        if self.phase == 1:
            self.ballistics.launch(n=140, max_velocity=320.0)
        elif self.phase == 3:
            self.pdc.trigger_collapse(n_particles=2600)

    # ------------------------------------------------------------------
    def reset(self):
        for sys in (self.column, self.pdc, self.ballistics, self.ash):
            sys.alive[:] = False
            sys.pos[:] = (0, 0, -1.0e6)
        self.ash.loading[:] = 0.0
        self.ballistics.impacts.clear()
        self.phase = 0
        self.sim_time = 0.0
        self.running = False
        self.hud.set_phase(PHASE_NAMES[0])

    # ------------------------------------------------------------------
    def update(self, task):
        dt = min(globalClock.getDt(), 0.05)
        if self.running:
            self.sim_time += dt

            # Column emission active in plinian + collapse phases
            if self.phase in (2, 3):
                self.column.emit_step(dt)
                # Seed ashfall from the umbrella region
                self._ash_seed_accum += 60 * dt
                n_seed = int(self._ash_seed_accum)
                self._ash_seed_accum -= n_seed
                if n_seed:
                    umbrella_c = (self.vent.x + self.scenario["wind"][0] * 3,
                                  self.vent.y + self.scenario["wind"][1] * 3)
                    self.ash.seed_from_umbrella(
                        umbrella_c, self.column.umbrella_radius,
                        self.column.plume_height, n=n_seed)

            self.column.update(dt)
            self.pdc.update(dt)
            self.ballistics.update(dt)
            self.ash.update(dt)

        self.hud.set_telemetry(
            self.vei, self.plume_km, self.sim_time,
            self.column.num_alive, self.pdc.num_alive,
            self.ballistics.num_alive, self.ash.num_alive)
        return task.cont
