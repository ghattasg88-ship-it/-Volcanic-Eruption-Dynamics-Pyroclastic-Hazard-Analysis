# User Guide

## Installation

```bash
git clone https://github.com/ghattasg88-ship-it/Volcanic-Eruption-Dynamics-Pyroclastic-Hazard-Analysis.git
cd Volcanic-Eruption-Dynamics-Pyroclastic-Hazard-Analysis
pip install -r requirements.txt
```

Requires Python 3.10+ and a GPU/driver supporting OpenGL (any modern machine).

## Running

```bash
python main.py                                   # default VEI 4 Plinian scenario
python main.py --scenario data/scenario_vesuvius79.json
python main.py --scenario data/scenario_pinatubo91.json
python main.py --scenario data/scenario_stromboli.json
```

## Controls

| Key / Input | Action |
|---|---|
| **SPACE** | Start, then advance through eruption phases |
| **R** | Reset the simulation to pre-eruption |
| **H** | Toggle the hazard-zone overlay |
| **1** | Camera preset: summit close-up |
| **2** | Camera preset: distal (town) viewpoint |
| **3** | Camera preset: side profile |
| **4** | Camera preset: top-down hazard map view |
| **Mouse drag** | Orbit the camera |
| **Mouse wheel** | Zoom in / out |
| **ESC** | Quit |

## Eruption Phases

Press SPACE to walk through the eruption:

1. **PRE-ERUPTION** — quiescent volcano. Orbit around to inspect the edifice.
2. **VENT OPENING** — a burst of glowing ballistic blocks is thrown from the vent.
3. **PLINIAN COLUMN** — a sustained eruption column rises, broadens into an
   umbrella cloud, and begins shedding ash downwind. Try camera preset **3**
   to see the full column profile.
4. **COLUMN COLLAPSE** — the column collapses and pyroclastic density currents
   sweep down the flanks, channelled by the valleys. Press **H** and use
   preset **4** (top-down) to compare the flows against the hazard rings.
5. **WANING** — emission tapers off; deposits and hazard zones remain.

## Reading the Hazard Zones (press H)

| Ring colour | Meaning |
|---|---|
| Red | Zone 1 — high PDC inundation probability |
| Orange | Zone 2 — moderate PDC reach |
| Yellow | Zone 3 — maximum credible PDC runout |
| Purple | Zone 4 — proximal ballistic fallout |

## Creating Your Own Scenario

Copy any file in `data/` and edit the parameters:

```json
{
  "name": "My volcano",
  "vei": 5,
  "plume_height_km": 30.0,
  "vent_velocity": 300.0,
  "vent_radius": 100.0,
  "heim_coefficient": 0.22,
  "collapse_height": 2400.0,
  "wind": [15.0, 0.0, 0.0]
}
```

- **Lower `heim_coefficient`** → longer, more dangerous PDC runout.
- **Higher `plume_height_km`** → taller column, wider ashfall.
- **Change `wind`** → steer the ash plume in a different direction.

## Headless / Testing

Run the physics and system tests without opening a window:

```bash
python -m pytest tests/ -v
```

Export the procedural terrain as a heightmap (no Panda3D needed):

```bash
python scripts/generate_terrain.py --out data/terrain --resolution 256
```
