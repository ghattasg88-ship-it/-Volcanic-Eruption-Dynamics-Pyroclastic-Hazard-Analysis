"""
ashfall.py
==========
Tephra fallout: fine ash lofted to the umbrella cloud is advected downwind
and settles according to particle terminal velocity. Accumulated ground
loading (kg/m^2) feeds the ashfall hazard isopach map.
"""

import numpy as np

from .particle_system import ParticleSystem
from .physics import terminal_settling_velocity, ASH_DENSITY


class AshFall(ParticleSystem):
    def __init__(self, render_root, terrain_sampler, wind=(12.0, 3.0, 0.0),
                 max_particles=7000):
        super().__init__(render_root, max_particles, point_size=4.0,
                         additive=False, name="ashfall")
        self.sample_height = terrain_sampler
        self.wind = np.asarray(wind, dtype=np.float32)
        self.diameter = np.full(max_particles, 1e-4, dtype=np.float32)
        # Coarse ground-loading accumulator grid for isopach mapping
        self.grid_res = 64
        self.grid_extent = 30000.0   # +/- 30 km
        self.loading = np.zeros((self.grid_res, self.grid_res),
                                dtype=np.float32)

    # ------------------------------------------------------------------
    def seed_from_umbrella(self, umbrella_center, umbrella_radius,
                           umbrella_height, n=200):
        for _ in range(int(n)):
            ang = np.random.uniform(0, 2 * np.pi)
            r = umbrella_radius * np.sqrt(np.random.uniform(0, 1))
            pos = np.array([
                umbrella_center[0] + r * np.cos(ang),
                umbrella_center[1] + r * np.sin(ang),
                umbrella_height * np.random.uniform(0.85, 1.0),
            ], dtype=np.float32)
            i = self._cursor
            self.diameter[i] = np.random.uniform(3e-5, 2e-3)  # 0.03-2 mm
            vel = self.wind + np.random.uniform(-2, 2, 3).astype(np.float32)
            color = np.array([0.55, 0.54, 0.52, 0.5], dtype=np.float32)
            super().emit(pos, vel, color,
                         lifetime=np.random.uniform(120, 400),
                         size=np.random.uniform(0.4, 1.0))

    # ------------------------------------------------------------------
    def update_physics(self, dt):
        live = self.alive
        if not live.any():
            return
        idx = np.where(live)[0]
        # Settling velocity per particle (altitude-dependent)
        for i in idx:
            vt = terminal_settling_velocity(float(self.diameter[i]),
                                            float(self.pos[i, 2]))
            self.vel[i, 0] = self.wind[0]
            self.vel[i, 1] = self.wind[1]
            self.vel[i, 2] = -vt
            self.pos[i] += self.vel[i] * dt
            ground = self.sample_height(self.pos[i, 0], self.pos[i, 1])
            if self.pos[i, 2] <= ground:
                self._deposit(self.pos[i, 0], self.pos[i, 1],
                              float(self.diameter[i]))
                self.alive[i] = False
                self.pos[i] = (0.0, 0.0, -1.0e6)

    # ------------------------------------------------------------------
    def _deposit(self, x, y, diameter):
        """Add particle mass to the ground-loading grid."""
        gx = int((x / self.grid_extent + 1.0) * 0.5 * (self.grid_res - 1))
        gy = int((y / self.grid_extent + 1.0) * 0.5 * (self.grid_res - 1))
        if 0 <= gx < self.grid_res and 0 <= gy < self.grid_res:
            mass = ASH_DENSITY * (4.0 / 3.0) * np.pi * (0.5 * diameter) ** 3
            # Each rendered particle represents a parcel; scale up for loading
            self.loading[gy, gx] += mass * 1.0e9

    def update_appearance(self):
        live = self.alive
        if not live.any():
            return
        life_frac = np.clip(self.age[live] / self.lifetime[live], 0, 1)
        self.color[live, 3] = 0.5 * (1.0 - 0.5 * life_frac)
