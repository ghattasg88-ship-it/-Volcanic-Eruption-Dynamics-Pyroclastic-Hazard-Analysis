"""
particle_system.py
==================
A lightweight, high-throughput particle renderer built directly on
Panda3D procedural geometry (GeomPoints with per-vertex colour).

Rather than instancing thousands of NodePaths (slow), we maintain a single
dynamic GeomVertexData and rewrite vertex positions / colours each frame
from NumPy arrays.  Subclasses implement the physics in `update_physics`.

This demonstrates:
  * procedural geometry creation (GeomVertexFormat / GeomVertexData)
  * dynamic per-frame vertex streaming (Geom.UHDynamic)
  * render-state control (point size, additive blending, depth write)
  * NumPy-backed simulation state decoupled from the scene graph
"""

import numpy as np
from panda3d.core import (
    Geom, GeomNode, GeomPoints, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, GeomVertexRewriter, GeomEnums,
    RenderModeAttrib, ColorBlendAttrib, DepthWriteAttrib,
    NodePath, LColor, Vec3, TransparencyAttrib,
)


class ParticleSystem:
    """Base class managing a pool of point particles."""

    def __init__(self, render_root, max_particles, point_size=6.0,
                 additive=False, name="particles"):
        self.max_particles = int(max_particles)
        self.name = name

        # ---- simulation state (NumPy) ----
        self.pos = np.zeros((self.max_particles, 3), dtype=np.float32)
        self.vel = np.zeros((self.max_particles, 3), dtype=np.float32)
        self.color = np.zeros((self.max_particles, 4), dtype=np.float32)
        self.age = np.zeros(self.max_particles, dtype=np.float32)
        self.lifetime = np.ones(self.max_particles, dtype=np.float32)
        self.size = np.full(self.max_particles, 1.0, dtype=np.float32)
        self.alive = np.zeros(self.max_particles, dtype=bool)
        self._cursor = 0

        # ---- Panda3D geometry ----
        fmt = GeomVertexFormat.getV3c4()
        self.vdata = GeomVertexData(name, fmt, Geom.UHDynamic)
        self.vdata.setNumRows(self.max_particles)

        self.prim = GeomPoints(Geom.UHDynamic)
        self.prim.addNextVertices(self.max_particles)

        self.geom = Geom(self.vdata)
        self.geom.addPrimitive(self.prim)
        self.gnode = GeomNode(name)
        self.gnode.addGeom(self.geom)

        self.np = render_root.attachNewNode(self.gnode)
        self.np.setRenderModeThickness(point_size)
        self.np.setTransparency(TransparencyAttrib.MAlpha)
        self.np.setBin("fixed", 0)
        self.np.setDepthWrite(False)
        if additive:
            self.np.setAttrib(ColorBlendAttrib.make(
                ColorBlendAttrib.MAdd,
                ColorBlendAttrib.OIncomingAlpha,
                ColorBlendAttrib.OOne))

        # Pre-build writers reused each frame
        self._initial_fill()

    # ------------------------------------------------------------------
    def _initial_fill(self):
        """Park every particle far below the scene initially."""
        self.pos[:] = (0.0, 0.0, -1.0e6)
        self._write_to_geom()

    # ------------------------------------------------------------------
    def emit(self, position, velocity, color, lifetime, size=1.0):
        """Spawn one particle, recycling the oldest slot (ring buffer)."""
        i = self._cursor
        self.pos[i] = position
        self.vel[i] = velocity
        self.color[i] = color
        self.age[i] = 0.0
        self.lifetime[i] = max(lifetime, 1e-3)
        self.size[i] = size
        self.alive[i] = True
        self._cursor = (self._cursor + 1) % self.max_particles

    def emit_burst(self, n, position, vel_func, color_func,
                   lifetime_func, size_func):
        """Emit n particles using callables for randomised attributes."""
        for _ in range(int(n)):
            self.emit(position, vel_func(), color_func(),
                      lifetime_func(), size_func())

    # ------------------------------------------------------------------
    def update(self, dt):
        """Advance ages, cull dead particles, run physics, push to GPU."""
        live = self.alive
        if not live.any():
            return
        self.age[live] += dt
        # Kill expired
        expired = live & (self.age >= self.lifetime)
        if expired.any():
            self.alive[expired] = False
            self.pos[expired] = (0.0, 0.0, -1.0e6)

        self.update_physics(dt)
        self.update_appearance()
        self._write_to_geom()

    # ------------------------------------------------------------------
    def update_physics(self, dt):
        """Override in subclass. Default: ballistic + gravity-free drift."""
        live = self.alive
        self.pos[live] += self.vel[live] * dt

    def update_appearance(self):
        """Override to fade/colour-shift particles over their lifetime."""
        pass

    # ------------------------------------------------------------------
    def _write_to_geom(self):
        """Stream NumPy state into the GeomVertexData (vertex + colour)."""
        vwriter = GeomVertexWriter(self.vdata, "vertex")
        cwriter = GeomVertexWriter(self.vdata, "color")
        p = self.pos
        c = self.color
        for i in range(self.max_particles):
            vwriter.setData3f(float(p[i, 0]), float(p[i, 1]), float(p[i, 2]))
            cwriter.setData4f(float(c[i, 0]), float(c[i, 1]),
                              float(c[i, 2]), float(c[i, 3]))

    # ------------------------------------------------------------------
    @property
    def num_alive(self):
        return int(self.alive.sum())

    def destroy(self):
        self.np.removeNode()
