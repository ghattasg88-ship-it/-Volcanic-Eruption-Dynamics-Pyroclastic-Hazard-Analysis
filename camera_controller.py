"""
camera_controller.py
====================
Orbit + zoom camera rig for inspecting the eruption. Mouse drag orbits,
wheel zooms, and number keys jump to preset vantage points (summit,
distal town, profile, top-down hazard view).
"""

import math

from panda3d.core import Vec3, Point3


class OrbitCamera:
    def __init__(self, base, target=Vec3(0, 0, 1500), distance=12000.0):
        self.base = base
        self.target = Vec3(target)
        self.distance = distance
        self.heading = 35.0       # degrees
        self.pitch = 22.0         # degrees above horizontal
        self.min_dist = 1500.0
        self.max_dist = 45000.0

        base.disableMouse()
        self._dragging = False
        self._last = (0, 0)

        self._bind()
        self.update()

    # ------------------------------------------------------------------
    def _bind(self):
        b = self.base
        b.accept("mouse1", self._start_drag)
        b.accept("mouse1-up", self._stop_drag)
        b.accept("wheel_up", self._zoom, [-0.12])
        b.accept("wheel_down", self._zoom, [0.12])
        # Preset views
        b.accept("1", self.preset, ["summit"])
        b.accept("2", self.preset, ["distal"])
        b.accept("3", self.preset, ["profile"])
        b.accept("4", self.preset, ["top"])
        b.taskMgr.add(self._drag_task, "orbit-cam-drag")

    # ------------------------------------------------------------------
    def _start_drag(self):
        self._dragging = True
        if self.base.mouseWatcherNode.hasMouse():
            m = self.base.mouseWatcherNode
            self._last = (m.getMouseX(), m.getMouseY())

    def _stop_drag(self):
        self._dragging = False

    def _zoom(self, factor):
        self.distance = max(self.min_dist,
                            min(self.max_dist, self.distance * (1.0 + factor)))
        self.update()

    def _drag_task(self, task):
        if self._dragging and self.base.mouseWatcherNode.hasMouse():
            m = self.base.mouseWatcherNode
            mx, my = m.getMouseX(), m.getMouseY()
            dx = mx - self._last[0]
            dy = my - self._last[1]
            self.heading -= dx * 90.0
            self.pitch = max(3.0, min(85.0, self.pitch + dy * 60.0))
            self._last = (mx, my)
            self.update()
        return task.cont

    # ------------------------------------------------------------------
    def preset(self, name):
        if name == "summit":
            self.target = Vec3(0, 0, 2600); self.distance = 4500
            self.heading, self.pitch = 30, 18
        elif name == "distal":
            self.target = Vec3(6000, -6000, 200); self.distance = 9000
            self.heading, self.pitch = 60, 10
        elif name == "profile":
            self.target = Vec3(0, 0, 1500); self.distance = 16000
            self.heading, self.pitch = 90, 4
        elif name == "top":
            self.target = Vec3(0, 0, 0); self.distance = 28000
            self.heading, self.pitch = 0, 85
        self.update()

    # ------------------------------------------------------------------
    def update(self):
        h = math.radians(self.heading)
        p = math.radians(self.pitch)
        x = self.distance * math.cos(p) * math.sin(h)
        y = -self.distance * math.cos(p) * math.cos(h)
        z = self.distance * math.sin(p)
        cam_pos = self.target + Vec3(x, y, z)
        self.base.camera.setPos(cam_pos)
        self.base.camera.lookAt(self.target)
