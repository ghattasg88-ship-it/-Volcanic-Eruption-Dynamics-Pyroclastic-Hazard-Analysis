# Data

Eruption scenario definitions (JSON) consumed by `main.py --scenario`.

| File | Event | VEI | Notes |
|---|---|---|---|
| `eruption_scenarios.json` | Generic reference | 4 | Default scenario |
| `scenario_vesuvius79.json` | Vesuvius AD 79 | 5 | Pompeii/Herculaneum PDCs |
| `scenario_pinatubo91.json` | Pinatubo 1991 | 6 | Highly mobile, voluminous PDCs |
| `scenario_stromboli.json` | Stromboli | 2 | Mild persistent activity |

Each scenario sets plume height, vent conditions, the PDC Heim coefficient,
column-collapse height and the mean wind vector. See `docs/User_Guide.md`
for how to author your own.

`terrain.npy` / `terrain.png` (if present) are exported by
`scripts/generate_terrain.py` and are reproducible artefacts, not required to
run the simulation.
