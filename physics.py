"""
physics.py
==========
Volcanological physics models and constants used across the simulation.

References
----------
- Mastin, L.G. et al. (2009). "A multidisciplinary effort to assign realistic
  source parameters to models of volcanic ash-cloud transport and dispersion."
  J. Volcanol. Geotherm. Res. 186, 10-21.   -> plume height <-> mass eruption rate
- Sparks, R.S.J. et al. (1997). "Volcanic Plumes." Wiley.
- Malin, M.C. & Sheridan, M.F. (1982). "Computer-assisted mapping of
  pyroclastic surges." Science 217, 637-640.  -> energy-cone runout model
- Newhall, C.G. & Self, S. (1982). "The Volcanic Explosivity Index (VEI)."
  J. Geophys. Res. 87, 1231-1238.

All SI units unless noted. Distances in metres, time in seconds, mass in kg.
"""

import math

import numpy as np

# ----------------------------------------------------------------------
# Physical constants
# ----------------------------------------------------------------------
GRAVITY = 9.81                  # m/s^2
AIR_DENSITY_SEA = 1.225         # kg/m^3 at sea level
SCALE_HEIGHT = 8500.0           # atmospheric scale height [m]
R_AIR = 287.05                  # specific gas constant for dry air [J/(kg K)]
TEMP_LAPSE = 0.0065             # K/m, environmental lapse rate

# Tephra / clast properties
ROCK_DENSITY = 2500.0           # kg/m^3 (dense rock equivalent)
PUMICE_DENSITY = 1000.0         # kg/m^3 (vesiculated pumice)
ASH_DENSITY = 1200.0            # kg/m^3 (fine ash particle)


def air_density(altitude_m):
    """Exponential atmosphere density approximation."""
    return AIR_DENSITY_SEA * math.exp(-max(altitude_m, 0.0) / SCALE_HEIGHT)


# ----------------------------------------------------------------------
# Volcanic Explosivity Index (VEI) reference table
# ----------------------------------------------------------------------
# (erupted_volume_m3, typical_plume_height_km, classification)
VEI_TABLE = {
    0: (1.0e4, 0.1, "Effusive (Hawaiian)"),
    1: (1.0e6, 1.0, "Gentle (Hawaiian/Strombolian)"),
    2: (1.0e7, 5.0, "Explosive (Strombolian/Vulcanian)"),
    3: (1.0e8, 15.0, "Severe (Vulcanian/Pelean)"),
    4: (1.0e9, 25.0, "Cataclysmic (Plinian)"),
    5: (1.0e10, 35.0, "Paroxysmal (Plinian)"),
    6: (1.0e11, 40.0, "Colossal (Plinian/Ultra-Plinian)"),
    7: (1.0e12, 45.0, "Super-colossal (Ultra-Plinian)"),
}


def mass_eruption_rate_from_height(plume_height_km):
    """
    Invert the Mastin et al. (2009) empirical relation:
        H = 2.00 * MER^0.241          (H in km, MER in kg/s)
    =>  MER = (H / 2.00)^(1/0.241)
    """
    return (plume_height_km / 2.00) ** (1.0 / 0.241)


def plume_height_from_mer(mer_kg_s):
    """Mastin et al. (2009) plume height [km] from mass eruption rate [kg/s]."""
    return 2.00 * (mer_kg_s ** 0.241)


