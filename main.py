#!/usr/bin/env python3
"""
Volcanic Eruption Dynamics & Pyroclastic Hazard Analysis
========================================================
Entry point. Launches the interactive Panda3D simulation.

Usage:
    python main.py
    python main.py --scenario data/eruption_scenarios.json
    python main.py --scenario data/scenario_vesuvius79.json

Controls:
    SPACE   start / advance eruption phase
    R       reset simulation
    H       toggle hazard-zone overlay
    1-4     preset camera views (summit / distal / profile / top-down)
    drag    orbit camera     wheel   zoom     ESC   quit
"""

import argparse

from src.app import VolcanoApp


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default=None,
                    help="Path to an eruption scenario JSON file")
    return ap.parse_args()


def main():
    args = parse_args()
    app = VolcanoApp(scenario_path=args.scenario)
    app.run()


if __name__ == "__main__":
    main()
