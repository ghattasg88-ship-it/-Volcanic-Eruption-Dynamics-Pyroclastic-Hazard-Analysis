"""
hud.py
======
On-screen telemetry and controls overlay: eruption phase, VEI, plume
height, live particle counts, and a key-binding legend. Pure Panda3D
OnscreenText / DirectGui — no external assets required.
"""

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode


class HUD:
    def __init__(self, base):
        self.base = base
        self.title = OnscreenText(
            text="Volcanic Eruption Dynamics  -  Pyroclastic Hazard Analysis",
            pos=(-1.30, 0.92), scale=0.052, fg=(1, 0.85, 0.5, 1),
            align=TextNode.ALeft, mayChange=False,
            shadow=(0, 0, 0, 0.7))

        self.telemetry = OnscreenText(
            text="", pos=(-1.30, 0.84), scale=0.045,
            fg=(0.9, 0.95, 1, 1), align=TextNode.ALeft, mayChange=True,
            shadow=(0, 0, 0, 0.7))

        self.phase = OnscreenText(
            text="", pos=(-1.30, 0.74), scale=0.05,
            fg=(1, 0.5, 0.3, 1), align=TextNode.ALeft, mayChange=True,
            shadow=(0, 0, 0, 0.7))

        legend = (
            "[SPACE] start/advance eruption phase    "
            "[R] reset\n"
            "[1] summit  [2] distal  [3] profile  [4] top-down\n"
            "[H] toggle hazard zones   [drag] orbit   [wheel] zoom   [ESC] quit"
        )
        self.legend = OnscreenText(
            text=legend, pos=(-1.30, -0.86), scale=0.040,
            fg=(0.8, 0.85, 0.9, 1), align=TextNode.ALeft, mayChange=False,
            shadow=(0, 0, 0, 0.7))

    # ------------------------------------------------------------------
    def set_phase(self, name):
        self.phase.setText(f"PHASE: {name}")

    def set_telemetry(self, vei, plume_km, sim_time,
                      n_column, n_pdc, n_ball, n_ash):
        self.telemetry.setText(
            f"VEI {vei}   Plume {plume_km:4.1f} km   t = {sim_time:6.1f} s\n"
            f"Column {n_column:5d}   PDC {n_pdc:5d}   "
            f"Ballistics {n_ball:4d}   Ash {n_ash:5d}")