# ----------------------------------------------------------------------
# Eruption column (buoyant plume) dynamics
# ----------------------------------------------------------------------
class PlumeModel:
    """
    Simplified 1-D buoyant plume: a jet phase (gas-thrust, momentum driven)
    transitioning to a convective phase (buoyancy driven), capping at a
    neutral buoyancy / umbrella level near the empirical plume height.
    """

    def __init__(self, vent_velocity, vent_radius, plume_height_km):
        self.vent_velocity = vent_velocity          # m/s
        self.vent_radius = vent_radius              # m
        self.plume_height = plume_height_km * 1000  # m
        # Gas-thrust region typically ~ a few vent radii tall
        self.gas_thrust_top = max(8.0 * vent_radius, 200.0)

    def vertical_velocity(self, z):
        """Upward velocity [m/s] as a function of height z above vent."""
        if z < self.gas_thrust_top:
            # Momentum jet decelerating roughly linearly
            frac = z / self.gas_thrust_top
            return self.vent_velocity * (1.0 - 0.6 * frac)
        # Convective region: velocity decays toward umbrella level
        remaining = max(self.plume_height - z, 0.0)
        return 40.0 * (remaining / self.plume_height) ** 0.5

    def radius(self, z):
        """Plume radius [m] grows with height (entrainment, ~0.1 z)."""
        return self.vent_radius + 0.10 * z


# ----------------------------------------------------------------------
# Pyroclastic density current (PDC) - energy cone runout
# ----------------------------------------------------------------------
def energy_cone_runout(collapse_height_m, heim_coefficient=0.25):
    """
    Malin & Sheridan (1982) energy-cone model.

    A pyroclastic flow runs out until the "energy line" (slope = H/L)
    intersects the topography.  For flat ground the maximum runout L is:

        L = collapse_height / Heim_coefficient

    Heim coefficient (H/L) ranges ~0.1 (very mobile) to ~0.4 (less mobile).
    Typical PDCs: 0.2-0.3.
    """
    return collapse_height_m / heim_coefficient


def pdc_front_velocity(slope_deg, friction_coeff=0.11):
    """
    Approximate steady PDC front velocity on a slope from a simple
    Coulomb-friction granular balance:

        v ~ sqrt(2 g d (sin theta - mu cos theta))   (per unit drop d=50 m used)
    Returns a representative speed [m/s], clamped to physical bounds.
    """
    theta = math.radians(slope_deg)
    drop = 50.0
    drive = math.sin(theta) - friction_coeff * math.cos(theta)
    if drive <= 0:
        return 0.0
    v = math.sqrt(2.0 * GRAVITY * drop * drive)
    return float(np.clip(v, 0.0, 120.0))   # PDCs rarely exceed ~100-120 m/s


# ----------------------------------------------------------------------
# Ballistic ejecta
# ----------------------------------------------------------------------
def drag_acceleration(velocity_vec, altitude_m, diameter_m,
                      density=ROCK_DENSITY, drag_coeff=1.0):
    """
    Quadratic aerodynamic drag deceleration vector for a spherical clast.
        a_drag = -0.5 * Cd * rho_air * A * |v| * v / m
    """
    speed = float(np.linalg.norm(velocity_vec))
    if speed < 1e-6:
        return np.zeros(3)
    rho = air_density(altitude_m)
    radius = 0.5 * diameter_m
    area = math.pi * radius ** 2
    mass = density * (4.0 / 3.0) * math.pi * radius ** 3
    mag = 0.5 * drag_coeff * rho * area * speed / mass
    return -mag * velocity_vec


# ----------------------------------------------------------------------
# Tephra / ash settling
# ----------------------------------------------------------------------
def terminal_settling_velocity(diameter_m, altitude_m, density=ASH_DENSITY):
    """
    Terminal fall velocity of a tephra particle.  Uses Stokes' law for
    fine ash (laminar) and a turbulent drag law for coarser clasts,
    selecting whichever regime applies via particle Reynolds number.
    """
    rho_air = air_density(altitude_m)
    mu = 1.8e-5                      # dynamic viscosity of air [Pa s]
    d = diameter_m
    # Stokes (Re < 1)
    v_stokes = (density - rho_air) * GRAVITY * d ** 2 / (18.0 * mu)
    re = rho_air * v_stokes * d / mu
    if re < 1.0:
        return v_stokes
    # Turbulent / intermediate: balance gravity with quadratic drag (Cd~1)
    cd = 1.0
    v_turb = math.sqrt(4.0 * (density - rho_air) * GRAVITY * d /
                       (3.0 * cd * rho_air))
    return v_turb
