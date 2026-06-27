"""
terrain.py
==========
Procedural volcanic edifice terrain: a stratovolcano cone with a summit
crater, secondary ridges and valleys (radial drainage), rendered as a
Panda3D mesh from a NumPy heightfield. Provides a fast height sampler used
by the pyroclastic-flow, ballistic and ashfall modules for ground coupling.
"""

import numpy as np
from panda3d.core import (
    Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, Vec3, LColor,
)


class VolcanoTerrain:
    def __init__(self, render_root, size=20000.0, resolution=180,
                 summit_height=2800.0, crater_radius=400.0):
        self.size = size                  # full width [m]
        self.res = resolution
        self.summit = summit_height
        self.crater_radius = crater_radius
        self.half = size / 2.0
        self.cell = size / (resolution - 1)

        self.heights = self._build_heightfield()
        self.np = render_root.attachNewNode(self._build_mesh())
        self.np.setTwoSided(True)

    # ------------------------------------------------------------------
    def _build_heightfield(self):
        res = self.res
        xs = np.linspace(-self.half, self.half, res)
        ys = np.linspace(-self.half, self.half, res)
        X, Y = np.meshgrid(xs, ys)
        R = np.sqrt(X ** 2 + Y ** 2)

        # Base stratovolcano cone: tall near centre, tapering to plain
        cone = self.summit * np.exp(-(R / (self.half * 0.42)) ** 2)

        # Summit crater: depress the very centre
        crater = np.where(R < self.crater_radius,
                          -0.35 * self.summit *
                          (1 - (R / self.crater_radius) ** 2),
                          0.0)

        # Radial drainage valleys (barrancas) - common PDC channels
        theta = np.arctan2(Y, X)
        valleys = 90.0 * np.sin(8 * theta) * np.exp(-(R / (self.half * 0.5)) ** 2)

        # Low-frequency terrain roughness
        rough = (60.0 * np.sin(X / 1500.0) * np.cos(Y / 1700.0) +
                 30.0 * np.sin(X / 600.0 + 1.3) * np.cos(Y / 550.0))

        h = cone + crater + valleys + rough * (R / self.half)
        return h.astype(np.float32)

    # ------------------------------------------------------------------
    def sample(self, x, y):
        """Bilinear height lookup at world (x, y)."""
        fx = (x + self.half) / self.cell
        fy = (y + self.half) / self.cell
        ix = int(np.clip(fx, 0, self.res - 2))
        iy = int(np.clip(fy, 0, self.res - 2))
        tx = np.clip(fx - ix, 0, 1)
        ty = np.clip(fy - iy, 0, 1)
        h = self.heights
        h00 = h[iy, ix]
        h10 = h[iy, ix + 1]
        h01 = h[iy + 1, ix]
        h11 = h[iy + 1, ix + 1]
        return float((h00 * (1 - tx) + h10 * tx) * (1 - ty) +
                     (h01 * (1 - tx) + h11 * tx) * ty)

    # ------------------------------------------------------------------
    def summit_pos(self):
        return Vec3(0.0, 0.0, self.sample(0.0, 0.0))

    # ------------------------------------------------------------------
    def _color_for_height(self, h):
        """Hypsometric tint: green lowland -> brown flank -> grey -> snow."""
        t = np.clip(h / self.summit, 0, 1)
        if t < 0.25:
            return (0.20, 0.42, 0.18)          # vegetated lowland
        elif t < 0.55:
            return (0.40, 0.32, 0.20)          # forested/soil flank
        elif t < 0.80:
            return (0.42, 0.40, 0.38)          # bare rock / older deposits
        else:
            return (0.80, 0.80, 0.82)          # summit ash/snow

    # ------------------------------------------------------------------
    def _build_mesh(self):
        res = self.res
        fmt = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData("terrain", fmt, Geom.UHStatic)
        vdata.setNumRows(res * res)
        vw = GeomVertexWriter(vdata, "vertex")
        nw = GeomVertexWriter(vdata, "normal")
        cw = GeomVertexWriter(vdata, "color")

        xs = np.linspace(-self.half, self.half, res)
        ys = np.linspace(-self.half, self.half, res)
        h = self.heights

        # Vertex normals via central differences
        gy, gx = np.gradient(h, self.cell)
        for j in range(res):
            for i in range(res):
                z = h[j, i]
                vw.setData3f(xs[i], ys[j], z)
                n = Vec3(-gx[j, i], -gy[j, i], 1.0)
                n.normalize()
                nw.setData3f(n)
                c = self._color_for_height(z)
                cw.setData4f(c[0], c[1], c[2], 1.0)

        tris = GeomTriangles(Geom.UHStatic)
        for j in range(res - 1):
            for i in range(res - 1):
                v0 = j * res + i
                v1 = v0 + 1
                v2 = v0 + res
                v3 = v2 + 1
                tris.addVertices(v0, v2, v1)
                tris.addVertices(v1, v2, v3)

        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode("volcano_terrain")
        node.addGeom(geom)
        return node
