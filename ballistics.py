"""
ballistics.py
=============
Ballistic ejecta: dense blocks and bombs launched on parabolic trajectories
from the vent, decelerated by aerodynamic drag (size-dependent) and impacting
the terrain. These define the proximal "ballistic hazard zone".
"""

import numpy as np

from .particle_system import ParticleSystem
from .physics import GRAVITY, drag_acceleration, ROCK_DENSITY


class BallisticEjecta(ParticleSystem):
    def __init__(self, render_root, vent_pos, terrain_sampler,
                 max_particles=1500):
        super().__init__(render_root, max_particles, point_size=9.0,
                         additive=False, name="ballistics")
        self.vent_pos = np.asarray(vent_pos, dtype=np.float32)
        self.sample_height = terrain_sampler
        self.diameter = np.full(max_particles, 0.3, dtype=np.float32)
        self.impacts = []          # list of (x, y) impact points for hazard map

    # ------------------------------------------------------------------
    def launch(self, n=120, max_velocity=320.0):
        for _ in range(int(n)):
            ang_h = np.random.uniform(0, 2 * np.pi)
            ang_v = np.random.uniform(np.radians(55), np.radians(88))
            v = np.random.uniform(0.4, 1.0) * max_velocity
            vh = v * np.cos(ang_v)
            vz = v * np.sin(ang_v)
            vel = np.array([vh * np.cos(ang_h), vh * np.sin(ang_h), vz],
                           dtype=np.float32)
            color = np.array([0.9, 0.35, 0.1, 1.0], dtype=np.float32)
            i = self._cursor
            self.diameter[i] = np.random.uniform(0.15, 0.8)   # 15-80 cm blocks
            super().emit(self.vent_pos + np.array([0, 0, 60], dtype=np.float32),
                         vel, color, lifetime=60.0,
                         size=np.random.uniform(1.0, 2.5))

    # ------------------------------------------------------------------
    def update_physics(self, dt):
        live = self.alive
        if not live.any():
            return
        idx = np.where(live)[0]
        for i in idx:
            a = drag_acceleration(self.vel[i], self.pos[i, 2],
                                  float(self.diameter[i]), density=ROCK_DENSITY)
            self.vel[i] += a * dt
            self.vel[i, 2] -= GRAVITY * dt
            self.pos[i] += self.vel[i] * dt
            # Impact test
            ground = self.sample_height(self.pos[i, 0], self.pos[i, 1])
            if self.pos[i, 2] <= ground:
                self.impacts.append((float(self.pos[i, 0]),
                                     float(self.pos[i, 1])))
                self.alive[i] = False
                self.pos[i] = (0.0, 0.0, -1.0e6)

    def update_appearance(self):
        live = self.alive
        if not live.any():
            return
        # Cooling glow as they fly
        life_frac = np.clip(self.age[live] / self.lifetime[live], 0, 1)
        self.color[live, 0] = 0.9 - 0.4 * life_frac
        self.color[live, 1] = 0.35 - 0.2 * life_frac
        self.color[live, 2] = 0.1
        self.color[live, 3] = 1.0
