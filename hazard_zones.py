"""
hazard_zones.py
==============
Hazard zonation overlay: concentric energy-cone hazard rings projected onto
the terrain, classifying ground into PDC-inundation, ballistic-fallout and
ashfall zones. Toggleable from the HUD. Rings are drawn as terrain-draped
line loops so they follow topography.
"""

import math

import numpy as np
from panda3d.core import (
    Geom, GeomLinestrips, GeomNode, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, LColor,
)


class HazardZones:
    # (label, runout_fraction_of_max, RGBA)
    ZONE_DEFS = [
        ("Zone 1 - PDC inundation (high)", 0.45, (0.85, 0.10, 0.10, 1.0)),
        ("Zone 2 - PDC reach (moderate)", 0.75, (0.95, 0.55, 0.10, 1.0)),
        ("Zone 3 - Max credible PDC", 1.00, (0.95, 0.85, 0.20, 1.0)),
        ("Zone 4 - Ballistic fallout", 0.18, (0.60, 0.10, 0.70, 1.0)),
    ]

    def __init__(self, render_root, terrain, max_runout, vent_xy=(0.0, 0.0)):
        self.terrain = terrain
        self.max_runout = max_runout
        self.vent = vent_xy
        self.root = render_root.attachNewNode("hazard_zones")
        self._build()
        self.root.hide()
        self.visible = False

    # ------------------------------------------------------------------
    def _ring_node(self, radius, color, segments=160):
        fmt = GeomVertexFormat.getV3c4()
        vdata = GeomVertexData("ring", fmt, Geom.UHStatic)
        vdata.setNumRows(segments + 1)
        vw = GeomVertexWriter(vdata, "vertex")
        cw = GeomVertexWriter(vdata, "color")
        for s in range(segments + 1):
            ang = 2 * math.pi * s / segments
            x = self.vent[0] + radius * math.cos(ang)
            y = self.vent[1] + radius * math.sin(ang)
            z = self.terrain.sample(x, y) + 30.0   # float above ground
            vw.setData3f(x, y, z)
            cw.setData4f(*color)
        strip = GeomLinestrips(Geom.UHStatic)
        strip.addConsecutiveVertices(0, segments + 1)
        strip.closePrimitive()
        geom = Geom(vdata)
        geom.addPrimitive(strip)
        node = GeomNode("ring")
        node.addGeom(geom)
        return node

    # ------------------------------------------------------------------
    def _build(self):
        for label, frac, color in self.ZONE_DEFS:
            radius = self.max_runout * frac
            np_ring = self.root.attachNewNode(
                self._ring_node(radius, color))
            np_ring.setRenderModeThickness(3.0)
            np_ring.setLightOff()

    # ------------------------------------------------------------------
    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self.root.show()
        else:
            self.root.hide()
