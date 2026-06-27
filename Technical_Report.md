# Technical Report — Volcanic Eruption Dynamics & Pyroclastic Hazard Analysis

**Author:** ghattasg88
**Engine:** Panda3D 1.10 (Python real-time 3D)
**Language:** Python 3.10+
**Date:** 2026

---

## 1. Purpose

This project is an interactive, physics-based 3D simulation of an explosive
volcanic eruption, built in the Panda3D game/visualization engine. It models
the four hazardous phenomena of a Plinian eruption and projects their reach
onto a procedural stratovolcano as quantitative hazard zones:

1. **Eruption column** (buoyant Plinian plume + umbrella cloud)
2. **Pyroclastic density currents (PDCs)** — the primary lethal hazard
3. **Ballistic ejecta** — proximal block-and-bomb fallout
4. **Ashfall (tephra dispersal)** — distal, wind-controlled fallout

The goal is twofold: (a) demonstrate real-time 3D engineering in Panda3D —
procedural geometry, dynamic particle systems, scene-graph management, custom
camera and HUD — and (b) ground every visual in published volcanological
models so the output is a defensible hazard-analysis tool rather than a
purely aesthetic effect.

---

## 2. System Architecture

```
main.py
  └── src/app.py  (VolcanoApp : ShowBase)
        ├── terrain.py            VolcanoTerrain   - procedural DEM mesh + sampler
        ├── eruption_column.py    EruptionColumn   - buoyant plume particle system
        ├── pyroclastic_flow.py   PyroclasticFlow  - terrain-coupled PDC system
        ├── ballistics.py         BallisticEjecta  - drag-decelerated projectiles
        ├── ashfall.py            AshFall          - wind-advected tephra + loading grid
        ├── particle_system.py    ParticleSystem   - GeomPoints GPU particle base class
        ├── camera_controller.py  OrbitCamera      - orbit/zoom/preset rig
        ├── hud.py                HUD              - telemetry + controls overlay
        ├── hazard_zones.py       HazardZones      - energy-cone hazard rings
        └── physics.py            (stateless volcanology models & constants)
```

The simulation state lives in NumPy arrays inside each particle system;
Panda3D is used for rendering, scene graph, input, and the task loop. This
separation keeps the physics testable headlessly (see `tests/`) and the
render path efficient.

---

## 3. Physical Models

All models are drawn from the volcanology literature (full citations in
`docs/Physics_Methodology.md`). Summary:

| Phenomenon | Model | Key reference |
|---|---|---|
| Plume height ↔ mass eruption rate | `H = 2.00 · MER^0.241` | Mastin et al. (2009) |
| Plume rise (jet → convective) | 1-D buoyant plume velocity profile | Sparks et al. (1997) |
| PDC runout | Energy-cone / Heim coefficient `L = H_c / (H/L)` | Malin & Sheridan (1982) |
| PDC front velocity | Coulomb granular slope balance | Branney & Kokelaar (2002) |
| Ballistic flight | Projectile + quadratic aerodynamic drag | Standard ballistics |
| Ash settling | Stokes / turbulent terminal velocity by Reynolds regime | Bonadonna et al. (1998) |
| Hazard zonation | Energy-cone inundation rings | Sheridan & Malin (1983) |

### 3.1 Validation of physical outputs

Verified numerically (`tests/test_physics.py`):

- Plume-height ↔ MER inversion round-trips to < 0.01 km across VEI 2–6.
- VEI 4 default (collapse height 2200 m, Heim 0.24) → PDC max runout 9.2 km,
  consistent with documented VEI 4–5 PDC runouts (5–15 km).
- Ballistic blocks (0.15–0.8 m) launched at 320 m/s land at 0.1–2.5 km,
  matching observed proximal ballistic fields.
- Fine ash (0.03–2 mm) settling velocities fall in the 0.1–5 m/s range
  expected from Stokes/turbulent theory.

---

## 4. Panda3D Engineering Detail

### 4.1 Particle system (`particle_system.py`)

Thousands of particles are rendered through a **single** `GeomNode` using
`GeomPoints` with a dynamic `GeomVertexData` (`Geom.UHDynamic`). Per frame,
NumPy position/colour arrays are streamed into the vertex buffer. This avoids
the cost of one `NodePath` per particle (which would not scale past a few
hundred). Render state controls point thickness, alpha transparency, depth
write, and optional additive blending for incandescent effects.

### 4.2 Terrain (`terrain.py`)

The stratovolcano is generated as a NumPy heightfield (Gaussian cone +
summit crater + radial drainage valleys + multi-octave roughness) and
converted to a lit, hypsometrically-tinted `Geom` mesh with per-vertex
normals from central differences. A bilinear `sample(x, y)` method gives the
other systems fast ground-height lookups for terrain coupling.

### 4.3 Terrain coupling

The PDC, ballistic and ashfall systems all query `terrain.sample()` each
frame: PDCs ride the surface and follow `-∇h` downslope, ballistics test for
ground impact, and ash deposits onto a loading grid at its landing cell. This
is what turns a particle effect into a hazard model — the flows respect the
real topography.

### 4.4 Application loop

`VolcanoApp` (a `ShowBase` subclass) drives a staged eruption through five
phases advanced with SPACE. A single `taskMgr` task steps every active
system with a clamped `dt`, seeds ashfall from the umbrella region during the
sustained phases, and updates the HUD telemetry.

---

## 5. Eruption Phases

| Phase | Name | Behaviour |
|---|---|---|
| 0 | PRE-ERUPTION | Quiescent edifice, no emission |
| 1 | VENT OPENING | Ballistic ejecta burst + gas-thrust jet |
| 2 | PLINIAN COLUMN | Sustained convective column + umbrella + ashfall |
| 3 | COLUMN COLLAPSE | Pyroclastic density currents sweep the flanks |
| 4 | WANING | Emission tapers; deposits and hazard zones remain |

---

## 6. Hazard Outputs

- **PDC inundation rings** (`hazard_zones.py`) — energy-cone zones at 45 %,
  75 % and 100 % of maximum credible runout, draped on the terrain.
- **Ballistic fallout zone** — proximal ring from observed impact range.
- **Ashfall loading grid** (`ashfall.loading`) — accumulated ground mass
  (kg/m²) on a 64×64 grid, the basis for an isopach (equal-thickness) map.

These are the standard products a volcanic hazard assessment delivers, here
generated dynamically from the simulated event.

---

## 7. Limitations & Future Work

1. **PDC model is depth-averaged & kinematic**, not a full two-phase
   Navier–Stokes solver (e.g. TITAN2D, VolcFlow). It captures runout and
   topographic steering, not internal turbulence or sedimentation.
2. **Ash dispersal uses a single mean wind**; a real assessment would use a
   layered wind profile and a model such as Ash3d or FALL3D.
3. **No DEM import yet** — terrain is procedural. A GeoTIFF DEM loader
   (rasterio) is the natural next step to target a specific real volcano.
4. **Single vent**; fissure eruptions and dome collapse are not modelled.

---

## 8. Reproducibility

```bash
pip install -r requirements.txt
python main.py                                    # default VEI 4 scenario
python main.py --scenario data/scenario_pinatubo91.json
python -m pytest tests/                           # headless physics + system tests
python scripts/generate_terrain.py --resolution 256   # export heightfield
```

Tested on Panda3D 1.10.16, Python 3.11, NumPy 1.26.

---

**ghattasg88** — Volcanic Eruption Dynamics & Pyroclastic Hazard Analysis
