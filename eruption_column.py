"""
eruption_column.py
==================
The convective eruption column (Plinian plume): a buoyant, turbulent
column of gas and ash rising from the vent, broadening with height and
spreading into an umbrella cloud at the neutral-buoyancy level.

Visual model: emit ash/gas particles at the vent with the plume's
height-dependent vertical velocity (PlumeModel), add turbulent jitter and
entrainment-driven radial spread, and fade from incandescent orange near
the vent through grey ash to translucent white at the umbrella.
"""

import numpy as np

from .particle_system import ParticleSystem
from .physics import PlumeModel, GRAVITY


class EruptionColumn(ParticleSystem):
    def __init__(self, render_root, vent_pos, plume_height_km,
                 vent_velocity=250.0, vent_radius=80.0,
                 emission_rate=900, max_particles=9000):
        super().__init__(render_root, max_particles, point_size=10.0,
                         additive=False, name="eruption_column")
        self.vent_pos = np.asarray(vent_pos, dtype=np.float32)
        self.emission_rate = emission_rate          # particles / second
        self.model = PlumeModel(vent_velocity, vent_radius, plume_height_km)
        self.plume_height = plume_height_km * 1000.0
        self._emit_accum = 0.0
        # Umbrella spread radius (empirical ~ 0.3 * height)
        self.umbrella_radius = 0.30 * self.plume_height
        self.wind = np.array([6.0, 0.0, 0.0], dtype=np.float32)  # m/s drift

    # ------------------------------------------------------------------
    def set_wind(self, wind_vec):
        self.wind = np.asarray(wind_vec, dtype=np.float32)

    # ------------------------------------------------------------------
    def emit_step(self, dt):
        self._emit_accum += self.emission_rate * dt
        n = int(self._emit_accum)
        self._emit_accum -= n
        for _ in range(n):
            ang = np.random.uniform(0, 2 * np.pi)
            r = np.random.uniform(0, self.model.vent_radius)
            offset = np.array([r * np.cos(ang), r * np.sin(ang), 0.0],
                              dtype=np.float32)
            v0 = self.model.vent_velocity * np.random.uniform(0.8, 1.1)
            vel = np.array([
                np.random.uniform(-8, 8),
                np.random.uniform(-8, 8),
                v0,
            ], dtype=np.float32)
            # Incandescent at the vent (hot)
            color = np.array([1.0, 0.55, 0.12, 0.95], dtype=np.float32)
            lifetime = np.random.uniform(8.0, 18.0)
            super().emit(self.vent_pos + offset, vel, color, lifetime,
                         size=np.random.uniform(0.6, 1.4))

    # ------------------------------------------------------------------
    def update_physics(self, dt):
        live = self.alive
        if not live.any():
            return
        z_rel = self.pos[live, 2] - self.vent_pos[2]
        z_rel = np.clip(z_rel, 0.0, None)

        # Height-dependent target vertical velocity from plume model
        v_up = np.array([self.model.vertical_velocity(z) for z in z_rel],
                        dtype=np.float32)
        # Relax current vertical velocity toward model profile
        self.vel[live, 2] += (v_up - self.vel[live, 2]) * np.clip(2.0 * dt, 0, 1)

        # Entrainment: radial outward drift growing with height
        dx = self.pos[live, 0] - self.vent_pos[0]
        dy = self.pos[live, 1] - self.vent_pos[1]
        radial = np.sqrt(dx * dx + dy * dy) + 1e-3
        spread = 0.04 * (z_rel / max(self.plume_height, 1.0))
        self.vel[live, 0] += (dx / radial) * spread * 60.0 * dt
        self.vel[live, 1] += (dy / radial) * spread * 60.0 * dt

        # Turbulent jitter
        n = int(live.sum())
        self.vel[live] += np.random.uniform(-3, 3, (n, 3)).astype(np.float32) * dt

        # Umbrella: above neutral buoyancy, kill vertical, spread laterally + wind
        at_top = z_rel >= 0.92 * self.plume_height
        idx = np.where(live)[0]
        top_idx = idx[at_top]
        if top_idx.size:
            self.vel[top_idx, 2] *= 0.3
            self.vel[top_idx, 0] += self.wind[0] * dt
            self.vel[top_idx, 1] += self.wind[1] * dt

        # Integrate
        self.pos[live] += self.vel[live] * dt

    # ------------------------------------------------------------------
    def update_appearance(self):
        live = self.alive
        if not live.any():
            return
        z_rel = np.clip(self.pos[live, 2] - self.vent_pos[2], 0.0,
                        self.plume_height)
        frac = z_rel / max(self.plume_height, 1.0)         # 0 vent -> 1 top
        life_frac = np.clip(self.age[live] / self.lifetime[live], 0, 1)

        # Colour ramp: hot orange -> dark ash grey -> pale grey
        r = np.where(frac < 0.15, 1.0, 0.45 - 0.1 * frac)
        g = np.where(frac < 0.15, 0.5, 0.43 - 0.05 * frac)
        b = np.where(frac < 0.15, 0.12, 0.42)
        a = (1.0 - life_frac) * np.where(frac < 0.15, 0.95, 0.55)
        self.color[live, 0] = r
        self.color[live, 1] = g
        self.color[live, 2] = b
        self.color[live, 3] = a
