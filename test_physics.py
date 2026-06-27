"""
test_physics.py
==============
Unit tests for the volcanological physics models. These run headlessly
(no Panda3D window) and validate that the implemented relations reproduce
known volcanological values and round-trip correctly.

Run:  python -m pytest tests/ -v
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import physics as p


# ----------------------------------------------------------------------
# Atmosphere
# ----------------------------------------------------------------------
def test_air_density_sea_level():
    assert abs(p.air_density(0) - p.AIR_DENSITY_SEA) < 1e-6


def test_air_density_decreases_with_altitude():
    assert p.air_density(10000) < p.air_density(0)
    # ~0.38 kg/m3 at 10 km from exponential model
    assert 0.30 < p.air_density(10000) < 0.45


# ----------------------------------------------------------------------
# Plume height <-> mass eruption rate (Mastin 2009)
# ----------------------------------------------------------------------
def test_plume_mer_roundtrip():
    for h_km in (2.0, 5.0, 15.0, 25.0, 35.0):
        mer = p.mass_eruption_rate_from_height(h_km)
        h_back = p.plume_height_from_mer(mer)
        assert abs(h_back - h_km) < 0.01, f"round-trip failed at {h_km} km"


def test_mer_increases_with_height():
    assert (p.mass_eruption_rate_from_height(30) >
            p.mass_eruption_rate_from_height(10))


def test_plume_height_realistic():
    # A VEI 4-5 MER (~1e4-1e5 kg/s) should give ~20-35 km plumes
    h = p.plume_height_from_mer(5.0e4)
    assert 20.0 < h < 35.0


# ----------------------------------------------------------------------
# PDC energy cone (Malin & Sheridan 1982)
# ----------------------------------------------------------------------
def test_energy_cone_runout():
    # 2000 m collapse, Heim 0.25 -> 8 km runout
    assert abs(p.energy_cone_runout(2000, 0.25) - 8000) < 1e-6


def test_lower_heim_gives_longer_runout():
    assert (p.energy_cone_runout(2000, 0.15) >
            p.energy_cone_runout(2000, 0.30))


def test_pdc_runout_in_documented_range():
    # VEI 4-6 PDCs documented at 5-16 km; our scenarios should land there
    for hc, heim in [(2200, 0.24), (2600, 0.21), (3000, 0.19)]:
        L = p.energy_cone_runout(hc, heim)
        assert 5000 < L < 18000


# ----------------------------------------------------------------------
# PDC front velocity
# ----------------------------------------------------------------------
def test_pdc_velocity_zero_on_flat():
    # On near-flat ground below the friction angle, no driving -> ~0
    assert p.pdc_front_velocity(2.0) == 0.0


def test_pdc_velocity_increases_with_slope():
    assert p.pdc_front_velocity(35) > p.pdc_front_velocity(15)


def test_pdc_velocity_capped():
    # Even on very steep slopes the model caps at physical PDC speeds
    assert p.pdc_front_velocity(60) <= 120.0


# ----------------------------------------------------------------------
# Ballistic drag
# ----------------------------------------------------------------------
def test_drag_opposes_motion():
    import numpy as np
    v = np.array([100.0, 0.0, 0.0])
    a = p.drag_acceleration(v, 0.0, 0.3)
    assert a[0] < 0  # drag points opposite to velocity


def test_drag_zero_at_rest():
    import numpy as np
    a = p.drag_acceleration(np.zeros(3), 0.0, 0.3)
    assert all(abs(x) < 1e-9 for x in a)


def test_larger_clast_less_decelerated():
    import numpy as np
    v = np.array([100.0, 0.0, 0.0])
    small = abs(p.drag_acceleration(v, 0, 0.1)[0])
    large = abs(p.drag_acceleration(v, 0, 0.8)[0])
    assert large < small  # bigger blocks have more inertia per area


# ----------------------------------------------------------------------
# Ash settling
# ----------------------------------------------------------------------
def test_settling_increases_with_diameter():
    assert (p.terminal_settling_velocity(1e-3, 5000) >
            p.terminal_settling_velocity(1e-4, 5000))


def test_settling_velocity_physical_range():
    # Fine ash to lapilli: ~0.1 to a few m/s
    v_fine = p.terminal_settling_velocity(5e-5, 5000)
    v_coarse = p.terminal_settling_velocity(2e-3, 5000)
    assert 0.0 < v_fine < 2.0
    assert 1.0 < v_coarse < 20.0


# ----------------------------------------------------------------------
# VEI table
# ----------------------------------------------------------------------
def test_vei_table_monotonic_volume():
    vols = [p.VEI_TABLE[i][0] for i in range(0, 8)]
    assert all(vols[i] < vols[i + 1] for i in range(len(vols) - 1))


def test_vei_table_has_classifications():
    for i in range(0, 8):
        assert isinstance(p.VEI_TABLE[i][2], str)
        assert len(p.VEI_TABLE[i][2]) > 0
